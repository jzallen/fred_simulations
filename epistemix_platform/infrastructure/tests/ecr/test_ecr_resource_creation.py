"""
Direct ECR resource testing without CloudFormation.

This module tests ECR resources directly using moto,
avoiding CloudFormation parsing limitations.
"""

import json
from pathlib import Path
from typing import Dict, Any

import boto3
import pytest
from moto import mock_ecr, mock_iam


class TestECRDirect:
    """Test ECR resources directly with moto."""

    @pytest.fixture
    def ecr_template(self) -> Dict[str, Any]:
        """Load ECR template from JSON."""
        template_path = Path(__file__).parent.parent.parent / "templates" / "ecr" / "simulation-runner-repository.json"
        with open(template_path, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def template_parameters(self) -> Dict[str, str]:
        """Default template parameters."""
        return {
            "RepositoryName": "fred-simulation-runner",
            "Environment": "dev",
            "EnableVulnerabilityScanning": "true",
            "EnableCloudWatchLogs": "true",
            "NotificationTopicArn": ""
        }

    @mock_ecr
    def test_ecr_repository_creation(self, ecr_template: Dict[str, Any], template_parameters: Dict[str, str]):
        """Test that ECR repository can be created with expected properties."""
        ecr_client = boto3.client("ecr", region_name="us-east-1")
        
        # Extract repository properties from template
        repo_resource = ecr_template["Resources"]["ECRRepository"]
        repo_props = repo_resource["Properties"]
        
        # Create repository
        repo_name = template_parameters["RepositoryName"]
        response = ecr_client.create_repository(
            repositoryName=repo_name,
            imageScanningConfiguration={
                "scanOnPush": template_parameters["EnableVulnerabilityScanning"].lower() == "true"
            },
            encryptionConfiguration={
                "encryptionType": "KMS" if "EncryptionConfiguration" in repo_props else "AES256"
            },
            imageTagMutability=repo_props.get("ImageTagMutability", "MUTABLE")
        )
        
        # Verify repository was created
        assert response["repository"]["repositoryName"] == repo_name
        assert response["repository"]["imageScanningConfiguration"]["scanOnPush"] is True
        assert response["repository"]["imageTagMutability"] == "MUTABLE"
        
        # Verify repository ARN format
        repo_arn = response["repository"]["repositoryArn"]
        assert f"repository/{repo_name}" in repo_arn
        assert "arn:aws:ecr:" in repo_arn

    @mock_ecr
    def test_lifecycle_policy(self, ecr_template: Dict[str, Any], template_parameters: Dict[str, str]):
        """Test that lifecycle policy can be applied to repository."""
        ecr_client = boto3.client("ecr", region_name="us-east-1")
        
        # Create repository first
        repo_name = template_parameters["RepositoryName"]
        ecr_client.create_repository(repositoryName=repo_name)
        
        # Extract lifecycle policy from template
        repo_resource = ecr_template["Resources"]["ECRRepository"]
        lifecycle_policy = repo_resource["Properties"].get("LifecyclePolicyText")
        
        if lifecycle_policy:
            # Apply lifecycle policy
            response = ecr_client.put_lifecycle_policy(
                repositoryName=repo_name,
                lifecyclePolicyText=json.dumps(lifecycle_policy) if isinstance(lifecycle_policy, dict) else lifecycle_policy
            )
            
            # Verify policy was applied
            assert response["repositoryName"] == repo_name
            assert "lifecyclePolicyText" in response

    @mock_iam
    def test_iam_roles_creation(self, ecr_template: Dict[str, Any]):
        """Test that IAM roles can be created with correct policies."""
        iam_client = boto3.client("iam", region_name="us-east-1")
        
        # Test CICD Role
        cicd_role = ecr_template["Resources"]["ECRCICDRole"]
        role_name = "test-ecr-cicd-role"
        
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(cicd_role["Properties"]["AssumeRolePolicyDocument"]),
            Description="CI/CD role for ECR access"
        )
        
        assert response["Role"]["RoleName"] == role_name
        assert "arn:aws:iam::" in response["Role"]["Arn"]
        
        # Test inline policies
        for policy_name, policy_doc in cicd_role["Properties"].get("Policies", []):
            if isinstance(policy_doc, dict) and "PolicyName" in policy_doc:
                iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_doc["PolicyName"],
                    PolicyDocument=json.dumps(policy_doc["PolicyDocument"])
                )

    @mock_ecr
    def test_repository_uri_format(self, template_parameters: Dict[str, str]):
        """Test that repository URI has correct format."""
        ecr_client = boto3.client("ecr", region_name="us-east-1")
        
        repo_name = template_parameters["RepositoryName"]
        response = ecr_client.create_repository(repositoryName=repo_name)
        
        repo_uri = response["repository"]["repositoryUri"]
        
        # Verify URI format: {account}.dkr.ecr.{region}.amazonaws.com/{repo_name}
        assert ".dkr.ecr." in repo_uri
        assert ".amazonaws.com/" in repo_uri
        assert repo_uri.endswith(repo_name)

    @mock_ecr
    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_specific_repos(self, environment: str):
        """Test repository creation for different environments."""
        ecr_client = boto3.client("ecr", region_name="us-east-1")
        
        repo_name = f"fred-simulation-runner-{environment}"
        response = ecr_client.create_repository(
            repositoryName=repo_name,
            tags=[
                {"Key": "Environment", "Value": environment},
                {"Key": "Component", "Value": "ECR"},
                {"Key": "Service", "Value": "SimulationRunner"}
            ]
        )
        
        assert response["repository"]["repositoryName"] == repo_name
        
        # List tags (moto supports this)
        tags_response = ecr_client.list_tags_for_resource(
            resourceArn=response["repository"]["repositoryArn"]
        )
        
        tag_dict = {tag["Key"]: tag["Value"] for tag in tags_response.get("tags", [])}
        assert tag_dict.get("Environment") == environment
        assert tag_dict.get("Component") == "ECR"

    @mock_ecr
    def test_repository_deletion(self, template_parameters: Dict[str, str]):
        """Test that repository can be deleted."""
        ecr_client = boto3.client("ecr", region_name="us-east-1")
        
        # Create repository
        repo_name = template_parameters["RepositoryName"]
        ecr_client.create_repository(repositoryName=repo_name)
        
        # Delete repository
        response = ecr_client.delete_repository(
            repositoryName=repo_name,
            force=True
        )
        
        assert response["repository"]["repositoryName"] == repo_name
        
        # Verify deletion
        with pytest.raises(ecr_client.exceptions.RepositoryNotFoundException):
            ecr_client.describe_repositories(repositoryNames=[repo_name])

    @mock_ecr
    def test_scan_configuration(self, template_parameters: Dict[str, str]):
        """Test vulnerability scanning configuration."""
        ecr_client = boto3.client("ecr", region_name="us-east-1")
        
        repo_name = template_parameters["RepositoryName"]
        scan_enabled = template_parameters["EnableVulnerabilityScanning"].lower() == "true"
        
        response = ecr_client.create_repository(
            repositoryName=repo_name,
            imageScanningConfiguration={"scanOnPush": scan_enabled}
        )
        
        # Verify scan configuration
        repo_info = response["repository"]
        assert repo_info["imageScanningConfiguration"]["scanOnPush"] == scan_enabled
        
        # Update scan configuration
        ecr_client.put_image_scanning_configuration(
            repositoryName=repo_name,
            imageScanningConfiguration={"scanOnPush": not scan_enabled}
        )
        
        # Verify update
        response = ecr_client.describe_repositories(repositoryNames=[repo_name])
        updated_config = response["repositories"][0]["imageScanningConfiguration"]
        assert updated_config["scanOnPush"] == (not scan_enabled)