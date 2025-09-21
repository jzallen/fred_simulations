"""Tests for list_sessions functionality."""

from unittest.mock import Mock, patch

from tcr.cli import list_sessions
from tcr.logging_config import LoggerType, logger_factory


class TestListSessions:
    """Test suite for list_sessions function."""

    @patch('subprocess.run')
    def test_list_sessions__when_no_sessions_running__logs_no_sessions(self, mock_run):
        """Test that list_sessions logs 'No TCR sessions' when pgrep finds nothing."""
        # pgrep returns 1 when no processes are found
        mock_run.return_value = Mock(returncode=1, stdout='')

        # Create a mock logger
        mock_logger = Mock()

        list_sessions(mock_logger)

        mock_run.assert_called_once_with(
            ['pgrep', '-a', 'tcr:'],
            capture_output=True,
            text=True
        )
        mock_logger.info.assert_called_once_with("No TCR sessions currently running")

    @patch('subprocess.run')
    @patch('builtins.print')
    def test_list_sessions__when_single_session_running__prints_raw_output(self, mock_print, mock_run):
        """Test that list_sessions prints raw pgrep output for a single session."""
        # pgrep -a output format: PID command
        mock_run.return_value = Mock(
            returncode=0,
            stdout='12345 tcr:my-feature\n'
        )

        # Create a mock logger
        mock_logger = Mock()

        list_sessions(mock_logger)

        mock_run.assert_called_once_with(
            ['pgrep', '-a', 'tcr:'],
            capture_output=True,
            text=True
        )

        # Check that raw output was printed
        mock_print.assert_called_once_with('12345 tcr:my-feature')

    @patch('subprocess.run')
    @patch('builtins.print')
    def test_list_sessions__when_multiple_sessions_running__prints_all_sessions(self, mock_print, mock_run):
        """Test that list_sessions prints raw output for multiple sessions."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='12345 tcr:feature-1\n67890 tcr:bugfix-xyz\n11111 tcr:test-session\n'
        )

        # Use null logger for this test since we're testing print output
        null_logger = logger_factory(LoggerType.NULL)

        list_sessions(null_logger)

        # Check that raw output was printed
        mock_print.assert_called_once_with('12345 tcr:feature-1\n67890 tcr:bugfix-xyz\n11111 tcr:test-session')

    @patch('subprocess.run')
    def test_list_sessions__when_pgrep_not_found__logs_error(self, mock_run):
        """Test that list_sessions handles missing pgrep gracefully."""
        mock_run.side_effect = FileNotFoundError("pgrep not found")

        # Create a mock logger
        mock_logger = Mock()

        list_sessions(mock_logger)

        mock_logger.error.assert_called_with("pgrep command not found. Please ensure procps is installed.")

    @patch('subprocess.run')
    def test_list_sessions__when_unexpected_error__logs_error(self, mock_run):
        """Test that list_sessions handles unexpected errors gracefully."""
        mock_run.side_effect = Exception("Unexpected error")

        # Create a mock logger
        mock_logger = Mock()

        list_sessions(mock_logger)

        mock_logger.error.assert_called_with("Error listing sessions: Unexpected error")

