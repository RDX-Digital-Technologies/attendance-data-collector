from sqlalchemy import create_engine, Engine
from typing import Optional
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DisconnectionError
import time
import urllib.parse
from scripts.utils.logger import get_logger
from scripts.utils.config import Config
from scripts.utils.discord_error_alert import send_discord_alert

logger = get_logger(__name__)
config = Config()

class DB:
    def __init__(self, max_retries=3):
        self.username = urllib.parse.quote_plus(config.DB_USERNAME)
        self.password = urllib.parse.quote_plus(str(config.DB_PASSWORD))
        self.host = config.DB_HOST
        self.port = config.DB_PORT
        self.db_name = config.DB_NAME
        self.max_retries = max_retries
        self._engine = None

    def get_connect(self) -> Optional[Engine]:
        """Get or create database engine with retry logic"""
        if self._engine is None:
            self._engine = self._create_engine_with_retry()
        return self._engine

    def _create_engine_with_retry(self) -> Engine:
        """Create engine with retry logic for transient failures"""
        for attempt in range(self.max_retries):
            try:
                engine = create_engine(
                    f"postgresql+psycopg2://{self.username}:{str(self.password)}@{self.host}:{self.port}/{self.db_name}",
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_recycle=3600,
                    pool_pre_ping=True,
                    pool_timeout=30,
                    connect_args={
                        'connect_timeout': 10
                    },
                    echo=False
                )
                logger.info("PostgreSQL database connection established successfully")
                return engine
                
            except (OperationalError, DisconnectionError) as e:
                send_discord_alert(
                    webhook_url=config.DISCORD_WEBHOOK_URL,
                    error_message=f"Database connection error on attempt {attempt + 1}: {e}",
                    exc=e
                )
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("All connection attempts failed")
                    raise
    
    def close(self):
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")

