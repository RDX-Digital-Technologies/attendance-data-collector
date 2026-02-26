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
from scripts.utils.logger import get_logger
from scripts.utils.config import Config
from scripts.utils.discord_error_alert import send_discord_alert

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
config = Config()

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def check_and_insert_employees(records):
    """
    Detect new employees from records and batch-insert them all at once.
    Returns True on success, None on error.
    """
    existing_employees = get_existing_employee_records()

    if existing_employees is None:
        log.error("Failed to fetch existing employee records")
        return None

    existing_employee_ids = {str(emp[0]) for emp in existing_employees}

    # Collect unique new employees in a single pass
    new_employees = {}
    for record in records:
        employee_id = str(record["employee_id"])
        if employee_id not in existing_employee_ids and employee_id not in new_employees:
            new_employees[employee_id] = record.get("employee_name") or f"Employee_{employee_id}"

    if not new_employees:
        log.info("No new employees found.")
        return True

    # Build list of dicts for batch insert
    employee_records = [
        {"employee_id": emp_id, "employee_name": emp_name}
        for emp_id, emp_name in new_employees.items()
    ]

    log.info("Inserting %d new employee(s) in batch...", len(employee_records))
    for r in employee_records:
        log.info("  -> Employee %s - %s", r["employee_id"], r["employee_name"])

    result = insert_employee_data_records(employee_records)   # single batch call
    if result is None:
        log.error("Batch employee insert failed.")
        return None

    log.info("Batch employee insert completed.")
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
            records, device_info = pull_attendance_logs(
                device_ip,
                config.DEVICE_PORT,
                config.TIMEOUT,
                config.COMM_KEY,
                config.FORCE_UDP,
                last_event_timestamp
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

    log.info("=== Collection Complete. Devices processed: %d ===", len(all_results))
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