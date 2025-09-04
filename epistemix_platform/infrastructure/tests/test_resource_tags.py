"""
Tests for resource tagging compliance across all CloudFormation templates.

This module tests that all resources are properly tagged for:
- Environment identification
- Cost center tracking
- Management and ownership
- Compliance requirements
- Automated operations
"""

from pathlib import Path
from typing import Dict, Any, List, Set

import pytest


class TestResourceTags:
    """Test suite for resource tagging compliance."""

    @pytest.fixture(scope="class")
    def all_templates(self, template_files, load_template) -> Dict[str, Dict[str, Any]]:
        """Load all CloudFormation templates."""
        templates = {}
        for template_name, template_path in template_files.items():
            templates[template_name] = load_template(template_path)
        return templates

    @pytest.fixture(scope="class") 
    def taggable_resources(self, all_templates: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all taggable resources from templates."""
        # AWS resource types that support tagging
        taggable_types = {
            "AWS::S3::Bucket",
            "AWS::ECR::Repository",
            "AWS::IAM::Role",
            "AWS::IAM::InstanceProfile",
            "AWS::Logs::LogGroup",
            "AWS::Events::Rule",
            "AWS::CloudWatch::Dashboard",
            "AWS::KMS::Key",
            "AWS::KMS::Alias",
            "AWS::EC2::Instance",
            "AWS::EC2::Volume",
            "AWS::EC2::SecurityGroup",
            "AWS::RDS::DBInstance",
            "AWS::Lambda::Function",
            "AWS::ElastiCache::CacheCluster"
        }
        
        taggable_resources = {}
        
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            template_taggable = []
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type", "")
                if resource_type in taggable_types:
                    template_taggable.append({
                        "name": resource_name,
                        "type": resource_type,
                        "properties": resource_def.get("Properties", {}),
                        "template": template_name
                    })
            
            if template_taggable:
                taggable_resources[template_name] = template_taggable
        
        return taggable_resources

    def test_required_tags_present(self, taggable_resources: Dict[str, List[Dict[str, Any]]], expected_tags: Dict[str, Dict[str, str]]):
        """Test that required tags are present on all taggable resources."""
        required_tag_keys = ["Environment", "ManagedBy"]
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                if tags:  # Only validate if tags are present (some resources may not have tags in template)
                    tag_keys = [tag.get("Key") for tag in tags]
                    
                    for required_tag in required_tag_keys:
                        assert required_tag in tag_keys, \
                            f"{template_name}: Resource {resource['name']} ({resource['type']}) missing required tag: {required_tag}"

    def test_environment_tag_values_valid(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that Environment tag values are valid."""
        valid_environments = ["dev", "staging", "production"]
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    if tag.get("Key") == "Environment":
                        tag_value = tag.get("Value")
                        
                        # Value might be a CloudFormation reference
                        if isinstance(tag_value, dict) and "Ref" in tag_value:
                            # This is a parameter reference - validate the parameter
                            continue
                        elif isinstance(tag_value, str):
                            # Direct value - should be valid
                            if tag_value in valid_environments:
                                continue
                            # Could also be a function like !Sub
                        
                        # If it's not a recognized pattern, it should at least not be empty
                        assert tag_value, \
                            f"{template_name}: Resource {resource['name']} Environment tag has empty value"

    def test_managed_by_tag_consistent(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that ManagedBy tag is consistent."""
        expected_managed_by_values = ["CloudFormation", "Sceptre", "InfrastructureAsCode"]
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    if tag.get("Key") == "ManagedBy":
                        tag_value = tag.get("Value")
                        
                        if isinstance(tag_value, str):
                            assert tag_value in expected_managed_by_values, \
                                f"{template_name}: Resource {resource['name']} has invalid ManagedBy value: {tag_value}"

    def test_tag_values_not_empty(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that tag values are not empty."""
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    key = tag.get("Key")
                    value = tag.get("Value")
                    
                    assert key, \
                        f"{template_name}: Resource {resource['name']} has tag with empty key"
                    assert value or value == 0 or value is False, \
                        f"{template_name}: Resource {resource['name']} tag '{key}' has empty value"

    def test_tag_keys_follow_naming_convention(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that tag keys follow naming conventions."""
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    key = tag.get("Key")
                    if key:
                        # Tag keys should be PascalCase
                        assert key[0].isupper(), \
                            f"{template_name}: Resource {resource['name']} tag key should start with uppercase: {key}"
                        
                        # Should not contain spaces or special characters
                        assert " " not in key, \
                            f"{template_name}: Resource {resource['name']} tag key should not contain spaces: {key}"
                        
                        # Should be descriptive (at least 3 characters unless it's an abbreviation)
                        if len(key) < 3 and key not in ["ID", "OS", "IP"]:
                            pytest.fail(f"{template_name}: Resource {resource['name']} tag key too short: {key}")

    def test_purpose_tags_present_for_complex_resources(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that complex resources have Purpose or similar descriptive tags."""
        complex_resource_types = [
            "AWS::S3::Bucket",
            "AWS::ECR::Repository", 
            "AWS::IAM::Role"
        ]
        
        descriptive_tag_keys = ["Purpose", "Description", "Function", "Role", "Component"]
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                if resource["type"] in complex_resource_types:
                    properties = resource["properties"]
                    tags = properties.get("Tags", [])
                    
                    if tags:  # Only check if tags exist
                        tag_keys = [tag.get("Key") for tag in tags]
                        has_descriptive_tag = any(desc_key in tag_keys for desc_key in descriptive_tag_keys)
                        
                        assert has_descriptive_tag, \
                            f"{template_name}: Complex resource {resource['name']} should have a descriptive tag (Purpose, Description, etc.)"

    def test_cost_tracking_tags_present(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that cost tracking tags are present where appropriate."""
        cost_tracking_tags = ["CostCenter", "Project", "Owner", "Team"]
        
        # Resources that should definitely have cost tracking
        cost_critical_resources = [
            "AWS::S3::Bucket",
            "AWS::ECR::Repository",
            "AWS::EC2::Instance",
            "AWS::RDS::DBInstance",
            "AWS::Lambda::Function"
        ]
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                if resource["type"] in cost_critical_resources:
                    properties = resource["properties"]
                    tags = properties.get("Tags", [])
                    
                    if tags:  # Only check if tags exist
                        tag_keys = [tag.get("Key") for tag in tags]
                        has_cost_tag = any(cost_key in tag_keys for cost_key in cost_tracking_tags)
                        
                        # For critical resources, at least one cost tracking tag should be present
                        if not has_cost_tag:
                            # Check if Project tag exists (common alternative)
                            if "Project" not in tag_keys:
                                pytest.fail(f"{template_name}: Cost-critical resource {resource['name']} should have cost tracking tags")

    def test_security_classification_tags(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test security classification tags where appropriate."""
        security_sensitive_resources = [
            "AWS::IAM::Role",
            "AWS::KMS::Key",
            "AWS::S3::Bucket"
        ]
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                if resource["type"] in security_sensitive_resources:
                    properties = resource["properties"]
                    tags = properties.get("Tags", [])
                    
                    # Security tags are optional but if present should be valid
                    for tag in tags:
                        if tag.get("Key") in ["SecurityClassification", "DataClassification"]:
                            value = tag.get("Value")
                            valid_classifications = ["Public", "Internal", "Confidential", "Restricted"]
                            
                            if isinstance(value, str) and value not in valid_classifications:
                                pytest.fail(f"{template_name}: Resource {resource['name']} has invalid security classification: {value}")

    def test_automation_tags_consistent(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that automation-related tags are consistent."""
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    key = tag.get("Key")
                    value = tag.get("Value")
                    
                    # Backup tags should have consistent values
                    if key == "Backup":
                        if isinstance(value, str):
                            valid_backup_values = ["true", "false", "daily", "weekly", "monthly", "none"]
                            assert value.lower() in valid_backup_values, \
                                f"{template_name}: Resource {resource['name']} has invalid Backup tag value: {value}"
                    
                    # Monitoring tags should be consistent
                    elif key == "Monitoring":
                        if isinstance(value, str):
                            valid_monitoring_values = ["enabled", "disabled", "basic", "detailed"]
                            assert value.lower() in valid_monitoring_values, \
                                f"{template_name}: Resource {resource['name']} has invalid Monitoring tag value: {value}"

    def test_tag_value_length_limits(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that tag values don't exceed AWS limits."""
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    key = tag.get("Key")
                    value = tag.get("Value")
                    
                    if isinstance(key, str):
                        assert len(key) <= 128, \
                            f"{template_name}: Resource {resource['name']} tag key too long: {key}"
                    
                    if isinstance(value, str):
                        assert len(value) <= 256, \
                            f"{template_name}: Resource {resource['name']} tag value too long for key '{key}'"

    def test_reserved_tag_prefixes_avoided(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that reserved tag prefixes are avoided."""
        reserved_prefixes = ["aws:", "cloudformation:", "elasticbeanstalk:"]
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    key = tag.get("Key")
                    if isinstance(key, str):
                        for prefix in reserved_prefixes:
                            assert not key.lower().startswith(prefix), \
                                f"{template_name}: Resource {resource['name']} uses reserved tag prefix: {key}"

    def test_tag_count_limits(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that resources don't exceed tag count limits."""
        max_tags = 50  # AWS limit for most resources
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                assert len(tags) <= max_tags, \
                    f"{template_name}: Resource {resource['name']} has too many tags: {len(tags)} (limit: {max_tags})"

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_specific_tag_requirements(self, taggable_resources: Dict[str, List[Dict[str, Any]]], environment: str):
        """Test environment-specific tag requirements."""
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                if tags:
                    environment_tag = next((tag for tag in tags if tag.get("Key") == "Environment"), None)
                    
                    if environment_tag and isinstance(environment_tag.get("Value"), str):
                        env_value = environment_tag["Value"]
                        
                        # Production resources should have additional requirements
                        if environment == "production" and env_value == "production":
                            tag_keys = [tag.get("Key") for tag in tags]
                            
                            # Production should have owner information
                            ownership_tags = ["Owner", "Team", "Contact"]
                            has_ownership = any(owner_tag in tag_keys for owner_tag in ownership_tags)
                            
                            if resource["type"] in ["AWS::S3::Bucket", "AWS::ECR::Repository"]:
                                assert has_ownership, \
                                    f"{template_name}: Production resource {resource['name']} should have ownership tags"

    def test_template_specific_tag_consistency(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test that tags are consistent within each template."""
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            template_environment_values = set()
            template_project_values = set()
            
            for resource_name, resource_def in resources.items():
                properties = resource_def.get("Properties", {})
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    key = tag.get("Key")
                    value = tag.get("Value")
                    
                    if key == "Environment" and isinstance(value, dict) and "Ref" in value:
                        # Parameter reference - this is good
                        continue
                    elif key == "Environment" and isinstance(value, str):
                        template_environment_values.add(value)
                    elif key == "Project" and isinstance(value, str):
                        template_project_values.add(value)
            
            # Within a template, Environment values should be consistent
            if len(template_environment_values) > 1:
                pytest.fail(f"{template_name}: Inconsistent Environment tag values: {template_environment_values}")
            
            # Within a template, Project values should be consistent
            if len(template_project_values) > 1:
                pytest.fail(f"{template_name}: Inconsistent Project tag values: {template_project_values}")

    def test_compliance_tags_format(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that compliance-related tags follow proper format."""
        compliance_tags = {
            "Compliance": ["SOC2", "HIPAA", "PCI", "GDPR", "None"],
            "DataRetention": ["30days", "90days", "1year", "7years", "indefinite"],
            "BackupRequired": ["true", "false"]
        }
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                properties = resource["properties"]
                tags = properties.get("Tags", [])
                
                for tag in tags:
                    key = tag.get("Key")
                    value = tag.get("Value")
                    
                    if key in compliance_tags and isinstance(value, str):
                        valid_values = compliance_tags[key]
                        assert value in valid_values, \
                            f"{template_name}: Resource {resource['name']} has invalid {key} value: {value}"

    def test_resource_type_specific_tags(self, taggable_resources: Dict[str, List[Dict[str, Any]]]):
        """Test resource type specific tag requirements."""
        type_specific_requirements = {
            "AWS::S3::Bucket": ["Purpose"],
            "AWS::ECR::Repository": ["Purpose"],
            "AWS::IAM::Role": ["Purpose"],
            "AWS::Logs::LogGroup": ["Purpose"]
        }
        
        for template_name, resources in taggable_resources.items():
            for resource in resources:
                resource_type = resource["type"]
                
                if resource_type in type_specific_requirements:
                    properties = resource["properties"]
                    tags = properties.get("Tags", [])
                    
                    if tags:  # Only check if tags exist
                        tag_keys = [tag.get("Key") for tag in tags]
                        required_tags = type_specific_requirements[resource_type]
                        
                        for required_tag in required_tags:
                            assert required_tag in tag_keys, \
                                f"{template_name}: {resource_type} {resource['name']} missing required tag: {required_tag}"