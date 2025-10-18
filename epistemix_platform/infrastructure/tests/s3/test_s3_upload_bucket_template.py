"""
Tests for S3 CloudFormation template validation.

This module tests the S3 upload bucket template for compliance with:
- CloudFormation syntax and schema validation
- Parameter constraints and validation
- Security configurations (public access blocks, CORS)
- Lifecycle policies and versioning
- Output definitions and exports
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest


class TestS3Template:
    """Test suite for S3 CloudFormation template."""

    @pytest.fixture(scope="class")
    def s3_template_path(self, templates_dir: Path) -> Path:
        """Return path to S3 template."""
        return templates_dir / "s3" / "s3-upload-bucket.json"

    @pytest.fixture(scope="class")
    def s3_template(self, s3_template_path: Path) -> dict[str, Any]:
        """Load S3 CloudFormation template from JSON."""
        with open(s3_template_path) as f:
            return json.load(f)

    def test_template_exists(self, s3_template_path: Path):
        """Test that S3 template file exists."""
        assert s3_template_path.exists(), f"S3 template not found at {s3_template_path}"
        assert s3_template_path.is_file(), f"S3 template path is not a file: {s3_template_path}"

    def test_template_valid_json(self, s3_template_path: Path):
        """Test that S3 template is valid JSON."""
        try:
            with open(s3_template_path, encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"S3 template is not valid JSON: {e}")

    def test_template_format_version(self, s3_template: dict[str, Any]):
        """Test that template has correct CloudFormation format version."""
        assert "AWSTemplateFormatVersion" in s3_template
        assert s3_template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_only_has_expected_parameters(self, s3_template: dict[str, Any]):
        """Test that only expected parameters are defined."""
        parameters = s3_template.get("Parameters", {})
        expected_params = ["BucketName", "Environment", "AllowedOrigins"]

        assert set(parameters.keys()) == set(
            expected_params
        ), f"Unexpected parameters found: {set(parameters.keys()) - set(expected_params)}"

    def test_bucket_name_has_string_type_constraint(self, s3_template: dict[str, Any]):
        """Test that BucketName parameter is of type String."""
        bucket_param = s3_template["Parameters"]["BucketName"]
        assert bucket_param["Type"] == "String"

    def test_bucket_name_has_min_length_3(self, s3_template: dict[str, Any]):
        """Test that BucketName parameter has a minimum length of 3."""
        bucket_param = s3_template["Parameters"]["BucketName"]
        assert bucket_param["MinLength"] == 3

    def test_bucket_name_has_max_length_63(self, s3_template: dict[str, Any]):
        """Test that BucketName parameter has a maximum length of 63."""
        bucket_param = s3_template["Parameters"]["BucketName"]
        assert bucket_param["MaxLength"] == 63

    def test_bucket_name_pattern_supports_valid_names(self, s3_template: dict[str, Any]):
        """Test that BucketName parameter pattern supports valid bucket names."""
        bucket_param = s3_template["Parameters"]["BucketName"]
        assert "AllowedPattern" in bucket_param

        pattern = bucket_param["AllowedPattern"]
        valid_names = ["my-bucket", "test-bucket-123", "app1-uploads", "data-bucket-2024"]

        for name in valid_names:
            assert re.match(pattern, name), f"Valid bucket name {name} should match pattern"

    def test_bucket_name_pattern_rejects_invalid_names(self, s3_template: dict[str, Any]):
        """Test that BucketName parameter pattern rejects invalid bucket names."""
        bucket_param = s3_template["Parameters"]["BucketName"]
        assert "AllowedPattern" in bucket_param

        pattern = bucket_param["AllowedPattern"]
        invalid_names = [
            "MyBucket",
            "bucket-",
            "-bucket",
            "bucket.",
            ".bucket",
            "bucket..name",
            "bucket_name",
        ]

        for name in invalid_names:
            assert not re.match(
                pattern, name
            ), f"Invalid bucket name {name} should not match pattern"

    def test_environment_has_string_type_constraint(self, s3_template: dict[str, Any]):
        """Test that Environment parameter is of type String."""
        env_param = s3_template["Parameters"]["Environment"]
        assert env_param["Type"] == "String"

    def test_environment_has_default_value(self, s3_template: dict[str, Any]):
        """Test that Environment parameter has a default value."""
        env_param = s3_template["Parameters"]["Environment"]
        assert "Default" in env_param
        assert env_param["Default"] == "dev"

    def test_environment_only_allows_expected_values(self, s3_template: dict[str, Any]):
        """Test that Environment parameter only allows expected values."""
        env_param = s3_template["Parameters"]["Environment"]
        assert "AllowedValues" in env_param
        assert set(env_param["AllowedValues"]) == {"dev", "staging", "production"}

    def test_allowed_origins_has_comma_delimited_list_type(self, s3_template: dict[str, Any]):
        """Test that AllowedOrigins parameter is of type CommaDelimitedList."""
        origins_param = s3_template["Parameters"]["AllowedOrigins"]
        assert origins_param["Type"] == "CommaDelimitedList"

    def test_allowed_origins_has_expected_default_value(self, s3_template: dict[str, Any]):
        """Test that AllowedOrigins parameter has a default value."""
        origins_param = s3_template["Parameters"]["AllowedOrigins"]
        assert origins_param["Default"] == "http://localhost:3000,https://localhost:3000"

    def test_s3_bucket_resource_exists(self, s3_template: dict[str, Any]):
        """Test S3 bucket resource configuration."""
        resources = s3_template.get("Resources", {})
        bucket = resources["UploadBucket"]
        assert bucket["Type"] == "AWS::S3::Bucket"

        properties = bucket["Properties"]
        assert "BucketName" in properties

    def test_upload_bucket_bucket_name_uses_parameter(self, s3_template: dict[str, Any]):
        """Test that UploadBucket uses the BucketName parameter."""
        bucket = s3_template["Resources"]["UploadBucket"]
        bucket_name = bucket["Properties"]["BucketName"]
        assert bucket_name["Ref"] == "BucketName"

    def test_s3_versioning_enabled(self, s3_template: dict[str, Any]):
        """Test that S3 versioning is enabled."""
        bucket = s3_template["Resources"]["UploadBucket"]
        versioning = bucket["Properties"]["VersioningConfiguration"]
        assert versioning["Status"] == "Enabled"

    def test_s3_public_access_blocked(self, s3_template: dict[str, Any]):
        """Test that public access is properly blocked."""
        bucket = s3_template["Resources"]["UploadBucket"]
        public_access_config = bucket["Properties"]["PublicAccessBlockConfiguration"]

        # All public access settings should be true
        required_settings = [
            "BlockPublicAcls",
            "BlockPublicPolicy",
            "IgnorePublicAcls",
            "RestrictPublicBuckets",
        ]

        for setting in required_settings:
            assert public_access_config[setting] is True, f"{setting} should be True"

    def test_s3__cors_rules__only_has_one_rule(self, s3_template: dict[str, Any]):
        """Test that CORS rules only has one rule defined."""
        bucket = s3_template["Resources"]["UploadBucket"]
        cors_rules = bucket["Properties"]["CorsConfiguration"]["CorsRules"]

        assert isinstance(cors_rules, list)
        assert len(cors_rules) == 1, "CORS should only have one rule defined."

    def test_s3__cors_rules__allows_all_headers(self, s3_template: dict[str, Any]):
        """Test that CORS rules allow all headers."""
        bucket = s3_template["Resources"]["UploadBucket"]
        cors_rule = bucket["Properties"]["CorsConfiguration"]["CorsRules"][0]

        assert cors_rule["AllowedHeaders"] == ["*"], "CORS should allow all headers."

    def test_s3__cors_rules__allows_specific_methods(self, s3_template: dict[str, Any]):
        """Test that CORS rules allow specific HTTP methods."""
        bucket = s3_template["Resources"]["UploadBucket"]
        cors_rule = bucket["Properties"]["CorsConfiguration"]["CorsRules"][0]

        allowed_methods = cors_rule["AllowedMethods"]
        expected_methods = ["GET", "PUT", "POST", "HEAD"]

        assert allowed_methods == expected_methods, f"CORS should allow methods {expected_methods}"

    def test_s3__cors_rules__uses_parameter_for_origins(self, s3_template: dict[str, Any]):
        """Test that CORS rules use the AllowedOrigins parameter."""
        bucket = s3_template["Resources"]["UploadBucket"]
        cors_rule = bucket["Properties"]["CorsConfiguration"]["CorsRules"][0]
        assert (
            cors_rule["AllowedOrigins"]["Ref"] == "AllowedOrigins"
        ), "CORS should use AllowedOrigins parameter."

    def test_s3__cors_rules__only_etag_header_exposed_to_client(self, s3_template: dict[str, Any]):
        """Test that CORS rules expose the ETag header to the client.

        The ETag header is important for clients to manage caching and verify object integrity.
        The tag value is a hash of the object contents.
        """
        bucket = s3_template["Resources"]["UploadBucket"]
        cors_rule = bucket["Properties"]["CorsConfiguration"]["CorsRules"][0]
        assert cors_rule["ExposedHeaders"] == ["ETag"], "CORS should expose the ETag header."

    def test_s3__cors_rules__has_max_age_3000(self, s3_template: dict[str, Any]):
        """Test that CORS rules have a MaxAge of 3000 seconds."""
        bucket = s3_template["Resources"]["UploadBucket"]
        cors_rule = bucket["Properties"]["CorsConfiguration"]["CorsRules"][0]
        assert cors_rule["MaxAge"] == 3000, "CORS MaxAge should be 3000 seconds."

    def test_s3__lifecycle_policies__has_two_rules(self, s3_template: dict[str, Any]):
        """Test that lifecycle policies have exactly two rules defined."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        assert isinstance(lifecycle_rules, list)
        assert len(lifecycle_rules) == 2, "Lifecycle configuration should have exactly two rules."

    def test_s3__lifecycle_policies__multipart_upload_rule_is_enabled(
        self, s3_template: dict[str, Any]
    ):
        """Test that multipart upload rule is enabled."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the multipart upload rule
        multipart_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "AbortIncompleteMultipartUploads"
        )

        assert multipart_rule["Status"] == "Enabled"

    def test_s3__lifecycle_policies__multipart_upload_abort_after_1_day(
        self, s3_template: dict[str, Any]
    ):
        """Test that multipart uploads are aborted after 1 day."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the multipart upload rule
        multipart_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "AbortIncompleteMultipartUploads"
        )

        assert multipart_rule["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 1

    def test_s3__lifecycle_policies__complete_file_lifecycle_is_enabled(
        self, s3_template: dict[str, Any]
    ):
        """Test that complete file lifecycle rule is enabled."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the complete file lifecycle rule
        complete_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle"
        )

        assert complete_rule["Status"] == "Enabled"

    def test_s3__lifecycle_policies__complete_file_lifecycle_has_1_transition_rule(
        self, s3_template: dict[str, Any]
    ):
        """Test that complete file lifecycle has exactly 1 transition rule."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the complete file lifecycle rule
        complete_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle"
        )

        transitions = complete_rule["Transitions"]
        assert len(transitions) == 1

    def test_s3__lifecycle_policies__complete_file_lifecycle_moves_to_glacier_after_2_days(
        self, s3_template: dict[str, Any]
    ):
        """Test that complete file lifecycle moves to Glacier after 2 days."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the complete file lifecycle rule
        complete_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle"
        )

        transitions = complete_rule["Transitions"]
        assert transitions[0]["StorageClass"] == "GLACIER"
        assert transitions[0]["TransitionInDays"] == 2

    def test_s3__lifecycle_policies__complete_file_lifecycle_expires_after_7_days(
        self, s3_template: dict[str, Any]
    ):
        """Test that complete file lifecycle expires after 7 days."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the complete file lifecycle rule
        complete_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle"
        )

        assert "ExpirationInDays" in complete_rule
        assert complete_rule["ExpirationInDays"] == 7

    def test_s3__lifecycle_policies__complete_file_lifecycle_non_current_version__has_1_transition_rule(
        self, s3_template: dict[str, Any]
    ):
        """Test that complete file lifecycle non-current version has exactly 1 transition rule."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the complete file lifecycle rule
        complete_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle"
        )

        assert "NoncurrentVersionTransitions" in complete_rule
        non_current_transitions = complete_rule["NoncurrentVersionTransitions"]
        assert len(non_current_transitions) == 1

    def test_s3__lifecycle_policies__complete_file_lifecycle_moves_non_current_versions_to_glacier_after_2_days(
        self, s3_template: dict[str, Any]
    ):
        """Test that complete file lifecycle moves non-current versions to Glacier after 2 days."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the complete file lifecycle rule
        complete_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle"
        )

        assert complete_rule["NoncurrentVersionTransitions"][0]["StorageClass"] == "GLACIER"
        assert complete_rule["NoncurrentVersionTransitions"][0]["TransitionInDays"] == 2

    def test_s3__lifecycle_policies__complete_file_lifecycle_expires_non_current_versions_after_7_days(
        self, s3_template: dict[str, Any]
    ):
        """Test that complete file lifecycle expires non-current versions after 7 days."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

        # Find the complete file lifecycle rule
        complete_rule = next(
            rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle"
        )

        assert "NoncurrentVersionExpirationInDays" in complete_rule
        assert complete_rule["NoncurrentVersionExpirationInDays"] == 7

    def test_upload_log_group_resource_exists(self, s3_template: dict[str, Any]):
        """Test CloudWatch Log Group configuration."""
        resources = s3_template.get("Resources", {})
        log_group = resources["UploadLogGroup"]
        assert log_group["Type"] == "AWS::Logs::LogGroup"

    def test_log_group_has_30_day_retention(self, s3_template: dict[str, Any]):
        resources = s3_template.get("Resources", {})
        log_group = resources["UploadLogGroup"]
        properties = log_group["Properties"]
        assert properties["RetentionInDays"] == 30

    def test_log_group_name_uses_bucket_name_parameter(self, s3_template: dict[str, Any]):
        resources = s3_template.get("Resources", {})
        log_group = resources["UploadLogGroup"]
        log_group_name = log_group["Properties"]["LogGroupName"]

        expected_sub = "/aws/s3/${BucketName}/access-logs"
        assert log_group_name["Fn::Sub"] == expected_sub, f"Log group name should be {expected_sub}"

    def test_log_group_has_expected_tags(self, s3_template: dict[str, Any]):
        resources = s3_template.get("Resources", {})
        log_group = resources["UploadLogGroup"]
        tags = log_group["Properties"]["Tags"]
        expected = [{"Key": "Environment", "Value": {"Ref": "Environment"}}]
        assert tags == expected, f"Log group tags should be {expected}"

    def test_iam_upload_role_resource_exists(self, s3_template: dict[str, Any]):
        """Test that IAM role for S3 uploads exists."""
        resources = s3_template.get("Resources", {})
        assert "S3UploadRole" in resources, "S3UploadRole resource not found in template."

    def test_iam_upload_role_name_uses_bucket_name_parameter(self, s3_template: dict[str, Any]):
        """Test that IAM role name uses the BucketName parameter."""
        resources = s3_template.get("Resources", {})
        role = resources["S3UploadRole"]
        role_name = role["Properties"]["RoleName"]
        expected_sub = "${BucketName}-upload-role"
        assert role_name["Fn::Sub"] == expected_sub, f"Role name should be {expected_sub}"

    def test_iam_upload_can_be_assumed_by_ec2(self, s3_template: dict[str, Any]):
        """Test that IAM role can be assumed by EC2 service."""
        resources = s3_template.get("Resources", {})
        assume_policy = resources["S3UploadRole"]["Properties"]["AssumeRolePolicyDocument"]

        statements = assume_policy["Statement"]
        expected_ec2_rule = {
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }

        assert (
            expected_ec2_rule in statements
        ), "EC2 service should be allowed to assume the S3 upload role."

    def test_iam_upload_can_be_assumed_by_ecs_tasks(self, s3_template: dict[str, Any]):
        """Test that IAM role can be assumed by ECS tasks service."""
        resources = s3_template.get("Resources", {})
        assume_policy = resources["S3UploadRole"]["Properties"]["AssumeRolePolicyDocument"]

        statements = assume_policy["Statement"]
        expected_ecs_rule = {
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }

        assert (
            expected_ecs_rule in statements
        ), "ECS tasks service should be allowed to assume the S3 upload role."

    def test_iam_upload_role_has_1_policy(self, s3_template: dict[str, Any]):
        """Test that IAM role has exactly one inline policy."""
        resources = s3_template.get("Resources", {})
        role = resources["S3UploadRole"]
        policies = role["Properties"]["Policies"]

        assert len(policies) == 1, "IAM role should have exactly one inline policy."

    def test_iam_upload_role__s3_upload_policy_exists(self, s3_template: dict[str, Any]):
        """Test that IAM role has S3 upload policy attached."""
        resources = s3_template.get("Resources", {})
        role = resources["S3UploadRole"]
        policies = role["Properties"]["Policies"]

        assert (
            policies[0]["PolicyName"] == "S3UploadPolicy"
        ), "IAM role should have S3UploadPolicy attached."

    def test_iam_upload_role__s3_upload_policy__has_3_statement_rules(
        self, s3_template: dict[str, Any]
    ):
        """Test that S3 upload policy has exactly 3 statements (encrypted upload, download, bucket operations)."""
        resources = s3_template.get("Resources", {})
        role = resources["S3UploadRole"]
        policy = role["Properties"]["Policies"][0]
        statements = policy["PolicyDocument"]["Statement"]

        assert len(statements) == 3, "S3 upload policy should have exactly 3 statements."

    def test_iam_upload_role__s3_upload_policy__has_encrypted_upload_and_download_rules(
        self, s3_template: dict[str, Any]
    ):
        """Test that S3 upload policy has separate encrypted upload and download rules."""
        resources = s3_template.get("Resources", {})
        role = resources["S3UploadRole"]
        policy = role["Properties"]["Policies"][0]
        statements = policy["PolicyDocument"]["Statement"]

        # Check for encrypted upload rule (should be first statement)
        upload_rule = {
            "Effect": "Allow",
            "Action": ["s3:PutObject"],
            "Resource": {"Fn::Sub": "arn:aws:s3:::${UploadBucket}/*"},
            "Condition": {"StringEquals": {"s3:x-amz-server-side-encryption": "AES256"}},
        }

        # Check for download/read rule (should be second statement)
        download_rule = {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:DeleteObject",
                "s3:RestoreObject",
            ],
            "Resource": {"Fn::Sub": "arn:aws:s3:::${UploadBucket}/*"},
        }

        assert (
            upload_rule in statements
        ), "S3 upload policy should have encrypted upload rule with AES256 condition."
        assert (
            download_rule in statements
        ), "S3 upload policy should have download/read rule without encryption condition."

    def test_iam_upload_role__s3_upload_policy__has_expected_bucket_level_rule(
        self, s3_template: dict[str, Any]
    ):
        """Test that S3 upload policy has expected bucket-level rule."""
        resources = s3_template.get("Resources", {})
        role = resources["S3UploadRole"]
        policy = role["Properties"]["Policies"][0]
        statements = policy["PolicyDocument"]["Statement"]

        expected_rule = {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetLifecycleConfiguration",
                "s3:PutLifecycleConfiguration",
            ],
            "Resource": {"Fn::Sub": "arn:aws:s3:::${UploadBucket}"},
        }

        assert (
            expected_rule in statements
        ), "S3 upload policy should have expected bucket-level rule."

    def test_iam_upload_role__s3_upload_policy__has_expected_tags(
        self, s3_template: dict[str, Any]
    ):
        """Test that S3 upload policy has expected tags."""
        resources = s3_template.get("Resources", {})
        role = resources["S3UploadRole"]
        tags = role["Properties"]["Tags"]

        expected_tags = [{"Key": "Environment", "Value": {"Ref": "Environment"}}]

        assert tags == expected_tags, f"S3 upload policy should have tags {expected_tags}"

    def test_bucket_name_defined_in_outputs(self, s3_template: dict[str, Any]):
        """Test that BucketName output is defined correctly."""
        outputs = s3_template["Outputs"]
        bucket_name_output = outputs["BucketName"]
        expected_definition = {
            "Description": "Name of the created S3 bucket",
            "Value": {"Ref": "UploadBucket"},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-BucketName"}},
        }
        assert (
            bucket_name_output == expected_definition
        ), "BucketName output is not defined as expected."

    def test_bucket_arn_defined_in_outputs(self, s3_template: dict[str, Any]):
        """Test that BucketArn output is defined correctly."""
        outputs = s3_template["Outputs"]
        bucket_arn_output = outputs["BucketArn"]
        expected_definition = {
            "Description": "ARN of the created S3 bucket",
            "Value": {"Fn::GetAtt": ["UploadBucket", "Arn"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-BucketArn"}},
        }

        assert (
            bucket_arn_output == expected_definition
        ), "BucketArn output is not defined as expected."

    def test_bucket_domain_name_defined_in_outputs(self, s3_template: dict[str, Any]):
        """Test that BucketDomainName output is defined correctly."""
        outputs = s3_template["Outputs"]
        bucket_domain_output = outputs["BucketDomainName"]
        expected_definition = {
            "Description": "Domain name of the S3 bucket",
            "Value": {"Fn::GetAtt": ["UploadBucket", "DomainName"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-BucketDomainName"}},
        }

        assert (
            bucket_domain_output == expected_definition
        ), "BucketDomainName output is not defined as expected."

    def test_upload_role_arn_defined_in_outputs(self, s3_template: dict[str, Any]):
        """Test that UploadRoleArn output is defined correctly."""
        outputs = s3_template["Outputs"]
        role_arn_output = outputs["UploadRoleArn"]
        expected_definition = {
            "Description": "ARN of the IAM role for S3 uploads",
            "Value": {"Fn::GetAtt": ["S3UploadRole", "Arn"]},
            "Export": {"Name": {"Fn::Sub": "${AWS::StackName}-UploadRoleArn"}},
        }

        assert (
            role_arn_output == expected_definition
        ), "UploadRoleArn output is not defined as expected."

    def test_template_outputs_defined(self, s3_template: dict[str, Any]):
        """Test that required outputs are defined."""
        outputs = s3_template.get("Outputs", {})
        required_outputs = ["BucketName", "BucketArn", "BucketDomainName", "UploadRoleArn"]

        for output in required_outputs:
            assert output in outputs, f"Required output {output} not found"

    def test_outputs_have_descriptions(self, s3_template: dict[str, Any]):
        """Test that all outputs have descriptions."""
        outputs = s3_template.get("Outputs", {})

        for output_name, output_def in outputs.items():
            assert "Description" in output_def, f"Output {output_name} missing description"
            assert isinstance(output_def["Description"], str)
            assert len(output_def["Description"].strip()) > 0

    def test_outputs_have_exports(self, s3_template: dict[str, Any]):
        """Test that all outputs have export names."""
        outputs = s3_template.get("Outputs", {})

        for output_name, output_def in outputs.items():
            assert "Export" in output_def, f"Output {output_name} missing export"
            assert "Name" in output_def["Export"], f"Output {output_name} export missing name"

    def test_resource_tags_present(self, s3_template: dict[str, Any]):
        """Test that resources have appropriate tags."""
        resources = s3_template.get("Resources", {})

        # Resources that should have tags
        tagged_resources = ["UploadBucket", "UploadLogGroup", "S3UploadRole"]

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

    def test_template_references_consistent(self, s3_template: dict[str, Any]):
        """Test that template references are consistent."""
        # Check that resources referenced in outputs exist
        resources = s3_template.get("Resources", {})
        outputs = s3_template.get("Outputs", {})

        for output_name, output_def in outputs.items():
            value = output_def.get("Value", "")
            if isinstance(value, dict):
                if "Ref" in value:
                    ref_resource = value["Ref"]
                    # Skip AWS pseudo parameters
                    if not ref_resource.startswith("AWS::"):
                        assert (
                            ref_resource in resources
                        ), f"Output {output_name} references non-existent resource {ref_resource}"
                elif "GetAtt" in value:
                    att_resource = (
                        value["GetAtt"][0] if isinstance(value["GetAtt"], list) else value["GetAtt"]
                    )
                    if not att_resource.startswith("AWS::"):
                        assert (
                            att_resource in resources
                        ), f"Output {output_name} GetAtt references non-existent resource {att_resource}"

    def test_bucket_has_ownership_controls(self, s3_template: dict[str, Any]):
        """Test that S3 bucket has ownership controls to disable ACLs."""
        resources = s3_template.get("Resources", {})
        bucket = resources["UploadBucket"]

        assert (
            "OwnershipControls" in bucket["Properties"]
        ), "S3 bucket should have OwnershipControls configuration."

        ownership_controls = bucket["Properties"]["OwnershipControls"]
        assert "Rules" in ownership_controls, "OwnershipControls should have Rules."

        rule = ownership_controls["Rules"][0]
        assert (
            rule["ObjectOwnership"] == "BucketOwnerEnforced"
        ), "Bucket should enforce BucketOwnerEnforced to disable ACLs."

    def test_bucket_has_encryption_configuration(self, s3_template: dict[str, Any]):
        """Test that S3 bucket has server-side encryption configured."""
        resources = s3_template.get("Resources", {})
        bucket = resources["UploadBucket"]

        assert (
            "BucketEncryption" in bucket["Properties"]
        ), "S3 bucket should have BucketEncryption configuration."

        encryption_config = bucket["Properties"]["BucketEncryption"]
        assert (
            "ServerSideEncryptionConfiguration" in encryption_config
        ), "BucketEncryption should have ServerSideEncryptionConfiguration."

        sse_config = encryption_config["ServerSideEncryptionConfiguration"][0]
        assert (
            sse_config["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
        ), "Bucket should use AES256 encryption."

    def test_bucket_encryption_policy_exists(self, s3_template: dict[str, Any]):
        """Test that bucket encryption policy resource exists."""
        resources = s3_template.get("Resources", {})

        assert (
            "BucketEncryptionPolicy" in resources
        ), "BucketEncryptionPolicy resource should exist."

        policy = resources["BucketEncryptionPolicy"]
        assert (
            policy["Type"] == "AWS::S3::BucketPolicy"
        ), "BucketEncryptionPolicy should be an S3 BucketPolicy."
        assert (
            policy["Properties"]["Bucket"]["Ref"] == "UploadBucket"
        ), "Policy should reference the UploadBucket."

    def test_bucket_encryption_policy_denies_insecure_connections(
        self, s3_template: dict[str, Any]
    ):
        """Test that bucket policy denies insecure connections."""
        resources = s3_template.get("Resources", {})
        policy = resources["BucketEncryptionPolicy"]
        statements = policy["Properties"]["PolicyDocument"]["Statement"]

        # Find the deny insecure connections statement
        deny_insecure = next(
            (s for s in statements if s.get("Sid") == "DenyInsecureConnections"), None
        )

        assert deny_insecure is not None, "Policy should have DenyInsecureConnections statement."
        assert deny_insecure["Effect"] == "Deny", "DenyInsecureConnections should be a Deny effect."
        assert (
            deny_insecure["Principal"] == "*"
        ), "DenyInsecureConnections should apply to all principals."
        assert (
            deny_insecure["Action"] == "s3:*"
        ), "DenyInsecureConnections should apply to all S3 actions."
        assert (
            deny_insecure["Condition"]["Bool"]["aws:SecureTransport"] == "false"
        ), "Should deny when SecureTransport is false."

    def test_bucket_encryption_policy_denies_unencrypted_uploads(self, s3_template: dict[str, Any]):
        """Test that bucket policy denies unencrypted uploads."""
        resources = s3_template.get("Resources", {})
        policy = resources["BucketEncryptionPolicy"]
        statements = policy["Properties"]["PolicyDocument"]["Statement"]

        # Find the deny unencrypted uploads statement
        deny_unencrypted = next(
            (s for s in statements if s.get("Sid") == "DenyUnencryptedObjectUploads"), None
        )

        assert (
            deny_unencrypted is not None
        ), "Policy should have DenyUnencryptedObjectUploads statement."
        assert (
            deny_unencrypted["Effect"] == "Deny"
        ), "DenyUnencryptedObjectUploads should be a Deny effect."
        assert (
            deny_unencrypted["Principal"] == "*"
        ), "DenyUnencryptedObjectUploads should apply to all principals."
        assert (
            deny_unencrypted["Action"] == "s3:PutObject"
        ), "DenyUnencryptedObjectUploads should apply to PutObject."
        assert (
            deny_unencrypted["Condition"]["StringNotEquals"]["s3:x-amz-server-side-encryption"]
            == "AES256"
        ), "Should deny when encryption is not AES256."

    def test_bucket_encryption_policy_denies_missing_encryption_header(
        self, s3_template: dict[str, Any]
    ):
        """Test that bucket policy denies uploads missing encryption header."""
        resources = s3_template.get("Resources", {})
        policy = resources["BucketEncryptionPolicy"]
        statements = policy["Properties"]["PolicyDocument"]["Statement"]

        # Find the deny missing header statement
        deny_missing = next(
            (s for s in statements if s.get("Sid") == "DenyMissingEncryptionHeader"), None
        )

        assert deny_missing is not None, "Policy should have DenyMissingEncryptionHeader statement."
        assert (
            deny_missing["Effect"] == "Deny"
        ), "DenyMissingEncryptionHeader should be a Deny effect."
        assert (
            deny_missing["Principal"] == "*"
        ), "DenyMissingEncryptionHeader should apply to all principals."
        assert (
            deny_missing["Action"] == "s3:PutObject"
        ), "DenyMissingEncryptionHeader should apply to PutObject."
        assert (
            deny_missing["Condition"]["Null"]["s3:x-amz-server-side-encryption"] == "true"
        ), "Should deny when encryption header is missing."
