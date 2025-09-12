"""Tests for TCRHandler class."""

import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from freezegun import freeze_time
from watchdog.events import FileModifiedEvent

from tcr.tcr import TCRConfig, TCRHandler


class TestTCRHandler:
    """Test suite for TCRHandler class."""
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def config(self, temp_dir):
        return TCRConfig(
            enabled=True,
            watch_paths=[str(temp_dir)],
            test_command='pytest',
            test_timeout=10,
            commit_prefix='TEST',
            revert_on_failure=True,
            debounce_seconds=1.0,
            ignore_patterns=[]  # Empty list to ensure tests aren't affected by default patterns
        )
    
    @pytest.fixture
    def handler(self, config):
        return TCRHandler(config)
    
    @pytest.fixture
    def temp_file(self, temp_dir):
        file_path = temp_dir / 'test_file.py'
        file_path.write_text('# Test file\n')
        return file_path
    
    def test_init__stores_passed_config(self, config):
        handler = TCRHandler(config)
        assert handler.config == config

    def test_intit__initializes_last_run(self, config):
        handler = TCRHandler(config)
        assert handler.last_run == 0
    
    def test_on_modified__when_event_is_for_directory__event_is_ignored(self, handler, temp_dir):
        event = FileModifiedEvent(str(temp_dir))
        event.is_directory = True
        
        with patch.object(handler, '_run_tcr_cycle') as mock_run:
            handler.on_modified(event)
            mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_on_modified__when_no_git_changes__event_ignored(self, mock_run, handler, temp_file):
        event = FileModifiedEvent(str(temp_file))
        event.is_directory = False
        
        # Mock git status returning empty (no changes)
        mock_run.return_value = Mock(stdout='', returncode=0)
        
        with patch.object(handler, '_run_tcr_cycle') as mock_cycle:
            handler.on_modified(event)
            mock_cycle.assert_not_called()
            mock_run.assert_called_once_with(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True
            )
    
    @patch('subprocess.run')
    def test_on_modified__when_git_changes__tcr_cycle_runs(self, mock_run, handler, temp_file):
        """Test that TCR cycle runs when git changes are detected."""
        event = FileModifiedEvent(str(temp_file))
        event.is_directory = False
        
        mock_run.return_value = Mock(stdout=f'M {temp_file.name}\n', returncode=0)
        
        with patch.object(handler, '_run_tcr_cycle') as mock_cycle:
            handler.on_modified(event)
            mock_cycle.assert_called_once()
            mock_run.assert_called_once_with(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True
            )
    
    @patch('subprocess.run')
    def test_on_modified__when_event_within_debounce_window__event_ignored(self, mock_run, handler, temp_file):
        event = FileModifiedEvent(str(temp_file))
        event.is_directory = False
        
        # Mock git status returning changes
        mock_run.return_value = Mock(stdout=f'M {temp_file.name}\n', returncode=0)
        
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            # First call at initial time
            with patch.object(handler, '_run_tcr_cycle') as mock_cycle:
                handler.on_modified(event)
                mock_cycle.assert_called_once()
            
            # Move time forward by 0.5 seconds (within debounce window of 1.0 seconds)
            frozen_time.tick(delta=timedelta(seconds=0.5))
            with patch.object(handler, '_run_tcr_cycle') as mock_cycle:
                handler.on_modified(event)
                mock_cycle.assert_not_called()
            
            # Move time forward to 1.5 seconds total (outside debounce window)
            frozen_time.tick(delta=timedelta(seconds=1.0))
            with patch.object(handler, '_run_tcr_cycle') as mock_cycle:
                handler.on_modified(event)
                mock_cycle.assert_called_once()
    
    @freeze_time("2024-01-01 12:00:00")
    @patch('subprocess.run')
    def test_run_tcr_cycle__when_tests_successful__changes_committed(self, mock_run, handler, temp_file):
        """Test that successful tests lead to commit."""
        # Mock all subprocess calls to return success
        mock_run.return_value = Mock(
            returncode=0,
            stdout='All tests passed',
            stderr=''
        )
        
        handler._run_tcr_cycle(temp_file)
        
        expected_calls = [
            call(
                handler.config.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=handler.config.test_timeout
            ),
            call(['git', 'add', '-A'], check=True, capture_output=True),
            call(
                ['git', 'commit', '-m', f'TEST: 2024-01-01 12:00:00 - Modified {temp_file.name}'],
                check=True,
                capture_output=True
            )
        ]
        
        mock_run.assert_has_calls(expected_calls)

    @patch('subprocess.run')
    def test_run_tcr_cycle__when_tests_fail__changes_reverted(self, mock_run, handler, temp_file):

        def side_effect(*args, **kwargs):
            if args[0] == handler.config.test_command:
                return Mock(returncode=1, stdout='Test failed', stderr='Error details')
            else:
                return Mock(returncode=0, stdout='', stderr='')
        
        mock_run.side_effect = side_effect
        
        handler._run_tcr_cycle(temp_file)
        
        expected_calls = [
            call(
                handler.config.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=handler.config.test_timeout
            ),
            call(['git', 'reset', '--hard', 'HEAD'], check=True, capture_output=True)
        ]
        
        mock_run.assert_has_calls(expected_calls)
    
    @patch('subprocess.run')
    def test_run_tests__when_timeout_raised__returns_false(self, mock_run, handler):
        mock_run.side_effect = subprocess.TimeoutExpired('pytest', handler.config.test_timeout)
        
        result = handler._run_tests()
        assert result is False
    
    @patch('subprocess.run')
    def test_run_tests__when_unexpected_exception_raised__returns_false(self, mock_run, handler):
        mock_run.side_effect = Exception('Unexpected error')
        result = handler._run_tests()
        assert result is False
    
    @freeze_time("2024-01-01 12:00:00")
    @patch('subprocess.run')
    def test_commit_changes__makes_expected_git_calls(self, mock_run, handler, temp_file):
        mock_run.return_value = Mock(returncode=0)
        handler._commit_changes(temp_file)
        expected_calls = [
            call(['git', 'add', '-A'], check=True, capture_output=True),
            call(['git', 'commit', '-m', f'TEST: 2024-01-01 12:00:00 - Modified {temp_file.name}'],
                 check=True, capture_output=True)
        ]
        mock_run.assert_has_calls(expected_calls)
    
    @patch('subprocess.run')
    def test_commit_changes__when_git_error__no_exception_raised(self, mock_run, handler, temp_file):
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
        handler._commit_changes(temp_file)
    
    @patch('subprocess.run')
    def test_revert__when_changes_revert_on_failure_true__makes_expected_git_calls(self, mock_run, handler):
        handler.config.revert_on_failure = True
        mock_run.return_value = Mock(returncode=0)
        
        handler._revert_changes()
        mock_run.assert_called_once_with(
            ['git', 'reset', '--hard', 'HEAD'],
            check=True,
            capture_output=True
        )
    
    @patch('subprocess.run')
    def test_revert_changes__when_changes_revert_on_failure_false__not_git_calls_made(self, mock_run, handler):
        """Test reverting changes when disabled."""
        handler.config.revert_on_failure = False
        with patch('tcr.tcr.logger') as mock_logger:
            handler._revert_changes()
            mock_run.assert_not_called()
            mock_logger.warning.assert_called_with("⚠️ Tests failed but revert is disabled")
    
    @patch('subprocess.run')
    def test_revert__when_git_error__no_exception_raised(self, mock_run, handler):
        """Test failed revert."""
        handler.config.revert_on_failure = True
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
        handler._revert_changes()
