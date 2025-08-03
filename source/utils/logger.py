import sys
import logging
import logging.handlers
from pathlib import Path


# Color codes for terminal output
LOG_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[37m",  # White
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
}
RESET_COLOR = "\033[0m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages."""

    def format(self, record):
        log_color = LOG_COLORS.get(record.levelname, RESET_COLOR)
        message = super().format(record)
        return f"{log_color}{message}{RESET_COLOR}"


def setup_logging(
    log_path: Path,
    level: str = "INFO",
    max_bytes: int = 1 * 1024 * 1024,  # 1 MB
    backup_count: int = 2,
    format_string: str = "[%(asctime)s:%(levelname)s] %(message)s",
) -> None:
    """Setup logging configuration for the application."""

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    file_formatter = logging.Formatter(format_string)
    console_formatter = ColoredFormatter(format_string)

    try:
        file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setFormatter(file_formatter)
    except PermissionError:
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    logging.basicConfig(level=numeric_level, handlers=[file_handler, console_handler], format=format_string)
