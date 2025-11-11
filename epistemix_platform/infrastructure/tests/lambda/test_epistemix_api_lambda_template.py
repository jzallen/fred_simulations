"""Tests for Epistemix API Lambda CloudFormation template."""

import json
from pathlib import Path
from typing import Any

import pytest
from aws_cdk.assertions import Match


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return path to the Lambda CloudFormation template."""
    return str(
        Path(__file__).parent.parent.parent / "templates" / "lambda" / "epistemix-api-lambda.json"
    )


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the Lambda CloudFormation template."""
    with open(template_path) as f:
        return json.load(f)


class TestLambdaTemplate:
    """Test suite for Lambda CloudFormation template with deep security validation."""

    def test_template_exists(self, template_path: str):
        assert Path(template_path).exists()

    def test_template_valid_json(self, template: dict[str, Any]):
        assert isinstance(template, dict)

    def test_template_format_version(self, template: dict[str, Any]):
        assert template.get("AWSTemplateFormatVersion") == "2010-09-09"

    # Parameter Validation
    # Note: DBPassword parameter removed - using IAM authentication instead

    def test_memory_size_within_valid_range(self, template: dict[str, Any]):
        """Memory size must be within AWS Lambda limits."""
        memory = template["Parameters"]["MemorySize"]
        assert memory.get("MinValue") == 128
        assert memory.get("MaxValue") == 10240
        # Default should be reasonable (not max)
        default = memory.get("Default", 128)
        assert default <= 4096, "Default memory should be reasonable, not excessive"

    def test_timeout_within_valid_range(self, template: dict[str, Any]):
        """Timeout must be within AWS Lambda limits."""
        timeout = template["Parameters"]["Timeout"]
        assert timeout.get("MinValue") == 3
        assert timeout.get("MaxValue") == 900
        # Default should be reasonable (not 15 minutes)
        default = timeout.get("Default", 3)
        assert default <= 300, "Default timeout should be reasonable (<5 min)"

    # Lambda Function Configuration

    def test_lambda_has_execution_role_reference(self, template, cdk_template_factory):
        """Lambda must reference an IAM execution role."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function",
            Match.object_like({"Role": {"Fn::GetAtt": Match.array_with(["LambdaExecutionRole"])}}),
        )

    def test_lambda_deployed_in_vpc(self, template, cdk_template_factory):
        """Lambda must be deployed in VPC for private resource access."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function",
            Match.object_like(
                {
                    "VpcConfig": Match.object_like(
                        {"SecurityGroupIds": Match.any_value(), "SubnetIds": Match.any_value()}
                    )
                }
            ),
        )

    def test_lambda_has_timeout_configured(self, template, cdk_template_factory):
        """Lambda must have explicit timeout to prevent runaway functions."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function", Match.object_like({"Timeout": Match.any_value()})
        )

    def test_lambda_has_memory_size_configured(self, template, cdk_template_factory):
        """Lambda must have explicit memory size for performance/cost control."""
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function", Match.object_like({"MemorySize": Match.any_value()})
        )

    def test_lambda_has_tags(self, template, cdk_template_factory):
        """Lambda must have tags for cost tracking and governance."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function",
            Match.object_like(
                {
                    "Tags": Match.array_with(
                        [
                            Match.object_like({"Key": "Environment"}),
                            Match.object_like({"Key": "Service"}),
                        ]
                    )
                }
            ),
        )

    # Environment Variables Security

    def test_lambda_environment_variables_defined(self, template: dict[str, Any]):
        """Lambda should have environment variables for configuration."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "Environment" in func
        assert "Variables" in func["Environment"]

    def test_iam_authentication_environment_variables(self, template: dict[str, Any]):
        """Lambda uses IAM authentication instead of password-based auth.

        IAM authentication provides better security:
        - Short-lived tokens (15 minutes) instead of static passwords
        - No password exposure in environment variables
        - Credentials managed by AWS IAM
        """
        func = template["Resources"]["LambdaFunction"]["Properties"]
        env_vars = func["Environment"]["Variables"]

        # Verify IAM auth is enabled
        assert env_vars.get("USE_IAM_AUTH") == "true", "USE_IAM_AUTH must be enabled"

        # Verify IAM auth environment variables are present
        assert "DATABASE_HOST" in env_vars, "DATABASE_HOST required for IAM auth"
        assert "DATABASE_PORT" in env_vars, "DATABASE_PORT required for IAM auth"
        assert "DATABASE_NAME" in env_vars, "DATABASE_NAME required for IAM auth"
        assert "DATABASE_IAM_USER" in env_vars, "DATABASE_IAM_USER required for IAM auth"

        # Verify password-based variables are NOT present (security improvement)
        assert "DB_PASSWORD" not in env_vars, "DB_PASSWORD should not exist with IAM auth"
        assert "DATABASE_URL" not in env_vars, "DATABASE_URL should not exist with IAM auth"

    # IAM Execution Role

    def test_execution_role_trusts_lambda_service(self, template, cdk_template_factory):
        """Execution role must trust lambda.amazonaws.com service."""

        cdk_template = cdk_template_factory(template)

        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "AssumeRolePolicyDocument": {
                        "Statement": Match.array_with(
                            [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "lambda.amazonaws.com"},
                                    "Action": "sts:AssumeRole",
                                }
                            ]
                        )
                    }
                }
            ),
        )

    def test_cloudwatch_logs_policy_is_scoped_to_function_logs(
        self, template, cdk_template_factory
    ):
        """CloudWatch Logs policy must be scoped to this function's log group only."""

        cdk_template = cdk_template_factory(template)

        # Verify CloudWatchLogsPolicy exists with scoped resources
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "Policies": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "PolicyName": "CloudWatchLogsPolicy",
                                    "PolicyDocument": {
                                        "Statement": Match.array_with(
                                            [
                                                Match.object_like(
                                                    {
                                                        "Effect": "Allow",
                                                        "Action": [
                                                            "logs:CreateLogGroup",
                                                            "logs:CreateLogStream",
                                                            "logs:PutLogEvents",
                                                        ],
                                                        # Resource must NOT be "*" - must be scoped
                                                        "Resource": Match.object_like(
                                                            {
                                                                "Fn::Sub": Match.string_like_regexp(
                                                                    r".*\/aws\/lambda\/.*"
                                                                )
                                                            }
                                                        ),
                                                    }
                                                )
                                            ]
                                        )
                                    },
                                }
                            )
                        ]
                    )
                }
            ),
        )

    def test_s3_policy_is_scoped_to_specific_bucket(self, template, cdk_template_factory):
        """S3 policy must be scoped to specific bucket, not wildcard."""

        cdk_template = cdk_template_factory(template)

        # Verify S3AccessPolicy with scoped resources (not "*")
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "Policies": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "PolicyName": "S3AccessPolicy",
                                    "PolicyDocument": {
                                        "Statement": Match.array_with(
                                            [
                                                Match.object_like(
                                                    {
                                                        "Effect": "Allow",
                                                        "Action": [
                                                            "s3:PutObject",
                                                            "s3:GetObject",
                                                            "s3:DeleteObject",
                                                            "s3:ListBucket",
                                                        ],
                                                        # Resource must be array with bucket and bucket/*
                                                        "Resource": Match.array_with(
                                                            [
                                                                Match.object_like(
                                                                    {
                                                                        "Fn::Sub": Match.string_like_regexp(
                                                                            r".*epistemix-uploads-.*"
                                                                        )
                                                                    }
                                                                )
                                                            ]
                                                        ),
                                                    }
                                                )
                                            ]
                                        )
                                    },
                                }
                            )
                        ]
                    )
                }
            ),
        )

    def test_rds_policy_has_iam_auth_permission(self, template, cdk_template_factory):
        """RDS policy should allow IAM database authentication."""

        cdk_template = cdk_template_factory(template)

        # Verify RDSAccessPolicy has IAM auth permissions
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "Policies": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "PolicyName": "RDSAccessPolicy",
                                    "PolicyDocument": {
                                        "Statement": Match.array_with(
                                            [
                                                # Describe permissions for metadata
                                                Match.object_like(
                                                    {
                                                        "Effect": "Allow",
                                                        "Action": [
                                                            "rds:DescribeDBInstances",
                                                            "rds:DescribeDBClusters",
                                                        ],
                                                        "Resource": "*",
                                                    }
                                                ),
                                                # IAM authentication permission
                                                Match.object_like(
                                                    {
                                                        "Effect": "Allow",
                                                        "Action": "rds-db:connect",
                                                        "Resource": Match.object_like(
                                                            {
                                                                "Fn::Sub": Match.string_like_regexp(
                                                                    r".*rds-db:.*:dbuser:\*\/\*"
                                                                )
                                                            }
                                                        ),
                                                    }
                                                ),
                                            ]
                                        )
                                    },
                                }
                            )
                        ]
                    )
                }
            ),
        )

    def test_ecr_policy_is_scoped_to_specific_repository(self, template, cdk_template_factory):
        """ECR policy must be scoped to specific repository."""

        cdk_template = cdk_template_factory(template)

        # Verify ECRAccessPolicy with repository-scoped permissions
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "Policies": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "PolicyName": "ECRAccessPolicy",
                                    "PolicyDocument": {
                                        "Statement": Match.array_with(
                                            [
                                                # Repository-scoped statement
                                                Match.object_like(
                                                    {
                                                        "Effect": "Allow",
                                                        "Action": [
                                                            "ecr:GetDownloadUrlForLayer",
                                                            "ecr:BatchGetImage",
                                                            "ecr:BatchCheckLayerAvailability",
                                                        ],
                                                        "Resource": Match.object_like(
                                                            {
                                                                "Fn::Sub": Match.string_like_regexp(
                                                                    r".*repository\/epistemix-api$"
                                                                )
                                                            }
                                                        ),
                                                    }
                                                ),
                                                # GetAuthorizationToken requires "*"
                                                Match.object_like(
                                                    {
                                                        "Effect": "Allow",
                                                        "Action": ["ecr:GetAuthorizationToken"],
                                                        "Resource": "*",
                                                    }
                                                ),
                                            ]
                                        )
                                    },
                                }
                            )
                        ]
                    )
                }
            ),
        )

    # Security Group Configuration

    def test_lambda_security_group_exists(self, template, cdk_template_factory):
        """Lambda security group must exist for VPC deployment."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::EC2::SecurityGroup", 1)

    def test_lambda_security_group_in_vpc(self, template, cdk_template_factory):
        """Security group must be associated with VPC."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup", Match.object_like({"VpcId": Match.any_value()})
        )

    def test_lambda_security_group_has_no_ingress_rules(self, template, cdk_template_factory):
        """Lambda security group should NOT have ingress rules.

        Lambda functions are invoked by AWS services, not direct connections.
        Ingress rules would be a security risk.
        """
        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup", Match.object_like({"SecurityGroupIngress": Match.absent()})
        )

    def test_lambda_security_group_has_explicit_egress(self, template, cdk_template_factory):
        """Security group should have explicit egress rules."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            Match.object_like(
                {
                    "SecurityGroupEgress": Match.array_with(
                        [Match.object_like({"IpProtocol": Match.any_value()})]
                    )
                }
            ),
        )

    def test_rds_security_group_ingress_allows_lambda_access(self, template, cdk_template_factory):
        """Template should create ingress rule allowing Lambda to access RDS."""

        cdk_template = cdk_template_factory(template)

        # Verify RDS security group ingress resource exists
        cdk_template.resource_count_is("AWS::EC2::SecurityGroupIngress", 1)

        # Verify ingress rule configuration
        cdk_template.has_resource_properties(
            "AWS::EC2::SecurityGroupIngress",
            Match.object_like(
                {
                    "IpProtocol": "tcp",
                    # References DBPort parameter
                    "FromPort": {"Ref": "DBPort"},
                    "ToPort": {"Ref": "DBPort"},
                    # Source is Lambda security group
                    "SourceSecurityGroupId": {"Ref": "LambdaSecurityGroup"},
                }
            ),
        )

    # CloudWatch Logs Configuration

    def test_log_group_exists(self, template, cdk_template_factory):
        """CloudWatch log group must exist for Lambda logs."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::Logs::LogGroup", 1)

    def test_log_group_name_matches_lambda_function(self, template, cdk_template_factory):
        """Log group name must match Lambda function naming pattern."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Logs::LogGroup",
            Match.object_like(
                {
                    "LogGroupName": {
                        "Fn::Sub": Match.string_like_regexp(
                            r"\/aws\/lambda\/.*\$\{ServiceName\}-\$\{Environment\}"
                        )
                    }
                }
            ),
        )

    def test_log_group_has_retention_policy(self, template, cdk_template_factory):
        """Log group must have retention to prevent unlimited storage costs."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Logs::LogGroup", Match.object_like({"RetentionInDays": Match.any_value()})
        )

    # Lambda Version & Alias

    def test_lambda_version_exists(self, template, cdk_template_factory):
        """Lambda version resource enables versioning."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::Lambda::Version", 1)

    def test_lambda_version_references_function(self, template, cdk_template_factory):
        """Lambda version must reference the function."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Version", Match.object_like({"FunctionName": {"Ref": "LambdaFunction"}})
        )

    def test_lambda_alias_exists(self, template, cdk_template_factory):
        """Lambda alias enables environment-based routing."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::Lambda::Alias", 1)

    def test_lambda_alias_name_matches_environment(self, template, cdk_template_factory):
        """Alias name should match environment parameter."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Alias", Match.object_like({"Name": {"Ref": "Environment"}})
        )

    # CDK Assertions (Behavioral Validation)

    def test_lambda_deployed_in_vpc_cdk(self, template, cdk_template_factory):
        """CDK assertion: Lambda must be in VPC."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function",
            Match.object_like(
                {
                    "VpcConfig": Match.object_like(
                        {"SecurityGroupIds": Match.any_value(), "SubnetIds": Match.any_value()}
                    )
                }
            ),
        )

    def test_lambda_has_execution_role_cdk(self, template, cdk_template_factory):
        """CDK assertion: Lambda must have execution role."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function",
            Match.object_like({"Role": Match.any_value()}),
        )

    def test_iam_role_trusts_lambda_service_cdk(self, template, cdk_template_factory):
        """CDK assertion: IAM role must trust Lambda service."""

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
                                        "Principal": {"Service": "lambda.amazonaws.com"},
                                        "Action": "sts:AssumeRole",
                                    }
                                )
                            ]
                        )
                    }
                }
            ),
        )

    def test_log_group_has_retention_cdk(self, template, cdk_template_factory):
        """CDK assertion: Log group must have retention policy."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Logs::LogGroup",
            Match.object_like({"RetentionInDays": Match.any_value()}),
        )
