from scripts.db_layer.db import DB  
from scripts.utils.logger import get_logger
from scripts.utils.discord_error_alert import send_discord_alert
from scripts.utils.config import Config
from sqlalchemy import text

db_obj = DB()
log = get_logger(__name__)
cred = Config()

def get_punch_status_records():
    try:
        conn = db_obj.get_connect().connect()
        with conn:
            result = conn.execute(text("SELECT * FROM punch_status"))
            return result.fetchall()
        
    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Database connection error while fetching punch status records: {ce}",
            exc=ce
        )
        return None
    
    except Exception as e:
        log.error(f"Error fetching punch status records: {e}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Error fetching punch status records: {e}",
            exc=e
        )
        return None

def get_last_fetched_timestamp(device_key:str):
    try:
        conn = db_obj.get_connect().connect()
        with conn:
            result = conn.execute(text("SELECT MAX(event_timestamp) FROM attendance_logs WHERE device_key = :device_key"), {"device_key": device_key})
            return result.scalar()
        
    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Database connection error while fetching last fetched timestamp: {ce}",
            exc=ce
        )
        return None
    
    except Exception as e:
        log.error(f"Error fetching last fetched timestamp: {e}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Error fetching last fetched timestamp: {e}",
            exc=e
        )
        return None
    
def get_device_info():
    try:
        conn = db_obj.get_connect().connect()
        with conn:
            result = conn.execute(
                text("SELECT * FROM device_info")
            )
            return result.fetchall()
    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Database connection error while fetching device info: {ce}",
            exc=ce)
        return None
    except Exception as e:
        log.error(f"Error fetching device info: {e}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Error fetching device info: {e}",
            exc=e
        )
        return None


def get_punch_method_records():
    try:
        conn = db_obj.get_connect().connect()
        with conn:
            result = conn.execute(text("SELECT * FROM punch_method"))
            return result.fetchall()
    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Database connection error while fetching punch method records: {ce}",
            exc=ce
        )
        return None
    except Exception as e:
        log.error(f"Error fetching punch method records: {e}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Error fetching punch method records: {e}",
            exc=e
        )
        return None


def get_existing_employee_records():
    try:
        conn = db_obj.get_connect().connect()
        with conn:
            result = conn.execute(text("SELECT * FROM employee_details"))
            return result.fetchall()
    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Database connection error while fetching existing employee records: {ce}",
            exc=ce
        )
        return None
    except Exception as e: 
        log.error(f"Error fetching existing employee records: {e}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Error fetching existing employee records: {e}",
            exc=e
        )
        return None

def get_all_recent_attendance_logs(last_fetched_timestamp):
    """
    Fetch all attendance logs with event_timestamp > last_fetched_timestamp.
    Uses SQLAlchemy named bind parameter (:ts) instead of %s.
    """
    try:
        conn = db_obj.get_connect().connect()
        with conn:
            result = conn.execute(
                text("""
                    SELECT
                        a.log_id, a.employee_id, e.employee_name,
                        a.device_id, d.device_name,
                        a.punch_method_id, p.method_name,
                        a.punch_status_id, s.status_name,
                        a.event_timestamp, a.pulled_timestamp
                    FROM attendance_logs a
                    JOIN employee_details e ON a.employee_id   = e.employee_id
                    JOIN device_info     d ON a.device_id      = d.device_id
                    JOIN punch_method    p ON a.punch_method_id = p.punch_method_id
                    JOIN punch_status    s ON a.punch_status_id = s.punch_status_id
                    WHERE a.event_timestamp > :ts
                """),
                {"ts": last_fetched_timestamp}
            )
            return result.fetchall()

    except ConnectionError as ce:
        log.error(f"Database connection error: {ce}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Database connection error while fetching recent attendance logs: {ce}",
            exc=ce
        )
        return None
    except Exception as e:
        log.error(f"Error fetching recent attendance logs: {e}")
        send_discord_alert(
            webhook_url=cred.DISCORD_WEBHOOK_URL,
            error_message=f"Error fetching recent attendance logs: {e}",
            exc=e
        )
        return None