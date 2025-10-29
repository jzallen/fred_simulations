"""Tests for Epistemix API ECR Repository CloudFormation template."""

import json
from pathlib import Path
from typing import Any

import pytest
from aws_cdk.assertions import Match


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return the path to the epistemix-api-repository CloudFormation template."""
    return str(
        Path(__file__).parent.parent.parent / "templates" / "ecr" / "epistemix-api-repository.json"
    )


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the epistemix-api-repository CloudFormation template as a dictionary."""
    with open(template_path) as f:
        return json.load(f)


class TestEpistemixAPIRepositoryTemplate:
    """Test suite for Epistemix API ECR repository CloudFormation template."""


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


    def test_ecr_repository_exists(self, template, cdk_template_factory):
        """Test ECRRepository resource exists."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::ECR::Repository", 1)

    def test_ecr_repository_type(self, template, cdk_template_factory):
        """Test ECRRepository has correct type."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::ECR::Repository", 1)

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

    def test_repository_name_is_epistemix_api(self, template, cdk_template_factory):
        """Test repository name is 'epistemix-api'."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository", Match.object_like({"RepositoryName": "epistemix-api"})
        )

    def test_image_tag_mutability_is_mutable(self, template, cdk_template_factory):
        """Test image tag mutability is set to MUTABLE."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository", Match.object_like({"ImageTagMutability": "MUTABLE"})
        )


    def test_image_scanning_enabled(self, template, cdk_template_factory):
        """Test image scanning is enabled."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {"ImageScanningConfiguration": Match.object_like({"ScanOnPush": True})}
            ),
        )

    def test_encryption_configured(self, template, cdk_template_factory):
        """Test encryption is configured (accepts AES256 or KMS)."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {"EncryptionConfiguration": Match.object_like({"EncryptionType": Match.string_like_regexp(r"^(AES256|KMS)$")})}
            ),
        )


    def test_lifecycle_policy_exists(self, template, cdk_template_factory):
        """Test lifecycle policy is configured."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository", Match.object_like({"LifecyclePolicy": Match.any_value()})
        )

    def test_lifecycle_policy_text_is_valid_json(self, template, cdk_template_factory):
        """Test lifecycle policy text is valid JSON."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {"LifecyclePolicy": Match.object_like({"LifecyclePolicyText": Match.any_value()})}
            ),
        )

        # Additionally validate JSON structure
        repo_props = template["Resources"]["ECRRepository"]["Properties"]
        policy_text = repo_props["LifecyclePolicy"]["LifecyclePolicyText"]
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


    def test_repository_policy_exists(self, template, cdk_template_factory):
        """Test repository policy is configured."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository", Match.object_like({"RepositoryPolicyText": Match.any_value()})
        )

    def test_repository_policy_allows_lambda_access(self, template, cdk_template_factory):
        """Test repository policy allows Lambda service access."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {
                    "RepositoryPolicyText": Match.object_like(
                        {
                            "Statement": Match.array_with(
                                [
                                    Match.object_like(
                                        {
                                            "Principal": {"Service": "lambda.amazonaws.com"},
                                            "Action": Match.array_with(
                                                ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
                                            ),
                                        }
                                    )
                                ]
                            )
                        }
                    )
                }
            ),
        )


    def test_repository_has_tags(self, template, cdk_template_factory):
        """Test repository has tags configured."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like({"Tags": Match.array_with([Match.object_like({})])}),
        )

    def test_repository_has_environment_tag(self, template, cdk_template_factory):
        """Test repository has Environment tag."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {"Tags": Match.array_with([Match.object_like({"Key": "Environment"})])}
            ),
        )

    def test_repository_has_service_tag(self, template, cdk_template_factory):
        """Test repository has Service tag set to EpistemixAPI."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {
                    "Tags": Match.array_with(
                        [Match.object_like({"Key": "Service", "Value": "EpistemixAPI"})]
                    )
                }
            ),
        )

    def test_repository_has_protection_tags(self, template, cdk_template_factory):
        """Test repository has protection-related tags."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {
                    "Tags": Match.array_with(
                        [
                            Match.object_like({"Key": "Protected", "Value": "true"}),
                            Match.object_like({"Key": "DeletionProtection", "Value": "Retain"}),
                        ]
                    )
                }
            ),
        )


