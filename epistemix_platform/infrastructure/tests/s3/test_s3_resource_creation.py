"""
Direct S3 resource testing without CloudFormation.

This module tests S3 resources directly using moto,
avoiding CloudFormation parsing limitations.
"""

import json
from pathlib import Path
from typing import Dict, Any

import boto3
import pytest
from moto import mock_s3, mock_iam


class TestS3Direct:
    """Test S3 resources directly with moto."""

    @pytest.fixture
    def s3_template(self) -> Dict[str, Any]:
        """Load S3 template from JSON."""
        template_path = Path(__file__).parent.parent.parent / "templates" / "s3" / "s3-upload-bucket.json"
        with open(template_path, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def template_parameters(self) -> Dict[str, str]:
        """Default template parameters."""
        return {
            "BucketName": "fred-simulations-uploads-test",
            "Environment": "dev",
            "AllowedOrigins": "http://localhost:3000,https://localhost:3000"
        }

    @mock_s3
    def test_s3_bucket_creation(self, s3_template: Dict[str, Any], template_parameters: Dict[str, str]):
        """Test that S3 bucket can be created with expected properties."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        # Create bucket
        bucket_name = template_parameters["BucketName"]
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Verify bucket exists
        response = s3_client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
        assert bucket_name in bucket_names
        
        # Get bucket location
        location = s3_client.get_bucket_location(Bucket=bucket_name)
        assert "LocationConstraint" in location

    @mock_s3
    def test_bucket_versioning(self, template_parameters: Dict[str, str]):
        """Test bucket versioning configuration."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        bucket_name = template_parameters["BucketName"]
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Enable versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Enabled"}
        )
        
        # Verify versioning is enabled
        response = s3_client.get_bucket_versioning(Bucket=bucket_name)
        assert response.get("Status") == "Enabled"

    @mock_s3
    def test_bucket_encryption(self, template_parameters: Dict[str, str]):
        """Test bucket encryption configuration."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        bucket_name = template_parameters["BucketName"]
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        )
        
        # Verify encryption
        response = s3_client.get_bucket_encryption(Bucket=bucket_name)
        rules = response["ServerSideEncryptionConfiguration"]["Rules"]
        assert len(rules) > 0
        assert rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"

    @mock_s3
    def test_bucket_cors(self, s3_template: Dict[str, Any], template_parameters: Dict[str, str]):
        """Test CORS configuration."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        bucket_name = template_parameters["BucketName"]
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Parse allowed origins
        allowed_origins = template_parameters["AllowedOrigins"].split(",")
        
        # Set CORS configuration
        cors_config = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD"],
                    "AllowedOrigins": allowed_origins,
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3000
                }
            ]
        }
        
        s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
        
        # Verify CORS configuration
        response = s3_client.get_bucket_cors(Bucket=bucket_name)
        assert "CORSRules" in response
        assert len(response["CORSRules"]) > 0
        
        rule = response["CORSRules"][0]
        assert set(rule["AllowedOrigins"]) == set(allowed_origins)
        assert "GET" in rule["AllowedMethods"]
        assert "POST" in rule["AllowedMethods"]

    @mock_s3
    def test_bucket_lifecycle(self, template_parameters: Dict[str, str]):
        """Test lifecycle configuration."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        bucket_name = template_parameters["BucketName"]
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set lifecycle configuration
        lifecycle_config = {
            "Rules": [
                {
                    "ID": "DeleteOldMultipartUploads",
                    "Status": "Enabled",
                    "AbortIncompleteMultipartUpload": {
                        "DaysAfterInitiation": 7
                    }
                },
                {
                    "ID": "TransitionToIA",
                    "Status": "Enabled",
                    "Transitions": [
                        {
                            "Days": 30,
                            "StorageClass": "STANDARD_IA"
                        }
                    ]
                }
            ]
        }
        
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        
        # Verify lifecycle configuration
        response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        assert "Rules" in response
        assert len(response["Rules"]) == 2
        
        # Check multipart upload rule
        multipart_rule = next((r for r in response["Rules"] if r["ID"] == "DeleteOldMultipartUploads"), None)
        assert multipart_rule is not None
        assert multipart_rule["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 7

    @mock_s3
    def test_bucket_public_access_block(self, template_parameters: Dict[str, str]):
        """Test public access block configuration."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        bucket_name = template_parameters["BucketName"]
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set public access block
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            }
        )
        
        # Verify public access block
        response = s3_client.get_public_access_block(Bucket=bucket_name)
        config = response["PublicAccessBlockConfiguration"]
        
        assert config["BlockPublicAcls"] is True
        assert config["BlockPublicPolicy"] is True
        assert config["IgnorePublicAcls"] is True
        assert config["RestrictPublicBuckets"] is True

    @mock_iam
    def test_s3_upload_role(self, s3_template: Dict[str, Any]):
        """Test IAM role for S3 uploads."""
        iam_client = boto3.client("iam", region_name="us-east-1")
        
        # Get role from template
        role_resource = s3_template["Resources"].get("S3UploadRole")
        if not role_resource:
            pytest.skip("No S3UploadRole in template")
        
        role_name = "test-s3-upload-role"
        
        # Create role
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(role_resource["Properties"]["AssumeRolePolicyDocument"]),
            Description="Role for S3 uploads"
        )
        
        assert response["Role"]["RoleName"] == role_name
        
        # Add inline policies
        for policy in role_resource["Properties"].get("Policies", []):
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy["PolicyName"],
                PolicyDocument=json.dumps(policy["PolicyDocument"])
            )

    @mock_s3
    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_specific_buckets(self, environment: str):
        """Test bucket creation for different environments."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        bucket_name = f"fred-simulations-uploads-{environment}"
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set tagging
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                "TagSet": [
                    {"Key": "Environment", "Value": environment},
                    {"Key": "Component", "Value": "S3"},
                    {"Key": "Service", "Value": "FileUploads"}
                ]
            }
        )
        
        # Verify tags
        response = s3_client.get_bucket_tagging(Bucket=bucket_name)
        tag_dict = {tag["Key"]: tag["Value"] for tag in response["TagSet"]}
        
        assert tag_dict["Environment"] == environment
        assert tag_dict["Component"] == "S3"
        assert tag_dict["Service"] == "FileUploads"

    @mock_s3
    def test_bucket_deletion(self, template_parameters: Dict[str, str]):
        """Test bucket deletion."""
        s3_client = boto3.client("s3", region_name="us-east-1")
        
        bucket_name = template_parameters["BucketName"]
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Put an object
        s3_client.put_object(Bucket=bucket_name, Key="test.txt", Body=b"test content")
        
        # Delete object first
        s3_client.delete_object(Bucket=bucket_name, Key="test.txt")
        
        # Delete bucket
        s3_client.delete_bucket(Bucket=bucket_name)
        
        # Verify deletion
        response = s3_client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
        assert bucket_name not in bucket_names