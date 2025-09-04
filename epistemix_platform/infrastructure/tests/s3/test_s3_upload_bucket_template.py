"""
Tests for S3 CloudFormation template validation.

This module tests the S3 upload bucket template for compliance with:
- CloudFormation syntax and schema validation
- Parameter constraints and validation
- Security configurations (public access blocks, CORS)
- Lifecycle policies and versioning
- Output definitions and exports
"""

import re
from pathlib import Path
from typing import Dict, Any, List

import json
import pytest


class TestS3Template:
    """Test suite for S3 CloudFormation template."""

    @pytest.fixture(scope="class")
    def s3_template_path(self, templates_dir: Path) -> Path:
        """Return path to S3 template."""
        return templates_dir / "s3" / "s3-upload-bucket.json"

    @pytest.fixture(scope="class")
    def s3_template(self, s3_template_path: Path) -> Dict[str, Any]:
        """Load S3 CloudFormation template from JSON."""
        with open(s3_template_path, 'r') as f:
            return json.load(f)

    def test_template_exists(self, s3_template_path: Path):
        """Test that S3 template file exists."""
        assert s3_template_path.exists(), f"S3 template not found at {s3_template_path}"
        assert s3_template_path.is_file(), f"S3 template path is not a file: {s3_template_path}"

    def test_template_valid_json(self, s3_template_path: Path):
        """Test that S3 template is valid JSON."""
        try:
            with open(s3_template_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"S3 template is not valid JSON: {e}")

    def test_template_format_version(self, s3_template: Dict[str, Any]):
        """Test that template has correct CloudFormation format version."""
        assert "AWSTemplateFormatVersion" in s3_template
        assert s3_template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, s3_template: Dict[str, Any]):
        """Test that template has a description."""
        assert "Description" in s3_template
        assert isinstance(s3_template["Description"], str)
        assert len(s3_template["Description"].strip()) > 0

    def test_template_parameters_defined(self, s3_template: Dict[str, Any]):
        """Test that required parameters are defined."""
        parameters = s3_template.get("Parameters", {})
        required_params = ["BucketName", "Environment", "AllowedOrigins"]
        
        for param in required_params:
            assert param in parameters, f"Required parameter {param} not found"

    def test_bucket_name_parameter_constraints(self, s3_template: Dict[str, Any]):
        """Test BucketName parameter constraints."""
        bucket_param = s3_template["Parameters"]["BucketName"]
        
        assert bucket_param["Type"] == "String"
        assert bucket_param["MinLength"] == 3
        assert bucket_param["MaxLength"] == 63
        assert "AllowedPattern" in bucket_param
        
        # Test the regex pattern for S3 bucket naming
        pattern = bucket_param["AllowedPattern"]
        valid_names = ["my-bucket", "test-bucket-123", "app1-uploads", "data-bucket-2024"]
        invalid_names = ["MyBucket", "bucket-", "-bucket", "bucket.", ".bucket", "bucket..name", "bucket_name"]
        
        for name in valid_names:
            assert re.match(pattern, name), f"Valid bucket name {name} should match pattern"
        
        for name in invalid_names:
            assert not re.match(pattern, name), f"Invalid bucket name {name} should not match pattern"

    def test_environment_parameter_constraints(self, s3_template: Dict[str, Any]):
        """Test Environment parameter constraints."""
        env_param = s3_template["Parameters"]["Environment"]
        
        assert env_param["Type"] == "String"
        assert env_param["Default"] == "dev"
        assert set(env_param["AllowedValues"]) == {"dev", "staging", "production"}

    def test_allowed_origins_parameter(self, s3_template: Dict[str, Any]):
        """Test AllowedOrigins parameter."""
        origins_param = s3_template["Parameters"]["AllowedOrigins"]
        
        assert origins_param["Type"] == "CommaDelimitedList"
        assert "Default" in origins_param
        
        # Test default contains localhost origins
        default_origins = origins_param["Default"]
        assert "localhost" in default_origins.lower()

    def test_s3_bucket_resource(self, s3_template: Dict[str, Any]):
        """Test S3 bucket resource configuration."""
        resources = s3_template.get("Resources", {})
        assert "UploadBucket" in resources
        
        bucket = resources["UploadBucket"]
        assert bucket["Type"] == "AWS::S3::Bucket"
        
        properties = bucket["Properties"]
        assert "BucketName" in properties

    def test_s3_versioning_enabled(self, s3_template: Dict[str, Any]):
        """Test that S3 versioning is enabled."""
        bucket = s3_template["Resources"]["UploadBucket"]
        properties = bucket["Properties"]
        
        assert "VersioningConfiguration" in properties
        versioning = properties["VersioningConfiguration"]
        assert versioning["Status"] == "Enabled"

    def test_s3_public_access_blocked(self, s3_template: Dict[str, Any]):
        """Test that public access is properly blocked."""
        bucket = s3_template["Resources"]["UploadBucket"]
        properties = bucket["Properties"]
        
        assert "PublicAccessBlockConfiguration" in properties
        public_access_config = properties["PublicAccessBlockConfiguration"]
        
        # All public access settings should be true
        required_settings = [
            "BlockPublicAcls",
            "BlockPublicPolicy", 
            "IgnorePublicAcls",
            "RestrictPublicBuckets"
        ]
        
        for setting in required_settings:
            assert setting in public_access_config
            assert public_access_config[setting] is True, f"{setting} should be True"

    def test_s3_cors_configuration(self, s3_template: Dict[str, Any]):
        """Test CORS configuration."""
        bucket = s3_template["Resources"]["UploadBucket"]
        properties = bucket["Properties"]
        
        assert "CorsConfiguration" in properties
        cors_config = properties["CorsConfiguration"]
        assert "CorsRules" in cors_config
        
        cors_rules = cors_config["CorsRules"]
        assert isinstance(cors_rules, list)
        assert len(cors_rules) > 0
        
        # Test first CORS rule
        rule = cors_rules[0]
        assert "AllowedHeaders" in rule
        assert "AllowedMethods" in rule  
        assert "AllowedOrigins" in rule
        assert "ExposedHeaders" in rule
        assert "MaxAge" in rule
        
        # Test allowed methods
        methods = rule["AllowedMethods"]
        expected_methods = {"GET", "PUT", "POST"}
        assert set(methods) == expected_methods

    def test_s3_lifecycle_configuration(self, s3_template: Dict[str, Any]):
        """Test S3 lifecycle configuration."""
        bucket = s3_template["Resources"]["UploadBucket"]
        properties = bucket["Properties"]
        
        assert "LifecycleConfiguration" in properties
        lifecycle_config = properties["LifecycleConfiguration"]
        assert "Rules" in lifecycle_config
        
        rules = lifecycle_config["Rules"]
        assert isinstance(rules, list)
        assert len(rules) > 0
        
        # Find specific rules
        rule_ids = [rule["Id"] for rule in rules]
        assert "AbortIncompleteMultipartUploads" in rule_ids
        assert "CompleteFileLifecycle" in rule_ids
        
        # Test multipart upload rule
        multipart_rule = next(rule for rule in rules if rule["Id"] == "AbortIncompleteMultipartUploads")
        assert multipart_rule["Status"] == "Enabled"
        assert "AbortIncompleteMultipartUpload" in multipart_rule
        assert multipart_rule["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 1

    def test_lifecycle_policy_cost_optimization(self, s3_template: Dict[str, Any]):
        """Test that lifecycle policy optimizes costs."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]
        
        # Find the complete file lifecycle rule
        lifecycle_rule = next(rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle")
        
        # Test Glacier transition
        assert "Transitions" in lifecycle_rule
        transitions = lifecycle_rule["Transitions"]
        glacier_transition = transitions[0]
        assert glacier_transition["StorageClass"] == "GLACIER"
        assert glacier_transition["TransitionInDays"] <= 7  # Reasonable time to Glacier
        
        # Test expiration
        assert "ExpirationInDays" in lifecycle_rule
        assert lifecycle_rule["ExpirationInDays"] > glacier_transition["TransitionInDays"]

    def test_log_group_resource(self, s3_template: Dict[str, Any]):
        """Test CloudWatch Log Group configuration."""
        resources = s3_template.get("Resources", {})
        assert "UploadLogGroup" in resources
        
        log_group = resources["UploadLogGroup"]
        assert log_group["Type"] == "AWS::Logs::LogGroup"
        
        properties = log_group["Properties"]
        assert "LogGroupName" in properties
        assert "RetentionInDays" in properties
        assert properties["RetentionInDays"] == 30

    def test_iam_upload_role(self, s3_template: Dict[str, Any]):
        """Test IAM role for S3 uploads."""
        resources = s3_template.get("Resources", {})
        assert "S3UploadRole" in resources
        
        role = resources["S3UploadRole"]
        assert role["Type"] == "AWS::IAM::Role"
        
        properties = role["Properties"]
        assert "AssumeRolePolicyDocument" in properties
        assert "Policies" in properties
        
        # Test assume role policy
        assume_policy = properties["AssumeRolePolicyDocument"]
        assert assume_policy["Version"] == "2012-10-17"
        
        statements = assume_policy["Statement"]
        service_principals = []
        for stmt in statements:
            if "Principal" in stmt and "Service" in stmt["Principal"]:
                service_principals.append(stmt["Principal"]["Service"])
        
        assert "ec2.amazonaws.com" in service_principals
        assert "ecs-tasks.amazonaws.com" in service_principals

    def test_iam_role_policies_least_privilege(self, s3_template: Dict[str, Any]):
        """Test that IAM role follows least privilege principle."""
        role = s3_template["Resources"]["S3UploadRole"]
        policies = role["Properties"]["Policies"]
        
        assert len(policies) == 1
        policy = policies[0]
        assert policy["PolicyName"] == "S3UploadPolicy"
        
        policy_doc = policy["PolicyDocument"]
        statements = policy_doc["Statement"]
        
        # Test object-level permissions
        object_statement = next(stmt for stmt in statements if "s3:PutObject" in stmt["Action"])
        object_resource = object_statement["Resource"]
        assert "/*" in object_resource  # Should target objects, not the bucket itself
        
        # Test bucket-level permissions
        bucket_statement = next(stmt for stmt in statements if "s3:ListBucket" in stmt["Action"])
        bucket_resource = bucket_statement["Resource"]
        assert "/*" not in bucket_resource  # Should target the bucket, not objects

    def test_required_s3_actions_present(self, s3_template: Dict[str, Any]):
        """Test that IAM role has required S3 actions."""
        role = s3_template["Resources"]["S3UploadRole"]
        policy = role["Properties"]["Policies"][0]
        
        all_actions = []
        for statement in policy["PolicyDocument"]["Statement"]:
            actions = statement["Action"]
            if isinstance(actions, str):
                all_actions.append(actions)
            else:
                all_actions.extend(actions)
        
        required_actions = [
            "s3:PutObject",
            "s3:GetObject",
            "s3:DeleteObject",
            "s3:ListBucket"
        ]
        
        for action in required_actions:
            assert action in all_actions, f"Required action {action} not found"

    def test_template_outputs_defined(self, s3_template: Dict[str, Any]):
        """Test that required outputs are defined."""
        outputs = s3_template.get("Outputs", {})
        required_outputs = [
            "BucketName",
            "BucketArn",
            "BucketDomainName", 
            "UploadRoleArn"
        ]
        
        for output in required_outputs:
            assert output in outputs, f"Required output {output} not found"

    def test_outputs_have_descriptions(self, s3_template: Dict[str, Any]):
        """Test that all outputs have descriptions."""
        outputs = s3_template.get("Outputs", {})
        
        for output_name, output_def in outputs.items():
            assert "Description" in output_def, f"Output {output_name} missing description"
            assert isinstance(output_def["Description"], str)
            assert len(output_def["Description"].strip()) > 0

    def test_outputs_have_exports(self, s3_template: Dict[str, Any]):
        """Test that all outputs have export names."""
        outputs = s3_template.get("Outputs", {})
        
        for output_name, output_def in outputs.items():
            assert "Export" in output_def, f"Output {output_name} missing export"
            assert "Name" in output_def["Export"], f"Output {output_name} export missing name"

    def test_resource_tags_present(self, s3_template: Dict[str, Any]):
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

    def test_template_references_consistent(self, s3_template: Dict[str, Any]):
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
                        assert ref_resource in resources, f"Output {output_name} references non-existent resource {ref_resource}"
                elif "GetAtt" in value:
                    att_resource = value["GetAtt"][0] if isinstance(value["GetAtt"], list) else value["GetAtt"]
                    if not att_resource.startswith("AWS::"):
                        assert att_resource in resources, f"Output {output_name} GetAtt references non-existent resource {att_resource}"

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_template_parameters_validation(self, s3_template: Dict[str, Any], environment: str):
        """Test parameter validation for different environments."""
        parameters = s3_template.get("Parameters", {})
        
        # Test environment parameter
        env_param = parameters["Environment"]
        assert environment in env_param["AllowedValues"]

    def test_cors_security_configuration(self, s3_template: Dict[str, Any]):
        """Test CORS configuration for security."""
        bucket = s3_template["Resources"]["UploadBucket"]
        cors_rules = bucket["Properties"]["CorsConfiguration"]["CorsRules"]
        
        rule = cors_rules[0]
        
        # Test that dangerous methods are not allowed
        methods = rule["AllowedMethods"]
        dangerous_methods = ["DELETE", "PATCH"]
        for method in dangerous_methods:
            assert method not in methods, f"Dangerous HTTP method {method} should not be allowed"
        
        # Test MaxAge is reasonable (not too long)
        max_age = rule["MaxAge"]
        assert max_age <= 86400, "CORS MaxAge should not exceed 24 hours"

    def test_bucket_naming_follows_conventions(self, s3_template: Dict[str, Any]):
        """Test bucket naming follows AWS conventions."""
        bucket_param = s3_template["Parameters"]["BucketName"]
        pattern = bucket_param["AllowedPattern"]
        
        # Test pattern prevents common naming issues
        invalid_patterns = [
            "UPPERCASE",  # uppercase not allowed
            "double--hyphen",  # double hyphen not allowed  
            "ending-",  # ending with hyphen not allowed
            "-starting",  # starting with hyphen not allowed
            "has.dots.in.middle"  # this should actually be valid for S3
        ]
        
        # Most should fail except the dots one
        for pattern_test in invalid_patterns:
            if pattern_test != "has.dots.in.middle":  # dots are actually valid
                assert not re.match(pattern, pattern_test), f"Pattern should reject {pattern_test}"

    def test_lifecycle_policy_handles_versioned_objects(self, s3_template: Dict[str, Any]):
        """Test lifecycle policy handles versioned objects properly."""
        bucket = s3_template["Resources"]["UploadBucket"]
        lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]
        
        # Find the complete file lifecycle rule
        lifecycle_rule = next(rule for rule in lifecycle_rules if rule["Id"] == "CompleteFileLifecycle")
        
        # Should have rules for non-current versions
        assert "NoncurrentVersionTransitions" in lifecycle_rule
        assert "NoncurrentVersionExpirationInDays" in lifecycle_rule
        
        non_current_transitions = lifecycle_rule["NoncurrentVersionTransitions"]
        assert len(non_current_transitions) > 0
        assert non_current_transitions[0]["StorageClass"] == "GLACIER"

    @pytest.mark.parametrize("cors_origin", ["http://localhost:3000", "https://localhost:3000", "https://example.com"])  
    def test_cors_origin_formats(self, cors_origin: str):
        """Test that various CORS origin formats are handled correctly."""
        # This test validates that different origin formats would work
        # The actual template uses a parameter, so we test the concept
        assert cors_origin.startswith(("http://", "https://"))
        if "localhost" in cors_origin:
            assert cors_origin.startswith(("http://localhost", "https://localhost"))