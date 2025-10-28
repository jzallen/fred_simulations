"""Tests for SSM Bastion CloudFormation template.

This test suite validates the SSM bastion template with DEEP validation of:
- EC2 instance configuration (IMDSv2, instance type)
- Security group configuration (no ingress, specific egress)
- IAM role and instance profile for SSM access
- Network configuration (private subnet, security groups)
- SSM-based access (no SSH keys required)
- RDS connectivity (PostgreSQL port forwarding)

Integration tests marked with @pytest.mark.integration can be skipped.
"""

import json
from pathlib import Path
from typing import Any
import pytest


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return path to the SSM Bastion CloudFormation template."""
    return str(
        Path(__file__).parent.parent.parent / "templates" / "ec2" / "ssm-bastion.json"
    )


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the SSM Bastion CloudFormation template."""
    with open(template_path, "r") as f:
        return json.load(f)


class TestSSMBastionTemplate:
    """Test suite for SSM Bastion CloudFormation template with deep security validation."""

    # ============================================================================
    # Template Structure Tests
    # ============================================================================

    def test_template_exists(self, template_path: str):
        assert Path(template_path).exists()

    def test_template_valid_json(self, template: dict[str, Any]):
        assert isinstance(template, dict)

    def test_template_format_version(self, template: dict[str, Any]):
        assert template.get("AWSTemplateFormatVersion") == "2010-09-09"

    # ============================================================================
    # Parameter Validation (DEEP)
    # ============================================================================

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
        assert "private" in subnet_desc.lower(), \
            "Bastion should be deployed in private subnet for security"

    # ============================================================================
    # EC2 Instance Configuration (DEEP with CDK Assertions)
    # ============================================================================

    def test_bastion_instance_exists(self, template, cdk_template_factory):
        """Bastion EC2 instance must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::EC2::Instance", 1)

    def test_bastion_uses_imdsv2_required(self, template, cdk_template_factory):
        """Bastion must use IMDSv2 (session-based) to prevent SSRF attacks."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like({
                "MetadataOptions": {
                    "HttpTokens": "required",  # IMDSv2
                    "HttpEndpoint": "enabled"
                }
            })
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
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like({
                "IamInstanceProfile": {"Ref": "BastionInstanceProfile"}
            })
        )

    def test_bastion_deployed_in_private_subnet(self, template, cdk_template_factory):
        """Bastion must be deployed in private subnet (no public IP)."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like({
                "SubnetId": {"Ref": "SubnetId"}
            })
        )

    def test_bastion_has_security_group(self, template, cdk_template_factory):
        """Bastion must have security group attached."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like({
                "SecurityGroupIds": Match.array_with([
                    {"Ref": "BastionSecurityGroup"}
                ])
            })
        )

    def test_bastion_has_tags(self, template, cdk_template_factory):
        """Bastion must have tags for governance and identification."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::Instance",
            Match.object_like({
                "Tags": Match.array_with([
                    Match.object_like({"Key": "Name"}),
                    Match.object_like({"Key": "Purpose"}),
                    Match.object_like({"Key": "Environment"}),
                    Match.object_like({"Key": "ManagedBy"})
                ])
            })
        )

    # ============================================================================
    # Security Group Configuration (DEEP with CDK Assertions)
    # ============================================================================

    def test_bastion_security_group_exists(self, template, cdk_template_factory):
        """Bastion security group must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::EC2::SecurityGroup", 1)

    def test_bastion_security_group_in_vpc(self, template, cdk_template_factory):
        """Security group must be associated with VPC."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            Match.object_like({
                "VpcId": {"Ref": "VPCId"}
            })
        )

    def test_bastion_security_group_has_no_ingress_rules(self, template: dict[str, Any]):
        """Bastion security group should NOT have ingress rules.

        SSM Session Manager provides access without SSH, so no ingress needed.
        """
        sg = template["Resources"]["BastionSecurityGroup"]["Properties"]

        # SecurityGroupIngress should not exist
        assert "SecurityGroupIngress" not in sg, \
            "Bastion should have no ingress rules (SSM access only)"

    def test_bastion_has_https_egress_for_ssm(self, template, cdk_template_factory):
        """Bastion must have HTTPS egress for SSM agent communication."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            Match.object_like({
                "SecurityGroupEgress": Match.array_with([
                    Match.object_like({
                        "IpProtocol": "tcp",
                        "FromPort": 443,
                        "ToPort": 443,
                        "CidrIp": "0.0.0.0/0",
                        "Description": Match.string_like_regexp(r".*SSM.*")
                    })
                ])
            })
        )

    def test_bastion_to_rds_egress_rule_exists(self, template, cdk_template_factory):
        """Separate egress rule for PostgreSQL access to RDS must exist."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)

        # Additional egress rule as separate resource
        cdk_template.resource_count_is("AWS::EC2::SecurityGroupEgress", 1)

        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroupEgress",
            Match.object_like({
                "GroupId": {"Ref": "BastionSecurityGroup"},
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "DestinationSecurityGroupId": {"Ref": "RDSSecurityGroupId"},
                "Description": Match.string_like_regexp(r".*PostgreSQL.*RDS.*")
            })
        )

    def test_rds_ingress_from_bastion_exists(self, template, cdk_template_factory):
        """RDS security group ingress rule from bastion must exist."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)

        # Ingress rule added to RDS security group
        cdk_template.resource_count_is("AWS::EC2::SecurityGroupIngress", 1)

        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroupIngress",
            Match.object_like({
                "GroupId": {"Ref": "RDSSecurityGroupId"},
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "SourceSecurityGroupId": {"Ref": "BastionSecurityGroup"},
                "Description": Match.string_like_regexp(r".*bastion.*")
            })
        )

    # ============================================================================
    # IAM Role and Instance Profile (DEEP with CDK Assertions)
    # ============================================================================

    def test_bastion_role_exists(self, template, cdk_template_factory):
        """IAM role for bastion must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::IAM::Role", 1)

    def test_bastion_role_trusts_ec2_service(self, template, cdk_template_factory):
        """Bastion role must trust ec2.amazonaws.com service."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like({
                "AssumeRolePolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        })
                    ])
                }
            })
        )

    def test_bastion_role_has_ssm_managed_policy(self, template, cdk_template_factory):
        """Bastion role must have AmazonSSMManagedInstanceCore policy for Session Manager."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like({
                "ManagedPolicyArns": Match.array_with([
                    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
                ])
            })
        )

    def test_instance_profile_exists(self, template, cdk_template_factory):
        """Instance profile must exist to attach role to instance."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::IAM::InstanceProfile", 1)

    def test_instance_profile_references_bastion_role(self, template, cdk_template_factory):
        """Instance profile must reference the bastion IAM role."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::InstanceProfile",
            Match.object_like({
                "Roles": [{"Ref": "BastionRole"}]
            })
        )

    # ============================================================================
    # Outputs (DEEP)
    # ============================================================================

    def test_outputs_export_key_resources(self, template: dict[str, Any]):
        """Outputs should export instance ID and security group ID.

        Using traditional assertions to verify outputs.
        """
        outputs = template["Outputs"]

        required_outputs = [
            "BastionInstanceId",
            "BastionSecurityGroupId",
            "StartCommand",
            "StopCommand",
            "PortForwardCommand"
        ]

        for output_name in required_outputs:
            assert output_name in outputs, f"{output_name} output missing"

    def test_instance_id_output_has_export(self, template: dict[str, Any]):
        """Instance ID output should have export for cross-stack references."""
        output = template["Outputs"]["BastionInstanceId"]
        assert "Export" in output
        assert "Value" in output
        assert output["Value"] == {"Ref": "BastionInstance"}

    def test_start_command_output_format(self, template: dict[str, Any]):
        """Start command output should provide AWS CLI command.

        Using traditional assertion to verify command structure.
        """
        output = template["Outputs"]["StartCommand"]["Value"]

        assert "Fn::Sub" in output
        command = output["Fn::Sub"]

        assert "aws ec2 start-instances" in command
        assert "--instance-ids" in command
        assert "${BastionInstance}" in command

    def test_stop_command_output_format(self, template: dict[str, Any]):
        """Stop command output should provide AWS CLI command."""
        output = template["Outputs"]["StopCommand"]["Value"]

        assert "Fn::Sub" in output
        command = output["Fn::Sub"]

        assert "aws ec2 stop-instances" in command
        assert "--instance-ids" in command
        assert "${BastionInstance}" in command

    def test_port_forward_command_uses_ssm(self, template: dict[str, Any]):
        """Port forward command should use SSM Session Manager.

        Using traditional assertion to verify SSM command structure.
        """
        output = template["Outputs"]["PortForwardCommand"]["Value"]

        assert "Fn::Sub" in output
        command = output["Fn::Sub"]

        # Should use SSM start-session command
        assert "aws ssm start-session" in command
        assert "--target ${BastionInstance}" in command
        assert "--document-name AWS-StartPortForwardingSessionToRemoteHost" in command

        # Should reference PostgreSQL port
        assert "5432" in command

    def test_port_forward_command_has_placeholder_for_rds_endpoint(self, template: dict[str, Any]):
        """Port forward command should have placeholder for RDS endpoint.

        Users need to replace this with actual RDS endpoint.
        """
        output = template["Outputs"]["PortForwardCommand"]["Value"]
        command = output["Fn::Sub"]

        # Should have placeholder for RDS endpoint
        assert "<RDS_ENDPOINT>" in command or "host" in command

    # ============================================================================
    # Resource Count Validation
    # ============================================================================

    def test_template_has_minimal_resources(self, template: dict[str, Any]):
        """Template should have minimal resources for bastion functionality.

        Using traditional assertion to verify resource counts.
        """
        resources = template["Resources"]

        expected_resource_types = {
            "AWS::EC2::Instance": 1,
            "AWS::EC2::SecurityGroup": 1,
            "AWS::EC2::SecurityGroupEgress": 1,
            "AWS::EC2::SecurityGroupIngress": 1,
            "AWS::IAM::Role": 1,
            "AWS::IAM::InstanceProfile": 1
        }

        for resource_type, expected_count in expected_resource_types.items():
            actual_count = sum(1 for r in resources.values() if r["Type"] == resource_type)
            assert actual_count == expected_count, \
                f"Expected {expected_count} {resource_type}, found {actual_count}"

    # ============================================================================
    # Security Best Practices Validation
    # ============================================================================

    def test_no_public_ip_assignment(self, template: dict[str, Any]):
        """Bastion should NOT have public IP (private subnet + SSM access).

        Using traditional assertion to verify NetworkInterfaces not configured.
        """
        instance = template["Resources"]["BastionInstance"]["Properties"]

        # Should not have NetworkInterfaces with AssociatePublicIpAddress
        assert "NetworkInterfaces" not in instance, \
            "Bastion should not configure network interfaces (use SubnetId instead)"

        # Should not have AssociatePublicIpAddress property
        assert "AssociatePublicIpAddress" not in instance, \
            "Bastion should not have public IP (SSM provides access)"

    def test_no_ssh_key_configured(self, template: dict[str, Any]):
        """Bastion should NOT have SSH key (SSM Session Manager access only).

        Using traditional assertion to verify KeyName not configured.
        """
        instance = template["Resources"]["BastionInstance"]["Properties"]

        assert "KeyName" not in instance, \
            "Bastion should not have SSH key (use SSM Session Manager instead)"

    def test_security_group_descriptions_are_meaningful(self, template: dict[str, Any]):
        """Security group and rules should have meaningful descriptions.

        Using traditional assertions to verify descriptions.
        """
        sg = template["Resources"]["BastionSecurityGroup"]["Properties"]

        # Security group should have GroupDescription
        assert "GroupDescription" in sg
        assert len(sg["GroupDescription"]) > 0, "GroupDescription should not be empty"

        # Egress rules should have descriptions
        for egress_rule in sg.get("SecurityGroupEgress", []):
            assert "Description" in egress_rule, \
                "Egress rules should have descriptions"
            assert len(egress_rule["Description"]) > 0, "Description should not be empty"

        # Separate egress rule
        bastion_to_rds = template["Resources"]["BastionToRDSEgress"]["Properties"]
        assert "Description" in bastion_to_rds
        assert len(bastion_to_rds["Description"]) > 0

        # Ingress rule to RDS
        rds_ingress = template["Resources"]["RDSFromBastionIngress"]["Properties"]
        assert "Description" in rds_ingress
        assert len(rds_ingress["Description"]) > 0

    # ============================================================================
    # Integration Tests (External Tools)
    # ============================================================================

    @pytest.mark.integration
    def test_template_passes_cfn_lint(self, template_path: str):
        """Test cfn-lint validation."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "cfnlint", template_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"cfn-lint failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.integration
    def test_template_passes_policy_validation(self, template_path: str):
        """Test cfn-guard policy validation."""
        import subprocess
        from pathlib import Path

        rules_path = (
            Path(__file__).parent.parent.parent
            / "guard_rules"
            / "ec2"
            / "ec2_security_rules.guard"
        )

        result = subprocess.run(
            ["cfn-guard", "validate", "--data", template_path, "--rules", str(rules_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"cfn-guard failed:\n{result.stdout}\n{result.stderr}"
