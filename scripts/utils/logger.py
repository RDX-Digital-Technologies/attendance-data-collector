import logging
import sys
from pathlib import Path

_log_path: str = None

def configure_logging(log_path: str):
    global _log_path
    _log_path = log_path

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured, nothing to do

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # <-- critical: stops bleed-through to root logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — always present
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler — only if log path has been configured
    if _log_path:
        try:
            Path(_log_path).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(_log_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error("Failed to set up file handler at %s: %s", _log_path, e)

    return logger