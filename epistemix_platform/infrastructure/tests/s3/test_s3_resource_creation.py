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
from unittest.mock import patch
from moto import mock_s3, mock_iam, mock_cloudformation


class TestS3ResourceCreation:
    """Test S3 resources with moto."""

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

    @patch('moto.logs.models.LogsBackend.tag_resource', return_value=None)
    def test_create_stack(self, mock_tag_resource, s3_template: Dict[str, Any], template_parameters: Dict[str, str]) -> None:
        """Test S3 bucket creation."""
        with mock_cloudformation(), mock_s3(), mock_iam():
            cf_client = boto3.client('cloudformation', region_name='us-east-1')
            s3_client = boto3.client('s3', region_name='us-east-1')

            # Create CloudFormation stack
            cf_client.create_stack(
                StackName="test-s3-stack",
                TemplateBody=json.dumps(s3_template),
                Parameters=[{"ParameterKey": k, "ParameterValue": v} for k, v in template_parameters.items()]
            )

            # Verify S3 bucket creation
            buckets = s3_client.list_buckets()
            bucket_names = [bucket['Name'] for bucket in buckets['Buckets']]
            assert template_parameters["BucketName"] in bucket_names