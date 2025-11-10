"""
Test configuration and fixtures for infrastructure tests.

This module provides pytest fixtures and configuration for testing
Sceptre-managed CloudFormation templates and deployed resources.
"""

import json
from pathlib import Path
from typing import Any

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


@pytest.fixture(scope="session")
def cfnlint_config_path(infrastructure_root: Path) -> str:
    """Return path to cfn-lint configuration file."""
    return str(infrastructure_root / ".cfnlintrc.yaml")
