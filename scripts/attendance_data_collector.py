from scripts.attendance_log_collector.pull_attendace_logs import pull_attendance_logs
from scripts.db_layer.get_data import (
    get_device_info,
    get_existing_employee_records,
    get_last_fetched_timestamp
)
from scripts.db_layer.insert_data import (
    insert_attendance_log_records,
    insert_device_info_records,
    insert_employee_data_records
)
from scripts.utils.logger import get_logger, configure_logging
from scripts.utils.config import Config
from scripts.utils.discord_error_alert import send_discord_alert

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
config = Config()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
configure_logging(config.LOG_PATH)
log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def check_and_insert_employees(records):
    """
    Detect new employees and batch-insert them.
    Also detect existing employees with mismatched names and update them.
    Returns True on success, None on error.
    """
    existing_employees = get_existing_employee_records()

    if existing_employees is None:
        log.error("Failed to fetch existing employee records")
        return None

    # Create a dict of existing employees: {employee_id: employee_name}
    existing_employee_map = {str(emp[0]): emp[1].strip().lower() for emp in existing_employees}

    # Collect unique new employees and employees with name mismatches
    new_employees = {}
    employees_to_update = {}
    
    for record in records:
        employee_id = str(record["employee_id"])
        employee_name = record.get("employee_name")
        if employee_name is None or employee_name.strip() == "":
            log.error("Record with employee_id %s has no employee_name. Skipping name checks for this record.", employee_id)
            continue
        
        normalized_name = employee_name.strip().lower().replace(' ','')
        
        if employee_id not in existing_employee_map and employee_id not in new_employees:
            # New employee
            new_employees[employee_id] = employee_name
        elif employee_id in existing_employee_map:
            # Check if name mismatch
            existing_name = existing_employee_map[employee_id].lower().strip().replace(' ','')
            if existing_name != normalized_name and employee_id not in employees_to_update:
                employees_to_update[employee_id] = employee_name
                log.info("Name mismatch detected for Employee %s: '%s' -> '%s'", 
                         employee_id, existing_name, employee_name)

    # Insert new employees
    if new_employees:
        employee_records = [
            {"employee_id": emp_id, "employee_name": emp_name}
            for emp_id, emp_name in new_employees.items()
        ]
        log.info("Inserting %d new employee(s) in batch...", len(employee_records))
        for r in employee_records:
            log.info("  -> Employee %s - %s", r["employee_id"], r["employee_name"])
        
        result = insert_employee_data_records(employee_records)
        if result is None:
            log.error("Batch employee insert failed.")
            return None
        log.info("Batch employee insert completed.")

    # Update employees with mismatched names
    if employees_to_update:
        update_records = [
            {"employee_id": emp_id, "employee_name": emp_name}
            for emp_id, emp_name in employees_to_update.items()
        ]
        log.warning("found %d employees with name mismatch...", len(update_records))
        for r in update_records:
            log.warning("  -> Employee %s - %s", r["employee_id"], r["employee_name"])

        log.critical("Employee name mismatches detected. Please review the above log entries and update employee names in the database accordingly to ensure data consistency.")
        send_discord_alert(config.DISCORD_WEBHOOK_URL, "Employee name mismatches detected. Please review the above log entries and update employee names in the database accordingly to ensure data consistency.")
        return None

    if not new_employees and not employees_to_update:
        log.info("No new employees")

    return True

def insert_attendance_records(records, batch_size=1000):
    if not records:
        return 0, 0

    total_inserted = 0
    total_failed = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        result = insert_attendance_log_records(batch)
        if result is None:
            total_failed += len(batch)
        else:
            total_inserted += result
            total_failed += len(batch) - result
    return total_inserted, total_failed


# ---------------------------------------------------------------------------
# Main Collection Function
# ---------------------------------------------------------------------------
def collect_attendance_data():
    """
    Main function to collect attendance data from device and store in database.
    """
    log.info("=== Attendance Data Collection Started ===")
    all_results = {}

    existing_devices = get_device_info()
    if existing_devices is None:
        log.error("Failed to fetch existing device records")
        send_discord_alert(config.DISCORD_WEBHOOK_URL, "Failed to fetch existing device records. Attendance data collection aborted.")
        return {}
    
    for device_cfg in existing_devices:
        device_ip = device_cfg[3]
        device_key = device_cfg[0]
        log.info("--- Processing device: %s ---", device_ip)
        try:
            last_event_timestamp = get_last_fetched_timestamp(device_key)
            if last_event_timestamp is None:
                effective_floor = config.START_DATE
            else:
                effective_floor = max(last_event_timestamp, config.START_DATE)
            records, device_info = pull_attendance_logs(
                device_ip,
                config.DEVICE_PORT,
                config.TIMEOUT,
                config.COMM_KEY,
                config.FORCE_UDP,
                effective_floor
            )

            if records is None and device_info is None:
                log.error("Failed to pull logs from %s. Skipping.", device_ip)
                send_discord_alert(config.DISCORD_WEBHOOK_URL, f"Failed to pull logs from device {device_ip}. Check logs for details.")
                continue 

            if not records:
                log.warning("No new records from %s.", device_ip)
                continue

            if device_key is None:
                log.error("Device key is none for %s. Skipping.", device_ip)
                send_discord_alert(config.DISCORD_WEBHOOK_URL, f"Device key is none for {device_ip}. Check logs for details.")
                continue

            original_count = len(records)
            records = [
                r for r in records
                if r.get("employee_name") and r["employee_name"].strip()
            ]
            dropped = original_count - len(records)
            if dropped:
                log.warning(
                    "Dropped %d record(s) from %s with unknown employee (not in device user list).",
                    dropped, device_ip
                )

            if not records:
                log.warning("No usable records from %s after dropping unknown employees.", device_ip)
                continue

            for r in records:
                r["device_key"] = device_key

            if check_and_insert_employees(records) is None:
                log.error("Employee insert failed for %s. Skipping.", device_ip)
                send_discord_alert(config.DISCORD_WEBHOOK_URL, f"Employee insert failed for {device_ip}. Check logs for details.")
                continue

            inserted, failed = insert_attendance_records(records)
            log.info("Device %s — %d inserted, %d failed", device_ip, inserted, failed)

            all_results[device_ip] = {
                "total_records": len(records),
                "inserted": inserted,
                "failed": failed,
                "device_info": device_info
            }

        except Exception as e:
            log.exception("Error processing device %s: %s", device_ip, e)
            send_discord_alert(config.DISCORD_WEBHOOK_URL,
                               f"Error processing device {device_ip}", e)
            continue 

    log.info("=== Collection Complete. Devices processed: %d ===", len(existing_devices))
    log.info("=== Total data collected and inserted: %d ===", len(all_results))
    return all_results

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import time

    curr = time.time()
    result = collect_attendance_data()
    if not result:
        log.warning("Attendance data collection have no data or it is failed. Check previous logs for details.")
    else:
        log.info(
            "Attendance data collection completed in %.2f seconds",
            time.time() - curr
        )