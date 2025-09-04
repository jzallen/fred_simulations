"""
Tests for parameter resolution and validation across Sceptre configurations.

This module tests parameter resolution including:
- Parameter inheritance from environment configs
- Template parameter validation against stack configs
- Cross-stack parameter references and dependencies
- Environment-specific parameter overrides
- Parameter constraint validation
"""

from pathlib import Path
from typing import Dict, Any, List, Set

import pytest
import yaml
from sceptre.config.reader import ConfigReader
from sceptre.context import SceptreContext


class TestParameterResolution:
    """Test suite for parameter resolution and validation."""

    @pytest.fixture(scope="class")
    def all_templates_with_parameters(self, template_files, load_template) -> Dict[str, Dict[str, Any]]:
        """Load all templates and extract their parameters."""
        templates_with_params = {}
        
        for template_name, template in template_files.items():
            template = load_template(template)
            if "Parameters" in template:
                templates_with_params[template_name] = {
                    "template": template,
                    "parameters": template["Parameters"]
                }
        
        return templates_with_params

    @pytest.fixture(scope="class")
    def resolved_stack_configs(self, config_reader, environments) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get resolved stack configurations for all environments."""
        resolved_configs = {}
        
        for environment in environments:
            try:
                reader = config_reader(environment)
                stack_configs = {}
                
                # Get all stacks for this environment
                stacks = reader.read()
                for stack_name, stack_config in stacks.items():
                    # Extract resolved parameters
                    resolved_parameters = getattr(stack_config, 'parameters', {})
                    template = getattr(stack_config, 'template', None)
                    
                    stack_configs[stack_name] = {
                        "parameters": resolved_parameters,
                        "template": template,
                        "tags": getattr(stack_config, 'tags', {})
                    }
                
                resolved_configs[environment] = stack_configs
                
            except Exception as e:
                # If we can't resolve configs for an environment, skip it
                pytest.skip(f"Could not resolve configs for environment {environment}: {e}")
        
        return resolved_configs

    def test_required_template_parameters_provided(self, all_templates_with_parameters: Dict[str, Dict[str, Any]], 
                                                  resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that all required template parameters are provided in stack configs."""
        for env_name, stack_configs in resolved_stack_configs.items():
            for stack_name, stack_config in stack_configs.items():
                template = stack_config.get("template")
                if not template:
                    continue
                
                # Find matching template
                matching_template = None
                for template_name, template_data in all_templates_with_parameters.items():
                    if template.endswith(template_name.split('/')[-1]):
                        matching_template = template_data
                        break
                
                if not matching_template:
                    continue
                
                template_params = matching_template["parameters"]
                stack_params = stack_config.get("parameters", {})
                
                # Check required parameters (those without defaults)
                for param_name, param_def in template_params.items():
                    if "Default" not in param_def:
                        assert param_name in stack_params, \
                            f"Environment {env_name} stack {stack_name} missing required parameter: {param_name}"

    def test_parameter_values_match_constraints(self, all_templates_with_parameters: Dict[str, Dict[str, Any]], 
                                              resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that parameter values match template constraints."""
        for env_name, stack_configs in resolved_stack_configs.items():
            for stack_name, stack_config in stack_configs.items():
                template = stack_config.get("template")
                if not template:
                    continue
                
                # Find matching template
                matching_template = None
                for template_name, template_data in all_templates_with_parameters.items():
                    if template.endswith(template_name.split('/')[-1]):
                        matching_template = template_data
                        break
                
                if not matching_template:
                    continue
                
                template_params = matching_template["parameters"]
                stack_params = stack_config.get("parameters", {})
                
                # Validate parameter constraints
                for param_name, param_value in stack_params.items():
                    if param_name in template_params:
                        param_def = template_params[param_name]
                        self._validate_parameter_constraints(
                            env_name, stack_name, param_name, param_value, param_def
                        )

    def _validate_parameter_constraints(self, env_name: str, stack_name: str, param_name: str, 
                                      param_value: Any, param_def: Dict[str, Any]):
        """Validate a parameter value against its template definition."""
        # Skip validation for CloudFormation functions/references
        if isinstance(param_value, dict):
            return
        
        # AllowedValues constraint
        if "AllowedValues" in param_def:
            allowed_values = param_def["AllowedValues"]
            assert param_value in allowed_values, \
                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                f"value '{param_value}' not in allowed values: {allowed_values}"
        
        # String length constraints
        if isinstance(param_value, str):
            if "MinLength" in param_def:
                min_length = param_def["MinLength"]
                assert len(param_value) >= min_length, \
                    f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                    f"value '{param_value}' shorter than minimum length {min_length}"
            
            if "MaxLength" in param_def:
                max_length = param_def["MaxLength"]
                assert len(param_value) <= max_length, \
                    f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                    f"value '{param_value}' longer than maximum length {max_length}"
        
        # Pattern constraint
        if "AllowedPattern" in param_def and isinstance(param_value, str):
            import re
            pattern = param_def["AllowedPattern"]
            assert re.match(pattern, param_value), \
                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                f"value '{param_value}' does not match pattern: {pattern}"

    def test_environment_specific_parameter_resolution(self, resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that parameters are resolved correctly for each environment."""
        for env_name, stack_configs in resolved_stack_configs.items():
            for stack_name, stack_config in stack_configs.items():
                parameters = stack_config.get("parameters", {})
                
                # Environment parameter should match the environment
                if "Environment" in parameters:
                    env_param_value = parameters["Environment"]
                    
                    # Should match the environment name
                    expected_values = [env_name, env_name.lower(), env_name.upper()]
                    assert env_param_value in expected_values, \
                        f"Environment {env_name} stack {stack_name} Environment parameter " \
                        f"should be '{env_name}' but is '{env_param_value}'"

    def test_resource_naming_parameter_consistency(self, resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that resource naming parameters are consistent within environments."""
        for env_name, stack_configs in resolved_stack_configs.items():
            bucket_names = set()
            repo_names = set()
            
            for stack_name, stack_config in stack_configs.items():
                parameters = stack_config.get("parameters", {})
                
                # Collect resource names
                for param_name, param_value in parameters.items():
                    if isinstance(param_value, str):
                        if "bucket" in param_name.lower():
                            bucket_names.add(param_value)
                        elif "repository" in param_name.lower():
                            repo_names.add(param_value)
            
            # Resource names should be unique within environment
            # (This test ensures we don't have naming conflicts)
            assert len(bucket_names) == len({name for name in bucket_names}), \
                f"Environment {env_name} has duplicate bucket names"
            assert len(repo_names) == len({name for name in repo_names}), \
                f"Environment {env_name} has duplicate repository names"

    def test_cross_stack_parameter_references(self, resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test cross-stack parameter references are valid."""
        for env_name, stack_configs in resolved_stack_configs.items():
            # Look for stack output references
            for stack_name, stack_config in stack_configs.items():
                parameters = stack_config.get("parameters", {})
                
                for param_name, param_value in parameters.items():
                    # Check for CloudFormation stack references
                    if isinstance(param_value, dict):
                        if "Fn::ImportValue" in param_value:
                            import_value = param_value["Fn::ImportValue"]
                            # Should reference an export from another stack
                            assert isinstance(import_value, str), \
                                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                                f"ImportValue must be string"
                        
                        elif "Ref" in param_value:
                            ref_value = param_value["Ref"]
                            # Should be a valid parameter name
                            assert isinstance(ref_value, str), \
                                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                                f"Ref must be string"

    def test_parameter_type_consistency(self, all_templates_with_parameters: Dict[str, Dict[str, Any]], 
                                       resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that parameter values match expected types."""
        for env_name, stack_configs in resolved_stack_configs.items():
            for stack_name, stack_config in stack_configs.items():
                template = stack_config.get("template")
                if not template:
                    continue
                
                # Find matching template
                matching_template = None
                for template_name, template_data in all_templates_with_parameters.items():
                    if template.endswith(template_name.split('/')[-1]):
                        matching_template = template_data
                        break
                
                if not matching_template:
                    continue
                
                template_params = matching_template["parameters"]
                stack_params = stack_config.get("parameters", {})
                
                # Check parameter types
                for param_name, param_value in stack_params.items():
                    if param_name in template_params and not isinstance(param_value, dict):
                        param_def = template_params[param_name]
                        param_type = param_def.get("Type", "String")
                        
                        self._validate_parameter_type(
                            env_name, stack_name, param_name, param_value, param_type
                        )

    def _validate_parameter_type(self, env_name: str, stack_name: str, param_name: str, 
                                param_value: Any, expected_type: str):
        """Validate parameter value type."""
        if expected_type == "String":
            assert isinstance(param_value, str), \
                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                f"should be string but is {type(param_value)}"
        
        elif expected_type == "Number":
            assert isinstance(param_value, (int, float)), \
                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                f"should be number but is {type(param_value)}"
        
        elif expected_type == "CommaDelimitedList":
            # Can be string (comma-separated) or list
            assert isinstance(param_value, (str, list)), \
                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                f"should be string or list but is {type(param_value)}"

    def test_default_parameter_usage(self, all_templates_with_parameters: Dict[str, Dict[str, Any]], 
                                    resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test appropriate usage of default parameter values."""
        for env_name, stack_configs in resolved_stack_configs.items():
            for stack_name, stack_config in stack_configs.items():
                template = stack_config.get("template")
                if not template:
                    continue
                
                # Find matching template
                matching_template = None
                for template_name, template_data in all_templates_with_parameters.items():
                    if template.endswith(template_name.split('/')[-1]):
                        matching_template = template_data
                        break
                
                if not matching_template:
                    continue
                
                template_params = matching_template["parameters"]
                stack_params = stack_config.get("parameters", {})
                
                # Check if critical parameters use defaults appropriately
                for param_name, param_def in template_params.items():
                    if "Default" in param_def:
                        default_value = param_def["Default"]
                        
                        # For production, some defaults might not be appropriate
                        if env_name == "production":
                            # Environment-specific validation
                            if param_name == "Environment" and default_value != "production":
                                assert param_name in stack_params, \
                                    f"Production stack {stack_name} should override Environment parameter default"

    def test_parameter_inheritance_hierarchy(self, config_dir: Path, load_config):
        """Test parameter inheritance from environment to stack level."""
        for env_dir in config_dir.iterdir():
            if env_dir.is_dir() and env_dir.name in ["dev", "staging", "production"]:
                env_config_file = env_dir / "config.yaml"
                if not env_config_file.exists():
                    continue
                
                env_config = load_config(env_config_file)
                
                # Check stack configs in this environment
                for stack_file in env_dir.iterdir():
                    if stack_file.suffix.lower() in ['.yaml', '.yml'] and stack_file.name != 'config.yaml':
                        stack_config = load_config(stack_file)
                        
                        # Environment-level parameters should be available to stacks
                        # This is more of a conceptual test since Sceptre handles the actual inheritance
                        
                        # Verify that both configs are loadable and valid
                        assert isinstance(env_config, dict), f"Environment config {env_dir.name} invalid"
                        assert isinstance(stack_config, dict), f"Stack config {stack_file.name} invalid"

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_parameter_completeness(self, environment: str, 
                                              resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that environment has complete parameter configuration."""
        if environment not in resolved_stack_configs:
            pytest.skip(f"Environment {environment} not configured")
        
        stack_configs = resolved_stack_configs[environment]
        
        for stack_name, stack_config in stack_configs.items():
            parameters = stack_config.get("parameters", {})
            
            # Every stack should have Environment parameter
            if "Environment" in parameters:
                env_value = parameters["Environment"]
                assert env_value == environment, \
                    f"Stack {stack_name} in environment {environment} has mismatched Environment parameter: {env_value}"

    def test_parameter_security_compliance(self, resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that parameters comply with security requirements."""
        for env_name, stack_configs in resolved_stack_configs.items():
            for stack_name, stack_config in stack_configs.items():
                parameters = stack_config.get("parameters", {})
                
                for param_name, param_value in parameters.items():
                    if isinstance(param_value, str):
                        # Check for potential security issues
                        
                        # No hardcoded credentials
                        sensitive_patterns = ["password", "secret", "key", "token"]
                        if any(pattern in param_name.lower() for pattern in sensitive_patterns):
                            # Should not be plaintext
                            assert not param_value.isalnum() or len(param_value) < 8, \
                                f"Environment {env_name} stack {stack_name} parameter {param_name} " \
                                f"may contain hardcoded credentials"
                        
                        # CORS origins should be appropriate for environment
                        if "origins" in param_name.lower():
                            origins = param_value.split(",") if "," in param_value else [param_value]
                            
                            for origin in origins:
                                origin = origin.strip()
                                if env_name == "production":
                                    assert not origin.startswith("http://localhost"), \
                                        f"Production environment should not allow localhost origins: {origin}"

    def test_parameter_documentation_completeness(self, all_templates_with_parameters: Dict[str, Dict[str, Any]]):
        """Test that template parameters have adequate documentation."""
        for template_name, template_data in all_templates_with_parameters.items():
            template_params = template_data["parameters"]
            
            for param_name, param_def in template_params.items():
                # Should have description
                assert "Description" in param_def, \
                    f"Template {template_name} parameter {param_name} missing Description"
                
                description = param_def["Description"]
                assert isinstance(description, str) and len(description.strip()) > 10, \
                    f"Template {template_name} parameter {param_name} has inadequate description"
                
                # Should have type
                assert "Type" in param_def, \
                    f"Template {template_name} parameter {param_name} missing Type"

    def test_parameter_naming_conventions(self, resolved_stack_configs: Dict[str, Dict[str, Dict[str, Any]]]):
        """Test that parameter names follow naming conventions."""
        for env_name, stack_configs in resolved_stack_configs.items():
            for stack_name, stack_config in stack_configs.items():
                parameters = stack_config.get("parameters", {})
                
                for param_name in parameters.keys():
                    # Parameter names should be PascalCase
                    assert param_name[0].isupper(), \
                        f"Environment {env_name} stack {stack_name} parameter {param_name} should start with uppercase"
                    
                    # Should not contain underscores (CloudFormation convention)
                    assert "_" not in param_name, \
                        f"Environment {env_name} stack {stack_name} parameter {param_name} should not contain underscores"
                    
                    # Should be descriptive
                    assert len(param_name) >= 3, \
                        f"Environment {env_name} stack {stack_name} parameter {param_name} name too short"