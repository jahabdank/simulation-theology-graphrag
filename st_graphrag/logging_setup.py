"""Centralized logging setup with timestamped log files."""

import logging
import sys
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"

_initialized = False


def setup_logging(
    level: int = logging.INFO,
    session_name: str = "session",
) -> Path:
    """Configure logging to both console and a timestamped log file.

    Creates a log file at logs/YYYYMMDD_HHMMSS_{session_name}.log

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        session_name: Descriptive name for the session (e.g., "seed", "query").

    Returns:
        Path to the created log file.
    """
    global _initialized

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{timestamp}_{session_name}.log"
    log_path = LOGS_DIR / log_filename

    # Clear any existing handlers to avoid duplicates on re-init
    root_logger = logging.getLogger()
    if _initialized:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    root_logger.setLevel(level)

    # Console handler — concise format
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    # File handler — detailed format with full timestamps
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # always capture debug in file
    file_fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _initialized = True

    logging.getLogger(__name__).info(
        "Logging initialized: %s (level=%s)", log_path, logging.getLevelName(level)
    )
    return log_path
