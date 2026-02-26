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
def check_and_insert_device(device_info):
    """
    Check if device exists in database; insert if not.
    Returns device_key on success, None on error.
    """
    existing_devices = get_device_info()

    if existing_devices is None:
        log.error("Failed to fetch existing device info")
        return None

    # Assume device_key is at index 0, device_ip at index 2
    for device in existing_devices:
        if device[3] == device_info["device_ip"]:
            log.info("Device %s already exists in database.", device_info["device_id"])
            return device[0]  # Return device_key

    log.info("New device found: %s. Inserting into database.", device_info["device_id"])
    insert_device_info_records(device_info)

    # Fetch again to get the new device's key
    updated_devices = get_device_info()
    for device in updated_devices:
        if device[2] == device_info["device_ip"]:
            return device[0]

    log.error("Failed to retrieve device key after insert.")
    return None

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
    try:
        log.info("=== Attendance Data Collection Started ===")

        # Step 1: Pull attendance logs from device
        last_event_timestamp = get_last_fetched_timestamp()
        log.info("Step 1: Pulling attendance logs from device...")
        records, device_info = pull_attendance_logs(
            config.DEVICE_IP, config.DEVICE_PORT,
            config.TIMEOUT, config.COMM_KEY, config.FORCE_UDP, last_event_timestamp
        )
        if records is None and device_info is None:
            log.error("Failed to pull attendance logs from device. Possible network issue.")
            return {}

        if not records:
            log.warning("No records found. Exiting.")
            return {}

        log.info("Pulled %d records from device.", len(records))

        # Step 2: Check and insert device info
        log.info("Step 2: Checking device information...")
        device_key = check_and_insert_device(device_info)
        if device_key is None:
            log.error("Device information check/insert failed. Cannot proceed.")
            return {}
        
        for i in records:
            i["device_key"] = device_key

        # Step 3: Check and batch-insert new employees
        log.info("Step 3: Checking for new employees...")
        if check_and_insert_employees(records) is None:
            log.error("Employee check/insert failed. Cannot proceed.")
            return {}

        # Step 4: Batch-insert attendance records
        log.info("Step 4: Inserting attendance records...")
        inserted, failed = insert_attendance_records(records)

        log.info("=== Attendance Data Collection Completed ===")
        log.info(
            "Summary: %d records processed, %d inserted, %d failed",
            len(records), inserted, failed
        )

        return {
            "total_records": len(records),
            "inserted": inserted,
            "failed": failed,
            "device_info": device_info
        }

    except Exception as e:
        log.exception("Error during attendance data collection: %s", e)
        send_discord_alert(config.DISCORD_WEBHOOK_URL, "Error during attendance data collection", e)
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import time

    curr = time.time()
    result = collect_attendance_data()
    if not result:
        log.error("Attendance data collection have no data or it is failed. Check previous logs for details.")
    else:
        log.info(
            "Attendance data collection completed in %.2f seconds",
            time.time() - curr
        )