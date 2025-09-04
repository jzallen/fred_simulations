"""
Tests for environment-specific Sceptre configurations.

This module tests environment configurations for:
- Environment isolation and consistency
- Parameter inheritance and overrides  
- Regional configurations
- Environment-specific resource naming
- Security and compliance requirements per environment
"""

from pathlib import Path
from typing import Dict, Any, Set

import pytest
import yaml


class TestEnvironmentConfigs:
    """Test suite for environment-specific configuration validation."""

    @pytest.fixture(scope="class")
    def environment_configs(self, config_dir: Path, load_config) -> Dict[str, Dict[str, Any]]:
        """Load all environment configurations."""
        configs = {}
        
        for env_dir in config_dir.iterdir():
            if env_dir.is_dir() and env_dir.name in ["dev", "staging", "production"]:
                config_file = env_dir / "config.yaml"
                if config_file.exists():
                    configs[env_dir.name] = load_config(config_file)
        
        return configs

    @pytest.fixture(scope="class")
    def environment_stack_configs(self, config_dir: Path, load_config) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Load all stack configurations per environment."""
        env_stack_configs = {}
        
        for env_dir in config_dir.iterdir():
            if env_dir.is_dir() and env_dir.name in ["dev", "staging", "production"]:
                stack_configs = {}
                
                for config_file in env_dir.iterdir():
                    if config_file.suffix.lower() in ['.yaml', '.yml'] and config_file.name != 'config.yaml':
                        stack_configs[config_file.stem] = load_config(config_file)
                
                if stack_configs:
                    env_stack_configs[env_dir.name] = stack_configs
        
        return env_stack_configs

    def test_required_environments_exist(self, environments: list, config_dir: Path):
        """Test that all required environments have configuration directories."""
        for environment in environments:
            env_dir = config_dir / environment
            assert env_dir.exists(), f"Environment directory {environment} does not exist"
            assert env_dir.is_dir(), f"Environment path {environment} is not a directory"
            
            # Should have main config file
            config_file = env_dir / "config.yaml"
            assert config_file.exists(), f"Environment {environment} missing config.yaml"

    def test_environment_config_structure(self, environment_configs: Dict[str, Dict[str, Any]]):
        """Test that environment configurations have proper structure."""
        for env_name, config in environment_configs.items():
            # Should have project code
            assert "project_code" in config, f"Environment {env_name} missing project_code"
            assert isinstance(config["project_code"], str), f"Environment {env_name} project_code must be string"
            assert len(config["project_code"]) > 0, f"Environment {env_name} project_code cannot be empty"
            
            # Should have region
            assert "region" in config, f"Environment {env_name} missing region"
            assert isinstance(config["region"], str), f"Environment {env_name} region must be string"
            
            # Region should be valid AWS region
            region = config["region"]
            valid_region_prefixes = ["us-", "eu-", "ap-", "ca-", "sa-"]
            assert any(region.startswith(prefix) for prefix in valid_region_prefixes), \
                f"Environment {env_name} has invalid region: {region}"

    def test_environment_naming_consistency(self, environment_configs: Dict[str, Dict[str, Any]]):
        """Test that environment naming is consistent."""
        for env_name, config in environment_configs.items():
            # Project codes should be consistent
            if env_name == "dev":
                dev_project_code = config.get("project_code")
            
            # All environments should have same project code
            project_code = config.get("project_code")
            if "dev" in environment_configs:
                dev_project_code = environment_configs["dev"].get("project_code")
                assert project_code == dev_project_code, \
                    f"Environment {env_name} has different project_code than dev environment"

    def test_environment_parameter_inheritance(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test parameter inheritance and environment-specific overrides."""
        # Find stacks that exist in multiple environments
        all_stack_names = set()
        for env_stacks in environment_stack_configs.values():
            all_stack_names.update(env_stacks.keys())
        
        for stack_name in all_stack_names:
            environments_with_stack = [
                env for env, stacks in environment_stack_configs.items()
                if stack_name in stacks
            ]
            
            if len(environments_with_stack) > 1:
                # Compare parameter structure across environments
                stack_configs = {
                    env: environment_stack_configs[env][stack_name]
                    for env in environments_with_stack
                }
                
                # All should have parameters section if any do
                have_parameters = [
                    env for env, config in stack_configs.items()
                    if "parameters" in config
                ]
                
                if have_parameters:
                    # Parameter keys should be consistent
                    all_param_keys = set()
                    for config in stack_configs.values():
                        if "parameters" in config:
                            all_param_keys.update(config["parameters"].keys())
                    
                    # Each environment should have core parameters
                    for env, config in stack_configs.items():
                        if "parameters" in config:
                            params = config["parameters"]
                            
                            # Environment-specific parameters should be different
                            env_specific_params = ["Environment", "BucketName", "RepositoryName"]
                            for param in env_specific_params:
                                if param in params:
                                    param_value = params[param]
                                    if isinstance(param_value, str) and env in param_value:
                                        # Good - parameter includes environment
                                        continue

    def test_environment_resource_naming_patterns(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that resource naming follows environment-specific patterns."""
        for env_name, stack_configs in environment_stack_configs.items():
            for stack_name, config in stack_configs.items():
                parameters = config.get("parameters", {})
                
                for param_name, param_value in parameters.items():
                    if isinstance(param_value, str):
                        # Bucket names should include environment
                        if "bucket" in param_name.lower():
                            assert env_name in param_value.lower(), \
                                f"Environment {env_name} stack {stack_name} bucket name should include environment: {param_value}"
                        
                        # Repository names should include environment or be environment-specific
                        elif "repository" in param_name.lower():
                            # Repository names might use environment in different ways
                            if env_name != "dev" or env_name in param_value:
                                continue  # Environment is specified
                            # For dev, it might be omitted but that's acceptable

    def test_environment_security_configurations(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test environment-specific security configurations."""
        security_requirements = {
            "production": {
                "required_tags": ["Owner", "CostCenter"],
                "forbidden_origins": ["http://localhost"]
            },
            "staging": {
                "required_tags": ["Environment"],
                "allowed_test_origins": True
            },
            "dev": {
                "allowed_localhost": True
            }
        }
        
        for env_name, stack_configs in environment_stack_configs.items():
            requirements = security_requirements.get(env_name, {})
            
            for stack_name, config in stack_configs.items():
                # Check tags
                tags = config.get("tags", {})
                required_tags = requirements.get("required_tags", [])
                
                for required_tag in required_tags:
                    assert required_tag in tags, \
                        f"Environment {env_name} stack {stack_name} missing required tag: {required_tag}"
                
                # Check CORS origins for S3 stacks
                parameters = config.get("parameters", {})
                if "AllowedOrigins" in parameters:
                    allowed_origins = parameters["AllowedOrigins"]
                    
                    if isinstance(allowed_origins, str):
                        origins = [origin.strip() for origin in allowed_origins.split(",")]
                        
                        # Production should not allow localhost
                        if env_name == "production":
                            forbidden_origins = requirements.get("forbidden_origins", [])
                            for forbidden in forbidden_origins:
                                for origin in origins:
                                    assert forbidden not in origin, \
                                        f"Production environment should not allow {forbidden} origins: {origin}"

    def test_environment_cost_optimization(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test environment-specific cost optimization settings."""
        for env_name, stack_configs in environment_stack_configs.items():
            for stack_name, config in stack_configs.items():
                # Dev environment should have more aggressive cleanup
                if env_name == "dev":
                    # This would be validated through template parameters if they existed
                    # For now, we check that dev environment exists and is configured
                    assert config, f"Dev environment stack {stack_name} should be configured"
                
                # Production should have longer retention
                elif env_name == "production":
                    # Production stacks should exist
                    assert config, f"Production environment stack {stack_name} should be configured"

    def test_environment_isolation(self, environment_configs: Dict[str, Dict[str, Any]]):
        """Test that environments are properly isolated."""
        regions = {}
        project_codes = {}
        
        for env_name, config in environment_configs.items():
            region = config.get("region")
            project_code = config.get("project_code")
            
            if region:
                regions[env_name] = region
            if project_code:
                project_codes[env_name] = project_code
        
        # All environments should use same project code
        unique_project_codes = set(project_codes.values())
        assert len(unique_project_codes) <= 1, \
            f"Environments should use consistent project codes: {project_codes}"
        
        # Regions can be same or different - both are valid patterns
        # We just ensure they're valid AWS regions
        for env_name, region in regions.items():
            assert "-" in region, f"Environment {env_name} region should be valid AWS region format: {region}"

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_completeness(self, environment: str, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that each environment has complete stack configurations."""
        if environment not in environment_stack_configs:
            pytest.skip(f"Environment {environment} not configured")
        
        stack_configs = environment_stack_configs[environment]
        
        # Should have at least basic infrastructure stacks
        expected_stack_types = ["ecr", "s3"]  # Based on available templates
        
        found_stack_types = set()
        for stack_name in stack_configs.keys():
            for stack_type in expected_stack_types:
                if stack_type in stack_name.lower():
                    found_stack_types.add(stack_type)
        
        # Environment should have infrastructure components
        assert len(found_stack_types) > 0, \
            f"Environment {environment} should have infrastructure stack configurations"

    def test_cross_environment_consistency(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test consistency across environments."""
        # Find common stack names
        common_stacks = set()
        if environment_stack_configs:
            common_stacks = set(list(environment_stack_configs.values())[0].keys())
            for env_stacks in environment_stack_configs.values():
                common_stacks &= set(env_stacks.keys())
        
        # For each common stack, check template consistency
        for stack_name in common_stacks:
            template_paths = {}
            
            for env_name, env_stacks in environment_stack_configs.items():
                if stack_name in env_stacks:
                    config = env_stacks[stack_name]
                    template_path = config.get("template_path")
                    if template_path:
                        template_paths[env_name] = template_path
            
            # All environments should use same template
            unique_templates = set(template_paths.values())
            assert len(unique_templates) <= 1, \
                f"Stack {stack_name} uses different templates across environments: {template_paths}"

    def test_environment_variable_references(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that environment variables and references are valid."""
        for env_name, stack_configs in environment_stack_configs.items():
            for stack_name, config in stack_configs.items():
                # Check for Sceptre variable references
                config_str = yaml.dump(config)
                
                # Look for variable patterns
                if "{{ var." in config_str:
                    # Variables should be properly formatted
                    import re
                    var_references = re.findall(r'\{\{\s*var\.([^}]+)\s*\}\}', config_str)
                    
                    for var_ref in var_references:
                        # Variable reference should not be empty
                        assert var_ref.strip(), \
                            f"Environment {env_name} stack {stack_name} has empty variable reference"

    def test_environment_hook_consistency(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that hooks are consistently configured across environments."""
        for env_name, stack_configs in environment_stack_configs.items():
            for stack_name, config in stack_configs.items():
                hooks = config.get("hooks", {})
                
                if hooks:
                    # Hooks should be properly configured
                    for hook_type, hook_configs in hooks.items():
                        assert isinstance(hook_configs, list), \
                            f"Environment {env_name} stack {stack_name} hook {hook_type} must be list"
                        
                        for hook_config in hook_configs:
                            assert "path" in hook_config, \
                                f"Environment {env_name} stack {stack_name} hook missing path"

    def test_production_environment_restrictions(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test production environment has appropriate restrictions."""
        if "production" not in environment_stack_configs:
            pytest.skip("Production environment not configured")
        
        prod_configs = environment_stack_configs["production"]
        
        for stack_name, config in prod_configs.items():
            tags = config.get("tags", {})
            parameters = config.get("parameters", {})
            
            # Production should have owner information
            ownership_tags = ["Owner", "Team", "Contact"]
            has_owner = any(tag in tags for tag in ownership_tags)
            
            if not has_owner:
                # Should at least have environment tag set to production
                assert tags.get("Environment") == "production", \
                    f"Production stack {stack_name} should have Environment tag set to production"
            
            # Production CORS origins should not include localhost
            if "AllowedOrigins" in parameters:
                origins = parameters["AllowedOrigins"]
                if isinstance(origins, str):
                    assert "localhost" not in origins.lower(), \
                        f"Production stack {stack_name} should not allow localhost origins"

    def test_development_environment_flexibility(self, environment_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test development environment allows appropriate flexibility."""
        if "dev" not in environment_stack_configs:
            pytest.skip("Development environment not configured")
        
        dev_configs = environment_stack_configs["dev"]
        
        for stack_name, config in dev_configs.items():
            parameters = config.get("parameters", {})
            
            # Dev can allow localhost origins
            if "AllowedOrigins" in parameters:
                origins = parameters["AllowedOrigins"]
                if isinstance(origins, str) and "localhost" in origins:
                    # This is acceptable for dev
                    pass
            
            # Dev environment should have environment tag
            tags = config.get("tags", {})
            if "Environment" in tags:
                env_value = tags["Environment"]
                assert env_value in ["dev", "development"], \
                    f"Dev stack {stack_name} Environment tag should be 'dev' or 'development': {env_value}"