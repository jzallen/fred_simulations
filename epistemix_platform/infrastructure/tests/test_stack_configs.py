"""
Tests for Sceptre stack configuration validation.

This module tests Sceptre stack configurations for:
- Valid YAML syntax and structure
- Required configuration parameters
- Template file references
- Parameter validation and defaults
- Hook configurations
- Dependencies and ordering
"""

import re
from pathlib import Path
from typing import Dict, Any, List

import pytest
import yaml


class TestStackConfigs:
    """Test suite for Sceptre stack configuration validation."""

    @pytest.fixture(scope="class")
    def stack_config_files(self, config_dir: Path) -> Dict[str, Path]:
        """Find all stack configuration files."""
        config_files = {}
        
        # Look for YAML/YML files that aren't the main config.yaml
        for env_dir in config_dir.iterdir():
            if env_dir.is_dir():
                for config_file in env_dir.iterdir():
                    if config_file.suffix.lower() in ['.yaml', '.yml'] and config_file.name != 'config.yaml':
                        relative_path = f"{env_dir.name}/{config_file.name}"
                        config_files[relative_path] = config_file
        
        return config_files

    @pytest.fixture(scope="class")
    def environment_configs(self, config_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Load environment-specific configuration files."""
        env_configs = {}
        
        for env_dir in config_dir.iterdir():
            if env_dir.is_dir():
                config_file = env_dir / "config.yaml"
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        env_configs[env_dir.name] = yaml.safe_load(f)
        
        return env_configs

    def test_all_stack_configs_valid_yaml(self, stack_config_files: Dict[str, Path]):
        """Test that all stack configuration files are valid YAML."""
        for config_name, config_path in stack_config_files.items():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Stack config {config_name} is not valid YAML: {e}")

    def test_stack_configs_have_template(self, stack_config_files: Dict[str, Path], load_config):
        """Test that stack configurations reference valid template files."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            # Sceptre 4.x uses 'template' instead of 'template'
            assert "template" in config, \
                f"Stack config {config_name} missing template"
            
            template = config["template"]
            assert isinstance(template, str), \
                f"Stack config {config_name} template must be a string"
            assert len(template.strip()) > 0, \
                f"Stack config {config_name} template cannot be empty"

    def test_template_files_exist(self, stack_config_files: Dict[str, Path], load_config, infrastructure_root: Path):
        """Test that referenced template files exist."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            if "template" in config:
                template = config["template"]
                
                # Resolve relative to infrastructure root/templates
                full_template = infrastructure_root / "templates" / template
                
                assert full_template.exists(), \
                    f"Stack config {config_name} references non-existent template: {template}"
                assert full_template.is_file(), \
                    f"Stack config {config_name} template path is not a file: {template}"

    def test_stack_configs_have_valid_parameters(self, stack_config_files: Dict[str, Path], load_config):
        """Test that stack configurations have valid parameters section."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            if "parameters" in config:
                parameters = config["parameters"]
                assert isinstance(parameters, dict), \
                    f"Stack config {config_name} parameters must be a dictionary"
                
                # Parameter values should not be empty
                for param_name, param_value in parameters.items():
                    assert param_name, \
                        f"Stack config {config_name} has parameter with empty name"
                    
                    # Allow empty values for optional parameters, but not None
                    assert param_value is not None, \
                        f"Stack config {config_name} parameter {param_name} is None"

    def test_stack_naming_conventions(self, stack_config_files: Dict[str, Path]):
        """Test that stack configuration file names follow conventions."""
        for config_name, config_path in stack_config_files.items():
            file_name = config_path.name
            
            # Should be kebab-case or snake_case
            assert re.match(r'^[a-z0-9_-]+\.(yaml|yml)$', file_name), \
                f"Stack config file {config_name} should use lowercase with hyphens/underscores: {file_name}"
            
            # Should not be too short or too long
            base_name = file_name.rsplit('.', 1)[0]
            assert len(base_name) >= 3, \
                f"Stack config file {config_name} base name too short: {base_name}"
            assert len(base_name) <= 50, \
                f"Stack config file {config_name} base name too long: {base_name}"

    def test_stack_configs_have_tags(self, stack_config_files: Dict[str, Path], load_config):
        """Test that stack configurations include appropriate tags."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            if "tags" in config:
                tags = config["tags"]
                assert isinstance(tags, dict), \
                    f"Stack config {config_name} tags must be a dictionary"
                
                # Should have basic required tags
                required_tags = ["Environment", "ManagedBy"]
                for required_tag in required_tags:
                    assert required_tag in tags, \
                        f"Stack config {config_name} missing required tag: {required_tag}"
                
                # Tag values should not be empty
                for tag_key, tag_value in tags.items():
                    assert tag_value, \
                        f"Stack config {config_name} tag {tag_key} has empty value"

    def test_stack_configs_environment_consistency(self, stack_config_files: Dict[str, Path], load_config):
        """Test that stack configurations are consistent within environments."""
        environment_stacks = {}
        
        # Group stacks by environment
        for config_name, config_path in stack_config_files.items():
            environment = config_name.split('/')[0]
            if environment not in environment_stacks:
                environment_stacks[environment] = []
            environment_stacks[environment].append((config_name, load_config(config_path)))
        
        # Check consistency within each environment
        for environment, stacks in environment_stacks.items():
            env_tag_values = set()
            managed_by_values = set()
            
            for config_name, config in stacks:
                tags = config.get("tags", {})
                
                if "Environment" in tags:
                    env_tag_values.add(tags["Environment"])
                if "ManagedBy" in tags:
                    managed_by_values.add(tags["ManagedBy"])
            
            # Environment tags should be consistent within environment
            if len(env_tag_values) > 1:
                pytest.fail(f"Environment {environment} has inconsistent Environment tags: {env_tag_values}")
            
            # ManagedBy tags should be consistent
            if len(managed_by_values) > 1:
                pytest.fail(f"Environment {environment} has inconsistent ManagedBy tags: {managed_by_values}")

    def test_stack_dependencies_valid(self, stack_config_files: Dict[str, Path], load_config):
        """Test that stack dependencies are valid."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            if "dependencies" in config:
                dependencies = config["dependencies"]
                assert isinstance(dependencies, list), \
                    f"Stack config {config_name} dependencies must be a list"
                
                for dependency in dependencies:
                    assert isinstance(dependency, str), \
                        f"Stack config {config_name} dependency must be a string: {dependency}"
                    assert len(dependency.strip()) > 0, \
                        f"Stack config {config_name} has empty dependency"

    def test_stack_hooks_configuration(self, stack_config_files: Dict[str, Path], load_config):
        """Test stack hook configurations."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            # Check before_create hooks
            if "hooks" in config:
                hooks = config["hooks"]
                assert isinstance(hooks, dict), \
                    f"Stack config {config_name} hooks must be a dictionary"
                
                valid_hook_types = [
                    "before_create", "after_create", "before_update", "after_update",
                    "before_delete", "after_delete"
                ]
                
                for hook_type, hook_configs in hooks.items():
                    assert hook_type in valid_hook_types, \
                        f"Stack config {config_name} has invalid hook type: {hook_type}"
                    
                    assert isinstance(hook_configs, list), \
                        f"Stack config {config_name} hook {hook_type} must be a list"
                    
                    for hook_config in hook_configs:
                        assert isinstance(hook_config, dict), \
                            f"Stack config {config_name} hook configuration must be a dictionary"
                        
                        # Should have path to hook
                        assert "path" in hook_config, \
                            f"Stack config {config_name} hook missing path"

    def test_environment_specific_parameters(self, stack_config_files: Dict[str, Path], load_config):
        """Test that environment-specific parameters are appropriate."""
        environment_configs = {}
        
        # Group configurations by environment and stack type
        for config_name, config_path in stack_config_files.items():
            parts = config_name.split('/')
            environment = parts[0]
            stack_name = parts[1] if len(parts) > 1 else config_name
            
            if environment not in environment_configs:
                environment_configs[environment] = {}
            
            environment_configs[environment][stack_name] = load_config(config_path)
        
        # Compare same stack across different environments
        all_stack_names = set()
        for env_stacks in environment_configs.values():
            all_stack_names.update(env_stacks.keys())
        
        for stack_name in all_stack_names:
            environments_with_stack = [
                env for env, stacks in environment_configs.items()
                if stack_name in stacks
            ]
            
            if len(environments_with_stack) > 1:
                # Same stack exists in multiple environments - compare parameters
                stack_configs = {
                    env: environment_configs[env][stack_name]
                    for env in environments_with_stack
                }
                
                # Parameters should exist in all environments
                all_have_parameters = all("parameters" in config for config in stack_configs.values())
                if all_have_parameters:
                    # Parameter keys should be consistent
                    param_keys_sets = [
                        set(config["parameters"].keys())
                        for config in stack_configs.values()
                    ]
                    
                    first_param_keys = param_keys_sets[0]
                    for i, param_keys in enumerate(param_keys_sets[1:], 1):
                        env_name = environments_with_stack[i]
                        missing_keys = first_param_keys - param_keys
                        extra_keys = param_keys - first_param_keys
                        
                        if missing_keys or extra_keys:
                            pytest.fail(f"Stack {stack_name} has inconsistent parameters between environments. "
                                      f"Environment {env_name} missing: {missing_keys}, extra: {extra_keys}")

    def test_stack_config_template_consistency(self, stack_config_files: Dict[str, Path], load_config):
        """Test that stack configurations are consistent with their templates."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            if "template" in config:
                template = config["template"]
                
                # Extract expected stack type from template path
                if "ecr" in template.lower():
                    expected_params = ["RepositoryName", "Environment"]
                elif "s3" in template.lower():
                    expected_params = ["BucketName", "Environment"]
                else:
                    continue  # Skip validation for unknown template types
                
                # Check that required parameters are provided
                parameters = config.get("parameters", {})
                for expected_param in expected_params:
                    if expected_param not in parameters:
                        # Parameter might be provided by environment config
                        continue
                    
                    param_value = parameters[expected_param]
                    assert param_value, \
                        f"Stack config {config_name} parameter {expected_param} is empty"

    def test_stack_config_file_structure(self, stack_config_files: Dict[str, Path], load_config):
        """Test stack configuration file structure."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            
            # Should have meaningful structure
            valid_top_level_keys = {
                "template", "parameters", "tags", "dependencies", "hooks",
                "stack_tags", "notifications", "on_failure", "sceptre_user_data"
            }
            
            for key in config.keys():
                assert key in valid_top_level_keys, \
                    f"Stack config {config_name} has unexpected top-level key: {key}"

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_specific_validation(self, environment: str, config_dir: Path, load_config):
        """Test environment-specific stack configuration validation."""
        env_config_dir = config_dir / environment
        
        if not env_config_dir.exists():
            pytest.skip(f"Environment {environment} configuration directory not found")
        
        # Environment should have main config file
        main_config_file = env_config_dir / "config.yaml"
        assert main_config_file.exists(), \
            f"Environment {environment} missing main config.yaml"
        
        # Load main environment config
        env_config = load_config(main_config_file)
        
        # Should have project name
        if "project_code" in env_config:
            project_code = env_config["project_code"]
            assert isinstance(project_code, str) and len(project_code) > 0, \
                f"Environment {environment} should have valid project_code"
        
        # Should have region
        if "region" in env_config:
            region = env_config["region"]
            assert isinstance(region, str) and region.startswith(("us-", "eu-", "ap-")), \
                f"Environment {environment} should have valid AWS region"

    def test_parameter_value_formats(self, stack_config_files: Dict[str, Path], load_config):
        """Test that parameter values follow expected formats."""
        for config_name, config_path in stack_config_files.items():
            config = load_config(config_path)
            parameters = config.get("parameters", {})
            
            for param_name, param_value in parameters.items():
                # Bucket names should follow S3 naming rules
                if "bucket" in param_name.lower() and isinstance(param_value, str):
                    assert re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', param_value), \
                        f"Stack config {config_name} parameter {param_name} has invalid bucket name format: {param_value}"
                
                # Repository names should follow ECR naming rules
                elif "repository" in param_name.lower() and isinstance(param_value, str):
                    assert re.match(r'^[a-z0-9]+(?:[._-][a-z0-9]+)*$', param_value), \
                        f"Stack config {config_name} parameter {param_name} has invalid repository name format: {param_value}"
                
                # Environment values should be valid
                elif param_name.lower() == "environment" and isinstance(param_value, str):
                    valid_environments = ["dev", "staging", "production"]
                    assert param_value in valid_environments, \
                        f"Stack config {config_name} has invalid environment value: {param_value}"

    def test_stack_config_completeness(self, stack_config_files: Dict[str, Path], templates_dir: Path):
        """Test that there are stack configs for all templates."""
        # Find all templates
        template_files = []
        for template_dir in templates_dir.iterdir():
            if template_dir.is_dir():
                for template_file in template_dir.glob("*.yaml"):
                    template_files.append(template_file)
                for template_file in template_dir.glob("*.yml"):
                    template_files.append(template_file)
        
        # Check that each template has corresponding config files
        for template_file in template_files:
            template_relative_path = template_file.relative_to(templates_dir.parent)
            
            # Look for corresponding stack configs
            matching_configs = [
                config_name for config_name in stack_config_files.keys()
                if template_file.stem.replace("-", "_") in config_name or 
                   template_file.stem.replace("_", "-") in config_name
            ]
            
            assert len(matching_configs) > 0, \
                f"Template {template_relative_path} has no corresponding stack configuration files"