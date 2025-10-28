"""Tests for Epistemix API ECR Repository CloudFormation template.

This test suite validates the epistemix-api-repository.json CloudFormation template
using multiple approaches:
- Traditional unit tests for template structure and properties
- Integration tests with external validation tools (cfn-lint, cfn-nag, cfn-guard)
- CDK assertions for flexible behavioral validation

Integration tests are marked with @pytest.mark.integration and can be skipped:
    pytest -m "not integration"  # Skip integration tests
    pytest -m "integration"      # Run only integration tests
"""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return the path to the epistemix-api-repository CloudFormation template."""
    return str(
        Path(__file__).parent.parent.parent
        / "templates"
        / "ecr"
        / "epistemix-api-repository.json"
    )


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the epistemix-api-repository CloudFormation template as a dictionary."""
    with open(template_path, "r") as f:
        return json.load(f)


class TestEpistemixAPIRepositoryTemplate:
    """Test suite for Epistemix API ECR repository CloudFormation template."""

    # ============================================================================
    # Template Structure Tests
    # ============================================================================

    def test_template_exists(self, template_path: str):
        """Test that the template file exists."""
        assert Path(template_path).exists(), "Template file does not exist"

    def test_template_valid_json(self, template: dict[str, Any]):
        """Test that the template is valid JSON."""
        assert isinstance(template, dict), "Template is not a valid JSON object"

    def test_template_format_version(self, template: dict[str, Any]):
        """Test template has correct CloudFormation format version."""
        assert (
            template.get("AWSTemplateFormatVersion") == "2010-09-09"
        ), "Invalid CloudFormation template version"

    def test_template_has_description(self, template: dict[str, Any]):
        """Test template has a description."""
        assert "Description" in template, "Template missing Description"
        assert (
            "Epistemix API" in template["Description"]
        ), "Description does not mention Epistemix API"

    # ============================================================================
    # Parameter Tests
    # ============================================================================

    def test_environment_parameter_exists(self, template: dict[str, Any]):
        """Test Environment parameter is defined."""
        parameters = template.get("Parameters", {})
        assert "Environment" in parameters, "Environment parameter not defined"

    def test_environment_parameter_default(self, template: dict[str, Any]):
        """Test Environment parameter has correct default value."""
        env_param = template["Parameters"]["Environment"]
        assert (
            env_param.get("Default") == "shared"
        ), "Environment parameter default should be 'shared'"

    def test_environment_parameter_allowed_values(self, template: dict[str, Any]):
        """Test Environment parameter has correct allowed values."""
        env_param = template["Parameters"]["Environment"]
        assert env_param.get("AllowedValues") == [
            "shared"
        ], "Environment parameter should only allow 'shared'"

    # ============================================================================
    # ECR Repository Resource Tests
    # ============================================================================

    def test_ecr_repository_exists(self, template: dict[str, Any]):
        """Test ECRRepository resource exists."""
        resources = template.get("Resources", {})
        assert "ECRRepository" in resources, "ECRRepository resource not found"

    def test_ecr_repository_type(self, template: dict[str, Any]):
        """Test ECRRepository has correct type."""
        repo = template["Resources"]["ECRRepository"]
        assert (
            repo.get("Type") == "AWS::ECR::Repository"
        ), "ECRRepository has incorrect type"

    def test_ecr_repository_has_retain_policy(self, template: dict[str, Any]):
        """Test ECRRepository has DeletionPolicy set to Retain."""
        repo = template["Resources"]["ECRRepository"]
        assert (
            repo.get("DeletionPolicy") == "Retain"
        ), "ECRRepository DeletionPolicy should be Retain"

    def test_ecr_repository_has_retain_update_policy(self, template: dict[str, Any]):
        """Test ECRRepository has UpdateReplacePolicy set to Retain."""
        repo = template["Resources"]["ECRRepository"]
        assert (
            repo.get("UpdateReplacePolicy") == "Retain"
        ), "ECRRepository UpdateReplacePolicy should be Retain"

    def test_repository_name_is_epistemix_api(self, template: dict[str, Any]):
        """Test repository name is 'epistemix-api'."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        assert (
            repo_props.get("RepositoryName") == "epistemix-api"
        ), "Repository name should be 'epistemix-api'"

    def test_image_tag_mutability_is_mutable(self, template: dict[str, Any]):
        """Test image tag mutability is set to MUTABLE."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        assert (
            repo_props.get("ImageTagMutability") == "MUTABLE"
        ), "ImageTagMutability should be MUTABLE"

    # ============================================================================
    # Security Configuration Tests
    # ============================================================================

    def test_image_scanning_enabled(self, template: dict[str, Any]):
        """Test image scanning is enabled."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        scan_config = repo_props.get("ImageScanningConfiguration", {})
        assert (
            scan_config.get("ScanOnPush") is True
        ), "ScanOnPush should be enabled (true)"

    def test_encryption_configured(self, template: dict[str, Any]):
        """Test encryption is configured."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        enc_config = repo_props.get("EncryptionConfiguration", {})
        assert enc_config, "EncryptionConfiguration should be present"
        assert (
            enc_config.get("EncryptionType") == "AES256"
        ), "EncryptionType should be AES256"

    # ============================================================================
    # Lifecycle Policy Tests
    # ============================================================================

    def test_lifecycle_policy_exists(self, template: dict[str, Any]):
        """Test lifecycle policy is configured."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        assert (
            "LifecyclePolicy" in repo_props
        ), "LifecyclePolicy should be configured"

    def test_lifecycle_policy_text_is_valid_json(self, template: dict[str, Any]):
        """Test lifecycle policy text is valid JSON."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        policy_text = repo_props["LifecyclePolicy"]["LifecyclePolicyText"]

        # Parse the policy text to verify it's valid JSON
        policy = json.loads(policy_text)
        assert isinstance(policy, dict), "Lifecycle policy should be a JSON object"
        assert "rules" in policy, "Lifecycle policy should have rules"

    def test_lifecycle_policy_retains_images(self, template: dict[str, Any]):
        """Test lifecycle policy keeps last 10 images."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        policy_text = repo_props["LifecyclePolicy"]["LifecyclePolicyText"]
        policy = json.loads(policy_text)

        rules = policy.get("rules", [])
        assert len(rules) > 0, "Lifecycle policy should have at least one rule"

        # Find the retention rule
        retention_rule = rules[0]
        assert (
            retention_rule.get("selection", {}).get("countNumber") == 10
        ), "Should keep last 10 images"

    # ============================================================================
    # Repository Policy Tests
    # ============================================================================

    def test_repository_policy_exists(self, template: dict[str, Any]):
        """Test repository policy is configured."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        assert (
            "RepositoryPolicyText" in repo_props
        ), "RepositoryPolicyText should be configured"

    def test_repository_policy_allows_lambda_access(self, template: dict[str, Any]):
        """Test repository policy allows Lambda service access."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        policy = repo_props["RepositoryPolicyText"]

        statements = policy.get("Statement", [])
        assert len(statements) > 0, "Repository policy should have statements"

        # Find Lambda access statement
        lambda_statement = next(
            (s for s in statements if "Lambda" in s.get("Sid", "")), None
        )
        assert lambda_statement is not None, "Lambda access statement not found"

        # Verify principal is Lambda service
        principal = lambda_statement.get("Principal", {})
        assert (
            principal.get("Service") == "lambda.amazonaws.com"
        ), "Principal should be lambda.amazonaws.com"

        # Verify required permissions
        actions = lambda_statement.get("Action", [])
        assert "ecr:BatchGetImage" in actions, "Should allow ecr:BatchGetImage"
        assert (
            "ecr:GetDownloadUrlForLayer" in actions
        ), "Should allow ecr:GetDownloadUrlForLayer"

    # ============================================================================
    # Tag Tests
    # ============================================================================

    def test_repository_has_tags(self, template: dict[str, Any]):
        """Test repository has tags configured."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        assert "Tags" in repo_props, "Repository should have tags"
        assert len(repo_props["Tags"]) > 0, "Repository should have at least one tag"

    def test_repository_has_environment_tag(self, template: dict[str, Any]):
        """Test repository has Environment tag."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        tags = repo_props["Tags"]

        env_tag = next((t for t in tags if t.get("Key") == "Environment"), None)
        assert env_tag is not None, "Environment tag not found"

    def test_repository_has_service_tag(self, template: dict[str, Any]):
        """Test repository has Service tag set to EpistemixAPI."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        tags = repo_props["Tags"]

        service_tag = next((t for t in tags if t.get("Key") == "Service"), None)
        assert service_tag is not None, "Service tag not found"
        assert (
            service_tag.get("Value") == "EpistemixAPI"
        ), "Service tag should be EpistemixAPI"

    def test_repository_has_protection_tags(self, template: dict[str, Any]):
        """Test repository has protection-related tags."""
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        tags = repo_props["Tags"]

        protected_tag = next((t for t in tags if t.get("Key") == "Protected"), None)
        assert protected_tag is not None, "Protected tag not found"
        assert (
            protected_tag.get("Value") == "true"
        ), "Protected tag should be 'true'"

        deletion_tag = next(
            (t for t in tags if t.get("Key") == "DeletionProtection"), None
        )
        assert deletion_tag is not None, "DeletionProtection tag not found"
        assert (
            deletion_tag.get("Value") == "Retain"
        ), "DeletionProtection tag should be 'Retain'"

    # ============================================================================
    # Output Tests
    # ============================================================================

    def test_outputs_exist(self, template: dict[str, Any]):
        """Test template has outputs defined."""
        assert "Outputs" in template, "Template should have Outputs section"
        assert len(template["Outputs"]) > 0, "Template should have at least one output"

    def test_repository_name_output_exists(self, template: dict[str, Any]):
        """Test RepositoryName output exists."""
        outputs = template["Outputs"]
        assert "RepositoryName" in outputs, "RepositoryName output not found"

    def test_repository_arn_output_exists(self, template: dict[str, Any]):
        """Test RepositoryArn output exists."""
        outputs = template["Outputs"]
        assert "RepositoryArn" in outputs, "RepositoryArn output not found"

    def test_repository_uri_output_exists(self, template: dict[str, Any]):
        """Test RepositoryUri output exists."""
        outputs = template["Outputs"]
        assert "RepositoryUri" in outputs, "RepositoryUri output not found"

    def test_outputs_have_exports(self, template: dict[str, Any]):
        """Test outputs have export names for cross-stack references."""
        outputs = template["Outputs"]

        for output_name, output_value in outputs.items():
            assert (
                "Export" in output_value
            ), f"{output_name} output should have Export configured"

    # ============================================================================
    # Validation Tests (cfn-lint, cfn-nag, cfn-guard)
    # ============================================================================
    # These tests validate the template using external tools for comprehensive
    # infrastructure validation. They are marked as integration tests because
    # they require external tools that may not be available in all environments.
    # Run with: pants test epistemix_platform/infrastructure/tests/ecr/ -- -m "integration"
    # Skip with: pants test epistemix_platform/infrastructure/tests/ecr/ -- -m "not integration"

    @pytest.mark.integration
    def test_template_passes_cfn_lint(self, template_path: str):
        """Test that the template passes cfn-lint validation.

        cfn-lint validates CloudFormation templates against AWS schema and best practices.
        This catches syntax errors, invalid property values, and common misconfigurations.

        Requires: cfn-lint (Python package in infrastructure_env)
        Install: pants export --resolve=infrastructure_env
        Config: .cfnlintrc.yaml
        """
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "cfnlint", template_path],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"cfn-lint validation failed:\n{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.integration
    def test_template_passes_security_scan(self, template_path: str):
        """Test that the template passes cfn-nag security scanning.

        cfn-nag scans CloudFormation templates for security anti-patterns with 140+ rules.
        It identifies potential security issues like overly permissive IAM policies,
        missing encryption, public access, and more.

        Requires: Docker with stelligent/cfn_nag image
        Install: docker pull stelligent/cfn_nag
        Usage: ./scripts/run-cfn-nag.sh <template>

        To suppress warnings, add metadata to resources:
        "Metadata": {
          "cfn_nag": {
            "rules_to_suppress": [{
              "id": "W79",
              "reason": "Explanation of why this is acceptable"
            }]
          }
        }
        """
        import subprocess
        from pathlib import Path

        script_path = Path(__file__).parent.parent.parent / "scripts" / "run-cfn-nag.sh"

        result = subprocess.run(
            [str(script_path), template_path],
            capture_output=True,
            text=True,
        )

        # cfn-nag returns 0 for pass, non-zero for failures/warnings
        assert result.returncode == 0, (
            f"cfn-nag security scan failed:\n{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.integration
    def test_template_passes_policy_validation(self, template_path: str):
        """Test that the template passes cfn-guard policy validation.

        cfn-guard validates CloudFormation templates against custom policy rules
        written in Guard DSL. This enforces organizational standards and compliance
        requirements specific to our infrastructure.

        Requires: cfn-guard binary (pre-built from AWS)
        Install: ./scripts/install-cfn-guard.sh
        Rules: guard_rules/ecr/ecr_security_rules.guard
        Docs: guard_rules/README.md
        """
        import subprocess
        from pathlib import Path

        rules_path = (
            Path(__file__).parent.parent.parent
            / "guard_rules"
            / "ecr"
            / "ecr_security_rules.guard"
        )

        result = subprocess.run(
            [
                "cfn-guard",
                "validate",
                "--data",
                template_path,
                "--rules",
                str(rules_path),
            ],
            capture_output=True,
            text=True,
        )

        # cfn-guard returns 0 for pass, non-zero for failures
        assert result.returncode == 0, (
            f"cfn-guard policy validation failed:\n{result.stdout}\n{result.stderr}"
        )

    # ============================================================================
    # CDK Assertion Tests (Behavioral Validation)
    # ============================================================================
    # These tests use AWS CDK's flexible assertion library to validate template
    # behavior without coupling to implementation details. They test WHAT the
    # template does (e.g., "encryption is enabled") rather than HOW it's structured
    # (e.g., "specific property names exist").
    #
    # Benefits:
    # - Resilient to refactoring (survives renaming, restructuring)
    # - More readable (business logic vs template structure)
    # - Flexible matching (Match.object_like, Match.array_with)
    #
    # Docs: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.assertions/README.html

    def test_repository_has_image_scanning_enabled(self, template, cdk_template_factory):
        """Test that the ECR repository has image scanning enabled.

        Image scanning automatically scans container images for vulnerabilities
        when pushed to the repository. This is critical for security compliance.

        Uses CDK assertions to verify the behavior exists without depending on
        specific property structures that might change during refactoring.
        """
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {"ImageScanningConfiguration": {"ScanOnPush": True}}
            ),
        )

    def test_repository_has_encryption_enabled(self, template, cdk_template_factory):
        """Test that the ECR repository has encryption enabled.

        Encryption at rest protects container images stored in ECR using either
        AES256 or KMS encryption. This is required for compliance with security
        standards.

        Uses flexible matching to accept either AES256 or KMS encryption types.
        """
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {
                    "EncryptionConfiguration": {
                        "EncryptionType": Match.string_like_regexp(r"^(AES256|KMS)$")
                    }
                }
            ),
        )

    def test_repository_has_lifecycle_policy(self, template, cdk_template_factory):
        """Test that the ECR repository has a lifecycle policy configured.

        Lifecycle policies automatically clean up old or untagged images to manage
        storage costs and maintain repository hygiene. This prevents unbounded
        growth of container image storage.

        Tests for the presence of a lifecycle policy without validating specific
        rules, allowing flexibility in policy configuration.
        """
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {
                    "LifecyclePolicy": Match.object_like(
                        {"LifecyclePolicyText": Match.any_value()}
                    )
                }
            ),
        )

    def test_repository_allows_lambda_access(self, template, cdk_template_factory):
        """Test that the repository policy allows Lambda service access.

        The Epistemix API runs as a Lambda function and needs permission to pull
        container images from this ECR repository. This test verifies the repository
        policy grants the necessary permissions to the Lambda service.
        """
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {
                    "RepositoryPolicyText": {
                        "Statement": Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        "Effect": "Allow",
                                        "Principal": {"Service": "lambda.amazonaws.com"},
                                        "Action": Match.array_with(
                                            ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
                                        ),
                                    }
                                )
                            ]
                        )
                    }
                }
            ),
        )
