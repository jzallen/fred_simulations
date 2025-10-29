"""
Test configuration and fixtures for infrastructure tests.

This module provides pytest fixtures and configuration for testing
Sceptre-managed CloudFormation templates and deployed resources.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import yaml
from aws_cdk.assertions import Template
from sceptre.config.reader import ConfigReader
from sceptre.context import SceptreContext


@pytest.fixture(scope="session")
def infrastructure_root() -> Path:
    """Return the path to the infrastructure root directory."""
    current_file = Path(__file__)
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
def environments() -> list[str]:
    """Return list of available environments."""
    return ["dev", "staging", "production"]


@pytest.fixture(scope="session")
def template_files(templates_dir: Path) -> dict[str, Path]:
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

    def _load_template(template_path: Path) -> dict[str, Any]:
        with open(template_path, encoding="utf-8") as f:
            return json.load(f)

    return _load_template


@pytest.fixture(scope="session")
def cdk_template_factory():
    """Factory function to create CDK Template objects from template dicts."""

    def _create_cdk_template(template_dict: dict[str, Any]) -> Template:
        return Template.from_string(json.dumps(template_dict))

    return _create_cdk_template


@pytest.fixture(scope="session")
def load_config():
    """Factory function to load a Sceptre config file."""

    def _load_config(config_path: Path) -> dict[str, Any]:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    return _load_config


@pytest.fixture(scope="session")
def sceptre_context():
    """Factory function to create SceptreContext for different environments."""

    def _create_context(environment: str) -> SceptreContext:
        project_path = Path(__file__).parent.parent
        command_path = environment
        return SceptreContext(project_path=str(project_path), command_path=command_path)

    return _create_context


@pytest.fixture(scope="session")
def config_reader():
    """Factory function to create ConfigReader for different environments."""

    def _create_reader(environment: str) -> ConfigReader:
        project_path = Path(__file__).parent.parent
        context = SceptreContext(project_path=str(project_path), command_path=environment)
        return ConfigReader(context)

    return _create_reader


@pytest.fixture
def expected_tags() -> dict[str, dict[str, str]]:
    """Expected tags for different environments."""
    return {
        "dev": {
            "Environment": "dev",
            "Project": "FREDSimulations",
            "ManagedBy": "Sceptre",
            "CreatedWith": "InfrastructureAsCode",
            "CostCenter": "Development",
        },
        "staging": {
            "Environment": "staging",
            "Project": "FREDSimulations",
            "ManagedBy": "Sceptre",
            "CreatedWith": "InfrastructureAsCode",
            "CostCenter": "Staging",
        },
        "production": {
            "Environment": "production",
            "Project": "FREDSimulations",
            "ManagedBy": "Sceptre",
            "CreatedWith": "InfrastructureAsCode",
            "CostCenter": "Production",
        },
    }


def create_mock_stack(
    stack_name: str, template: dict[str, Any], parameters: dict[str, str] = None
) -> Mock:
    """Create a mock CloudFormation stack for testing."""
    mock_stack = Mock()
    mock_stack.stack_name = stack_name
    mock_stack.template_body = json.dumps(template)
    mock_stack.parameters = [
        {"ParameterKey": k, "ParameterValue": v} for k, v in (parameters or {}).items()
    ]
    mock_stack.stack_status = "CREATE_COMPLETE"
    mock_stack.tags = []
    return mock_stack


def extract_resource_properties(
    template: dict[str, Any], resource_type: str
) -> list[dict[str, Any]]:
    """Extract properties of resources of a specific type from a template."""
    resources = []
    for resource_name, resource_def in template.get("Resources", {}).items():
        if resource_def.get("Type") == resource_type:
            resources.append(
                {
                    "name": resource_name,
                    "properties": resource_def.get("Properties", {}),
                    "type": resource_type,
                }
            )
    return resources


def validate_parameter_constraints(
    template: dict[str, Any], parameter_name: str, value: str
) -> bool:
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


def assert_resource_has_properties(cdk_template: Template, resource_type: str, **properties):
    """Assert resource has specific properties using CDK Match.

    This helper reduces boilerplate for common CDK assertion patterns.

    Args:
        cdk_template: CDK Template object from cdk_template_factory
        resource_type: CloudFormation resource type (e.g., "AWS::Lambda::Function")
        **properties: Property name/value pairs to match

    Example:
        assert_resource_has_properties(
            cdk_template,
            "AWS::Lambda::Function",
            Timeout=Match.any_value(),
            MemorySize=Match.any_value()
        )
    """
    from aws_cdk.assertions import Match

    cdk_template.has_resource_properties(resource_type, Match.object_like(properties))


def assert_resource_has_tags(cdk_template: Template, resource_type: str, *required_tags):
    """Assert resource has specific tag keys using CDK assertions.

    Args:
        cdk_template: CDK Template object from cdk_template_factory
        resource_type: CloudFormation resource type
        *required_tags: Tag key names that must exist

    Example:
        assert_resource_has_tags(
            cdk_template,
            "AWS::Lambda::Function",
            "Environment", "Service", "ManagedBy"
        )
    """
    from aws_cdk.assertions import Match

    tags_matchers = [Match.object_like({"Key": tag}) for tag in required_tags]
    cdk_template.has_resource_properties(
        resource_type, Match.object_like({"Tags": Match.array_with(tags_matchers)})
    )


def assert_resource_property_exists(cdk_template: Template, resource_type: str, property_name: str):
    """Assert a property exists without checking its value.

    Useful for testing that configuration exists, regardless of the specific value.

    Args:
        cdk_template: CDK Template object from cdk_template_factory
        resource_type: CloudFormation resource type
        property_name: Property name that should exist

    Example:
        assert_resource_property_exists(
            cdk_template,
            "AWS::Lambda::Function",
            "Timeout"
        )
    """
    from aws_cdk.assertions import Match

    cdk_template.has_resource_properties(
        resource_type, Match.object_like({property_name: Match.any_value()})
    )


@pytest.fixture(scope="session")
def cfnlint_config_path(infrastructure_root: Path) -> str:
    """Return path to cfn-lint configuration file."""
    return str(infrastructure_root / ".cfnlintrc.yaml")


@pytest.fixture(scope="session")
def cfn_nag_script_path(infrastructure_root: Path) -> str:
    """Return path to cfn-nag Docker wrapper script."""
    return str(infrastructure_root / "scripts" / "run-cfn-nag.sh")
