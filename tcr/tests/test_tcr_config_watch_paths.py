"""Tests for TCRConfig watch_paths validation."""

import tempfile
from pathlib import Path

import yaml

from tcr.tcr import TCRConfig


class TestTCRConfigWatchPaths:
    """Test suite for TCRConfig watch_paths validation."""

    def test_init__watch_paths_never_empty__defaults_to_current_dir(self):
        """Test that watch_paths always has at least one path (current directory)."""
        config = TCRConfig()
        assert config.watch_paths == ['.']

    def test_from_yaml__when_no_watch_paths__defaults_to_current_dir(self):
        """Test that watch_paths defaults to current directory when not specified."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                'tcr': {
                    'enabled': True,
                    'test_command': 'pytest'
                }
            }
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)

        try:
            config = TCRConfig.from_yaml(temp_path)
            assert config.watch_paths == ['.']
        finally:
            temp_path.unlink()

    def test_init__when_empty_watch_paths_provided__uses_current_dir(self):
        """Test that empty watch_paths list is replaced with current directory."""
        config = TCRConfig(watch_paths=[])
        assert config.watch_paths == ['.']

    def test_from_yaml__when_empty_watch_paths__uses_current_dir(self):
        """Test that empty watch_paths in YAML is replaced with current directory."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                'tcr': {
                    'enabled': True,
                    'watch_paths': [],
                    'test_command': 'pytest'
                }
            }
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)

        try:
            config = TCRConfig.from_yaml(temp_path)
            assert config.watch_paths == ['.']
        finally:
            temp_path.unlink()