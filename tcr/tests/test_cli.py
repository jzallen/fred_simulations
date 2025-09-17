"""Tests for TCR CLI functionality."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tcr.tcr import main


class TestCLI:
    """Test suite for CLI functionality."""

    @patch('tcr.tcr.TCRRunner')
    def test_start_command_with_session_id(self, mock_runner_class):
        """Test that start command accepts --session-id argument."""
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner

        # Simulate command line arguments
        test_args = ['tcr', 'start', '--session-id', 'test-session-123']
        with patch('sys.argv', test_args):
            main()

        # TCRRunner should be initialized with session_id
        mock_runner_class.assert_called_once_with(config_path=None, session_id='test-session-123')
        mock_runner.start.assert_called_once()

    @patch('tcr.tcr.TCRRunner')
    def test_start_command_without_session_id(self, mock_runner_class):
        """Test that start command works without --session-id argument."""
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner

        # Simulate command line arguments
        test_args = ['tcr', 'start']
        with patch('sys.argv', test_args):
            main()

        # TCRRunner should be initialized without session_id (defaults to None)
        mock_runner_class.assert_called_once_with(config_path=None, session_id=None)
        mock_runner.start.assert_called_once()

    @patch('tcr.tcr.TCRRunner')
    def test_start_command_with_config_and_session_id(self, mock_runner_class):
        """Test that start command accepts both --config and --session-id arguments."""
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner

        # Simulate command line arguments
        test_args = ['tcr', 'start', '--config', '/path/to/config.yaml', '--session-id', 'my-session']
        with patch('sys.argv', test_args):
            main()

        # TCRRunner should be initialized with both config_path and session_id
        mock_runner_class.assert_called_once_with(
            config_path=Path('/path/to/config.yaml'),
            session_id='my-session'
        )
        mock_runner.start.assert_called_once()

    @patch('tcr.tcr.list_sessions')
    def test_ls_command_calls_list_sessions(self, mock_list_sessions):
        """Test that ls command calls list_sessions function."""
        mock_list_sessions.return_value = None

        # Simulate command line arguments
        test_args = ['tcr', 'ls']
        with patch('sys.argv', test_args):
            main()

        # list_sessions should be called once
        mock_list_sessions.assert_called_once()