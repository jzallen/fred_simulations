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
from typing import Dict, Any

import pytest
from jsonschema import validate, ValidationError


class TestECRTemplate:
    """Test suite for ECR CloudFormation template."""

    @pytest.fixture(scope="class")
    def ecr_template_path(self, templates_dir: Path) -> Path:
        """Return path to ECR template."""
        return templates_dir / "ecr" / "simulation-runner-repository.json"

    @pytest.fixture(scope="class")
    def ecr_template(self, ecr_template_path: Path) -> Dict[str, Any]:
        """Load ECR CloudFormation template from JSON."""
        with open(ecr_template_path, 'r') as f:
            return json.load(f)

    def test_template_exists(self, ecr_template_path: Path):
        """Test that ECR template file exists."""
        assert ecr_template_path.exists(), f"ECR template not found at {ecr_template_path}"
        assert ecr_template_path.is_file(), f"ECR template path is not a file: {ecr_template_path}"

    def test_template_valid_json(self, ecr_template_path: Path):
        """Test that ECR template is valid JSON."""
        try:
            with open(ecr_template_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"ECR template is not valid JSON: {e}")

    def test_template_format_version(self, ecr_template: Dict[str, Any]):
        """Test that template has correct CloudFormation format version."""
        assert "AWSTemplateFormatVersion" in ecr_template
        assert ecr_template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, ecr_template: Dict[str, Any]):
        """Test that template has a description."""
        assert "Description" in ecr_template
        assert isinstance(ecr_template["Description"], str)
        assert len(ecr_template["Description"].strip()) > 0

    def test_template_parameters_defined(self, ecr_template: Dict[str, Any]):
        """Test that required parameters are defined."""
        parameters = ecr_template.get("Parameters", {})
        required_params = [
            "RepositoryName",
            "Environment", 
            "EnableVulnerabilityScanning",
            "EnableCloudWatchLogs",
            "NotificationTopicArn"
        ]
        
        for param in required_params:
            assert param in parameters, f"Required parameter {param} not found"

    def test_repository_name_parameter_constraints(self, ecr_template: Dict[str, Any]):
        """Test RepositoryName parameter constraints."""
        repo_param = ecr_template["Parameters"]["RepositoryName"]
        
        assert repo_param["Type"] == "String"
        assert repo_param["MinLength"] == 2
        assert repo_param["MaxLength"] == 256
        assert "AllowedPattern" in repo_param
        
        # Test the regex pattern
        pattern = repo_param["AllowedPattern"]
        valid_names = ["fred-simulation-runner", "my-app", "test.repo", "app_name"]
        invalid_names = ["Fred-App", "app-", "-app", "app..name"]
        
        for name in valid_names:
            assert re.match(pattern, name), f"Valid name {name} should match pattern"
        
        for name in invalid_names:
            assert not re.match(pattern, name), f"Invalid name {name} should not match pattern"

    def test_environment_parameter_constraints(self, ecr_template: Dict[str, Any]):
        """Test Environment parameter constraints."""
        env_param = ecr_template["Parameters"]["Environment"]
        
        assert env_param["Type"] == "String"
        assert env_param["Default"] == "dev"
        assert set(env_param["AllowedValues"]) == {"dev", "staging", "production"}

    def test_boolean_parameters_constraints(self, ecr_template: Dict[str, Any]):
        """Test boolean parameter constraints."""
        boolean_params = ["EnableVulnerabilityScanning", "EnableCloudWatchLogs"]
        
        for param_name in boolean_params:
            param = ecr_template["Parameters"][param_name]
            assert param["Type"] == "String"
            assert param["Default"] == "true"
            assert set(param["AllowedValues"]) == {"true", "false"}

    def test_template_conditions_defined(self, ecr_template: Dict[str, Any]):
        """Test that required conditions are defined."""
        conditions = ecr_template.get("Conditions", {})
        required_conditions = [
            "HasNotificationTopic",
            "EnableCloudWatchLogsCondition", 
            "IsProduction"
        ]
        
        for condition in required_conditions:
            assert condition in conditions, f"Required condition {condition} not found"

    def test_ecr_repository_resource(self, ecr_template: Dict[str, Any]):
        """Test ECR repository resource configuration."""
        resources = ecr_template.get("Resources", {})
        assert "ECRRepository" in resources
        
        ecr_repo = resources["ECRRepository"]
        assert ecr_repo["Type"] == "AWS::ECR::Repository"
        
        properties = ecr_repo["Properties"]
        assert "RepositoryName" in properties
        assert properties["ImageTagMutability"] == "MUTABLE"
        
        # Test scanning configuration
        scan_config = properties["ImageScanningConfiguration"]
        assert "ScanOnPush" in scan_config
        
        # Test encryption
        encryption_config = properties["EncryptionConfiguration"] 
        assert encryption_config["EncryptionType"] == "KMS"
        
        # Test lifecycle policy exists
        assert "LifecyclePolicy" in properties
        assert "LifecyclePolicyText" in properties["LifecyclePolicy"]

    def test_ecr_lifecycle_policy_valid_json(self, ecr_template: Dict[str, Any]):
        """Test that ECR lifecycle policy is valid JSON."""
        ecr_repo = ecr_template["Resources"]["ECRRepository"]
        lifecycle_text = ecr_repo["Properties"]["LifecyclePolicy"]["LifecyclePolicyText"]
        
        try:
            policy = json.loads(lifecycle_text)
            assert "rules" in policy
            assert isinstance(policy["rules"], list)
            assert len(policy["rules"]) > 0
        except json.JSONDecodeError as e:
            pytest.fail(f"Lifecycle policy is not valid JSON: {e}")

    def test_iam_roles_defined(self, ecr_template: Dict[str, Any]):
        """Test that required IAM roles are defined."""
        resources = ecr_template.get("Resources", {})
        required_roles = ["ECRCICDRole", "ECREKSRole", "ECEC2Role"]
        
        for role in required_roles:
            assert role in resources, f"Required IAM role {role} not found"
            assert resources[role]["Type"] == "AWS::IAM::Role"

    def test_cicd_role_configuration(self, ecr_template: Dict[str, Any]):
        """Test CI/CD role configuration."""
        cicd_role = ecr_template["Resources"]["ECRCICDRole"]
        properties = cicd_role["Properties"]
        
        # Test assume role policy
        assume_policy = properties["AssumeRolePolicyDocument"]
        assert assume_policy["Version"] == "2012-10-17"
        
        statements = assume_policy["Statement"]
        service_principals = []
        for stmt in statements:
            if "Principal" in stmt and "Service" in stmt["Principal"]:
                if isinstance(stmt["Principal"]["Service"], list):
                    service_principals.extend(stmt["Principal"]["Service"])
                else:
                    service_principals.append(stmt["Principal"]["Service"])
        
        assert "codebuild.amazonaws.com" in service_principals
        assert "codepipeline.amazonaws.com" in service_principals
        
        # Test policies
        assert "Policies" in properties
        policies = properties["Policies"]
        assert len(policies) > 0
        assert policies[0]["PolicyName"] == "ECRFullAccess"

    def test_eks_role_configuration(self, ecr_template: Dict[str, Any]):
        """Test EKS role configuration for IRSA."""
        eks_role = ecr_template["Resources"]["ECREKSRole"]
        properties = eks_role["Properties"]
        
        # Test assume role policy for IRSA
        assume_policy = properties["AssumeRolePolicyDocument"]
        statement = assume_policy["Statement"][0]
        
        assert statement["Principal"]["Federated"].startswith("arn:aws:iam::")
        assert "oidc-provider" in statement["Principal"]["Federated"]
        assert statement["Action"] == "sts:AssumeRoleWithWebIdentity"
        
        # Test IRSA conditions
        condition = statement["Condition"]["StringEquals"]
        assert any("sub" in key for key in condition.keys())
        assert any("aud" in key for key in condition.keys())

    def test_ec2_instance_profile(self, ecr_template: Dict[str, Any]):
        """Test EC2 instance profile configuration."""
        resources = ecr_template.get("Resources", {})
        assert "ECEC2InstanceProfile" in resources
        
        profile = resources["ECEC2InstanceProfile"]
        assert profile["Type"] == "AWS::IAM::InstanceProfile"
        assert "Roles" in profile["Properties"]

    def test_cloudwatch_resources(self, ecr_template: Dict[str, Any]):
        """Test CloudWatch-related resources."""
        resources = ecr_template.get("Resources", {})
        
        # Log group
        assert "ECRLogGroup" in resources
        log_group = resources["ECRLogGroup"]
        assert log_group["Type"] == "AWS::Logs::LogGroup"
        assert log_group["Condition"] == "EnableCloudWatchLogsCondition"
        
        # Dashboard
        assert "ECRDashboard" in resources
        dashboard = resources["ECRDashboard"]
        assert dashboard["Type"] == "AWS::CloudWatch::Dashboard"

    def test_eventbridge_rule(self, ecr_template: Dict[str, Any]):
        """Test EventBridge rule configuration."""
        resources = ecr_template.get("Resources", {})
        assert "ECRScanEventRule" in resources
        
        event_rule = resources["ECRScanEventRule"]
        assert event_rule["Type"] == "AWS::Events::Rule"
        assert event_rule["Condition"] == "HasNotificationTopic"
        
        properties = event_rule["Properties"]
        assert "EventPattern" in properties
        assert properties["State"] == "ENABLED"

    def test_template_outputs_defined(self, ecr_template: Dict[str, Any]):
        """Test that required outputs are defined."""
        outputs = ecr_template.get("Outputs", {})
        required_outputs = [
            "RepositoryName",
            "RepositoryArn", 
            "RepositoryUri",
            "RegistryId",
            "CICDRoleArn",
            "EKSRoleArn", 
            "EC2RoleArn",
            "EC2InstanceProfileArn",
            "DashboardUrl"
        ]
        
        for output in required_outputs:
            assert output in outputs, f"Required output {output} not found"

    def test_outputs_have_descriptions(self, ecr_template: Dict[str, Any]):
        """Test that all outputs have descriptions."""
        outputs = ecr_template.get("Outputs", {})
        
        for output_name, output_def in outputs.items():
            assert "Description" in output_def, f"Output {output_name} missing description"
            assert isinstance(output_def["Description"], str)
            assert len(output_def["Description"].strip()) > 0

    def test_outputs_have_exports(self, ecr_template: Dict[str, Any]):
        """Test that all outputs have export names."""
        outputs = ecr_template.get("Outputs", {})
        
        for output_name, output_def in outputs.items():
            assert "Export" in output_def, f"Output {output_name} missing export"
            assert "Name" in output_def["Export"], f"Output {output_name} export missing name"

    def test_resource_tags_present(self, ecr_template: Dict[str, Any]):
        """Test that resources have appropriate tags."""
        resources = ecr_template.get("Resources", {})
        
        # Resources that should have tags
        tagged_resources = [
            "ECRRepository",
            "ECRCICDRole", 
            "ECREKSRole",
            "ECEC2Role",
            "ECRLogGroup"
        ]
        
        for resource_name in tagged_resources:
            if resource_name in resources:
                resource = resources[resource_name]
                properties = resource.get("Properties", {})
                
                if "Tags" in properties:
                    tags = properties["Tags"]
                    assert isinstance(tags, list)
                    
                    # Check for required tag keys
                    tag_keys = [tag["Key"] for tag in tags]
                    assert "Environment" in tag_keys
                    assert "ManagedBy" in tag_keys

    def test_template_references_consistent(self, ecr_template: Dict[str, Any]):
        """Test that template references are consistent."""
        # Check that resources referenced in outputs exist
        resources = ecr_template.get("Resources", {})
        outputs = ecr_template.get("Outputs", {})
        
        for output_name, output_def in outputs.items():
            value = output_def.get("Value", "")
            if isinstance(value, dict) and "Ref" in value:
                ref_resource = value["Ref"]
                # Skip AWS pseudo parameters
                if not ref_resource.startswith("AWS::"):
                    assert ref_resource in resources, f"Output {output_name} references non-existent resource {ref_resource}"

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_template_parameters_validation(self, ecr_template: Dict[str, Any], environment: str):
        """Test parameter validation for different environments."""
        parameters = ecr_template.get("Parameters", {})
        
        # Test environment parameter
        env_param = parameters["Environment"]
        assert environment in env_param["AllowedValues"]
        
        # Test boolean parameters
        for bool_param in ["EnableVulnerabilityScanning", "EnableCloudWatchLogs"]:
            param = parameters[bool_param]
            assert "true" in param["AllowedValues"]
            assert "false" in param["AllowedValues"]

    def test_iam_policy_actions_least_privilege(self, ecr_template: Dict[str, Any]):
        """Test that IAM policies follow least privilege principle."""
        resources = ecr_template.get("Resources", {})
        
        # Check CI/CD role policies
        cicd_role = resources["ECRCICDRole"]
        policies = cicd_role["Properties"]["Policies"]
        
        for policy in policies:
            statements = policy["PolicyDocument"]["Statement"]
            for stmt in statements:
                # Should not have wildcards on resources for sensitive actions
                actions = stmt.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]
                
                sensitive_actions = [act for act in actions if "Delete" in act or "Put" in act]
                if sensitive_actions:
                    resources_list = stmt.get("Resource", [])
                    if isinstance(resources_list, str):
                        resources_list = [resources_list]
                    
                    # Should not allow * resource for sensitive actions
                    assert "*" not in resources_list or len([act for act in sensitive_actions if "GetAuthorizationToken" not in act]) == 0