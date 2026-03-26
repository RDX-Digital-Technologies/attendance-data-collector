from dotenv import load_dotenv
import os
from scripts.utils.discord_error_alert import send_discord_alert

load_dotenv(dotenv_path=".env")

class Config:
    def __init__(self):

        #------ Device Config -------
        self.DEVICE_PORT = os.getenv("DEVICE_PORT", None)
        if self.DEVICE_PORT is not None:
            self.DEVICE_PORT = int(self.DEVICE_PORT)
        else:
            send_discord_alert(self.DISCORD_WEBHOOK_URL, "DEVICE_PORT must be set in .env file")
            raise ValueError("DEVICE_PORT must be set in .env file")
            
        self.COMM_KEY = os.getenv("DEVICE_COMM_KEY", None)
        if self.COMM_KEY is not None:
            self.COMM_KEY = int(self.COMM_KEY)
        else:
            send_discord_alert(self.DISCORD_WEBHOOK_URL, "DEVICE_COMM_KEY must be set in .env file")
            raise ValueError("DEVICE_COMM_KEY must be set in .env file")

        self.TIMEOUT = os.getenv("DEVICE_TIMEOUT", None)
        if self.TIMEOUT is not None:
            self.TIMEOUT = int(self.TIMEOUT)
        else:
            send_discord_alert(self.DISCORD_WEBHOOK_URL, "DEVICE_TIMEOUT must be set in .env file")
            raise ValueError("DEVICE_TIMEOUT must be set in .env file")

        self.FORCE_UDP = False
        
        #------ Logging Config -------
        self.LOG_PATH = os.getenv("LOG_PATH", None)
        if self.LOG_PATH is None:
            send_discord_alert(self.DISCORD_WEBHOOK_URL, "LOG_PATH must be set in .env file")
            raise ValueError("LOG_PATH must be set in .env file")
        else:
            os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)
            
        #------ Database Config -------
        self.DB_USERNAME = os.getenv("DB_USERNAME", None)
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", None)
        self.DB_HOST = os.getenv("DB_HOST", None)
        self.DB_PORT = os.getenv("DB_PORT", None)
        self.DB_NAME = os.getenv("DB_NAME", None)
        if not all([self.DB_USERNAME, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME]):
            send_discord_alert(self.DISCORD_WEBHOOK_URL, "All database configuration variables (DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME) must be set in .env file")
            raise ValueError("All database configuration variables (DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME) must be set in .env file")
        
        #------ Discord Webhook Config -------
        self.DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", None)
        if self.DISCORD_WEBHOOK_URL is None:
            raise ValueError("DISCORD_WEBHOOK_URL must be set in .env file")
        
        #------ approved device_alias --------
        self.APPROVED_DEVICE = os.getenv("approved_device_alias", None)

        #------ attendance collection start date ----
        self.ATTENDANCE_COLLECTION_START_DATE = os.getenv("start_date", None)