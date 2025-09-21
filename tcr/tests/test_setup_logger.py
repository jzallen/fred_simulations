"""Tests for setup_logger function."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tcr.logging_config import setup_logger


class TestSetupLogger:
    """Test suite for setup_logger function."""

    @pytest.fixture
    def temp_home_dir(self):
        """Create a temporary home directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_setup_logger__creates_log_file_at_specified_path(self, temp_home_dir):
        """Test that setup_logger creates log file at the specified path."""
        log_file = temp_home_dir / 'test_logs' / 'tcr.log'

        logger = setup_logger(log_file)

        # Logger should be configured
        assert logger.name == 'tcr'
        assert logger.level == logging.DEBUG

        # Log directory should be created
        assert log_file.parent.exists()

        # File handler should be pointing to the specified log file
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == log_file

    def test_setup_logger__creates_parent_directories_if_not_exist(self, temp_home_dir):
        """Test that setup_logger creates parent directories if they don't exist."""
        log_file = temp_home_dir / 'deep' / 'nested' / 'path' / 'tcr.log'

        # Ensure directories don't exist initially
        assert not log_file.parent.exists()

        logger = setup_logger(log_file)

        # All parent directories should be created
        assert log_file.parent.exists()

        # File handler should be created
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == log_file

    def test_setup_logger__clears_existing_handlers(self, temp_home_dir):
        """Test that setup_logger clears existing handlers before adding new ones."""
        log_file = temp_home_dir / 'tcr.log'

        # Get the logger and add some existing handlers
        tcr_logger = logging.getLogger('tcr')
        # Clear any existing handlers first
        tcr_logger.handlers.clear()
        tcr_logger.addHandler(logging.StreamHandler())
        tcr_logger.addHandler(logging.FileHandler(str(temp_home_dir / 'old.log')))
        assert len(tcr_logger.handlers) == 2

        # Call setup_logger
        logger = setup_logger(log_file)

        # Should have exactly 2 handlers (console + file)
        assert len(logger.handlers) == 2
        assert logger is tcr_logger  # Same logger instance

    def test_setup_logger__maintains_proper_logger_configuration(self, temp_home_dir):
        """Test that setup_logger maintains proper logger configuration."""
        log_file = temp_home_dir / 'tcr.log'

        logger = setup_logger(log_file)

        # Logger should have proper configuration
        assert logger.name == 'tcr'
        assert logger.level == logging.DEBUG

        # Should have both console and file handlers
        assert len(logger.handlers) == 2

        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)]
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]

        assert len(console_handlers) == 1
        assert len(file_handlers) == 1

        # Console handler should be INFO level
        assert console_handlers[0].level == logging.INFO

        # File handler should be DEBUG level
        assert file_handlers[0].level == logging.DEBUG

    def test_setup_logger__configures_rotating_file_handler(self, temp_home_dir):
        """Test that file handler is configured with rotation settings."""
        log_file = temp_home_dir / 'tcr.log'

        logger = setup_logger(log_file)

        # Get the rotating file handler
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1

        handler = file_handlers[0]
        # Check rotation settings
        assert handler.maxBytes == 10 * 1024 * 1024  # 10MB
        assert handler.backupCount == 5