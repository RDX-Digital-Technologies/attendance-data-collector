import logging
import sys
from pathlib import Path
from typing import Optional

class Logger:
    _instance: Optional[logging.Logger] = None
    
    @classmethod
    def get_logger(cls, name: str, log_path: str) -> logging.Logger:
        """
        Get or create a logger instance.
        """
        if cls._instance is None:
            cls._instance = cls._setup_logger(name, log_path)
        return cls._instance
    
    @classmethod
    def _setup_logger(cls, name: str, log_path: str) -> logging.Logger:
        """
        Setup and configure the logger.
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        try:
            log_file = Path(log_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to setup file handler: {e}")
        
        return logger

def get_logger(name: str ) -> logging.Logger:
    """
    Get logger instance with configuration from Config.
    """
    try:
        from scripts.utils.config import Config
        config = Config()
        return Logger.get_logger(name, config.LOG_PATH)
    except Exception:
        # Fallback to a default log path if Config import fails
        default_log_path = "tmp/attendance_collector.log"
        return Logger.get_logger(name, default_log_path)