"""Test TCR ignore patterns functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from watchdog.events import FileModifiedEvent

from tcr.tcr import TCRConfig, TCRHandler


class TestIgnorePatterns:
    """Test ignore pattern functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def config_with_patterns(self, temp_dir):
        """Config with specific ignore patterns."""
        return TCRConfig(
            enabled=True,
            watch_paths=[str(temp_dir)],
            test_command='pytest',
            ignore_patterns=[
                'test_*.py', 
                '**/test_*.py', 
                '*_test.py', 
                '**/*_test.py', 
                'tests/**', 
                '**/tests/**', 
                '*.pyc', 
                '**/*.pyc'
            ]
        )
    
    @pytest.fixture
    def handler(self, config_with_patterns):
        return TCRHandler(config_with_patterns)
    
    def test_should_ignore_file__when_test_prefix__returns_true(self, handler):
        """Files starting with test_ should be ignored."""
        assert handler._should_ignore_file(Path('test_module.py'))
        assert handler._should_ignore_file(Path('src/test_something.py'))
        assert handler._should_ignore_file(Path('/full/path/test_file.py'))
    
    def test_should_ignore_file__when_test_suffix__returns_true(self, handler):
        """Files ending with _test.py should be ignored."""
        assert handler._should_ignore_file(Path('module_test.py'))
        assert handler._should_ignore_file(Path('src/something_test.py'))
        assert handler._should_ignore_file(Path('/full/path/file_test.py'))
    
    def test_should_ignore_file__when_in_tests_directory__returns_true(self, handler):
        """Files in tests directories should be ignored."""
        assert handler._should_ignore_file(Path('tests/module.py'))
        assert handler._should_ignore_file(Path('src/tests/something.py'))
        assert handler._should_ignore_file(Path('project/tests/subdir/file.py'))
    
    def test_should_ignore_file__when_pyc_extension__returns_true(self, handler):
        """Compiled Python files should be ignored."""
        assert handler._should_ignore_file(Path('module.pyc'))
        assert handler._should_ignore_file(Path('src/__pycache__/module.pyc'))
    
    def test_should_ignore_file__when_regular_python_file__returns_false(self, handler):
        """Regular Python files should not be ignored."""
        assert not handler._should_ignore_file(Path('module.py'))
        assert not handler._should_ignore_file(Path('src/app.py'))
        assert not handler._should_ignore_file(Path('project/main.py'))
        # Edge case: "test" in the middle of filename
        assert not handler._should_ignore_file(Path('contest.py'))
        assert not handler._should_ignore_file(Path('latest_data.py'))
    
    @patch('subprocess.run')
    def test_on_modified__when_file_matches_ignore_pattern__no_git_check(self, mock_run, handler, temp_dir):
        """When file matches ignore pattern, git status should not be called."""
        test_file = temp_dir / 'test_ignored.py'
        test_file.write_text('# Test file')
        
        event = FileModifiedEvent(str(test_file))
        event.is_directory = False
        
        with patch.object(handler, '_run_tcr_cycle') as mock_cycle:
            handler.on_modified(event)
            # Should not call git status or run TCR cycle
            mock_run.assert_not_called()
            mock_cycle.assert_not_called()
    
    @patch('subprocess.run')
    def test_on_modified__when_file_not_ignored__git_check_called(self, mock_run, handler, temp_dir):
        """When file doesn't match ignore pattern, git status should be called."""
        regular_file = temp_dir / 'module.py'
        regular_file.write_text('# Regular module')
        
        event = FileModifiedEvent(str(regular_file))
        event.is_directory = False
        
        # Mock git status with changes
        mock_run.return_value = Mock(stdout=f'M {regular_file.name}\n', returncode=0)
        
        with patch.object(handler, '_run_tcr_cycle') as mock_cycle:
            handler.on_modified(event)
            # Should call git status
            mock_run.assert_called_once_with(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True
            )
            # Should run TCR cycle
            mock_cycle.assert_called_once()