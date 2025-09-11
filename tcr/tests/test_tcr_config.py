"""Tests for TCRConfig class."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from tcr.tcr import TCRConfig


class TestTCRConfig:
    """Test suite for TCRConfig class."""
    
    def test_init__when_no_args__default_values_set(self):
        """Test default configuration values."""
        config = TCRConfig()
        assert config.enabled is True
        assert config.watch_paths == []
        assert config.test_command == 'poetry run pytest -xvs'
        assert config.test_timeout == 30
        assert config.commit_prefix == 'TCR'
        assert config.revert_on_failure is True
        assert config.debounce_seconds == 2.0

    def test_init__when_custom_values_provided__values_set_correctly(self):
        """Test creating config with custom values."""
        config = TCRConfig(
            enabled=False,
            watch_paths=['src', 'tests'],
            test_command='pytest',
            test_timeout=60,
            commit_prefix='AUTO',
            revert_on_failure=False,
            debounce_seconds=5.0
        )
        assert config.enabled is False
        assert config.watch_paths == ['src', 'tests']
        assert config.test_command == 'pytest'
        assert config.test_timeout == 60
        assert config.commit_prefix == 'AUTO'
        assert config.revert_on_failure is False
        assert config.debounce_seconds == 5.0

    def test_from_yaml__when_tcr_section_present__config_properties_set(self):
        """Test loading config from YAML file with 'tcr' section."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                'tcr': {
                    'enabled': False,
                    'watch_paths': ['app', 'lib'],
                    'test_command': 'make test',
                    'test_timeout': 45,
                    'commit_prefix': 'AUTOCOMMIT',
                    'revert_on_failure': False,
                    'debounce_seconds': 3.5
                }
            }
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)
        
        try:
            config = TCRConfig.from_yaml(temp_path)
            assert config.enabled is False
            assert config.watch_paths == ['app', 'lib']
            assert config.test_command == 'make test'
            assert config.test_timeout == 45
            assert config.commit_prefix == 'AUTOCOMMIT'
            assert config.revert_on_failure is False
            assert config.debounce_seconds == 3.5
        finally:
            temp_path.unlink()

    def test_from_yaml__when_no_tcr_section__config_properties_assumed_to_global(self):
        """Test loading config from YAML file without 'tcr' section."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                'enabled': True,
                'watch_paths': ['code'],
                'test_command': 'npm test',
                'test_timeout': 20
            }
            yaml.dump(yaml_content, f)
            temp_path = Path(f.name)
        
        try:
            config = TCRConfig.from_yaml(temp_path)
            assert config.enabled is True
            assert config.watch_paths == ['code']
            assert config.test_command == 'npm test'
            assert config.test_timeout == 20
            # Check defaults for unspecified values
            assert config.commit_prefix == 'TCR'
            assert config.revert_on_failure is True
            assert config.debounce_seconds == 2.0
        finally:
            temp_path.unlink()

    def test_from_yaml__when_nonexistent_file__returns_defaults(self):
        """Test loading config from nonexistent YAML file returns defaults."""
        config = TCRConfig.from_yaml(Path('/nonexistent/path/config.yaml'))
        assert config.enabled is True
        assert config.watch_paths == []
        assert config.test_command == 'poetry run pytest -xvs'
        assert config.test_timeout == 30
        assert config.commit_prefix == 'TCR'
        assert config.revert_on_failure is True
        assert config.debounce_seconds == 2.0

    def test_from_yaml__when_empty_file__returns_defaults(self):
        """Test loading config from empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('')
            temp_path = Path(f.name)
        
        try:
            config = TCRConfig.from_yaml(temp_path)
            assert config.enabled is True
            assert config.watch_paths == []
            assert config.test_command == 'poetry run pytest -xvs'
            assert config.test_timeout == 30
            assert config.commit_prefix == 'TCR'
            assert config.revert_on_failure is True
            assert config.debounce_seconds == 2.0
        finally:
            temp_path.unlink()
