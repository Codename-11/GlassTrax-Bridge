### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Custom Logger Setup -
# Author: Bailey Dixon
# Date: 01/30/2025
# Python: 3.11
####################

# Standard Imports
import logging
from datetime import datetime
from pathlib import Path


class CustomFormatter(logging.Formatter):
    """Custom formatter for GlassTrax Bridge logging with specific time format"""

    def format(self, record):
        """
        Format log record with custom time format: HH:MM:SS AM/PM - name - LEVEL:

        Args:
            record: LogRecord instance

        Returns:
            Formatted log string
        """
        # Get timestamp in 12-hour format
        timestamp = datetime.fromtimestamp(record.created).strftime("%I:%M:%S %p")

        # Build the formatted message
        formatted_msg = f"{timestamp} - {record.name} - {record.levelname}: {record.getMessage()}"

        # Handle exceptions if present
        if record.exc_info:
            formatted_msg += "\n" + self.formatException(record.exc_info)

        return formatted_msg


def setup_logger(
    name: str, level: int = logging.INFO, log_to_file: bool = True, log_to_console: bool = True
) -> logging.Logger:
    """
    Set up a custom logger for GlassTrax Bridge

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        log_to_file: Whether to log to file (default: True)
        log_to_console: Whether to log to console (default: True)

    Returns:
        Configured logger instance

    Example:
        logger = setup_logger(__name__)
        logger.info("This is an info message")
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Create custom formatter
    formatter = CustomFormatter()

    # Set up file logging if requested
    if log_to_file:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create file handler with date-based filename
        log_filename = f"glasstrax_bridge_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_filepath = logs_dir / log_filename

        file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Set up console logging if requested
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one with default settings

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return setup_logger(name)


# Create a default logger for the utils module
logger = setup_logger(__name__)
