"""
Tests for AWS Batch VPC Endpoint CloudFormation template.

Validates that the batch-vpc-endpoint.json template:
- Is valid JSON
- Defines all required resources (VPC endpoint, security group)
- Has correct security group ingress rules for Lambda access
- Configures VPC endpoint with private DNS enabled
- Has proper exports for cross-stack references
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def template():
    """Load the Batch VPC Endpoint CloudFormation template."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "templates"
        / "vpc"
        / "batch-vpc-endpoint.json"
    )
    with open(template_path) as f:
        return json.load(f)


def test_template_is_valid_json():
    """Template should be valid JSON format."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "templates"
        / "vpc"
        / "batch-vpc-endpoint.json"
    )
    with open(template_path) as f:
        data = json.load(f)

    assert data is not None
    assert "AWSTemplateFormatVersion" in data
    assert data["AWSTemplateFormatVersion"] == "2010-09-09"


def test_template_has_description(template):
    """Template should have a description."""
    assert "Description" in template
    assert "VPC Endpoint" in template["Description"]
    assert "AWS Batch" in template["Description"]


def test_template_has_required_parameters(template):
    """Template should define required parameters."""
    params = template["Parameters"]

    # VPC configuration
    assert "VpcId" in params
    assert params["VpcId"]["Type"] == "AWS::EC2::VPC::Id"

    assert "SubnetIds" in params
    assert params["SubnetIds"]["Type"] == "List<AWS::EC2::Subnet::Id>"

    # Lambda security groups that need access
    assert "LambdaSecurityGroupIds" in params
    assert params["LambdaSecurityGroupIds"]["Type"] == "List<AWS::EC2::SecurityGroup::Id>"


def test_template_defines_security_group(template):
    """Template should define security group for VPC endpoint."""
    resources = template["Resources"]
    assert "BatchVpcEndpointSecurityGroup" in resources

    sg = resources["BatchVpcEndpointSecurityGroup"]
    assert sg["Type"] == "AWS::EC2::SecurityGroup"


def test_security_group_allows_https_from_lambda(template):
    """Security group should allow HTTPS (port 443) from Lambda security groups."""
    sg = template["Resources"]["BatchVpcEndpointSecurityGroup"]
    ingress_rules = sg["Properties"]["SecurityGroupIngress"]

    # Should have 2 ingress rules (dev and staging Lambda SGs)
    assert len(ingress_rules) >= 2

    # Check first rule (dev Lambda)
    dev_rule = ingress_rules[0]
    assert dev_rule["IpProtocol"] == "tcp"
    assert dev_rule["FromPort"] == 443
    assert dev_rule["ToPort"] == 443
    assert "SourceSecurityGroupId" in dev_rule
    assert "Fn::Select" in dev_rule["SourceSecurityGroupId"]

    # Check second rule (staging Lambda)
    staging_rule = ingress_rules[1]
    assert staging_rule["IpProtocol"] == "tcp"
    assert staging_rule["FromPort"] == 443
    assert staging_rule["ToPort"] == 443
    assert "SourceSecurityGroupId" in staging_rule


def test_security_group_has_descriptive_tags(template):
    """Security group should have descriptive tags."""
    sg = template["Resources"]["BatchVpcEndpointSecurityGroup"]
    tags = {tag["Key"]: tag["Value"] for tag in sg["Properties"]["Tags"]}

    assert tags["Name"] == "batch-vpc-endpoint-sg"
    assert tags["Purpose"] == "BatchVPCEndpoint"
    assert tags["ManagedBy"] == "CloudFormation"


def test_template_defines_vpc_endpoint(template):
    """Template should define VPC endpoint for AWS Batch."""
    resources = template["Resources"]
    assert "BatchVpcEndpoint" in resources

    vpc_endpoint = resources["BatchVpcEndpoint"]
    assert vpc_endpoint["Type"] == "AWS::EC2::VPCEndpoint"


def test_vpc_endpoint_is_interface_type(template):
    """VPC endpoint should be Interface type (not Gateway)."""
    vpc_endpoint = template["Resources"]["BatchVpcEndpoint"]
    props = vpc_endpoint["Properties"]

    assert props["VpcEndpointType"] == "Interface"


def test_vpc_endpoint_service_name_is_batch(template):
    """VPC endpoint should connect to AWS Batch service."""
    vpc_endpoint = template["Resources"]["BatchVpcEndpoint"]
    props = vpc_endpoint["Properties"]

    service_name = props["ServiceName"]
    assert "Fn::Sub" in service_name
    assert "com.amazonaws.${AWS::Region}.batch" in service_name["Fn::Sub"]


def test_vpc_endpoint_uses_subnets_parameter(template):
    """VPC endpoint should use SubnetIds parameter."""
    vpc_endpoint = template["Resources"]["BatchVpcEndpoint"]
    props = vpc_endpoint["Properties"]

    assert "SubnetIds" in props
    assert "Ref" in props["SubnetIds"]
    assert props["SubnetIds"]["Ref"] == "SubnetIds"


def test_vpc_endpoint_uses_security_group(template):
    """VPC endpoint should use the created security group."""
    vpc_endpoint = template["Resources"]["BatchVpcEndpoint"]
    props = vpc_endpoint["Properties"]

    assert "SecurityGroupIds" in props
    sg_ids = props["SecurityGroupIds"]
    assert len(sg_ids) == 1
    assert "Ref" in sg_ids[0]
    assert sg_ids[0]["Ref"] == "BatchVpcEndpointSecurityGroup"


def test_vpc_endpoint_enables_private_dns(template):
    """VPC endpoint should enable private DNS."""
    vpc_endpoint = template["Resources"]["BatchVpcEndpoint"]
    props = vpc_endpoint["Properties"]

    assert props["PrivateDnsEnabled"] is True


def test_vpc_endpoint_has_descriptive_tags(template):
    """VPC endpoint should have descriptive tags."""
    vpc_endpoint = template["Resources"]["BatchVpcEndpoint"]
    tags = {tag["Key"]: tag["Value"] for tag in vpc_endpoint["Properties"]["Tags"]}

    assert tags["Name"] == "batch-api-vpc-endpoint"
    assert tags["Purpose"] == "BatchAPIAccess"
    assert tags["ManagedBy"] == "CloudFormation"
    assert tags["Shared"] == "true"


def test_template_exports_vpc_endpoint_id(template):
    """Template should export VPC endpoint ID for cross-stack references."""
    outputs = template["Outputs"]

    assert "VpcEndpointId" in outputs
    vpc_endpoint_output = outputs["VpcEndpointId"]

    assert "Ref" in vpc_endpoint_output["Value"]
    assert vpc_endpoint_output["Value"]["Ref"] == "BatchVpcEndpoint"
    assert "Export" in vpc_endpoint_output
    assert vpc_endpoint_output["Export"]["Name"] == "batch-vpc-endpoint-id"


def test_template_outputs_dns_entries(template):
    """Template should output DNS entries for the VPC endpoint."""
    outputs = template["Outputs"]

    assert "VpcEndpointDnsEntries" in outputs
    dns_output = outputs["VpcEndpointDnsEntries"]

    assert "Fn::Join" in dns_output["Value"]
    join_parts = dns_output["Value"]["Fn::Join"]
    assert join_parts[0] == ","  # Join with comma
    assert "Fn::GetAtt" in join_parts[1]
    assert join_parts[1]["Fn::GetAtt"] == ["BatchVpcEndpoint", "DnsEntries"]
