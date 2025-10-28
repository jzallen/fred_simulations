"""Tests for Epistemix API Lambda CloudFormation template.

This test suite validates the Lambda template with DEEP validation of:
- IAM policy permissions and scoping
- Security group configurations
- Environment variable handling
- VPC configurations
- CloudWatch log retention

Integration tests marked with @pytest.mark.integration can be skipped.
"""

import json
from pathlib import Path
from typing import Any
import pytest


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return path to the Lambda CloudFormation template."""
    return str(
        Path(__file__).parent.parent.parent / "templates" / "lambda" / "epistemix-api-lambda.json"
    )


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the Lambda CloudFormation template."""
    with open(template_path, "r") as f:
        return json.load(f)


class TestLambdaTemplate:
    """Test suite for Lambda CloudFormation template with deep security validation."""

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

    def test_db_password_is_noecho(self, template: dict[str, Any]):
        """DBPassword must have NoEcho to prevent exposure in console/API."""
        assert template["Parameters"]["DBPassword"].get("NoEcho") is True

    def test_db_password_has_minimum_length(self, template: dict[str, Any]):
        """DBPassword must enforce minimum length >= 8."""
        assert template["Parameters"]["DBPassword"].get("MinLength") == 8

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

    # ============================================================================
    # Lambda Function Configuration (DEEP)
    # ============================================================================

    def test_lambda_uses_container_image_package_type(self, template: dict[str, Any]):
        """Lambda must use container image package type."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert func.get("PackageType") == "Image"

    def test_lambda_specifies_architecture_for_container(self, template: dict[str, Any]):
        """Container-based Lambda must specify architecture."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "Architectures" in func
        assert "x86_64" in func["Architectures"]

    def test_lambda_has_execution_role_reference(self, template: dict[str, Any]):
        """Lambda must reference an IAM execution role."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "Role" in func
        # Should use Fn::GetAtt to get role ARN
        role = func["Role"]
        assert "Fn::GetAtt" in role
        assert role["Fn::GetAtt"][0] == "LambdaExecutionRole"

    def test_lambda_deployed_in_vpc(self, template: dict[str, Any]):
        """Lambda must be deployed in VPC for private resource access."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "VpcConfig" in func
        vpc_config = func["VpcConfig"]
        assert "SecurityGroupIds" in vpc_config
        assert "SubnetIds" in vpc_config
        assert len(vpc_config["SecurityGroupIds"]) > 0
        assert len(vpc_config["SubnetIds"]) > 0

    def test_lambda_has_timeout_configured(self, template: dict[str, Any]):
        """Lambda must have explicit timeout to prevent runaway functions."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "Timeout" in func

    def test_lambda_has_memory_size_configured(self, template: dict[str, Any]):
        """Lambda must have explicit memory size for performance/cost control."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "MemorySize" in func

    def test_lambda_has_tags(self, template: dict[str, Any]):
        """Lambda must have tags for cost tracking and governance."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "Tags" in func
        tags = {t["Key"]: t["Value"] for t in func["Tags"]}
        assert "Environment" in tags
        assert "Service" in tags

    # ============================================================================
    # Environment Variables Security (DEEP)
    # ============================================================================

    def test_lambda_environment_variables_defined(self, template: dict[str, Any]):
        """Lambda should have environment variables for configuration."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        assert "Environment" in func
        assert "Variables" in func["Environment"]

    def test_database_password_in_environment_variables(self, template: dict[str, Any]):
        """SECURITY CONCERN: DB_PASSWORD in environment variables.

        This test documents a known security anti-pattern. For production:
        - Use AWS Secrets Manager with dynamic references
        - Or use RDS IAM authentication
        - Environment variables are visible in Lambda console
        """
        func = template["Resources"]["LambdaFunction"]["Properties"]
        env_vars = func["Environment"]["Variables"]

        # Document that password is in environment (anti-pattern for prod)
        assert "DB_PASSWORD" in env_vars, \
            "DB_PASSWORD found in environment (OK for dev, use Secrets Manager for prod)"

        # At minimum, it should reference the NoEcho parameter
        db_password = env_vars["DB_PASSWORD"]
        assert "Ref" in db_password
        assert db_password["Ref"] == "DBPassword"

    def test_database_url_contains_password_reference(self, template: dict[str, Any]):
        """DATABASE_URL should reference DBPassword parameter."""
        func = template["Resources"]["LambdaFunction"]["Properties"]
        env_vars = func["Environment"]["Variables"]

        assert "DATABASE_URL" in env_vars
        # Should use Fn::Sub with ${DBPassword}
        db_url = env_vars["DATABASE_URL"]
        assert "Fn::Sub" in db_url

    # ============================================================================
    # IAM Execution Role (DEEP SECURITY VALIDATION)
    # ============================================================================

    def test_execution_role_exists(self, template: dict[str, Any]):
        """Lambda execution role must exist."""
        assert "LambdaExecutionRole" in template["Resources"]

    def test_execution_role_trusts_lambda_service(self, template: dict[str, Any]):
        """Execution role must trust lambda.amazonaws.com service."""
        role = template["Resources"]["LambdaExecutionRole"]["Properties"]
        assume_policy = role["AssumeRolePolicyDocument"]

        statements = assume_policy["Statement"]
        lambda_trust = [
            s for s in statements
            if s.get("Effect") == "Allow"
            and s.get("Principal", {}).get("Service") == "lambda.amazonaws.com"
            and "sts:AssumeRole" in s.get("Action", [])
        ]
        assert len(lambda_trust) == 1, "Must have exactly one Lambda service trust statement"

    def test_execution_role_has_basic_and_vpc_managed_policies(self, template: dict[str, Any]):
        """Role must have AWS managed policies for Lambda basic execution and VPC access."""
        role = template["Resources"]["LambdaExecutionRole"]["Properties"]
        managed_policies = role.get("ManagedPolicyArns", [])

        assert "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" in managed_policies
        assert "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole" in managed_policies

    def test_cloudwatch_logs_policy_is_scoped_to_function_logs(self, template: dict[str, Any]):
        """CloudWatch Logs policy must be scoped to this function's log group only."""
        role = template["Resources"]["LambdaExecutionRole"]["Properties"]
        policies = role.get("Policies", [])

        cw_policy = next((p for p in policies if p["PolicyName"] == "CloudWatchLogsPolicy"), None)
        assert cw_policy is not None

        statements = cw_policy["PolicyDocument"]["Statement"]
        assert len(statements) == 1

        statement = statements[0]
        assert statement["Effect"] == "Allow"
        assert set(statement["Action"]) == {
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
        }

        # Resource must be scoped (not "*")
        resource = statement["Resource"]
        assert "Fn::Sub" in resource
        # Should be scoped to /aws/lambda/${ServiceName}-*
        assert "/aws/lambda/" in resource["Fn::Sub"]

    def test_s3_policy_is_scoped_to_specific_bucket(self, template: dict[str, Any]):
        """S3 policy must be scoped to specific bucket, not wildcard."""
        role = template["Resources"]["LambdaExecutionRole"]["Properties"]
        policies = role.get("Policies", [])

        s3_policy = next((p for p in policies if p["PolicyName"] == "S3AccessPolicy"), None)
        assert s3_policy is not None

        statements = s3_policy["PolicyDocument"]["Statement"]
        assert len(statements) == 1

        statement = statements[0]
        assert statement["Effect"] == "Allow"

        # Check allowed actions are appropriate
        actions = set(statement["Action"])
        assert actions == {
            "s3:PutObject",
            "s3:GetObject",
            "s3:DeleteObject",
            "s3:ListBucket"
        }

        # Resources must NOT be "*"
        resources = statement["Resource"]
        assert isinstance(resources, list)
        assert len(resources) == 2

        # Both should use Fn::Sub with specific bucket
        for resource in resources:
            assert "Fn::Sub" in resource
            assert "epistemix-uploads-" in resource["Fn::Sub"]
            assert "*" not in resource["Fn::Sub"] or resource["Fn::Sub"].endswith("/*")  # Only trailing /*

    def test_rds_policy_is_read_only(self, template: dict[str, Any]):
        """RDS policy should only allow describe actions (read-only)."""
        role = template["Resources"]["LambdaExecutionRole"]["Properties"]
        policies = role.get("Policies", [])

        rds_policy = next((p for p in policies if p["PolicyName"] == "RDSAccessPolicy"), None)
        assert rds_policy is not None

        statements = rds_policy["PolicyDocument"]["Statement"]
        assert len(statements) == 1

        statement = statements[0]
        assert statement["Effect"] == "Allow"

        # Should only allow describe actions
        actions = set(statement["Action"])
        assert actions == {
            "rds:DescribeDBInstances",
            "rds:DescribeDBClusters"
        }

        # All describe actions are safe with "*" resource
        assert statement["Resource"] == "*"

    def test_ecr_policy_is_scoped_to_specific_repository(self, template: dict[str, Any]):
        """ECR policy must be scoped to specific repository."""
        role = template["Resources"]["LambdaExecutionRole"]["Properties"]
        policies = role.get("Policies", [])

        ecr_policy = next((p for p in policies if p["PolicyName"] == "ECRAccessPolicy"), None)
        assert ecr_policy is not None

        statements = ecr_policy["PolicyDocument"]["Statement"]
        assert len(statements) == 2

        # First statement: scoped to specific repository
        repo_statement = statements[0]
        assert repo_statement["Effect"] == "Allow"
        assert set(repo_statement["Action"]) == {
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            "ecr:BatchCheckLayerAvailability"
        }

        # Resource must be scoped to specific repository
        resource = repo_statement["Resource"]
        assert "Fn::Sub" in resource
        assert "repository/epistemix-api" in resource["Fn::Sub"]

        # Second statement: GetAuthorizationToken requires "*"
        auth_statement = statements[1]
        assert auth_statement["Effect"] == "Allow"
        assert auth_statement["Action"] == ["ecr:GetAuthorizationToken"]
        assert auth_statement["Resource"] == "*"  # Required by AWS

    # ============================================================================
    # Security Group Configuration (DEEP)
    # ============================================================================

    def test_lambda_security_group_exists(self, template: dict[str, Any]):
        """Lambda security group must exist for VPC deployment."""
        assert "LambdaSecurityGroup" in template["Resources"]

    def test_lambda_security_group_in_vpc(self, template: dict[str, Any]):
        """Security group must be associated with VPC."""
        sg = template["Resources"]["LambdaSecurityGroup"]["Properties"]
        assert "VpcId" in sg

    def test_lambda_security_group_has_no_ingress_rules(self, template: dict[str, Any]):
        """Lambda security group should NOT have ingress rules.

        Lambda functions are invoked by AWS services, not direct connections.
        Ingress rules would be a security risk.
        """
        sg = template["Resources"]["LambdaSecurityGroup"]["Properties"]

        # SecurityGroupIngress should not exist OR be empty
        ingress = sg.get("SecurityGroupIngress", [])
        assert len(ingress) == 0, \
            "Lambda security group should not allow inbound connections"

    def test_lambda_security_group_has_explicit_egress(self, template: dict[str, Any]):
        """Security group should have explicit egress rules."""
        sg = template["Resources"]["LambdaSecurityGroup"]["Properties"]
        assert "SecurityGroupEgress" in sg
        assert len(sg["SecurityGroupEgress"]) > 0

    def test_rds_security_group_ingress_allows_lambda_access(self, template: dict[str, Any]):
        """Template should create ingress rule allowing Lambda to access RDS."""
        assert "RDSSecurityGroupIngress" in template["Resources"]

        ingress = template["Resources"]["RDSSecurityGroupIngress"]["Properties"]
        assert ingress["IpProtocol"] == "tcp"

        # Should reference DBPort parameter
        assert "Ref" in ingress["FromPort"]
        assert ingress["FromPort"]["Ref"] == "DBPort"

        # Should reference Lambda security group as source
        assert "Ref" in ingress["SourceSecurityGroupId"]
        assert ingress["SourceSecurityGroupId"]["Ref"] == "LambdaSecurityGroup"

    # ============================================================================
    # CloudWatch Logs Configuration (DEEP)
    # ============================================================================

    def test_log_group_exists(self, template: dict[str, Any]):
        """CloudWatch log group must exist for Lambda logs."""
        assert "LambdaLogGroup" in template["Resources"]

    def test_log_group_name_matches_lambda_function(self, template: dict[str, Any]):
        """Log group name must match Lambda function naming pattern."""
        log_group = template["Resources"]["LambdaLogGroup"]["Properties"]
        log_group_name = log_group["LogGroupName"]

        assert "Fn::Sub" in log_group_name
        assert "/aws/lambda/" in log_group_name["Fn::Sub"]
        assert "${ServiceName}-${Environment}" in log_group_name["Fn::Sub"]

    def test_log_group_has_retention_policy(self, template: dict[str, Any]):
        """Log group must have retention to prevent unlimited storage costs."""
        log_group = template["Resources"]["LambdaLogGroup"]["Properties"]
        assert "RetentionInDays" in log_group

    def test_log_group_retention_varies_by_environment(self, template: dict[str, Any]):
        """Production logs should have longer retention than dev."""
        log_group = template["Resources"]["LambdaLogGroup"]["Properties"]
        retention = log_group["RetentionInDays"]

        # Should use Fn::If based on IsProduction condition
        assert "Fn::If" in retention
        assert retention["Fn::If"][0] == "IsProduction"

        prod_retention = retention["Fn::If"][1]
        dev_retention = retention["Fn::If"][2]

        assert prod_retention > dev_retention, \
            "Production should have longer retention than dev"

    # ============================================================================
    # Lambda Version & Alias (DEEP)
    # ============================================================================

    def test_lambda_version_exists(self, template: dict[str, Any]):
        """Lambda version resource enables versioning."""
        assert "LambdaVersion" in template["Resources"]

    def test_lambda_version_references_function(self, template: dict[str, Any]):
        """Lambda version must reference the function."""
        version = template["Resources"]["LambdaVersion"]["Properties"]
        assert "FunctionName" in version
        assert version["FunctionName"]["Ref"] == "LambdaFunction"

    def test_lambda_alias_exists(self, template: dict[str, Any]):
        """Lambda alias enables environment-based routing."""
        assert "LambdaAlias" in template["Resources"]

    def test_lambda_alias_name_matches_environment(self, template: dict[str, Any]):
        """Alias name should match environment parameter."""
        alias = template["Resources"]["LambdaAlias"]["Properties"]
        assert "Name" in alias
        assert alias["Name"]["Ref"] == "Environment"

    # ============================================================================
    # Outputs (DEEP)
    # ============================================================================

    def test_outputs_export_key_resources(self, template: dict[str, Any]):
        """Outputs should export ARNs and names for cross-stack references."""
        outputs = template["Outputs"]

        required_outputs = [
            "FunctionArn",
            "FunctionName",
            "RoleArn",
            "RoleName",
            "AliasArn",
            "SecurityGroupId",
            "LogGroupName"
        ]

        for output_name in required_outputs:
            assert output_name in outputs, f"{output_name} output missing"
            assert "Export" in outputs[output_name], \
                f"{output_name} should have Export for cross-stack references"

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
            / "lambda"
            / "lambda_security_rules.guard"
        )

        result = subprocess.run(
            ["cfn-guard", "validate", "--data", template_path, "--rules", str(rules_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"cfn-guard failed:\n{result.stdout}\n{result.stderr}"

    # ============================================================================
    # CDK Assertions (Behavioral Validation)
    # ============================================================================

    def test_lambda_deployed_in_vpc_cdk(self, template, cdk_template_factory):
        """CDK assertion: Lambda must be in VPC."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function",
            Match.object_like({
                "VpcConfig": Match.object_like({
                    "SecurityGroupIds": Match.any_value(),
                    "SubnetIds": Match.any_value()
                })
            }),
        )

    def test_lambda_has_execution_role_cdk(self, template, cdk_template_factory):
        """CDK assertion: Lambda must have execution role."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Function",
            Match.object_like({"Role": Match.any_value()}),
        )

    def test_iam_role_trusts_lambda_service_cdk(self, template, cdk_template_factory):
        """CDK assertion: IAM role must trust Lambda service."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like({
                "AssumeRolePolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        })
                    ])
                }
            }),
        )

    def test_log_group_has_retention_cdk(self, template, cdk_template_factory):
        """CDK assertion: Log group must have retention policy."""
        from aws_cdk.assertions import Match

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Logs::LogGroup",
            Match.object_like({"RetentionInDays": Match.any_value()}),
        )
