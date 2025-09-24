"""
Test configuration and fixtures for infrastructure tests.

This module provides pytest fixtures and configuration for testing
Sceptre-managed CloudFormation templates and deployed resources.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock

import pytest
import yaml
from sceptre.config.reader import ConfigReader
from sceptre.context import SceptreContext


@pytest.fixture(scope="session")
def infrastructure_root() -> Path:
    """Return the path to the infrastructure root directory."""
    # Start from the current file's directory
    current_file = Path(__file__)

    # Go up from conftest.py to tests/, then to infrastructure/
    # conftest.py is in infrastructure/tests/, so parent.parent gives us infrastructure/
    infrastructure_dir = current_file.parent.parent

    return infrastructure_dir


@pytest.fixture(scope="session") 
def templates_dir(infrastructure_root: Path) -> Path:
    """Return the path to the templates directory."""
    return infrastructure_root / "templates"


@pytest.fixture(scope="session")
def config_dir(infrastructure_root: Path) -> Path:
    """Return the path to the config directory."""
    return infrastructure_root / "config"


@pytest.fixture(scope="session")
def environments() -> List[str]:
    """Return list of available environments."""
    return ["dev", "staging", "production"]


@pytest.fixture(scope="session")
def template_files(templates_dir: Path) -> Dict[str, Path]:
    """Return dictionary mapping template names to their file paths."""
    templates = {}
    for template_dir in templates_dir.iterdir():
        if template_dir.is_dir():
            # Look for JSON templates only
            for template_file in template_dir.glob("*.json"):
                templates[f"{template_dir.name}/{template_file.name}"] = template_file
    return templates


@pytest.fixture(scope="session")
def load_template():
    """Factory function to load a CloudFormation template from JSON."""
    def _load_template(template_path: Path) -> Dict[str, Any]:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return _load_template


@pytest.fixture(scope="session")
def load_config():
    """Factory function to load a Sceptre config file."""
    def _load_config(config_path: Path) -> Dict[str, Any]:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return _load_config


@pytest.fixture(scope="session")
def sceptre_context():
    """Factory function to create SceptreContext for different environments."""
    def _create_context(environment: str) -> SceptreContext:
        project_path = Path(__file__).parent.parent
        command_path = environment
        return SceptreContext(
            project_path=str(project_path),
            command_path=command_path
        )
    return _create_context


@pytest.fixture(scope="session")
def config_reader():
    """Factory function to create ConfigReader for different environments."""
    def _create_reader(environment: str) -> ConfigReader:
        project_path = Path(__file__).parent.parent
        context = SceptreContext(
            project_path=str(project_path),
            command_path=environment
        )
        return ConfigReader(context)
    return _create_reader


@pytest.fixture
def expected_tags() -> Dict[str, Dict[str, str]]:
    """Expected tags for different environments."""
    return {
        "dev": {
            "Environment": "dev",
            "Project": "FREDSimulations",
            "ManagedBy": "Sceptre",
            "CreatedWith": "InfrastructureAsCode",
            "CostCenter": "Development"
        },
        "staging": {
            "Environment": "staging",
            "Project": "FREDSimulations", 
            "ManagedBy": "Sceptre",
            "CreatedWith": "InfrastructureAsCode",
            "CostCenter": "Staging"
        },
        "production": {
            "Environment": "production",
            "Project": "FREDSimulations",
            "ManagedBy": "Sceptre", 
            "CreatedWith": "InfrastructureAsCode",
            "CostCenter": "Production"
        }
    }


# Helper functions
def create_mock_stack(stack_name: str, template: Dict[str, Any], parameters: Dict[str, str] = None) -> Mock:
    """Create a mock CloudFormation stack for testing."""
    mock_stack = Mock()
    mock_stack.stack_name = stack_name
    mock_stack.template_body = json.dumps(template)
    mock_stack.parameters = [
        {"ParameterKey": k, "ParameterValue": v} 
        for k, v in (parameters or {}).items()
    ]
    mock_stack.stack_status = "CREATE_COMPLETE"
    mock_stack.tags = []
    return mock_stack


def extract_resource_properties(template: Dict[str, Any], resource_type: str) -> List[Dict[str, Any]]:
    """Extract properties of resources of a specific type from a template."""
    resources = []
    for resource_name, resource_def in template.get("Resources", {}).items():
        if resource_def.get("Type") == resource_type:
            resources.append({
                "name": resource_name,
                "properties": resource_def.get("Properties", {}),
                "type": resource_type
            })
    return resources


def validate_parameter_constraints(template: Dict[str, Any], parameter_name: str, value: str) -> bool:
    """Validate a parameter value against template constraints."""
    parameters = template.get("Parameters", {})
    if parameter_name not in parameters:
        return False
    
    param_def = parameters[parameter_name]
    
    # Check AllowedValues
    allowed_values = param_def.get("AllowedValues")
    if allowed_values and value not in allowed_values:
        return False
    
    # Check MinLength/MaxLength for strings
    min_length = param_def.get("MinLength")
    max_length = param_def.get("MaxLength")
    if min_length and len(value) < min_length:
        return False
    if max_length and len(value) > max_length:
        return False
    
    # Check AllowedPattern
    import re
    pattern = param_def.get("AllowedPattern")
    if pattern and not re.match(pattern, value):
        return False
    
    return True