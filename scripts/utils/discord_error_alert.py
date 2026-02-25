import requests
import traceback
from scripts.utils.logger import get_logger
from datetime import datetime

log = get_logger(__name__)

def send_discord_alert(
    webhook_url: str,
    error_message: str,
    exc: Exception = None,
) -> bool:
    if not webhook_url:
        log.warning("Discord webhook URL not configured. Skipping notification.")
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Extract file and line number from traceback
    file_info = "Unknown"
    line_info = "Unknown"
    if exc:
        tb = traceback.TracebackException.from_exception(exc)
        last_frame = list(tb.stack)[-1] if tb.stack else None
        if last_frame:
            file_info = last_frame.filename
            line_info = str(last_frame.lineno)

    # Get full traceback string
    stack_trace = (
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if exc else "No traceback available"
    )

    fields = [
        {
            "name": "📄 Error Description",
            "value": f"```{error_message[:1000]}```",
            "inline": False
        },
        {
            "name": "📁 File",
            "value": f"`{file_info}`",
            "inline": True
        },
        {
            "name": "📍 Line",
            "value": f"`{line_info}`",
            "inline": True
        },
        {
            "name": "🔍 Error Type",
            "value": f"`{type(exc).__name__}`" if exc else "`Unknown`",
            "inline": False
        },
        {
            "name": "🧵 Stack Trace",
            "value": f"```{stack_trace[-900:]}```",
            "inline": False
        },
    ]

    payload = {
        "embeds": [
            {
                "title": "🚨 Application Error",
                "color": 0xFF0000,  # Red
                "fields": fields,
                "footer": {
                    "text": f"🕒 {timestamp}"
                }
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        log.info("Discord alert sent successfully.")
        return True
    except requests.exceptions.RequestException as e:
        log.error("Failed to send Discord alert: %s", e)
        return False