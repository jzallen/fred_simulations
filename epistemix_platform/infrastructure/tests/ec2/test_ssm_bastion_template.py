"""Tests for SSM Bastion CloudFormation template."""

import json
from pathlib import Path
from typing import Any

import pytest
from aws_cdk.assertions import Match


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return path to the SSM Bastion CloudFormation template."""
    return str(Path(__file__).parent.parent.parent / "templates" / "ec2" / "ssm-bastion.json")


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the SSM Bastion CloudFormation template."""
    with open(template_path) as f:
        return json.load(f)


class TestSSMBastionTemplate:
    """Test suite for SSM Bastion CloudFormation template with deep security validation."""


    def test_template_exists(self, template_path: str):
        assert Path(template_path).exists()

    def test_template_valid_json(self, template: dict[str, Any]):
        assert isinstance(template, dict)

    def test_template_format_version(self, template: dict[str, Any]):
        assert template.get("AWSTemplateFormatVersion") == "2010-09-09"

    # Parameter Validation

    def test_instance_type_has_allowed_values(self, template: dict[str, Any]):
        """Instance type parameter must be constrained to small instance types."""
        param = template["Parameters"]["InstanceType"]
        allowed = param.get("AllowedValues", [])

        # Bastion should only use small instances (cost control)
        assert allowed == ["t3.nano", "t3.micro", "t3.small"]
        assert param.get("Default") == "t3.nano", "Default should be smallest instance"

    def test_vpc_and_subnet_parameters_required(self, template: dict[str, Any]):
        """VPC and Subnet parameters must have correct types for validation."""
        assert template["Parameters"]["VPCId"]["Type"] == "AWS::EC2::VPC::Id"
        assert template["Parameters"]["SubnetId"]["Type"] == "AWS::EC2::Subnet::Id"
        assert template["Parameters"]["RDSSecurityGroupId"]["Type"] == "AWS::EC2::SecurityGroup::Id"

    def test_subnet_description_indicates_private(self, template: dict[str, Any]):
        """Subnet parameter should indicate private subnet usage."""
        subnet_desc = template["Parameters"]["SubnetId"]["Description"]
        assert (
            "private" in subnet_desc.lower()
        ), "Bastion should be deployed in private subnet for security"

    # EC2 Instance Configuration

    def test_bastion_instance_exists(self, template, cdk_template_factory):
        """Bastion EC2 instance must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::EC2::Instance", 1)

    def test_bastion_uses_imdsv2_required(self, template, cdk_template_factory):
        """Bastion must use IMDSv2 (session-based) to prevent SSRF attacks."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like(
                {
                    "MetadataOptions": {
                        "HttpTokens": "required",  # IMDSv2
                        "HttpEndpoint": "enabled",
                    }
                }
            ),
        )

    def test_bastion_uses_dynamic_ami_from_ssm(self, template: dict[str, Any]):
        """Bastion should use dynamic AMI resolution for automatic updates.

        Using traditional assertion to verify SSM parameter syntax.
        """
        instance = template["Resources"]["BastionInstance"]["Properties"]
        image_id = instance["ImageId"]

        # Should use {{resolve:ssm:...}} syntax for dynamic AMI
        assert "{{resolve:ssm:" in image_id
        assert "ami-amazon-linux-latest" in image_id
        assert "al2023" in image_id, "Should use Amazon Linux 2023"

    def test_bastion_has_instance_profile(self, template, cdk_template_factory):
        """Bastion must have IAM instance profile for SSM access."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like({"IamInstanceProfile": {"Ref": "BastionInstanceProfile"}}),
        )

    def test_bastion_deployed_in_private_subnet(self, template, cdk_template_factory):
        """Bastion must be deployed in private subnet (no public IP)."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance", Match.object_like({"SubnetId": {"Ref": "SubnetId"}})
        )

    def test_bastion_has_security_group(self, template, cdk_template_factory):
        """Bastion must have security group attached."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like(
                {"SecurityGroupIds": Match.array_with([{"Ref": "BastionSecurityGroup"}])}
            ),
        )

    def test_bastion_has_tags(self, template, cdk_template_factory):
        """Bastion must have tags for governance and identification."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like(
                {
                    "Tags": Match.array_with(
                        [
                            Match.object_like({"Key": "Name"}),
                            Match.object_like({"Key": "Purpose"}),
                            Match.object_like({"Key": "Environment"}),
                            Match.object_like({"Key": "ManagedBy"}),
                        ]
                    )
                }
            ),
        )

    # Security Group Configuration

    def test_bastion_security_group_exists(self, template, cdk_template_factory):
        """Bastion security group must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::EC2::SecurityGroup", 1)

    def test_bastion_security_group_in_vpc(self, template, cdk_template_factory):
        """Security group must be associated with VPC."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup", Match.object_like({"VpcId": {"Ref": "VPCId"}})
        )

    def test_bastion_security_group_has_no_ingress_rules(self, template, cdk_template_factory):
        """Bastion security group should NOT have ingress rules.

        SSM Session Manager provides access without SSH, so no ingress needed.
        """
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup", Match.object_like({"SecurityGroupIngress": Match.absent()})
        )

    def test_bastion_has_https_egress_for_ssm(self, template, cdk_template_factory):
        """Bastion must have HTTPS egress for SSM agent communication."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            Match.object_like(
                {
                    "SecurityGroupEgress": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "IpProtocol": "tcp",
                                    "FromPort": 443,
                                    "ToPort": 443,
                                    "CidrIp": "0.0.0.0/0",
                                    "Description": Match.string_like_regexp(r".*SSM.*"),
                                }
                            )
                        ]
                    )
                }
            ),
        )

    def test_bastion_to_rds_egress_rule_exists(self, template, cdk_template_factory):
        """Separate egress rule for PostgreSQL access to RDS must exist."""

        cdk_template = cdk_template_factory(template)

        # Additional egress rule as separate resource
        cdk_template.resource_count_is("AWS::EC2::SecurityGroupEgress", 1)

        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroupEgress",
            Match.object_like(
                {
                    "GroupId": {"Ref": "BastionSecurityGroup"},
                    "IpProtocol": "tcp",
                    "FromPort": 5432,
                    "ToPort": 5432,
                    "DestinationSecurityGroupId": {"Ref": "RDSSecurityGroupId"},
                    "Description": Match.string_like_regexp(r".*PostgreSQL.*RDS.*"),
                }
            ),
        )

    def test_rds_ingress_from_bastion_exists(self, template, cdk_template_factory):
        """RDS security group ingress rule from bastion must exist."""

        cdk_template = cdk_template_factory(template)

        # Ingress rule added to RDS security group
        cdk_template.resource_count_is("AWS::EC2::SecurityGroupIngress", 1)

        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroupIngress",
            Match.object_like(
                {
                    "GroupId": {"Ref": "RDSSecurityGroupId"},
                    "IpProtocol": "tcp",
                    "FromPort": 5432,
                    "ToPort": 5432,
                    "SourceSecurityGroupId": {"Ref": "BastionSecurityGroup"},
                    "Description": Match.string_like_regexp(r".*bastion.*"),
                }
            ),
        )

    # IAM Role and Instance Profile

    def test_bastion_role_exists(self, template, cdk_template_factory):
        """IAM role for bastion must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::IAM::Role", 1)

    def test_bastion_role_trusts_ec2_service(self, template, cdk_template_factory):
        """Bastion role must trust ec2.amazonaws.com service."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "AssumeRolePolicyDocument": {
                        "Statement": Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        "Effect": "Allow",
                                        "Principal": {"Service": "ec2.amazonaws.com"},
                                        "Action": "sts:AssumeRole",
                                    }
                                )
                            ]
                        )
                    }
                }
            ),
        )

    def test_bastion_role_has_ssm_managed_policy(self, template, cdk_template_factory):
        """Bastion role must have AmazonSSMManagedInstanceCore policy for Session Manager."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "ManagedPolicyArns": Match.array_with(
                        ["arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"]
                    )
                }
            ),
        )

    def test_instance_profile_exists(self, template, cdk_template_factory):
        """Instance profile must exist to attach role to instance."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::IAM::InstanceProfile", 1)

    def test_instance_profile_references_bastion_role(self, template, cdk_template_factory):
        """Instance profile must reference the bastion IAM role."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::InstanceProfile", Match.object_like({"Roles": [{"Ref": "BastionRole"}]})
        )

    # Resource Count Validation

    def test_template_has_minimal_resources(self, template, cdk_template_factory):
        """Template should have minimal resources for bastion functionality."""
        cdk_template = cdk_template_factory(template)

        expected_resource_types = {
            "AWS::EC2::Instance": 1,
            "AWS::EC2::SecurityGroup": 1,
            "AWS::EC2::SecurityGroupEgress": 1,
            "AWS::EC2::SecurityGroupIngress": 1,
            "AWS::IAM::Role": 1,
            "AWS::IAM::InstanceProfile": 1,
        }

        for resource_type, expected_count in expected_resource_types.items():
            cdk_template.resource_count_is(resource_type, expected_count)

    # Security Best Practices Validation

    def test_no_public_ip_assignment(self, template, cdk_template_factory):
        """Bastion should NOT have public IP (private subnet + SSM access)."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like(
                {"NetworkInterfaces": Match.absent(), "AssociatePublicIpAddress": Match.absent()}
            ),
        )

    def test_no_ssh_key_configured(self, template, cdk_template_factory):
        """Bastion should NOT have SSH key (SSM Session Manager access only)."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance", Match.object_like({"KeyName": Match.absent()})
        )

    def test_security_group_descriptions_are_meaningful(self, template, cdk_template_factory):
        """Security group and rules should have meaningful descriptions."""
        cdk_template = cdk_template_factory(template)

        # Security group must have a non-empty GroupDescription
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            Match.object_like({"GroupDescription": Match.string_like_regexp(".+")}),
        )

        # All egress rules must have descriptions
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            Match.object_like(
                {
                    "SecurityGroupEgress": Match.array_with(
                        [Match.object_like({"Description": Match.string_like_regexp(".+")})]
                    )
                }
            ),
        )

        # Separate egress rule must have description
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroupEgress",
            Match.object_like({"Description": Match.string_like_regexp(".+")}),
        )

        # Ingress rule must have description
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroupIngress",
            Match.object_like({"Description": Match.string_like_regexp(".+")}),
        )

