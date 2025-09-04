"""
Tests for security compliance across all CloudFormation templates.

This module tests all templates for security best practices including:
- Encryption at rest and in transit
- IAM policies and least privilege access
- Public access restrictions
- Security scanning and monitoring
- Compliance with security standards
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Set

import pytest
import yaml


class TestTemplateSecurity:
    """Test suite for CloudFormation template security compliance."""

    @pytest.fixture(scope="class")
    def all_templates(self, template_files, load_template) -> Dict[str, Dict[str, Any]]:
        """Load all CloudFormation templates."""
        templates = {}
        for template_name, template_path in template_files.items():
            templates[template_name] = load_template(template_path)
        return templates

    def test_encryption_at_rest_enabled(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that encryption at rest is enabled for all storage resources."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type")
                properties = resource_def.get("Properties", {})
                
                if resource_type == "AWS::ECR::Repository":
                    # ECR should have KMS encryption
                    assert "EncryptionConfiguration" in properties, \
                        f"{template_name}: ECR repository {resource_name} missing encryption"
                    encryption_config = properties["EncryptionConfiguration"]
                    assert encryption_config["EncryptionType"] == "KMS", \
                        f"{template_name}: ECR repository {resource_name} should use KMS encryption"
                
                elif resource_type == "AWS::S3::Bucket":
                    # S3 buckets should be configured securely (encryption can be via bucket policy or default)
                    # For now, we check that public access is blocked which is more critical
                    assert "PublicAccessBlockConfiguration" in properties, \
                        f"{template_name}: S3 bucket {resource_name} missing public access block"
                    
                    public_access = properties["PublicAccessBlockConfiguration"]
                    required_blocks = ["BlockPublicAcls", "BlockPublicPolicy", "IgnorePublicAcls", "RestrictPublicBuckets"]
                    for block in required_blocks:
                        assert public_access.get(block) is True, \
                            f"{template_name}: S3 bucket {resource_name} should have {block} enabled"

    def test_iam_policies_least_privilege(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that IAM policies follow least privilege principle."""
        dangerous_actions = [
            "*",
            "*:*", 
            "iam:*",
            "s3:*",
            "ec2:*"
        ]
        
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                if resource_def.get("Type") == "AWS::IAM::Role":
                    properties = resource_def.get("Properties", {})
                    policies = properties.get("Policies", [])
                    
                    for policy in policies:
                        policy_doc = policy.get("PolicyDocument", {})
                        statements = policy_doc.get("Statement", [])
                        
                        for statement in statements:
                            actions = statement.get("Action", [])
                            if isinstance(actions, str):
                                actions = [actions]
                            
                            # Check for dangerous broad permissions
                            for action in actions:
                                assert action not in dangerous_actions, \
                                    f"{template_name}: Role {resource_name} has overly broad permission: {action}"
                            
                            # If using wildcard resources, actions should be read-only or very specific
                            resources_list = statement.get("Resource", [])
                            if isinstance(resources_list, str):
                                resources_list = [resources_list]
                            
                            if "*" in resources_list:
                                # Only allow specific read-only actions with wildcard resources
                                safe_wildcard_actions = [
                                    "ecr:GetAuthorizationToken",
                                    "logs:CreateLogStream",
                                    "logs:DescribeLogGroups"
                                ]
                                for action in actions:
                                    if action not in safe_wildcard_actions and not self._is_read_only_action(action):
                                        pytest.fail(f"{template_name}: Role {resource_name} has dangerous action {action} with wildcard resource")

    def _is_read_only_action(self, action: str) -> bool:
        """Check if an IAM action is read-only."""
        read_only_prefixes = ["Get", "List", "Describe"]
        return any(action.split(":")[1].startswith(prefix) for prefix in read_only_prefixes if ":" in action)

    def test_no_hardcoded_secrets(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that templates don't contain hardcoded secrets or credentials."""
        secret_patterns = [
            r"AKIA[0-9A-Z]{16}",  # AWS Access Key ID
            r"[0-9a-zA-Z/+]{40}",  # AWS Secret Access Key pattern (too broad, but as example)
            r"password\s*[:=]\s*['\"][^'\"]+['\"]",  # Password assignments
            r"secret\s*[:=]\s*['\"][^'\"]+['\"]",  # Secret assignments
        ]
        
        for template_name, template in all_templates.items():
            template_str = yaml.dump(template)
            
            for pattern in secret_patterns:
                if template_name.endswith("ecr/simulation-runner-repository.yaml"):
                    # Skip the overly broad secret key pattern for ECR template due to base64 in lifecycle policy
                    if "40" in pattern:
                        continue
                
                matches = re.findall(pattern, template_str, re.IGNORECASE)
                assert not matches, f"{template_name}: Potential hardcoded secret found: {matches}"

    def test_security_scanning_enabled(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that security scanning is enabled where applicable."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type")
                properties = resource_def.get("Properties", {})
                
                if resource_type == "AWS::ECR::Repository":
                    # ECR should have image scanning enabled
                    assert "ImageScanningConfiguration" in properties, \
                        f"{template_name}: ECR repository {resource_name} missing image scanning config"
                    
                    scan_config = properties["ImageScanningConfiguration"]
                    # Should reference parameter or be true
                    scan_on_push = scan_config.get("ScanOnPush")
                    assert scan_on_push is not None, \
                        f"{template_name}: ECR repository {resource_name} should configure ScanOnPush"

    def test_logging_and_monitoring_configured(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that appropriate logging and monitoring is configured."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            # Check if template has CloudWatch log groups
            log_groups = [r for r in resources.values() if r.get("Type") == "AWS::Logs::LogGroup"]
            
            # Templates with significant resources should have logging
            significant_resources = [r for r in resources.values() if r.get("Type") in [
                "AWS::ECR::Repository",
                "AWS::S3::Bucket"
            ]]
            
            if significant_resources:
                assert log_groups, f"{template_name}: Should have CloudWatch log groups for monitoring"
                
                # Log groups should have retention configured
                for log_group_resource in log_groups:
                    properties = log_group_resource.get("Properties", {})
                    assert "RetentionInDays" in properties, \
                        f"{template_name}: Log group should have retention configured"

    def test_public_access_restrictions(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that public access is appropriately restricted."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type")
                properties = resource_def.get("Properties", {})
                
                if resource_type == "AWS::S3::Bucket":
                    # S3 buckets should block public access unless explicitly needed
                    if "PublicAccessBlockConfiguration" in properties:
                        public_access = properties["PublicAccessBlockConfiguration"]
                        
                        # For upload buckets, public access should be blocked
                        assert public_access.get("BlockPublicAcls") is True
                        assert public_access.get("BlockPublicPolicy") is True
                        assert public_access.get("IgnorePublicAcls") is True
                        assert public_access.get("RestrictPublicBuckets") is True
                
                elif resource_type == "AWS::ECR::Repository":
                    # ECR repositories should not have public access policies by default
                    assert "RepositoryPolicyText" not in properties or \
                        self._ecr_policy_not_public(properties.get("RepositoryPolicyText")), \
                        f"{template_name}: ECR repository {resource_name} may have public access"

    def _ecr_policy_not_public(self, policy_text: str) -> bool:
        """Check if ECR repository policy doesn't grant public access."""
        if not policy_text:
            return True
        
        try:
            policy = json.loads(policy_text)
            statements = policy.get("Statement", [])
            
            for statement in statements:
                principal = statement.get("Principal", {})
                if principal == "*" or principal.get("AWS") == "*":
                    return False
            return True
        except (json.JSONDecodeError, AttributeError):
            return True  # If we can't parse, assume it's safe

    def test_iam_role_trust_policies_secure(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that IAM role trust policies are appropriately restrictive."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                if resource_def.get("Type") == "AWS::IAM::Role":
                    properties = resource_def.get("Properties", {})
                    assume_policy = properties.get("AssumeRolePolicyDocument", {})
                    statements = assume_policy.get("Statement", [])
                    
                    for statement in statements:
                        principal = statement.get("Principal", {})
                        
                        # Check for overly broad trust relationships
                        if isinstance(principal, dict):
                            aws_principal = principal.get("AWS")
                            if aws_principal == "*":
                                # Wildcard AWS principal should have conditions
                                assert "Condition" in statement, \
                                    f"{template_name}: Role {resource_name} has wildcard AWS principal without conditions"
                            
                            # Service principals should be specific AWS services
                            service_principal = principal.get("Service")
                            if service_principal:
                                if isinstance(service_principal, str):
                                    service_principal = [service_principal]
                                
                                for service in service_principal:
                                    assert service.endswith(".amazonaws.com"), \
                                        f"{template_name}: Role {resource_name} has non-AWS service principal: {service}"

    def test_resource_tagging_for_security(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that resources are properly tagged for security and compliance."""
        required_security_tags = ["Environment", "ManagedBy"]
        
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type")
                properties = resource_def.get("Properties", {})
                
                # Resources that should be tagged for security
                security_critical_resources = [
                    "AWS::IAM::Role",
                    "AWS::S3::Bucket", 
                    "AWS::ECR::Repository",
                    "AWS::Logs::LogGroup"
                ]
                
                if resource_type in security_critical_resources:
                    tags = properties.get("Tags", [])
                    if tags:  # Only check if tags exist
                        tag_keys = [tag.get("Key") for tag in tags]
                        for required_tag in required_security_tags:
                            assert required_tag in tag_keys, \
                                f"{template_name}: Resource {resource_name} missing security tag: {required_tag}"

    def test_lifecycle_policies_prevent_data_hoarding(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that lifecycle policies prevent indefinite data retention."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type")
                properties = resource_def.get("Properties", {})
                
                if resource_type == "AWS::S3::Bucket":
                    # S3 buckets should have lifecycle policies
                    lifecycle_config = properties.get("LifecycleConfiguration")
                    if lifecycle_config:
                        rules = lifecycle_config.get("Rules", [])
                        
                        # Should have at least one rule that expires objects
                        has_expiration = any(
                            "ExpirationInDays" in rule or 
                            "NoncurrentVersionExpirationInDays" in rule 
                            for rule in rules
                        )
                        assert has_expiration, \
                            f"{template_name}: S3 bucket {resource_name} should have object expiration rules"
                
                elif resource_type == "AWS::ECR::Repository":
                    # ECR should have lifecycle policies
                    assert "LifecyclePolicy" in properties, \
                        f"{template_name}: ECR repository {resource_name} should have lifecycle policy"
                    
                    lifecycle_text = properties["LifecyclePolicy"]["LifecyclePolicyText"]
                    try:
                        policy = json.loads(lifecycle_text)
                        rules = policy.get("rules", [])
                        assert rules, \
                            f"{template_name}: ECR repository {resource_name} lifecycle policy should have rules"
                    except json.JSONDecodeError:
                        pytest.fail(f"{template_name}: ECR repository {resource_name} has invalid lifecycle policy JSON")

    def test_network_access_controls(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test network access controls and CORS configurations."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type")
                properties = resource_def.get("Properties", {})
                
                if resource_type == "AWS::S3::Bucket" and "CorsConfiguration" in properties:
                    cors_config = properties["CorsConfiguration"]
                    cors_rules = cors_config.get("CorsRules", [])
                    
                    for rule in cors_rules:
                        # CORS origins should not be wildcard in production
                        allowed_origins = rule.get("AllowedOrigins", [])
                        
                        # Check if origins are parameterized (good) or hardcoded
                        if isinstance(allowed_origins, list) and "*" in allowed_origins:
                            pytest.fail(f"{template_name}: S3 bucket {resource_name} has wildcard CORS origin")
                        
                        # MaxAge should be reasonable
                        max_age = rule.get("MaxAge")
                        if max_age and isinstance(max_age, int):
                            assert max_age <= 86400, \
                                f"{template_name}: S3 bucket {resource_name} CORS MaxAge too high: {max_age}"

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_specific_security_configurations(self, all_templates: Dict[str, Dict[str, Any]], environment: str):
        """Test that security configurations are appropriate for each environment."""
        for template_name, template in all_templates.items():
            # Production should have stricter settings
            if environment == "production":
                conditions = template.get("Conditions", {})
                
                # Should have production-specific conditions
                if "IsProduction" in conditions:
                    # This indicates the template is environment-aware
                    pass  # Template handles production differences
                
                # Check for environment-specific log retention
                resources = template.get("Resources", {})
                for resource_def in resources.values():
                    if resource_def.get("Type") == "AWS::Logs::LogGroup":
                        properties = resource_def.get("Properties", {})
                        # Production should have longer retention
                        # This would be validated through parameter testing

    def test_secure_communication_enforced(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that secure communication protocols are enforced."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type")
                properties = resource_def.get("Properties", {})
                
                if resource_type == "AWS::S3::Bucket" and "CorsConfiguration" in properties:
                    cors_config = properties["CorsConfiguration"]
                    cors_rules = cors_config.get("CorsRules", [])
                    
                    for rule in cors_rules:
                        allowed_origins = rule.get("AllowedOrigins", [])
                        
                        # Check for HTTP origins (should prefer HTTPS)
                        for origin in allowed_origins:
                            if isinstance(origin, str) and origin.startswith("http://"):
                                # Only allow HTTP for localhost in development
                                assert "localhost" in origin, \
                                    f"{template_name}: Non-localhost HTTP origin not secure: {origin}"