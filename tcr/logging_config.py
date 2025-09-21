#!/usr/bin/env python3
"""Logging configuration for TCR."""

import logging
import logging.handlers
from enum import Enum
from pathlib import Path


class LoggerType(Enum):
    """Enum for different logger types."""
    DEFAULT = "default"
    NULL = "null"
    CONSOLE = "console"


def setup_logger(log_file: Path) -> logging.Logger:
    """Set up logger to write to both console and file.

    Args:
        log_file: Path to log file.

    Returns:
        Configured logger instance
    """
    # Ensure parent directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger('tcr')
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)

    # File handler with DEBUG level and rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def create_null_logger() -> logging.Logger:
    """Create a null logger that discards all messages.

    Returns:
        Logger with NullHandler
    """
    logger = logging.getLogger('tcr.null')
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    return logger


def create_console_logger() -> logging.Logger:
    """Create a console logger for simple output.

    Returns:
        Logger with console handler for INFO level messages
    """
    logger = logging.getLogger('tcr.console')
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)

    logger.addHandler(console_handler)
    return logger


def logger_factory(logger_type: LoggerType = LoggerType.DEFAULT, log_file: Path = None) -> logging.Logger:
    """Factory function to create different types of loggers.

    Args:
        logger_type: Type of logger to create
        log_file: Path to log file (required for DEFAULT logger)

    Returns:
        Configured logger instance based on type
    """
    if logger_type == LoggerType.NULL:
        return create_null_logger()
    elif logger_type == LoggerType.CONSOLE:
        return create_console_logger()
    elif logger_type == LoggerType.DEFAULT:
        if log_file is None:
            raise ValueError("log_file is required for DEFAULT logger")
        return setup_logger(log_file=log_file)
    else:
        raise ValueError(f"Unknown logger type: {logger_type}")