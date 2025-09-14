"""Tests for TCRRunner class."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from watchdog.observers import Observer

from tcr.tcr import TCRConfig, TCRRunner


class TestTCRRunner:
    """Test suite for TCRRunner class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def temp_config_file(self, temp_dir):
        """Create a temporary config file."""
        config_file = temp_dir / 'tcr.yaml'
        config_file.write_text("""
tcr:
  enabled: true
  watch_paths:
    - src
    - tests
  test_command: pytest
  test_timeout: 30
  commit_prefix: AUTO
  revert_on_failure: true
  debounce_seconds: 2.0
""")
        return config_file
    
    def test_init__with_config_file__config_set_with_values_from_file(self, temp_config_file):
        runner = TCRRunner(temp_config_file)
        assert runner.config.enabled is True
        assert runner.config.watch_paths == ['src', 'tests']
        assert runner.config.test_command == 'pytest'
        assert runner.config.test_timeout == 30
        assert runner.config.commit_prefix == 'AUTO'
        assert isinstance(runner.observer, Observer)
        assert runner.handler is not None
    
    def test_init__without_config_file__config_set_with_defaults(self):
        with patch.object(Path, 'exists', return_value=False):
            runner = TCRRunner()
            assert runner.config.enabled is True
            assert runner.config.watch_paths == []
            assert runner.config.test_command == 'poetry run pytest -xvs'
    
    def test_init__uses_tcr_yaml_in_home_directory_as_default_config(self):
        """Test TCRRunner uses ~/tcr.yaml by default."""
        # Create a temporary file with specific config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
tcr:
  enabled: false
  test_command: make test
  watch_paths:
    - custom_src
  commit_prefix: CUSTOM
""")
            f.flush()
            temp_path = Path(f.name)
        
        try:
            mock_home_dir = temp_path.parent
            tcr_yaml_path = mock_home_dir / 'tcr.yaml'
            temp_path.rename(tcr_yaml_path)
            
            with patch.object(Path, 'home', return_value=mock_home_dir):
                # Now TCRRunner should read from our mocked ~/tcr.yaml
                runner = TCRRunner()
                
                # Verify the config was loaded from the file
                assert runner.config.enabled is False
                assert runner.config.test_command == 'make test'
                assert runner.config.watch_paths == ['custom_src']
                assert runner.config.commit_prefix == 'CUSTOM'
        finally:
            # Clean up
            if tcr_yaml_path.exists():
                tcr_yaml_path.unlink()
    
    @patch('subprocess.run')
    def test_start__when_enabled_false__file_observer_not_started(self, mock_run):
        with patch('tcr.tcr.TCRConfig.from_yaml') as mock_from_yaml:
            mock_from_yaml.return_value = TCRConfig(enabled=False)
            runner = TCRRunner()
            
            with patch.object(runner, 'observer') as mock_observer:
                with patch('tcr.tcr.logger') as mock_logger:
                    runner.start()
                    
                    mock_observer.start.assert_not_called()
                    mock_logger.info.assert_called_with("TCR is disabled in configuration")
    
    @patch('subprocess.run')
    def test_start__when_uncommitted_changes__logs_warning_and_starts_observer(self, mock_run, temp_dir):
        with patch('tcr.tcr.TCRConfig.from_yaml') as mock_from_yaml:
            mock_from_yaml.return_value = TCRConfig(
                enabled=True,
                watch_paths=[str(temp_dir)]
            )
            
            with patch('tcr.tcr.Observer') as mock_observer_class:
                mock_observer = Mock()
                mock_observer_class.return_value = mock_observer
                
                runner = TCRRunner()
                
                # Mock git status to show uncommitted changes
                mock_run.return_value = Mock(stdout='M file.py\nA new_file.txt\n', returncode=0)
                
                # Use KeyboardInterrupt to exit the loop after setup
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    with patch('tcr.tcr.logger') as mock_logger:
                        runner.start()
                        
                        # Check that warning was logged
                        mock_logger.warning.assert_called_with(
                            "⚠️ Warning: You have uncommitted changes. Consider committing or stashing them first."
                        )
                
                mock_observer.start.assert_called()
    
    @patch('subprocess.run')
    def test_start__calls_observer_start(self, mock_run, temp_dir):
        with patch('tcr.tcr.TCRConfig.from_yaml') as mock_from_yaml:
            mock_from_yaml.return_value = TCRConfig(
                enabled=True,
                watch_paths=[str(temp_dir)]
            )
            
            with patch('tcr.tcr.Observer') as mock_observer_class:
                mock_observer = Mock()
                mock_observer_class.return_value = mock_observer
                
                runner = TCRRunner()
                
                # Mock git status to show no changes
                mock_run.return_value = Mock(stdout='', returncode=0)
                
                # Use KeyboardInterrupt to exit the loop after one iteration
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    runner.start()
                
                mock_observer.start.assert_called()
    
    @patch('subprocess.run')
    def test_start__when_multiple_watch_paths__all_paths_scheduled(self, mock_run, temp_dir):
        src_dir = temp_dir / 'src'
        tests_dir = temp_dir / 'tests'
        src_dir.mkdir()
        tests_dir.mkdir()
        
        with patch('tcr.tcr.TCRConfig.from_yaml') as mock_from_yaml:
            mock_from_yaml.return_value = TCRConfig(
                enabled=True,
                watch_paths=[str(src_dir), str(tests_dir)]
            )
            
            with patch('tcr.tcr.Observer') as mock_observer_class:
                mock_observer = Mock()
                mock_observer_class.return_value = mock_observer
                
                runner = TCRRunner()
                
                # Mock git status
                mock_run.return_value = Mock(stdout='', returncode=0)
                
                # Use KeyboardInterrupt to exit the loop immediately
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    runner.start()
                
                expected_calls = [
                    call(runner.handler, str(src_dir), recursive=True),
                    call(runner.handler, str(tests_dir), recursive=True)
                ]
                mock_observer.schedule.assert_has_calls(expected_calls, any_order=True)
                
                # Also verify the exact number of calls
                assert mock_observer.schedule.call_count == 2
    
    @patch('subprocess.run')
    def test_start__when_nonexistent_watch_path__path_not_scheduled_with_observer(self, mock_run, temp_dir):
        """Test that only existing paths are scheduled with observer."""
        # Create one existing directory
        existing_dir = temp_dir / 'existing'
        existing_dir.mkdir()
        nonexistent_path = '/nonexistent/path'
        
        with patch('tcr.tcr.TCRConfig.from_yaml') as mock_from_yaml:
            mock_from_yaml.return_value = TCRConfig(
                enabled=True,
                watch_paths=[str(existing_dir), nonexistent_path]
            )
            
            with patch('tcr.tcr.Observer') as mock_observer_class:
                mock_observer = Mock()
                mock_observer_class.return_value = mock_observer
                
                runner = TCRRunner()
                
                # Mock git status to show no changes
                mock_run.return_value = Mock(stdout='', returncode=0)
                
                # Use KeyboardInterrupt to exit the loop immediately
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    runner.start()
                
                mock_observer.schedule.assert_called_once_with(
                    runner.handler, 
                    str(existing_dir), 
                    recursive=True
                )                
                mock_observer.start.assert_called_once()
    
    def test_stop__stops_file_observer(self):
        """Test stopping the runner."""
        runner = TCRRunner()
        
        # Mock the observer
        mock_observer = Mock()
        runner.observer = mock_observer
        
        with patch('tcr.tcr.logger') as mock_logger:
            runner.stop()
            
            mock_observer.stop.assert_called_once()
            # Verify logging calls
            assert any("🛑 Stopping TCR mode..." in str(call) for call in mock_logger.info.call_args_list)
            assert any("TCR mode stopped" in str(call) for call in mock_logger.info.call_args_list)
    
    @patch('subprocess.run')
    def test_run__when_keyboard_interrupt__file_observer_stopped(self, mock_run, temp_dir):
        with patch('tcr.tcr.TCRConfig.from_yaml') as mock_from_yaml:
            mock_from_yaml.return_value = TCRConfig(
                enabled=True,
                watch_paths=[str(temp_dir)]
            )
            
            with patch('tcr.tcr.Observer') as mock_observer_class:
                mock_observer = Mock()
                mock_observer_class.return_value = mock_observer
                
                runner = TCRRunner()
                
                # Mock git status
                mock_run.return_value = Mock(stdout='', returncode=0)
                
                # Simulate KeyboardInterrupt after setup
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    runner.start()
                
                mock_observer.stop.assert_called_once()
