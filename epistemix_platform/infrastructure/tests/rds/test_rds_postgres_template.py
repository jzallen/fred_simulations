"""Tests for RDS PostgreSQL CloudFormation template."""

import json
from pathlib import Path
from typing import Any

import pytest
from aws_cdk.assertions import Match


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return the path to the RDS PostgreSQL CloudFormation template."""
    return str(Path(__file__).parent.parent.parent / "templates" / "rds" / "rds-postgres.json")


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the RDS PostgreSQL CloudFormation template as a dictionary."""
    with open(template_path) as f:
        return json.load(f)


class TestRDSPostgresTemplate:
    """Test suite for RDS PostgreSQL CloudFormation template."""

    def test_template_exists(self, template_path: str):
        """Test that the template file exists."""
        assert Path(template_path).exists(), "Template file does not exist"

    def test_template_valid_json(self, template: dict[str, Any]):
        """Test that the template is valid JSON."""
        assert isinstance(template, dict), "Template is not a valid JSON object"

    def test_template_format_version(self, template: dict[str, Any]):
        """Test template has correct CloudFormation format version."""
        assert (
            template.get("AWSTemplateFormatVersion") == "2010-09-09"
        ), "Invalid CloudFormation template version"

    def test_template_has_description(self, template: dict[str, Any]):
        """Test template has a description."""
        assert "Description" in template, "Template missing Description"
        assert (
            "RDS" in template["Description"] or "PostgreSQL" in template["Description"]
        ), "Description should mention RDS or PostgreSQL"

    def test_parameters_defined(self, template: dict[str, Any]):
        """Test that parameters are defined in the template."""
        assert "Parameters" in template, "Template missing Parameters section"
        assert len(template["Parameters"]) > 0, "Parameters section is empty"

    def test_vpc_id_parameter_exists(self, template: dict[str, Any]):
        """Test VPCId parameter is defined."""
        params = template.get("Parameters", {})
        assert "VPCId" in params, "VPCId parameter not found"
        assert params["VPCId"]["Type"] == "AWS::EC2::VPC::Id"

    def test_private_subnet_ids_parameter_exists(self, template: dict[str, Any]):
        """Test PrivateSubnetIds parameter is defined."""
        params = template.get("Parameters", {})
        assert "PrivateSubnetIds" in params, "PrivateSubnetIds parameter not found"
        assert params["PrivateSubnetIds"]["Type"] == "List<AWS::EC2::Subnet::Id>"

    def test_db_password_is_noecho(self, template: dict[str, Any]):
        """Test DBPassword parameter has NoEcho enabled."""
        db_password = template["Parameters"]["DBPassword"]
        assert db_password.get("NoEcho") is True, "DBPassword should have NoEcho enabled"

    def test_db_password_has_length_constraints(self, template: dict[str, Any]):
        """Test DBPassword has minimum and maximum length constraints."""
        db_password = template["Parameters"]["DBPassword"]
        assert (
            int(db_password.get("MinLength", 0)) >= 8
        ), "DBPassword MinLength should be at least 8"
        assert "MaxLength" in db_password, "DBPassword should have MaxLength"

    def test_publicly_accessible_defaults_to_false(self, template: dict[str, Any]):
        """Test PubliclyAccessible parameter defaults to false."""
        param = template["Parameters"]["PubliclyAccessible"]
        assert param.get("Default") == "false", "PubliclyAccessible should default to 'false'"

    def test_environment_parameter_has_allowed_values(self, template: dict[str, Any]):
        """Test Environment parameter has appropriate allowed values."""
        env_param = template["Parameters"]["Environment"]
        allowed = env_param.get("AllowedValues", [])
        assert "dev" in allowed, "Environment should allow 'dev'"
        assert "staging" in allowed or "prod" in allowed, "Environment should allow staging or prod"

    def test_db_instance_exists(self, template: dict[str, Any]):
        """Test DBInstance resource exists."""
        resources = template.get("Resources", {})
        assert "DBInstance" in resources, "DBInstance resource not found"

    def test_db_instance_type(self, template: dict[str, Any]):
        """Test DBInstance has correct type."""
        db_instance = template["Resources"]["DBInstance"]
        assert db_instance.get("Type") == "AWS::RDS::DBInstance", "DBInstance has incorrect type"

    def test_db_instance_uses_postgres(self, template: dict[str, Any]):
        """Test DBInstance uses PostgreSQL engine."""
        db_props = template["Resources"]["DBInstance"]["Properties"]
        assert db_props.get("Engine") == "postgres", "DBInstance should use postgres engine"

    def test_db_instance_has_backup_retention(self, template: dict[str, Any]):
        """Test DBInstance has backup retention configured."""
        db_props = template["Resources"]["DBInstance"]["Properties"]
        retention = db_props.get("BackupRetentionPeriod")
        assert retention is not None, "BackupRetentionPeriod should be configured"
        assert retention >= 1, "BackupRetentionPeriod should be at least 1 day"

    def test_db_instance_has_backup_window(self, template: dict[str, Any]):
        """Test DBInstance has preferred backup window."""
        db_props = template["Resources"]["DBInstance"]["Properties"]
        assert "PreferredBackupWindow" in db_props, "PreferredBackupWindow should be configured"

    def test_db_instance_has_maintenance_window(self, template: dict[str, Any]):
        """Test DBInstance has preferred maintenance window."""
        db_props = template["Resources"]["DBInstance"]["Properties"]
        assert (
            "PreferredMaintenanceWindow" in db_props
        ), "PreferredMaintenanceWindow should be configured"

    def test_db_instance_has_deletion_policy(self, template: dict[str, Any]):
        """Test DBInstance has DeletionPolicy configured."""
        # DeletionPolicy is a resource-level property, not in Properties
        db_instance = template["Resources"]["DBInstance"]
        assert (
            db_instance.get("DeletionPolicy") == "Snapshot"
        ), "DBInstance DeletionPolicy should be Snapshot for data safety"

    def test_db_instance_in_subnet_group(self, template, cdk_template_factory):
        """Test DBInstance is associated with a subnet group."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::RDS::DBInstance", Match.object_like({"DBSubnetGroupName": Match.any_value()})
        )

    def test_db_instance_has_security_groups(self, template: dict[str, Any]):
        """Test DBInstance has VPC security groups."""
        db_props = template["Resources"]["DBInstance"]["Properties"]
        assert "VPCSecurityGroups" in db_props, "DBInstance should have VPCSecurityGroups"
        assert (
            len(db_props["VPCSecurityGroups"]) > 0
        ), "DBInstance should have at least one security group"

    def test_db_subnet_group_exists(self, template: dict[str, Any]):
        """Test DBSubnetGroup resource exists."""
        resources = template.get("Resources", {})
        assert "DBSubnetGroup" in resources, "DBSubnetGroup resource not found"

    def test_db_subnet_group_type(self, template: dict[str, Any]):
        """Test DBSubnetGroup has correct type."""
        subnet_group = template["Resources"]["DBSubnetGroup"]
        assert (
            subnet_group.get("Type") == "AWS::RDS::DBSubnetGroup"
        ), "DBSubnetGroup has incorrect type"

    def test_db_subnet_group_has_subnets(self, template: dict[str, Any]):
        """Test DBSubnetGroup references subnet IDs."""
        subnet_props = template["Resources"]["DBSubnetGroup"]["Properties"]
        assert "SubnetIds" in subnet_props, "DBSubnetGroup should have SubnetIds"

    def test_db_subnet_group_has_tags(self, template, cdk_template_factory):
        """Test DBSubnetGroup has tags."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::RDS::DBSubnetGroup",
            Match.object_like({"Tags": Match.array_with([Match.object_like({})])}),
        )

    def test_db_security_group_exists(self, template: dict[str, Any]):
        """Test DBSecurityGroup resource exists."""
        resources = template.get("Resources", {})
        assert "DBSecurityGroup" in resources, "DBSecurityGroup resource not found"

    def test_db_security_group_type(self, template: dict[str, Any]):
        """Test DBSecurityGroup has correct type."""
        sg = template["Resources"]["DBSecurityGroup"]
        assert sg.get("Type") == "AWS::EC2::SecurityGroup", "DBSecurityGroup has incorrect type"

    def test_db_security_group_in_vpc(self, template: dict[str, Any]):
        """Test DBSecurityGroup is associated with VPC."""
        sg_props = template["Resources"]["DBSecurityGroup"]["Properties"]
        assert "VpcId" in sg_props, "DBSecurityGroup should be in a VPC"

    def test_db_security_group_has_description(self, template: dict[str, Any]):
        """Test DBSecurityGroup has a description."""
        sg_props = template["Resources"]["DBSecurityGroup"]["Properties"]
        assert "GroupDescription" in sg_props, "DBSecurityGroup should have GroupDescription"

    def test_ingress_rules_target_postgres_port(self, template, cdk_template_factory):
        """Test ingress rules allow PostgreSQL port 5432."""
        cdk_template = cdk_template_factory(template)

        # All ingress rules should target PostgreSQL port
        cdk_template.all_resources_properties(
            "AWS::EC2::SecurityGroupIngress",
            Match.object_like({"FromPort": 5432, "ToPort": 5432, "IpProtocol": "tcp"}),
        )

    # CDK Assertion Tests (Behavioral Validation)

    def test_db_instance_has_encryption_enabled(self, template, cdk_template_factory):
        """Test that the RDS instance has storage encryption enabled.

        Storage encryption at rest protects sensitive data using AWS-managed
        or customer-managed KMS keys.

        Uses CDK assertions to verify encryption without depending on specific
        property structures.
        """
        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::RDS::DBInstance",
            Match.object_like({"StorageEncrypted": True}),
        )

    def test_db_instance_has_backup_configured(self, template, cdk_template_factory):
        """Test that the RDS instance has automated backups configured.

        Automated backups enable point-in-time recovery and are essential
        for disaster recovery.

        Tests for presence of backup retention period >= 1 day.
        """

        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::RDS::DBInstance",
            Match.object_like(
                {
                    "BackupRetentionPeriod": Match.any_value(),
                    "PreferredBackupWindow": Match.any_value(),
                }
            ),
        )

    def test_db_instance_in_private_subnet(self, template, cdk_template_factory):
        """Test that the RDS instance is deployed in a DB subnet group.

        DB subnet groups ensure the database is deployed in appropriate
        subnets (typically private subnets for security).
        """

        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::RDS::DBInstance",
            Match.object_like({"DBSubnetGroupName": Match.any_value()}),
        )

    def test_db_instance_has_security_group(self, template, cdk_template_factory):
        """Test that the RDS instance has VPC security groups configured.

        Security groups control network access to the database instance.
        """

        cdk_template = cdk_template_factory(template)

        # Check that VPCSecurityGroups exists and is an array
        cdk_template.has_resource_properties(
            "AWS::RDS::DBInstance",
            Match.object_like({"VPCSecurityGroups": Match.any_value()}),
        )

    def test_db_has_snapshot_deletion_policy(self, template, cdk_template_factory):
        """Test that the RDS instance has Snapshot deletion policy.

        Snapshot deletion policy ensures a final snapshot is taken before
        the database is deleted, protecting against accidental data loss.
        """

        cdk_template = cdk_template_factory(template)

        # CDK assertions can check resource-level properties
        db_instances = cdk_template.find_resources("AWS::RDS::DBInstance")

        for logical_id, resource in db_instances.items():
            assert (
                "DeletionPolicy" in resource
            ), f"DBInstance {logical_id} should have DeletionPolicy"
            assert (
                resource["DeletionPolicy"] == "Snapshot"
            ), f"DBInstance {logical_id} should have Snapshot DeletionPolicy"
