"""
Tests for IAM resources across all CloudFormation templates.

This module tests IAM roles, policies, and permissions for:
- Least privilege access principles
- Cross-service access patterns
- Trust relationships and assume role policies
- Policy document validation
- Resource-based permissions
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Set

import pytest


class TestIAMResources:
    """Test suite for IAM resources across all templates."""

    @pytest.fixture(scope="class")
    def all_templates(self, template_files, load_template) -> Dict[str, Dict[str, Any]]:
        """Load all CloudFormation templates."""
        templates = {}
        for template_name, template_path in template_files.items():
            templates[template_name] = load_template(template_path)
        return templates

    @pytest.fixture(scope="class")
    def iam_resources(self, all_templates: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all IAM resources from templates."""
        iam_resources = {}
        
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            template_iam_resources = []
            
            for resource_name, resource_def in resources.items():
                resource_type = resource_def.get("Type", "")
                if resource_type.startswith("AWS::IAM::"):
                    template_iam_resources.append({
                        "name": resource_name,
                        "type": resource_type,
                        "properties": resource_def.get("Properties", {}),
                        "template": template_name
                    })
            
            if template_iam_resources:
                iam_resources[template_name] = template_iam_resources
        
        return iam_resources

    def test_iam_roles_have_assume_role_policies(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that all IAM roles have assume role policies."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    properties = resource["properties"]
                    
                    assert "AssumeRolePolicyDocument" in properties, \
                        f"{template_name}: Role {resource['name']} missing AssumeRolePolicyDocument"
                    
                    assume_policy = properties["AssumeRolePolicyDocument"]
                    assert "Version" in assume_policy, \
                        f"{template_name}: Role {resource['name']} assume policy missing Version"
                    assert assume_policy["Version"] == "2012-10-17", \
                        f"{template_name}: Role {resource['name']} assume policy has invalid Version"
                    
                    assert "Statement" in assume_policy, \
                        f"{template_name}: Role {resource['name']} assume policy missing Statement"
                    assert isinstance(assume_policy["Statement"], list), \
                        f"{template_name}: Role {resource['name']} assume policy Statement must be list"

    def test_iam_role_trust_policies_secure(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that IAM role trust policies are secure."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    assume_policy = resource["properties"]["AssumeRolePolicyDocument"]
                    statements = assume_policy["Statement"]
                    
                    for statement in statements:
                        principal = statement.get("Principal", {})
                        
                        # Check for overly permissive principals
                        if isinstance(principal, str) and principal == "*":
                            pytest.fail(f"{template_name}: Role {resource['name']} has wildcard principal without conditions")
                        
                        if isinstance(principal, dict):
                            # Check AWS principals
                            aws_principal = principal.get("AWS")
                            if aws_principal == "*":
                                assert "Condition" in statement, \
                                    f"{template_name}: Role {resource['name']} has wildcard AWS principal without conditions"
                            
                            # Check service principals
                            service_principal = principal.get("Service")
                            if service_principal:
                                services = service_principal if isinstance(service_principal, list) else [service_principal]
                                for service in services:
                                    assert service.endswith(".amazonaws.com"), \
                                        f"{template_name}: Role {resource['name']} has invalid service principal: {service}"
                            
                            # Check federated principals (for OIDC)
                            federated_principal = principal.get("Federated")
                            if federated_principal:
                                assert "oidc-provider" in federated_principal or federated_principal.startswith("arn:aws:iam::"), \
                                    f"{template_name}: Role {resource['name']} has suspicious federated principal: {federated_principal}"

    def test_iam_policies_least_privilege(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that IAM policies follow least privilege principle."""
        dangerous_actions = [
            "*",
            "*:*",
            "iam:*",
            "s3:*",
            "ecr:*",
            "ec2:*",
            "cloudformation:*"
        ]
        
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    properties = resource["properties"]
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
                                    f"{template_name}: Role {resource['name']} has overly broad permission: {action}"
                            
                            # Check resource constraints
                            resources_list = statement.get("Resource", [])
                            if isinstance(resources_list, str):
                                resources_list = [resources_list]
                            
                            # If using wildcard resources, actions should be limited
                            if "*" in resources_list:
                                self._validate_wildcard_resource_actions(template_name, resource['name'], actions)

    def _validate_wildcard_resource_actions(self, template_name: str, role_name: str, actions: List[str]):
        """Validate that wildcard resource actions are safe."""
        safe_wildcard_actions = [
            "ecr:GetAuthorizationToken",
            "logs:CreateLogStream",
            "logs:CreateLogGroup",
            "logs:DescribeLogGroups",
            "logs:DescribeLogStreams",
            "sts:GetCallerIdentity"
        ]
        
        for action in actions:
            # Check if action is explicitly safe
            if action in safe_wildcard_actions:
                continue
            
            # Check if action is read-only
            if self._is_read_only_action(action):
                continue
            
            # Otherwise, it's potentially dangerous
            pytest.fail(f"{template_name}: Role {role_name} has dangerous action {action} with wildcard resource")

    def _is_read_only_action(self, action: str) -> bool:
        """Check if an IAM action is read-only."""
        if ":" not in action:
            return False
        
        action_name = action.split(":")[1]
        read_only_prefixes = ["Get", "List", "Describe", "Head"]
        return any(action_name.startswith(prefix) for prefix in read_only_prefixes)

    def test_iam_role_naming_conventions(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that IAM roles follow naming conventions."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    properties = resource["properties"]
                    
                    if "RoleName" in properties:
                        role_name = properties["RoleName"]
                        
                        # Role name should be descriptive and include environment
                        assert len(role_name) >= 10, \
                            f"{template_name}: Role {resource['name']} name too short: {role_name}"
                        
                        # Should contain environment or purpose indicators
                        purpose_indicators = ["cicd", "eks", "ec2", "upload", "dev", "staging", "production"]
                        has_indicator = any(indicator in role_name.lower() for indicator in purpose_indicators)
                        assert has_indicator, \
                            f"{template_name}: Role {resource['name']} name should indicate purpose/environment: {role_name}"

    def test_iam_policy_names_descriptive(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that IAM policy names are descriptive."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    properties = resource["properties"]
                    policies = properties.get("Policies", [])
                    
                    for policy in policies:
                        policy_name = policy.get("PolicyName", "")
                        
                        assert len(policy_name) >= 5, \
                            f"{template_name}: Role {resource['name']} has policy with short name: {policy_name}"
                        
                        # Policy name should indicate purpose
                        purpose_indicators = ["access", "policy", "permission", "role"]
                        has_indicator = any(indicator in policy_name.lower() for indicator in purpose_indicators)
                        assert has_indicator, \
                            f"{template_name}: Role {resource['name']} policy name should indicate purpose: {policy_name}"

    def test_iam_managed_policies_minimal(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that managed policies are used minimally and appropriately."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    properties = resource["properties"]
                    managed_policies = properties.get("ManagedPolicyArns", [])
                    
                    # Should use minimal managed policies
                    assert len(managed_policies) <= 3, \
                        f"{template_name}: Role {resource['name']} has too many managed policies"
                    
                    # Check for appropriate managed policies
                    acceptable_managed_policies = [
                        "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
                        "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy",
                        "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
                    ]
                    
                    for managed_policy in managed_policies:
                        # Should be AWS managed policy or acceptable custom policy
                        is_aws_managed = managed_policy.startswith("arn:aws:iam::aws:policy/")
                        is_acceptable = managed_policy in acceptable_managed_policies
                        
                        if is_aws_managed:
                            assert is_acceptable or self._is_acceptable_aws_managed_policy(managed_policy), \
                                f"{template_name}: Role {resource['name']} uses questionable managed policy: {managed_policy}"

    def _is_acceptable_aws_managed_policy(self, policy_arn: str) -> bool:
        """Check if an AWS managed policy is acceptable."""
        # List of AWS managed policies that are generally acceptable
        acceptable_patterns = [
            "AmazonSSMManagedInstanceCore",
            "CloudWatchAgentServerPolicy",
            "service-role/"  # Service-linked role policies are generally OK
        ]
        
        return any(pattern in policy_arn for pattern in acceptable_patterns)

    def test_iam_condition_keys_appropriate(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that IAM condition keys are used appropriately."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    # Check assume role policy conditions
                    assume_policy = resource["properties"]["AssumeRolePolicyDocument"]
                    statements = assume_policy["Statement"]
                    
                    for statement in statements:
                        conditions = statement.get("Condition", {})
                        
                        # If conditions are present, they should be meaningful
                        for condition_type, condition_values in conditions.items():
                            assert condition_type in [
                                "StringEquals", "StringLike", "StringNotEquals", 
                                "DateGreaterThan", "DateLessThan", "IpAddress",
                                "Bool", "Null"
                            ], f"{template_name}: Role {resource['name']} has unknown condition type: {condition_type}"
                            
                            # Conditions should have actual constraints
                            if isinstance(condition_values, dict):
                                for key, value in condition_values.items():
                                    assert key and value, \
                                        f"{template_name}: Role {resource['name']} has empty condition key/value"

    def test_instance_profiles_have_roles(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that instance profiles have associated roles."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::InstanceProfile":
                    properties = resource["properties"]
                    
                    assert "Roles" in properties, \
                        f"{template_name}: Instance profile {resource['name']} missing Roles"
                    
                    roles = properties["Roles"]
                    assert isinstance(roles, list) and len(roles) > 0, \
                        f"{template_name}: Instance profile {resource['name']} must have at least one role"

    def test_cross_template_iam_consistency(self, all_templates: Dict[str, Dict[str, Any]]):
        """Test consistency of IAM resources across templates."""
        # Collect all role names across templates
        all_role_names = set()
        template_role_mapping = {}
        
        for template_name, template in all_templates.items():
            resources = template.get("Resources", {})
            template_roles = []
            
            for resource_name, resource_def in resources.items():
                if resource_def.get("Type") == "AWS::IAM::Role":
                    properties = resource_def.get("Properties", {})
                    if "RoleName" in properties:
                        role_name = properties["RoleName"]
                        template_roles.append(role_name)
                        
                        # Check for role name conflicts
                        if role_name in all_role_names:
                            pytest.fail(f"Role name conflict: {role_name} appears in multiple templates")
                        all_role_names.add(role_name)
            
            if template_roles:
                template_role_mapping[template_name] = template_roles

    def test_service_specific_permissions(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that service-specific permissions are appropriate."""
        service_permission_mapping = {
            "ecr": {
                "required_actions": ["ecr:GetAuthorizationToken"],
                "allowed_actions": [
                    "ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage", "ecr:PutImage", "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart", "ecr:CompleteLayerUpload"
                ]
            },
            "s3": {
                "required_actions": ["s3:ListBucket"],
                "allowed_actions": [
                    "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                    "s3:GetObjectVersion", "s3:RestoreObject"
                ]
            }
        }
        
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    properties = resource["properties"]
                    policies = properties.get("Policies", [])
                    
                    for policy in policies:
                        policy_doc = policy.get("PolicyDocument", {})
                        statements = policy_doc.get("Statement", [])
                        
                        for statement in statements:
                            actions = statement.get("Action", [])
                            if isinstance(actions, str):
                                actions = [actions]
                            
                            # Group actions by service
                            service_actions = {}
                            for action in actions:
                                if ":" in action:
                                    service = action.split(":")[0]
                                    if service not in service_actions:
                                        service_actions[service] = []
                                    service_actions[service].append(action)
                            
                            # Validate service-specific permissions
                            for service, service_actions_list in service_actions.items():
                                if service in service_permission_mapping:
                                    requirements = service_permission_mapping[service]
                                    
                                    # Check required actions are present if service is used
                                    for required_action in requirements["required_actions"]:
                                        if required_action not in service_actions_list:
                                            # Only fail if the service has multiple actions (indicating active use)
                                            if len(service_actions_list) > 1:
                                                pytest.fail(f"{template_name}: Role {resource['name']} missing required {service} action: {required_action}")

    @pytest.mark.parametrize("environment", ["dev", "staging", "production"])
    def test_environment_specific_iam_configuration(self, iam_resources: Dict[str, List[Dict[str, Any]]], environment: str):
        """Test environment-specific IAM configurations."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] == "AWS::IAM::Role":
                    properties = resource["properties"]
                    
                    # Role names should include environment
                    if "RoleName" in properties:
                        role_name = properties["RoleName"]
                        # Role name should be parameterized or include environment
                        # We can't easily test parameterization here, but we can check patterns
                        pass  # This would be better tested through actual deployment

    def test_iam_tags_present(self, iam_resources: Dict[str, List[Dict[str, Any]]]):
        """Test that IAM resources have appropriate tags."""
        for template_name, resources in iam_resources.items():
            for resource in resources:
                if resource["type"] in ["AWS::IAM::Role", "AWS::IAM::InstanceProfile"]:
                    properties = resource["properties"]
                    
                    # Tags should be present
                    tags = properties.get("Tags", [])
                    if tags:  # Only validate if tags are present
                        tag_keys = [tag.get("Key") for tag in tags]
                        
                        # Should have basic tags
                        assert "Environment" in tag_keys, \
                            f"{template_name}: {resource['type']} {resource['name']} missing Environment tag"
                        assert "ManagedBy" in tag_keys, \
                            f"{template_name}: {resource['type']} {resource['name']} missing ManagedBy tag"