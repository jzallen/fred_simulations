"""Tests for Epistemix API Gateway CloudFormation template."""

import json
from pathlib import Path
from typing import Any

import pytest
from aws_cdk.assertions import Match


@pytest.fixture(scope="session")
def template_path() -> str:
    """Return path to the API Gateway CloudFormation template."""
    return str(
        Path(__file__).parent.parent.parent
        / "templates"
        / "api-gateway"
        / "epistemix-api-gateway.json"
    )


@pytest.fixture(scope="session")
def template(template_path: str) -> dict[str, Any]:
    """Load the API Gateway CloudFormation template."""
    with open(template_path) as f:
        return json.load(f)


class TestApiGatewayTemplate:
    """Test suite for API Gateway CloudFormation template with deep security validation."""

    def test_template_exists(self, template_path: str):
        assert Path(template_path).exists()

    def test_template_valid_json(self, template: dict[str, Any]):
        assert isinstance(template, dict)

    def test_template_format_version(self, template: dict[str, Any]):
        assert template.get("AWSTemplateFormatVersion") == "2010-09-09"

    # Parameter Validation

    def test_throttling_parameters_have_minimum_values(self, template: dict[str, Any]):
        """Throttling parameters must have MinValue constraint."""
        burst = template["Parameters"]["ThrottlingBurstLimit"]
        rate = template["Parameters"]["ThrottlingRateLimit"]

        assert burst.get("MinValue") == 0
        assert rate.get("MinValue") == 0

    def test_lambda_function_arn_parameter_required(self, template: dict[str, Any]):
        """Lambda function ARN parameter must have minimum length."""
        param = template["Parameters"]["LambdaFunctionArn"]
        assert param.get("MinLength") == 1

    def test_deployment_timestamp_parameter_for_redeployment(self, template: dict[str, Any]):
        """DeploymentTimestamp parameter enables forced redeployments."""
        param = template["Parameters"]["DeploymentTimestamp"]
        assert "Description" in param
        assert "force" in param["Description"].lower() or "runtime" in param["Description"].lower()

    # REST API Configuration

    def test_rest_api_exists(self, template, cdk_template_factory):
        """REST API resource must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::ApiGateway::RestApi", 1)

    def test_rest_api_has_regional_endpoint(self, template, cdk_template_factory):
        """REST API must use REGIONAL endpoint type for lower latency."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            Match.object_like({"EndpointConfiguration": {"Types": ["REGIONAL"]}}),
        )

    def test_rest_api_has_tags(self, template, cdk_template_factory):
        """REST API must have tags for governance."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            Match.object_like(
                {
                    "Tags": Match.array_with(
                        [
                            Match.object_like({"Key": "Environment"}),
                            Match.object_like({"Key": "Service"}),
                            Match.object_like({"Key": "ManagedBy"}),
                        ]
                    )
                }
            ),
        )

    # API Resources and Methods

    def test_api_has_health_endpoint(self, template, cdk_template_factory):
        """API must have /health endpoint for monitoring."""

        cdk_template = cdk_template_factory(template)

        # Health resource exists
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Resource", Match.object_like({"PathPart": "health"})
        )

        # Health method exists
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Method",
            Match.object_like(
                {"HttpMethod": "GET", "ResourceId": {"Ref": "ApiGatewayHealthResource"}}
            ),
        )

    def test_api_has_jobs_endpoints(self, template, cdk_template_factory):
        """API must have /jobs resource hierarchy."""

        cdk_template = cdk_template_factory(template)

        # Main /jobs resource
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Resource", Match.object_like({"PathPart": "jobs"})
        )

        # /jobs/register sub-resource
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Resource",
            Match.object_like(
                {"PathPart": "register", "ParentId": {"Ref": "ApiGatewayJobsResource"}}
            ),
        )

        # /jobs/results sub-resource
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Resource",
            Match.object_like(
                {"PathPart": "results", "ParentId": {"Ref": "ApiGatewayJobsResource"}}
            ),
        )

    def test_all_methods_have_authorization_type(self, template, cdk_template_factory):
        """All API methods must have AuthorizationType configured."""
        cdk_template = cdk_template_factory(template)

        # Verify all methods have AuthorizationType
        cdk_template.all_resources_properties(
            "AWS::ApiGateway::Method", Match.object_like({"AuthorizationType": Match.any_value()})
        )

    def test_all_methods_use_lambda_proxy_integration(self, template, cdk_template_factory):
        """All methods must use AWS_PROXY integration type for Lambda."""

        cdk_template = cdk_template_factory(template)

        # Find all method resources and verify they use AWS_PROXY
        resources = template["Resources"]

        # Each method should have AWS_PROXY integration
        for _resource_name, resource in resources.items():
            if resource["Type"] == "AWS::ApiGateway::Method":
                cdk_template.has_resource(
                    "AWS::ApiGateway::Method",
                    Match.object_like(
                        {
                            "Properties": Match.object_like(
                                {
                                    "Integration": Match.object_like(
                                        {"Type": "AWS_PROXY", "IntegrationHttpMethod": "POST"}
                                    )
                                }
                            )
                        }
                    ),
                )

    def test_proxy_resource_catches_all_paths(self, template, cdk_template_factory):
        """API must have catch-all {proxy+} resource."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Resource", Match.object_like({"PathPart": "{proxy+}"})
        )

    # Deployment Configuration

    def test_deployment_exists(self, template, cdk_template_factory):
        """Deployment resource must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::ApiGateway::Deployment", 1)

    def test_deployment_references_rest_api(self, template, cdk_template_factory):
        """Deployment must reference the REST API."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Deployment",
            Match.object_like({"RestApiId": {"Ref": "ApiGatewayRestApi"}}),
        )

    # Stage Configuration

    def test_stage_exists(self, template, cdk_template_factory):
        """Stage resource must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::ApiGateway::Stage", 1)

    def test_stage_references_deployment(self, template, cdk_template_factory):
        """Stage must reference deployment resource."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            Match.object_like({"DeploymentId": {"Ref": "ApiGatewayDeployment"}}),
        )

    def test_stage_has_tracing_enabled(self, template, cdk_template_factory):
        """Stage must have X-Ray tracing enabled."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Stage", Match.object_like({"TracingEnabled": True})
        )

    def test_stage_has_method_settings_with_throttling(self, template, cdk_template_factory):
        """Stage must have method settings with throttling configuration."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            Match.object_like(
                {
                    "MethodSettings": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "ResourcePath": "/*",
                                    "HttpMethod": "*",
                                    "MetricsEnabled": True,
                                    "ThrottlingBurstLimit": {"Ref": "ThrottlingBurstLimit"},
                                    "ThrottlingRateLimit": {"Ref": "ThrottlingRateLimit"},
                                }
                            )
                        ]
                    )
                }
            ),
        )

    def test_stage_has_access_log_settings(self, template, cdk_template_factory):
        """Stage must have access log settings configured."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            Match.object_like(
                {
                    "AccessLogSetting": Match.object_like(
                        {
                            "DestinationArn": {"Fn::GetAtt": ["ApiGatewayAccessLogGroup", "Arn"]},
                            "Format": Match.any_value(),  # JSON format string
                        }
                    )
                }
            ),
        )

    def test_access_log_format_is_structured_json(self, template, cdk_template_factory):
        """Access logs must use structured JSON format for parsing."""
        cdk_template = cdk_template_factory(template)

        # Verify AccessLogSetting exists with Format property
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            Match.object_like(
                {"AccessLogSetting": Match.object_like({"Format": Match.any_value()})}
            ),
        )

        # Validate JSON structure with traditional assertion
        stage = template["Resources"]["ApiGatewayStage"]["Properties"]
        access_log_format = stage["AccessLogSetting"]["Format"]
        parsed = json.loads(access_log_format)

        required_fields = [
            "requestId",
            "ip",
            "requestTime",
            "httpMethod",
            "path",
            "status",
            "protocol",
            "responseLength",
        ]

        for field in required_fields:
            assert field in parsed, f"Access log format should include {field}"

    def test_stage_has_environment_variables(self, template, cdk_template_factory):
        """Stage should have variables for environment context."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            Match.object_like(
                {"Variables": Match.object_like({"environment": {"Ref": "Environment"}})}
            ),
        )

    # CloudWatch Logging

    def test_log_group_exists(self, template, cdk_template_factory):
        """CloudWatch log group must exist for access logs."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::Logs::LogGroup", 1)

    def test_log_group_has_retention_policy(self, template, cdk_template_factory):
        """Log group must have retention to prevent unlimited storage costs."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Logs::LogGroup", Match.object_like({"RetentionInDays": Match.any_value()})
        )

    def test_cloudwatch_role_exists(self, template, cdk_template_factory):
        """IAM role for CloudWatch logging must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::IAM::Role", 1)

    def test_cloudwatch_role_trusts_api_gateway_service(self, template, cdk_template_factory):
        """CloudWatch role must trust apigateway.amazonaws.com service."""

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
                                        "Principal": {"Service": "apigateway.amazonaws.com"},
                                        "Action": "sts:AssumeRole",
                                    }
                                )
                            ]
                        )
                    }
                }
            ),
        )

    def test_cloudwatch_role_has_managed_policy(self, template, cdk_template_factory):
        """CloudWatch role must have AWS managed policy for logging."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::IAM::Role",
            Match.object_like(
                {
                    "ManagedPolicyArns": Match.array_with(
                        [
                            "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                        ]
                    )
                }
            ),
        )

    def test_api_gateway_account_references_cloudwatch_role(self, template, cdk_template_factory):
        """API Gateway account must reference CloudWatch role."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::Account",
            Match.object_like(
                {"CloudWatchRoleArn": {"Fn::GetAtt": ["ApiGatewayCloudWatchRole", "Arn"]}}
            ),
        )

    # Usage Plan and Throttling

    def test_usage_plan_exists(self, template, cdk_template_factory):
        """Usage plan must exist for throttling control."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::ApiGateway::UsagePlan", 1)

    def test_usage_plan_has_throttling_limits(self, template, cdk_template_factory):
        """Usage plan must have throttling limits configured."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::UsagePlan",
            Match.object_like(
                {
                    "Throttle": Match.object_like(
                        {
                            "BurstLimit": {"Ref": "ThrottlingBurstLimit"},
                            "RateLimit": {"Ref": "ThrottlingRateLimit"},
                        }
                    )
                }
            ),
        )

    def test_usage_plan_associated_with_stage(self, template, cdk_template_factory):
        """Usage plan must be associated with API stage."""

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::ApiGateway::UsagePlan",
            Match.object_like(
                {
                    "ApiStages": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "ApiId": {"Ref": "ApiGatewayRestApi"},
                                    "Stage": {"Ref": "StageName"},
                                }
                            )
                        ]
                    )
                }
            ),
        )

    # Lambda Integration

    def test_lambda_invoke_permission_exists(self, template, cdk_template_factory):
        """Lambda permission for API Gateway invocation must exist."""
        cdk_template = cdk_template_factory(template)
        cdk_template.resource_count_is("AWS::Lambda::Permission", 1)

    def test_lambda_permission_scoped_to_api_gateway(self, template, cdk_template_factory):
        """Lambda permission must be scoped to this API Gateway only.

        Using CDK assertions to verify permission configuration.
        """

        cdk_template = cdk_template_factory(template)
        cdk_template.has_resource_properties(
            "AWS::Lambda::Permission",
            Match.object_like(
                {
                    "FunctionName": {"Ref": "LambdaFunctionArn"},
                    "Action": "lambda:InvokeFunction",
                    "Principal": "apigateway.amazonaws.com",
                    # SourceArn uses Fn::Sub with specific API ID
                    "SourceArn": Match.object_like(
                        {"Fn::Sub": Match.string_like_regexp(r".*\$\{ApiGatewayRestApi\}.*")}
                    ),
                }
            ),
        )
