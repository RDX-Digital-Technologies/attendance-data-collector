from scripts.db_layer.db import DB  
from scripts.utils.logger import get_logger
from scripts.utils.discord_error_alert import send_discord_alert
from scripts.utils.config import Config
from sqlalchemy import text

db_obj = DB()
log = get_logger(__name__)

cred = Config()
def insert_attendance_log_records(records: list[dict]):
    """
    Batch insert a list of attendance log records.
    Each record must be a dict with keys:
      employee_id, punch_method_id, punch_status_id, device_key,
      event_timestamp, pulled_timestamp
    """
    if not records:
        log.warning("No attendance log records to insert.")
        return 0

    try:
        conn = db_obj.get_connect().connect()
        with conn:
            conn.execute(
                text("""
                    INSERT INTO attendance_logs
                        (employee_id, punch_method_id, punch_status_id,
                         device_key, event_timestamp, pulled_timestamp)
                    VALUES
                        (:employee_id, :punch_method_id, :punch_status_id,
                         :device_key, :event_timestamp, :pulled_timestamp)
                """),
                records   # SQLAlchemy executemany when a list of dicts is passed
            )
            conn.commit()
            log.info("Batch inserted %d attendance log records.", len(records))
            return len(records)

    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
                webhook_url=cred.DISCORD_WEBHOOK_URL,
                error_message=f"Database connection error while inserting attendance logs: {ce}",
                exc=ce
            )
        return None
    except Exception as e:
        log.error(f"Error inserting attendance log records: {e}")
        send_discord_alert(
                webhook_url=cred.DISCORD_WEBHOOK_URL,
                error_message=f"Error inserting attendance log records: {e}",
                exc=e
            )
        return None


def insert_device_info_records(record: dict):
    """
    Insert a single device info record.
    record must be a dict with keys: device_id, device_name, device_ip
    """
    try:
        conn = db_obj.get_connect().connect()
        with conn:
            conn.execute(
                text("""
                    INSERT INTO device_info (device_id, device_name, device_ip)
                    VALUES (:device_id, :device_name, :device_ip)
                """),
                record
            )
            conn.commit()
            log.info("Device %s inserted successfully.", record["device_id"])

    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
                webhook_url=cred.DISCORD_WEBHOOK_URL,
                error_message=f"Database connection error while inserting device info: {ce}",
                exc=ce
            )
        return None
    except Exception as e:
        log.error(f"Error inserting device info records: {e}")
        send_discord_alert(
                webhook_url=cred.DISCORD_WEBHOOK_URL,
                error_message=f"Error inserting device info records: {e}",
                exc=e
            )
        return None


def insert_employee_data_records(records: list[dict]):
    """
    Batch insert a list of employee records.
    Each record must be a dict with keys: employee_id, employee_name
    """
    if not records:
        log.warning("No employee records to insert.")
        return 0

    try:
        conn = db_obj.get_connect().connect()
        with conn:
            conn.execute(
                text("""
                    INSERT INTO employee_details (employee_id, employee_name)
                    VALUES (:employee_id, :employee_name)
                """),
                records   # SQLAlchemy executemany when a list of dicts is passed
            )
            conn.commit()
            log.info("Batch inserted %d employee records.", len(records))
            return len(records)

    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
                webhook_url=cred.DISCORD_WEBHOOK_URL,
                error_message=f"Database connection error while inserting employee data records: {ce}",
                exc=ce
            )
        return None
    except Exception as e:
        log.error(f"Error inserting employee data records: {e}")
        send_discord_alert(
                webhook_url=cred.DISCORD_WEBHOOK_URL,
                error_message=f"Error inserting employee data records: {e}",
                exc=e
            )
        return None