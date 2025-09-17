"""Tests for setup_logger function with session_id functionality."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tcr.tcr import setup_logger


class TestSetupLogger:
    """Test suite for setup_logger function with session_id support."""

    @pytest.fixture
    def temp_home_dir(self):
        """Create a temporary home directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_setup_logger__when_session_id_provided__creates_log_file_with_session_id_path(self, temp_home_dir):
        """Test that setup_logger creates log file in session-specific directory when session_id is provided."""
        session_id = "test_session_123"
        expected_log_path = temp_home_dir / '.local' / 'share' / 'tcr' / session_id / 'tcr.log'

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir):
            logger = setup_logger(session_id=session_id)

        # Logger should be configured
        assert logger.name == 'tcr'
        assert logger.level == logging.DEBUG

        # Log directory should be created
        assert expected_log_path.parent.exists()

        # File handler should be pointing to the session-specific log file
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == expected_log_path

    def test_setup_logger__when_session_id_none__generates_random_session_id_using_secrets(self, temp_home_dir):
        """Test that setup_logger generates random session_id using secrets library when none provided."""
        mock_session_id = "abc123def456"

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir), \
             patch('tcr.tcr.secrets.token_urlsafe', return_value=mock_session_id) as mock_secrets:

            logger = setup_logger(session_id=None)

        # secrets.token_urlsafe should have been called to generate session_id
        mock_secrets.assert_called_once_with(8)

        # Log file should be created with generated session_id
        expected_log_path = temp_home_dir / '.local' / 'share' / 'tcr' / mock_session_id / 'tcr.log'
        assert expected_log_path.parent.exists()

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        rotating_file_handler = file_handlers[0]
        assert Path(rotating_file_handler.baseFilename) == expected_log_path

    def test_setup_logger__when_session_id_not_provided__generates_random_session_id_using_secrets(self, temp_home_dir):
        """Test that setup_logger generates random session_id when parameter is not provided at all."""
        mock_session_id = "xyz789uvw012"

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir), \
             patch('tcr.tcr.secrets.token_urlsafe', return_value=mock_session_id) as mock_secrets:

            logger = setup_logger()  # No session_id parameter provided

        # secrets.token_urlsafe should have been called to generate session_id
        mock_secrets.assert_called_once_with(8)

        # Log file should be created with generated session_id
        expected_log_path = temp_home_dir / '.local' / 'share' / 'tcr' / mock_session_id / 'tcr.log'
        assert expected_log_path.parent.exists()

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == expected_log_path

    def test_setup_logger__when_session_id_empty_string__generates_random_session_id(self, temp_home_dir):
        """Test that setup_logger generates random session_id when empty string is provided."""
        mock_session_id = "empty456str789"

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir), \
             patch('tcr.tcr.secrets.token_urlsafe', return_value=mock_session_id) as mock_secrets:

            logger = setup_logger(session_id="")

        # secrets.token_urlsafe should have been called for empty string
        mock_secrets.assert_called_once_with(8)

        # Log file should be created with generated session_id
        expected_log_path = temp_home_dir / '.local' / 'share' / 'tcr' / mock_session_id / 'tcr.log'
        assert expected_log_path.parent.exists()

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == expected_log_path

    def test_setup_logger__when_session_id_has_special_characters__sanitizes_session_id(self, temp_home_dir):
        """Test that setup_logger handles session_id with special characters appropriately."""
        session_id = "test/session\\with:special*chars"
        # Expected sanitized version (implementation will determine exact sanitization)

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir):
            logger = setup_logger(session_id=session_id)

        # Should create log directory (exact path depends on sanitization implementation)
        tcr_base_dir = temp_home_dir / '.local' / 'share' / 'tcr'
        assert tcr_base_dir.exists()

        # Should have exactly one subdirectory for the session
        session_dirs = [d for d in tcr_base_dir.iterdir() if d.is_dir()]
        assert len(session_dirs) == 1

        # File handler should be created
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_setup_logger__when_session_id_alphanumeric__uses_session_id_directly(self, temp_home_dir):
        """Test that setup_logger uses alphanumeric session_id directly without modification."""
        session_id = "SessionABC123"
        expected_log_path = temp_home_dir / '.local' / 'share' / 'tcr' / session_id / 'tcr.log'

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir):
            logger = setup_logger(session_id=session_id)

        # Log directory should be created with exact session_id
        assert expected_log_path.parent.exists()
        assert expected_log_path.parent.name == session_id

        # File handler should point to correct path
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == expected_log_path

    def test_setup_logger__creates_directory_structure_recursively(self, temp_home_dir):
        """Test that setup_logger creates the complete directory structure recursively."""
        session_id = "recursive_test"

        # Ensure the .local directory doesn't exist initially
        local_dir = temp_home_dir / '.local'
        assert not local_dir.exists()

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir):
            logger = setup_logger(session_id=session_id)

        # All directories should be created
        expected_log_path = temp_home_dir / '.local' / 'share' / 'tcr' / session_id / 'tcr.log'
        assert expected_log_path.parent.exists()
        assert expected_log_path.parent.parent.exists()  # tcr directory
        assert expected_log_path.parent.parent.parent.exists()  # share directory
        assert expected_log_path.parent.parent.parent.parent.exists()  # .local directory

    def test_setup_logger__maintains_existing_logger_configuration(self, temp_home_dir):
        """Test that setup_logger maintains proper logger configuration with session_id."""
        session_id = "config_test"

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir):
            logger = setup_logger(session_id=session_id)

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

    def test_setup_logger__when_log_file_parameter_provided__ignores_session_id(self, temp_home_dir):
        """Test that when log_file parameter is provided, session_id is ignored."""
        session_id = "should_be_ignored"
        custom_log_file = temp_home_dir / 'custom.log'

        with patch('tcr.tcr.Path.home', return_value=temp_home_dir):
            logger = setup_logger(log_file=custom_log_file, session_id=session_id)

        # File handler should point to custom log file, not session-based path
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == custom_log_file

        # Session directory should not be created
        session_dir = temp_home_dir / '.local' / 'share' / 'tcr' / session_id
        assert not session_dir.exists()