"""
logger.py
---------
Configures application-wide logging.

Why this matters:
When something goes wrong (an API times out, the scheduler crashes, a
malformed URL is passed in), you want a permanent, timestamped record —
not just a print() statement that disappears. This file sets up a
logger that writes to logs/monitoring.log AND prints to the console,
so you can watch it live while developing and still have a file to
review later.
"""

import logging
from logging.handlers import RotatingFileHandler

from backend.config import LOG_FILE_PATH


def get_logger(name: str = "api_monitor") -> logging.Logger:
    """
    Returns a configured logger instance. Safe to call multiple times
    from different files — it won't duplicate handlers.

    Args:
        name: logger name, usually __name__ of the calling module.
    """
    logger = logging.getLogger(name)

    # Prevent adding duplicate handlers if get_logger() is called
    # more than once for the same logger name (e.g. across module imports).
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- File handler: rotates after 1MB, keeps 3 backups, so the log
    # file never grows unbounded during long-running monitoring. ---
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # --- Console handler: so logs are visible while running in a terminal. ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger
