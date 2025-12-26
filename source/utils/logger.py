import logging
import logging.handlers
import re
import sys
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


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from log messages."""

    def __init__(self):
        super().__init__()
        # Patterns to match sensitive data
        self.patterns = [
            # GitHub token in Authorization header
            (
                re.compile(r"(Authorization['\"]?\s*:\s*['\"]?token\s+)ghp_[a-zA-Z0-9]{36,}", re.IGNORECASE),
                r"\1ghp_***REDACTED***",
            ),
            # GitHub token standalone
            (re.compile(r"\bghp_[a-zA-Z0-9]{36,}"), r"ghp_***REDACTED***"),
            # Generic bearer tokens
            (re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), r"\1***REDACTED***"),
            # Authorization header value
            (re.compile(r"('Authorization':\s*')([^']+)(')", re.IGNORECASE), r"\1***REDACTED***\3"),
            (re.compile(r'("Authorization":\s*")([^"]+)(")', re.IGNORECASE), r"\1***REDACTED***\3"),
        ]

    def filter(self, record):
        """Redact sensitive data from the log record message."""
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)

        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(self._sanitize_value(arg) for arg in record.args)
            elif isinstance(record.args, dict):
                record.args = {key: self._sanitize_value(value) for key, value in record.args.items()}

        return True

    def _sanitize_value(self, value):
        """Sanitize a single value (string)."""
        if isinstance(value, str):
            for pattern, replacement in self.patterns:
                value = pattern.sub(replacement, value)
        return value


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

    # Create sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    try:
        file_handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(sensitive_filter)
    except PermissionError:
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(sensitive_filter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(sensitive_filter)

    logging.basicConfig(level=numeric_level, handlers=[file_handler, console_handler], format=format_string)
