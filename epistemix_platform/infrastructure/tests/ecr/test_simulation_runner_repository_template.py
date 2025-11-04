"""
Tests for ECR CloudFormation template validation.

This module tests the ECR repository template for compliance with:
- CloudFormation syntax and schema validation
- Parameter constraints and validation
- Resource configuration and security settings
- Output definitions and exports
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest


class TestECRTemplate:
    """Test suite for ECR CloudFormation template."""

    @pytest.fixture(scope="class")
    def ecr_template_path(self, templates_dir: Path) -> Path:
        """Return path to ECR template."""
        return templates_dir / "ecr" / "simulation-runner-repository.json"

    @pytest.fixture(scope="class")
    def ecr_template(self, ecr_template_path: Path) -> dict[str, Any]:
        """Load ECR CloudFormation template from JSON."""
        with open(ecr_template_path) as f:
            return json.load(f)

    def test_template_exists(self, ecr_template_path: Path):
        """Test that ECR template file exists."""
        assert ecr_template_path.exists(), f"ECR template not found at {ecr_template_path}"
        assert ecr_template_path.is_file(), f"ECR template path is not a file: {ecr_template_path}"

    def test_template_valid_json(self, ecr_template_path: Path):
        """Test that ECR template is valid JSON."""
        try:
            with open(ecr_template_path, encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"ECR template is not valid JSON: {e}")

    def test_template_format_version(self, ecr_template: dict[str, Any]):
        """Test that template has correct CloudFormation format version."""
        assert "AWSTemplateFormatVersion" in ecr_template
        assert ecr_template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_parameters_defined(self, ecr_template: dict[str, Any]):
        """Test that required parameters are defined."""
        parameters = ecr_template.get("Parameters", {})
        required_params = [
            "RepositoryName",
            "Environment",
            "EnableVulnerabilityScanning",
            "EnableCloudWatchLogs",
        ]

        for param in required_params:
            assert param in parameters, f"Required parameter {param} not found"

    def test_repository_name_has_string_type_constraint(self, ecr_template: dict[str, Any]):
        """Test RepositoryName parameter has String type constraint."""
        repo_param = ecr_template["Parameters"]["RepositoryName"]
        assert repo_param["Type"] == "String"

    def test_repository_name_has_min_length_of_2(self, ecr_template: dict[str, Any]):
        """Test RepositoryName parameter has minimum length of 2."""
        repo_param = ecr_template["Parameters"]["RepositoryName"]
        assert repo_param["MinLength"] == 2

    def test_repository_name_has_max_length_of_256(self, ecr_template: dict[str, Any]):
        """Test RepositoryName parameter has maximum length of 256."""
        repo_param = ecr_template["Parameters"]["RepositoryName"]
        assert repo_param["MaxLength"] == 256

    def test_repository_name_allowed_pattern_matches_valid_names(
        self, ecr_template: dict[str, Any]
    ):
        """Test RepositoryName parameter's AllowedPattern matches valid names."""
        repo_param = ecr_template["Parameters"]["RepositoryName"]
        pattern = repo_param["AllowedPattern"]
        valid_names = ["fred-simulation-runner", "my-app", "test.repo", "app_name"]

        for name in valid_names:
            assert re.match(pattern, name), f"Valid name {name} should match pattern"

    def test_repository_name_disallowed_pattern_rejects_invalid_names(
        self, ecr_template: dict[str, Any]
    ):
        """Test RepositoryName parameter's AllowedPattern rejects invalid names."""
        repo_param = ecr_template["Parameters"]["RepositoryName"]
        pattern = repo_param["AllowedPattern"]
        invalid_names = ["Fred-App", "app-", "-app", "app..name"]

        for name in invalid_names:
            assert not re.match(pattern, name), f"Invalid name {name} should not match pattern"

    def test_environment_parameter_has_string_type_constraint(self, ecr_template: dict[str, Any]):
        """Test Environment parameter has String type constraint."""
        env_param = ecr_template["Parameters"]["Environment"]
        assert env_param["Type"] == "String"

    def test_environment_parameter_has_default_value(self, ecr_template: dict[str, Any]):
        """Test Environment parameter has default value."""
        env_param = ecr_template["Parameters"]["Environment"]
        assert env_param["Default"] == "shared"

    def test_environment_parameter_has_allowed_values(self, ecr_template: dict[str, Any]):
        """Test Environment parameter has correct allowed values."""
        env_param = ecr_template["Parameters"]["Environment"]
        assert set(env_param["AllowedValues"]) == {"shared"}

    def test_enable_vulnerability_scanning_parameter_defaults_to_true(
        self, ecr_template: dict[str, Any]
    ):
        """Test EnableVulnerabilityScanning parameter defaults to true."""
        scan_param = ecr_template["Parameters"]["EnableVulnerabilityScanning"]
        assert scan_param["Default"] == "true"

    def test_enable_vulnerability_scanning_parameter_allowed_values_are_booleans(
        self, ecr_template: dict[str, Any]
    ):
        """Test EnableVulnerabilityScanning parameter has correct allowed values."""
        scan_param = ecr_template["Parameters"]["EnableVulnerabilityScanning"]
        assert set(scan_param["AllowedValues"]) == {"true", "false"}

    def test_enable_cloudwatch_logs_parameter_defaults_to_true(self, ecr_template: dict[str, Any]):
        """Test EnableCloudWatchLogs parameter defaults to true."""
        logs_param = ecr_template["Parameters"]["EnableCloudWatchLogs"]
        assert logs_param["Default"] == "true"

    def test_enable_cloudwatch_logs_parameter_allowed_values_are_booleans(
        self, ecr_template: dict[str, Any]
    ):
        """Test EnableCloudWatchLogs parameter has correct allowed values."""
        logs_param = ecr_template["Parameters"]["EnableCloudWatchLogs"]
        assert set(logs_param["AllowedValues"]) == {"true", "false"}

    def test_enable_cloudwatch_logs_condition_defines_true_as_enable_cloudwatch_logs_is_true(
        self, ecr_template: dict[str, Any]
    ):
        """Test EnableCloudWatchLogsCondition logic."""
        conditions = ecr_template.get("Conditions", {})
        condition = conditions["EnableCloudWatchLogsCondition"]
        expected_condition = {"Fn::Equals": [{"Ref": "EnableCloudWatchLogs"}, "true"]}
        assert (
            condition == expected_condition
        ), "EnableCloudWatchLogsCondition does not match expected logic"

    def test_enable_vulnerability_scanning_condition_defines_true_as_enable_vulnerability_scanning_is_true(
        self, ecr_template: dict[str, Any]
    ):
        """Test EnableVulnerabilityScanningCondition logic."""
        conditions = ecr_template.get("Conditions", {})
        condition = conditions["EnableVulnerabilityScanningCondition"]
        expected_condition = {"Fn::Equals": [{"Ref": "EnableVulnerabilityScanning"}, "true"]}
        assert (
            condition == expected_condition
        ), "EnableVulnerabilityScanningCondition does not match expected logic"

    def test_ecr_repository_resource_exists(self, ecr_template: dict[str, Any]):
        """Test ECR repository resource configuration."""
        resources = ecr_template.get("Resources", {})
        ecr_repo = resources["ECRRepository"]
        assert ecr_repo["Type"] == "AWS::ECR::Repository"

    def test_ecr_repository_name_matches_parameter(self, ecr_template: dict[str, Any]):
        """Test ECR repository name matches RepositoryName parameter."""
        ecr_repo = ecr_template["Resources"]["ECRRepository"]
        repo_name_ref = ecr_repo["Properties"]["RepositoryName"]
        assert repo_name_ref == {"Ref": "RepositoryName"}

    def test_ecr_repository_tags_are_mutable(self, ecr_template: dict[str, Any]):
        """Test ECR repository tags are mutable."""
        ecr_repo = ecr_template["Resources"]["ECRRepository"]
        assert ecr_repo["Properties"]["ImageTagMutability"] == "MUTABLE"

    def test_ecr_repository_scanning_configuration_defined_by_parameter(
        self, ecr_template: dict[str, Any]
    ):
        """Test ECR repository scanning configuration is defined by parameter."""
        ecr_repo = ecr_template["Resources"]["ECRRepository"]
        scan_config = ecr_repo["Properties"]["ImageScanningConfiguration"]
        expected_config = {
            "ScanOnPush": {"Fn::If": ["EnableVulnerabilityScanningCondition", True, False]}
        }
        assert (
            scan_config == expected_config
        ), "ECR scanning configuration does not match expected logic"

    def test_ecr_repository_encryption_configured(self, ecr_template: dict[str, Any]):
        """Test ECR repository encryption is configured (accepts AES256 or KMS)."""
        ecr_repo = ecr_template["Resources"]["ECRRepository"]
        encryption_config = ecr_repo["Properties"]["EncryptionConfiguration"]
        encryption_type = encryption_config["EncryptionType"]
        assert encryption_type in [
            "AES256",
            "KMS",
        ], f"ECR encryption must be AES256 or KMS, got {encryption_type}"

    def test_ecr_repository_has_expected_tags(self, ecr_template: dict[str, Any]):
        """Test ECR repository has expected tags."""
        ecr_repo = ecr_template["Resources"]["ECRRepository"]
        tags = ecr_repo["Properties"]["Tags"]
        expected_tags = [
            {"Key": "Environment", "Value": {"Ref": "Environment"}},
            {"Key": "Purpose", "Value": "FREDSimulationRunner"},
            {"Key": "ManagedBy", "Value": "CloudFormation"},
            {"Key": "Protected", "Value": "true"},
            {"Key": "DeletionProtection", "Value": "Retain"},
        ]
        assert tags == expected_tags, "ECR repository tags do not match expected tags"

    def test_ecr_iam_role_for_eks_exists(self, ecr_template: dict[str, Any]):
        """Test IAM role for EKS exists."""
        resources = ecr_template.get("Resources", {})
        eks_role = resources["ECREKSRole"]
        assert eks_role["Type"] == "AWS::IAM::Role", "ECR EKS IAM role type is not correct"

    def test_eks_role_name_uses_environment_and_repository_name_parameters(
        self, ecr_template: dict[str, Any]
    ):
        """Test EKS role name uses Environment and RepositoryName parameters."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        role_name = eks_role["Properties"]["RoleName"]
        expected_role_name = {"Fn::Sub": "${RepositoryName}-eks-role-${Environment}"}
        assert role_name == expected_role_name, "EKS role name does not match expected format"

    def test_eks_role_assume_role_only_applies_to_simulation_runner_service_in_default_namespace(
        self, ecr_template: dict[str, Any]
    ):
        """Test EKS role assume role policy only applies to simulation-runner service in default namespace."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        assume_policy = eks_role["Properties"]["AssumeRolePolicyDocument"]
        expected_statement = [
            {
                "Effect": "Allow",
                "Principal": {
                    "Federated": {
                        "Fn::Sub": "arn:aws:iam::${AWS::AccountId}:oidc-provider/oidc.eks.${AWS::Region}.amazonaws.com"
                    }
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        "oidc.eks.${AWS::Region}.amazonaws.com:sub": "system:serviceaccount:default:fred-simulation-runner",
                        "oidc.eks.${AWS::Region}.amazonaws.com:aud": "sts.amazonaws.com",
                    }
                },
            }
        ]
        assert (
            assume_policy["Statement"] == expected_statement
        ), "EKS role assume role policy does not match expected"

    def test_eks_role_only_has_1_policy(self, ecr_template: dict[str, Any]):
        """Test EKS role only has one policy."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        policies = eks_role["Properties"]["Policies"]
        assert len(policies) == 1, "EKS role should only have one policy"

    def test_eks_role_read_only_policy_statement_has_2_rules(self, ecr_template: dict[str, Any]):
        """Test EKS role read-only policy has exactly 2 statements."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        read_only_policy = eks_role["Properties"]["Policies"][0]
        statements = read_only_policy["PolicyDocument"]["Statement"]
        assert len(statements) == 2, "EKS role read-only policy should have exactly 2 statements"

    def test_eks_role_read_only_policy_allows_authorization_token_for_any_resource(
        self, ecr_template: dict[str, Any]
    ):
        """Test EKS role read-only policy allows GetAuthorizationToken for any resource."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        read_only_policy = eks_role["Properties"]["Policies"][0]
        statements = read_only_policy["PolicyDocument"]["Statement"]
        expected_get_authorization_token_rule = {
            "Effect": "Allow",
            "Action": ["ecr:GetAuthorizationToken"],
            "Resource": "*",
        }
        assert (
            expected_get_authorization_token_rule in statements
        ), "EKS role read-only policy does not allow GetAuthorizationToken for any resource"

    def test_eks_role_read_only_policy_allows_read_actions_only_on_repository(
        self, ecr_template: dict[str, Any]
    ):
        """Test EKS role read-only policy allows read actions only on the repository."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        read_only_policy = eks_role["Properties"]["Policies"][0]
        statement = read_only_policy["PolicyDocument"]["Statement"]
        expected_read_actions_rule = {
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:GetRepositoryPolicy",
                "ecr:DescribeRepositories",
                "ecr:ListImages",
                "ecr:DescribeImages",
                "ecr:BatchGetImage",
                "ecr:GetLifecyclePolicy",
                "ecr:GetLifecyclePolicyPreview",
                "ecr:ListTagsForResource",
                "ecr:DescribeImageScanFindings",
            ],
            "Resource": {"Fn::GetAtt": ["ECRRepository", "Arn"]},
        }
        assert (
            expected_read_actions_rule in statement
        ), "EKS role read-only policy does not allow read actions on the repository"

    def test_eks_role_has_expected_resource_tags(self, ecr_template: dict[str, Any]):
        """Test EKS role has expected resource tags."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        tags = eks_role["Properties"]["Tags"]
        expected_tags = [
            {"Key": "Environment", "Value": {"Ref": "Environment"}},
            {"Key": "Purpose", "Value": "ECREKSAccess"},
            {"Key": "ManagedBy", "Value": "CloudFormation"},
        ]
        assert tags == expected_tags, "EKS role tags do not match expected tags"

    def test_ecr_ec2_instance_profile_exists(self, ecr_template: dict[str, Any]):
        """Test EC2 instance profile resource exists."""
        resources = ecr_template.get("Resources", {})
        instance_profile = resources["ECREC2InstanceProfile"]
        assert (
            instance_profile["Type"] == "AWS::IAM::InstanceProfile"
        ), "EC2 instance profile type is not correct"

    def test_ecr_ec2_instance_profile_name_uses_environment_and_repository_name_parameters(
        self, ecr_template: dict[str, Any]
    ):
        """Test EC2 instance profile name uses Environment and RepositoryName parameters."""
        instance_profile = ecr_template["Resources"]["ECREC2InstanceProfile"]
        profile_name = instance_profile["Properties"]["InstanceProfileName"]
        expected_profile_name = {"Fn::Sub": "${RepositoryName}-ec2-profile-${Environment}"}
        assert (
            profile_name == expected_profile_name
        ), "EC2 instance profile name does not match expected format"

    def test_ecr_ec2_instance_profile_includes_ec2_role(self, ecr_template: dict[str, Any]):
        """Test EC2 instance profile includes the EC2 role."""
        instance_profile = ecr_template["Resources"]["ECREC2InstanceProfile"]
        roles = instance_profile["Properties"]["Roles"]
        expected_role = {"Ref": "ECREC2Role"}
        assert expected_role in roles, "EC2 instance profile does not include the EC2 role"

    def test_ecr_ec2_role_exists(self, ecr_template: dict[str, Any]):
        """Test EC2 IAM role resource exists."""
        resources = ecr_template.get("Resources", {})
        ec2_role = resources["ECREC2Role"]
        assert ec2_role["Type"] == "AWS::IAM::Role", "EC2 IAM role type is not correct"

    def test_ecr_ec2_role_name_uses_environment_and_repository_name_parameters(
        self, ecr_template: dict[str, Any]
    ):
        """Test EC2 role name uses Environment and RepositoryName parameters."""
        ec2_role = ecr_template["Resources"]["ECREC2Role"]
        role_name = ec2_role["Properties"]["RoleName"]
        expected_role_name = {"Fn::Sub": "${RepositoryName}-ec2-role-${Environment}"}
        assert role_name == expected_role_name, "EC2 role name does not match expected format"

    def test_ecr_ec2_role_can_be_assumed_by_ecs_service(self, ecr_template: dict[str, Any]):
        """Test EC2 role can be assumed by EC2 service."""
        ec2_role = ecr_template["Resources"]["ECREC2Role"]
        assume_policy = ec2_role["Properties"]["AssumeRolePolicyDocument"]
        expected_statement = [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ]
        assert (
            assume_policy["Statement"] == expected_statement
        ), "EC2 role assume role policy does not match expected"

    def test_ecr_ec2_role_has_1_managed_policy(self, ecr_template: dict[str, Any]):
        """Test EC2 role has exactly one managed policy."""
        ec2_role = ecr_template["Resources"]["ECREC2Role"]
        managed_policies = ec2_role["Properties"]["ManagedPolicyArns"]
        assert len(managed_policies) == 1, "EC2 role should have exactly one managed policy"

    def test_ecr_ec2_role_has_managed_policy_for_systems_manager(
        self, ecr_template: dict[str, Any]
    ):
        """Test EC2 role has managed policy for Systems Manager."""
        ec2_role = ecr_template["Resources"]["ECREC2Role"]
        managed_policies = ec2_role["Properties"]["ManagedPolicyArns"]
        expected_policy = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
        assert (
            expected_policy in managed_policies
        ), "EC2 role does not have Systems Manager managed policy"

    def test_ecr_ec2_role_has_expected_resource_tags(self, ecr_template: dict[str, Any]):
        """Test EC2 role has expected resource tags."""
        ec2_role = ecr_template["Resources"]["ECREC2Role"]
        tags = ec2_role["Properties"]["Tags"]
        expected_tags = [
            {"Key": "Environment", "Value": {"Ref": "Environment"}},
            {"Key": "Purpose", "Value": "ECREC2Access"},
            {"Key": "ManagedBy", "Value": "CloudFormation"},
        ]
        assert tags == expected_tags, "EC2 role tags do not match expected tags"

    def test_ecr_log_group_exists(self, ecr_template: dict[str, Any]):
        """Test CloudWatch Log Group resource exists."""
        resources = ecr_template.get("Resources", {})
        log_group = resources["ECRLogGroup"]
        assert (
            log_group["Type"] == "AWS::Logs::LogGroup"
        ), "CloudWatch Log Group type is not correct"

    def test_ecr_log_group_name_uses_repository_name_parameter(self, ecr_template: dict[str, Any]):
        """Test Log Group name uses RepositoryName parameter."""
        log_group = ecr_template["Resources"]["ECRLogGroup"]
        log_group_name = log_group["Properties"]["LogGroupName"]
        expected_log_group_name = {"Fn::Sub": "/aws/ecr/${RepositoryName}"}
        assert (
            log_group_name == expected_log_group_name
        ), "Log Group name does not match expected format"

    def test_ecr_log_group_retention_set_to_14_days(self, ecr_template: dict[str, Any]):
        """Test Log Group retention is set to 14 days for shared environment."""
        log_group = ecr_template["Resources"]["ECRLogGroup"]
        retention_in_days = log_group["Properties"]["RetentionInDays"]
        assert (
            retention_in_days == 14
        ), "Log Group retention should be 14 days for shared environment"

    def test_ecr_log_group_has_expected_resource_tags(self, ecr_template: dict[str, Any]):
        """Test Log Group has expected resource tags."""
        log_group = ecr_template["Resources"]["ECRLogGroup"]
        tags = log_group["Properties"]["Tags"]
        expected_tags = [
            {"Key": "Environment", "Value": {"Ref": "Environment"}},
            {"Key": "Purpose", "Value": "ECRLogs"},
            {"Key": "ManagedBy", "Value": "CloudFormation"},
        ]
        assert tags == expected_tags, "Log Group tags do not match expected tags"

    def test_repository_name_output_defined(self, ecr_template: dict[str, Any]):
        """Test RepositoryName output is defined."""
        outputs = ecr_template["Outputs"]
        repo_name_output = outputs["RepositoryName"]
        expected_definition = {
            "Description": "Name of the ECR repository",
            "Value": {"Ref": "ECRRepository"},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-RepositoryName"}},
        }
        assert (
            repo_name_output == expected_definition
        ), "RepositoryName output definition does not match expected"

    def test_repository_arn_output_defined(self, ecr_template: dict[str, Any]):
        """Test RepositoryArn output is defined."""
        outputs = ecr_template["Outputs"]
        repo_arn_output = outputs["RepositoryArn"]
        expected_definition = {
            "Description": "ARN of the ECR repository",
            "Value": {"Fn::GetAtt": ["ECRRepository", "Arn"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-RepositoryArn"}},
        }
        assert (
            repo_arn_output == expected_definition
        ), "RepositoryArn output definition does not match expected"

    def test_repository_uri_output_defined(self, ecr_template: dict[str, Any]):
        """Test RepositoryUri output is defined."""
        outputs = ecr_template["Outputs"]
        repo_uri_output = outputs["RepositoryUri"]
        expected_definition = {
            "Description": "URI of the ECR repository",
            "Value": {"Fn::GetAtt": ["ECRRepository", "RepositoryUri"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-RepositoryUri"}},
        }
        assert (
            repo_uri_output == expected_definition
        ), "RepositoryUri output definition does not match expected"

    def test_registry_id_output_defined(self, ecr_template: dict[str, Any]):
        """Test RegistryId output is defined."""
        outputs = ecr_template["Outputs"]
        registry_id_output = outputs["RegistryId"]
        expected_definition = {
            "Description": "Registry ID (AWS Account ID) of the ECR repository",
            "Value": {"Ref": "AWS::AccountId"},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-RegistryId"}},
        }
        assert (
            registry_id_output == expected_definition
        ), "RegistryId output definition does not match expected"

    def test_eks_role_arn_output_defined(self, ecr_template: dict[str, Any]):
        """Test EKSRoleArn output is defined."""
        outputs = ecr_template["Outputs"]
        eks_role_output = outputs["EKSRoleArn"]
        expected_definition = {
            "Description": "ARN of the IAM role for EKS pods (IRSA)",
            "Value": {"Fn::GetAtt": ["ECREKSRole", "Arn"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-EKSRoleArn"}},
        }
        assert (
            eks_role_output == expected_definition
        ), "EKSRoleArn output definition does not match expected"

    def test_ec2_role_arn_output_defined(self, ecr_template: dict[str, Any]):
        """Test EC2RoleArn output is defined."""
        outputs = ecr_template["Outputs"]
        ec2_role_output = outputs["EC2RoleArn"]
        expected_definition = {
            "Description": "ARN of the IAM role for EC2 instances",
            "Value": {"Fn::GetAtt": ["ECREC2Role", "Arn"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-EC2RoleArn"}},
        }
        assert (
            ec2_role_output == expected_definition
        ), "EC2RoleArn output definition does not match expected"

    def test_ec2_instance_profile_arn_output_defined(self, ecr_template: dict[str, Any]):
        """Test EC2InstanceProfileArn output is defined."""
        outputs = ecr_template["Outputs"]
        instance_profile_output = outputs["EC2InstanceProfileArn"]
        expected_definition = {
            "Description": "ARN of the IAM instance profile for EC2 instances",
            "Value": {"Fn::GetAtt": ["ECREC2InstanceProfile", "Arn"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-EC2InstanceProfileArn"}},
        }
        assert (
            instance_profile_output == expected_definition
        ), "EC2InstanceProfileArn output definition does not match expected"

    def test_dashboard_url_output_defined(self, ecr_template: dict[str, Any]):
        """Test DashboardUrl output is defined."""
        outputs = ecr_template["Outputs"]
        dashboard_output = outputs["DashboardUrl"]
        expected_definition = {
            "Description": "CloudWatch Dashboard URL for ECR metrics",
            "Value": {
                "Fn::Sub": "https://${AWS::Region}.console.aws.amazon.com/cloudwatch/home?region=${AWS::Region}#dashboards:name=${ECRDashboard}"
            },
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-DashboardUrl"}},
        }
        assert (
            dashboard_output == expected_definition
        ), "DashboardUrl output definition does not match expected"

    # Validates removal of SNS notification related resources and parameters
    # TODO: Remove these tests on next update after confirming no stacks use SNS notifications
    def test_notification_topic_arn_parameter_not_present(self, ecr_template: dict[str, Any]):
        """Test NotificationTopicArn parameter is not present in the template."""
        parameters = ecr_template.get("Parameters", {})
        assert (
            "NotificationTopicArn" not in parameters
        ), "NotificationTopicArn parameter should not exist after SNS notification removal"

    def test_has_notification_topic_condition_not_present(self, ecr_template: dict[str, Any]):
        """Test HasNotificationTopic condition is not present in the template."""
        conditions = ecr_template.get("Conditions", {})
        assert (
            "HasNotificationTopic" not in conditions
        ), "HasNotificationTopic condition should not exist after SNS notification removal"

    def test_ecr_scan_event_rule_not_present(self, ecr_template: dict[str, Any]):
        """Test ECRScanEventRule resource is not present in the template."""
        resources = ecr_template.get("Resources", {})
        assert (
            "ECRScanEventRule" not in resources
        ), "ECRScanEventRule resource should not exist after SNS notification removal"

    def test_repository_has_image_scanning_enabled(self, ecr_template, cdk_template_factory):
        """Test that the ECR repository has image scanning enabled."""
        from aws_cdk.assertions import Match

        template = cdk_template_factory(ecr_template)

        template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like({"ImageScanningConfiguration": {"ScanOnPush": Match.any_value()}}),
        )

    def test_repository_has_encryption_enabled(self, ecr_template, cdk_template_factory):
        """Test that the ECR repository has encryption enabled.

        Encryption at rest protects container images stored in ECR using either
        AES256 or KMS encryption. This is required for compliance with security
        standards.

        Uses flexible matching to accept either AES256 or KMS encryption types.
        """
        from aws_cdk.assertions import Match

        template = cdk_template_factory(ecr_template)

        template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {
                    "EncryptionConfiguration": {
                        "EncryptionType": Match.string_like_regexp(r"^(AES256|KMS)$")
                    }
                }
            ),
        )

    def test_repository_has_lifecycle_policy(self, ecr_template, cdk_template_factory):
        """Test that the ECR repository has a lifecycle policy configured."""
        from aws_cdk.assertions import Match

        template = cdk_template_factory(ecr_template)

        template.has_resource_properties(
            "AWS::ECR::Repository",
            Match.object_like(
                {"LifecyclePolicy": Match.object_like({"LifecyclePolicyText": Match.any_value()})}
            ),
        )
