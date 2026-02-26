from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Add this import at the top
from zk import ZK
from zk.exception import ZKNetworkError
import time

from scripts.utils.logger import get_logger
from scripts.utils.discord_error_alert import send_discord_alert
from scripts.utils.config import Config

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
config = Config()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------
def pull_attendance_logs(device_ip, device_port, timeout, comm_key, force_udp, last_pulled_timestamp, max_retries=3, retry_delay=2):
    """
    Pull attendance logs from the biometric device.
    Retries connection up to max_retries times.
    """
    zk  = ZK(device_ip, port=device_port, timeout=timeout,
              password=comm_key, force_udp=force_udp, ommit_ping=False)
    dev = None

    try:
        log.info("Connecting to %s:%d …", device_ip, device_port)
        for attempt in range(1, max_retries + 1):
            try:
                dev = zk.connect()
                break
            except ZKNetworkError as e:
                log.warning("Network error connecting to device (attempt %d/%d): %s", attempt, max_retries, e)
                if attempt == max_retries:
                    log.error("Max retries reached. Giving up.")
                    send_discord_alert(
                        webhook_url=config.DISCORD_WEBHOOK_URL,
                        error_message=f"Failed to connect to device at {device_ip} after {max_retries} attempts: {e}",
                        exc=e
                    )
                    return None, None
                time.sleep(retry_delay)
            except Exception as e:
                log.error("Failed to connect to device: %s", e)
                send_discord_alert(
                    webhook_url=config.DISCORD_WEBHOOK_URL,
                    error_message=f"Failed to connect to device at {device_ip}: {e}",
                    exc=e
                )
                return None, None

        firmware = dev.get_firmware_version()
        serial   = dev.get_serialnumber()
        device_name = dev.get_device_name() if hasattr(dev, 'get_device_name') else "Unknown"
        
        log.info("Connected. Firmware: %s  Serial: %s  Device: %s",
                 firmware, serial, device_name)

        device_info = {
            "device_id": serial,
            "device_name": device_name,
            "device_ip": device_ip,
        }

        # Pull user roster for name lookup
        users    = dev.get_users()
        user_map = {str(u.user_id): getattr(u, "name", None) for u in users}
        log.info("Fetched %d users.", len(users))

        # Disable device briefly for a consistent snapshot
        dev.disable_device()
        log.info("Device disabled for log pull.")
        attendance = dev.get_attendance()
        dev.enable_device()
        log.info("Device re-enabled. Fetched %d raw records.", len(attendance))

        # Format attendance records
        pulled_at = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).isoformat()
        formatted_records = []
        
        # Parse last_pulled_timestamp to datetime (if provided)
        last_dt = None
        if last_pulled_timestamp:
            if isinstance(last_pulled_timestamp, str):
                try:
                    last_dt = datetime.strptime(last_pulled_timestamp, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        last_dt = datetime.strptime(last_pulled_timestamp, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        send_discord_alert(
                            webhook_url=config.DISCORD_WEBHOOK_URL,
                            error_message=f"Invalid last_pulled_timestamp format: {last_pulled_timestamp}",
                            exc=None
                        )
                        log.error("Invalid last_pulled_timestamp format: %s", last_pulled_timestamp)
                        last_dt = None
            elif isinstance(last_pulled_timestamp, datetime):
                last_dt = last_pulled_timestamp
            else:
                send_discord_alert(
                    webhook_url=config.DISCORD_WEBHOOK_URL,
                    error_message=f"Unrecognized type for last_pulled_timestamp: {type(last_pulled_timestamp)}",
                    exc=None
                )
                log.error("last_pulled_timestamp is not a recognized type: %s", type(last_pulled_timestamp))

        for rec in attendance:
            event_ts = rec.timestamp
            # Only include records after last_pulled_timestamp
            if last_dt is None or (event_ts and event_ts > last_dt):
                formatted_records.append({
                    "employee_id": str(rec.user_id),
                    "employee_name": user_map.get(str(rec.user_id)),
                    "event_timestamp": event_ts.isoformat() if event_ts else None,
                    "punch_status_id": getattr(rec, "punch", None),
                    "punch_method_id": getattr(rec, "status", None),
                    "pulled_timestamp": pulled_at
                })

        return formatted_records, device_info

    except Exception as e:
        log.exception("Error during attendance pull.")
        if dev:
            try:
                dev.enable_device()
                log.info("Device re-enabled after error.")
            except Exception:
                log.exception("Failed to re-enable device after error!")
        raise e

    finally:
        if dev:
            try:
                dev.disconnect()
                log.info("Disconnected from device.")
            except Exception:
                log.exception("Error during disconnect.")

# ---------------------------------------------------------------------------
# Main 
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log.info("=== pull_x2008 run start ===")
    records, device_info, user_map = pull_attendance_logs()
    log.info("Pulled %d records from device %s", len(records), device_info["device_id"])
    log.info("=== pull_x2008 run end ===")