"""
Tests for AWS Batch infrastructure CloudFormation template.

Validates that the batch-infrastructure.json template:
- Is valid JSON
- Defines all required resources
- Has correct IAM trust policies
- Configures compute environment with correct instance types
- Uses SPOT instances for cost optimization
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def template():
    """Load the Batch infrastructure CloudFormation template."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "templates"
        / "batch"
        / "batch-infrastructure.json"
    )
    with open(template_path) as f:
        return json.load(f)


def test_template_is_valid_json():
    """Template should be valid JSON format."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "templates"
        / "batch"
        / "batch-infrastructure.json"
    )
    with open(template_path) as f:
        data = json.load(f)

    assert data is not None
    assert "AWSTemplateFormatVersion" in data
    assert data["AWSTemplateFormatVersion"] == "2010-09-09"


def test_template_has_description(template):
    """Template should have a description."""
    assert "Description" in template
    assert "AWS Batch" in template["Description"]
    assert "FRED" in template["Description"]


def test_template_defines_required_parameters(template):
    """Template should define all required parameters."""
    required_params = {
        "Environment",
        "VpcId",
        "SubnetIds",
        "ECRRepositoryUri",
        "DatabaseSecretArn",
        "UploadBucketName",
        "ResultsBucketName",
        "MaxvCpus",
        "LogRetentionDays",
        "SpotBidPercentage",
    }

    assert "Parameters" in template
    params = set(template["Parameters"].keys())
    assert required_params.issubset(params), f"Missing parameters: {required_params - params}"


def test_template_has_environment_allowed_values(template):
    """Environment parameter should restrict to dev/staging/production."""
    env_param = template["Parameters"]["Environment"]
    assert "AllowedValues" in env_param
    assert set(env_param["AllowedValues"]) == {"dev", "staging", "production"}


def test_template_defines_all_iam_roles(template):
    """Template should define all four IAM roles."""
    required_roles = {
        "BatchServiceRole",
        "BatchInstanceRole",
        "BatchExecutionRole",
        "BatchJobRole",
    }

    resources = template["Resources"]
    iam_roles = {
        name for name, resource in resources.items() if resource["Type"] == "AWS::IAM::Role"
    }

    assert required_roles.issubset(
        iam_roles
    ), f"Missing IAM roles: {required_roles - iam_roles}"


def test_batch_service_role_has_correct_trust_policy(template):
    """BatchServiceRole should trust batch.amazonaws.com."""
    role = template["Resources"]["BatchServiceRole"]
    trust_policy = role["Properties"]["AssumeRolePolicyDocument"]

    assert trust_policy["Version"] == "2012-10-17"
    statements = trust_policy["Statement"]
    assert len(statements) == 1

    stmt = statements[0]
    assert stmt["Effect"] == "Allow"
    assert stmt["Principal"]["Service"] == "batch.amazonaws.com"
    assert stmt["Action"] == "sts:AssumeRole"


def test_batch_instance_role_has_correct_trust_policy(template):
    """BatchInstanceRole should trust ec2.amazonaws.com."""
    role = template["Resources"]["BatchInstanceRole"]
    trust_policy = role["Properties"]["AssumeRolePolicyDocument"]

    statements = trust_policy["Statement"]
    assert len(statements) == 1

    stmt = statements[0]
    assert stmt["Effect"] == "Allow"
    assert stmt["Principal"]["Service"] == "ec2.amazonaws.com"
    assert stmt["Action"] == "sts:AssumeRole"


def test_batch_execution_role_has_correct_trust_policy(template):
    """BatchExecutionRole should trust ecs-tasks.amazonaws.com."""
    role = template["Resources"]["BatchExecutionRole"]
    trust_policy = role["Properties"]["AssumeRolePolicyDocument"]

    statements = trust_policy["Statement"]
    assert len(statements) == 1

    stmt = statements[0]
    assert stmt["Effect"] == "Allow"
    assert stmt["Principal"]["Service"] == "ecs-tasks.amazonaws.com"
    assert stmt["Action"] == "sts:AssumeRole"


def test_batch_job_role_has_correct_trust_policy(template):
    """BatchJobRole should trust ecs-tasks.amazonaws.com."""
    role = template["Resources"]["BatchJobRole"]
    trust_policy = role["Properties"]["AssumeRolePolicyDocument"]

    statements = trust_policy["Statement"]
    assert len(statements) == 1

    stmt = statements[0]
    assert stmt["Effect"] == "Allow"
    assert stmt["Principal"]["Service"] == "ecs-tasks.amazonaws.com"
    assert stmt["Action"] == "sts:AssumeRole"


def test_batch_service_role_has_managed_policy(template):
    """BatchServiceRole should have AWSBatchServiceRole managed policy."""
    role = template["Resources"]["BatchServiceRole"]
    managed_policies = role["Properties"]["ManagedPolicyArns"]

    assert len(managed_policies) == 1
    assert "AWSBatchServiceRole" in managed_policies[0]


def test_batch_instance_role_has_ecs_policy(template):
    """BatchInstanceRole should have ECS container service policy."""
    role = template["Resources"]["BatchInstanceRole"]
    managed_policies = role["Properties"]["ManagedPolicyArns"]

    assert len(managed_policies) == 1
    assert "AmazonEC2ContainerServiceforEC2Role" in managed_policies[0]


def test_batch_job_role_has_s3_permissions(template):
    """BatchJobRole should have separate read and write S3 policies."""
    role = template["Resources"]["BatchJobRole"]
    policies = role["Properties"]["Policies"]

    policy_names = {p["PolicyName"] for p in policies}
    assert "S3UploadsReadAccess" in policy_names
    assert "S3ResultsWriteAccess" in policy_names


def test_batch_compute_environment_uses_spot_instances(template):
    """Compute environment should use SPOT instances for cost savings."""
    compute_env = template["Resources"]["BatchComputeEnvironment"]
    compute_resources = compute_env["Properties"]["ComputeResources"]

    assert compute_resources["Type"] == "SPOT"
    assert compute_resources["AllocationStrategy"] == "SPOT_CAPACITY_OPTIMIZED"


def test_compute_environment_uses_correct_instance_types(template):
    """Compute environment should use c5.xlarge and c5.2xlarge (compute-optimized)."""
    compute_env = template["Resources"]["BatchComputeEnvironment"]
    compute_resources = compute_env["Properties"]["ComputeResources"]

    instance_types = compute_resources["InstanceTypes"]
    assert "c5.xlarge" in instance_types
    assert "c5.2xlarge" in instance_types


def test_compute_environment_scales_to_zero(template):
    """Compute environment should scale to zero when idle."""
    compute_env = template["Resources"]["BatchComputeEnvironment"]
    compute_resources = compute_env["Properties"]["ComputeResources"]

    assert compute_resources["MinvCpus"] == 0
    assert compute_resources["DesiredvCpus"] == 0


def test_batch_job_definition_configures_resources_correctly(template):
    """Job definition should allocate 4 vCPUs and 8192 MB for FRED simulations."""
    job_def = template["Resources"]["BatchJobDefinition"]
    container_props = job_def["Properties"]["ContainerProperties"]

    assert container_props["Vcpus"] == 4
    assert container_props["Memory"] == 8192


def test_job_definition_uses_ec2_platform(template):
    """Job definition should use EC2 platform (not Fargate)."""
    job_def = template["Resources"]["BatchJobDefinition"]
    platform = job_def["Properties"]["PlatformCapabilities"]

    assert platform == ["EC2"]


def test_job_definition_has_retry_strategy(template):
    """Job definition should have retry strategy for Spot interruptions."""
    job_def = template["Resources"]["BatchJobDefinition"]
    retry_strategy = job_def["Properties"]["RetryStrategy"]

    assert retry_strategy["Attempts"] == 3
    assert "EvaluateOnExit" in retry_strategy


def test_job_definition_configures_cloudwatch_logs(template):
    """Job definition should configure CloudWatch Logs."""
    job_def = template["Resources"]["BatchJobDefinition"]
    log_config = job_def["Properties"]["ContainerProperties"]["LogConfiguration"]

    assert log_config["LogDriver"] == "awslogs"
    assert "awslogs-group" in log_config["Options"]
    assert "awslogs-region" in log_config["Options"]


def test_security_group_allows_https_egress(template):
    """Security group should allow outbound HTTPS for S3, ECR, Secrets Manager."""
    sg = template["Resources"]["BatchSecurityGroup"]
    egress_rules = sg["Properties"]["SecurityGroupEgress"]

    https_rules = [r for r in egress_rules if r["FromPort"] == 443 and r["ToPort"] == 443]
    assert len(https_rules) > 0
    assert https_rules[0]["IpProtocol"] == "tcp"


def test_security_group_allows_postgres_egress(template):
    """Security group should allow outbound PostgreSQL access."""
    sg = template["Resources"]["BatchSecurityGroup"]
    egress_rules = sg["Properties"]["SecurityGroupEgress"]

    postgres_rules = [
        r for r in egress_rules if r["FromPort"] == 5432 and r["ToPort"] == 5432
    ]
    assert len(postgres_rules) > 0
    assert postgres_rules[0]["IpProtocol"] == "tcp"


def test_cloudwatch_log_group_created(template):
    """Template should create CloudWatch Logs group."""
    assert "BatchLogGroup" in template["Resources"]
    log_group = template["Resources"]["BatchLogGroup"]
    assert log_group["Type"] == "AWS::Logs::LogGroup"


def test_template_exports_all_required_outputs(template):
    """Template should export ARNs and names for use by other stacks."""
    required_outputs = {
        "BatchServiceRoleArn",
        "BatchInstanceRoleArn",
        "BatchExecutionRoleArn",
        "BatchJobRoleArn",
        "BatchSecurityGroupId",
        "BatchLogGroupName",
        "BatchComputeEnvironmentArn",
        "BatchJobQueueArn",
        "BatchJobQueueName",
        "BatchJobDefinitionArn",
    }

    outputs = set(template["Outputs"].keys())
    assert required_outputs.issubset(outputs), f"Missing outputs: {required_outputs - outputs}"


def test_outputs_have_exports(template):
    """All outputs should have Export names for cross-stack references."""
    outputs = template["Outputs"]

    for output_name, output_config in outputs.items():
        assert "Export" in output_config, f"Output {output_name} missing Export"
        assert "Name" in output_config["Export"], f"Output {output_name} missing Export.Name"


def test_instance_profile_references_instance_role(template):
    """Instance profile should reference the instance role."""
    instance_profile = template["Resources"]["BatchInstanceProfile"]
    roles = instance_profile["Properties"]["Roles"]

    assert len(roles) == 1
    assert roles[0] == {"Ref": "BatchInstanceRole"}


def test_compute_environment_references_service_role(template):
    """Compute environment should reference the service role."""
    compute_env = template["Resources"]["BatchComputeEnvironment"]
    service_role_arn = compute_env["Properties"]["ServiceRole"]

    assert service_role_arn == {"Fn::GetAtt": ["BatchServiceRole", "Arn"]}


def test_job_queue_references_compute_environment(template):
    """Job queue should reference the compute environment."""
    job_queue = template["Resources"]["BatchJobQueue"]
    compute_env_order = job_queue["Properties"]["ComputeEnvironmentOrder"]

    assert len(compute_env_order) == 1
    assert compute_env_order[0]["Order"] == 1
    assert compute_env_order[0]["ComputeEnvironment"] == {"Ref": "BatchComputeEnvironment"}


def test_all_resources_have_tags(template):
    """All resources that support tagging should have Environment tag."""
    taggable_resources = [
        "BatchServiceRole",
        "BatchInstanceRole",
        "BatchExecutionRole",
        "BatchJobRole",
        "BatchSecurityGroup",
        "BatchLogGroup",
    ]

    for resource_name in taggable_resources:
        resource = template["Resources"][resource_name]
        assert "Tags" in resource["Properties"], f"{resource_name} missing Tags"


def test_batch_job_role_has_secrets_manager_access(template):
    """BatchJobRole should have permission to read database secrets."""
    role = template["Resources"]["BatchJobRole"]
    policies = role["Properties"]["Policies"]

    secrets_policies = [p for p in policies if "SecretsManager" in p["PolicyName"]]
    assert len(secrets_policies) > 0

    policy_doc = secrets_policies[0]["PolicyDocument"]
    statements = policy_doc["Statement"]
    actions = statements[0]["Action"]

    assert "secretsmanager:GetSecretValue" in actions


def test_job_definition_sets_required_environment_variables(template):
    """Job definition should set FRED_HOME and other required env vars."""
    job_def = template["Resources"]["BatchJobDefinition"]
    env_vars = job_def["Properties"]["ContainerProperties"]["Environment"]

    env_names = {e["Name"] for e in env_vars}
    required_vars = {
        "FRED_HOME",
        "AWS_REGION",
        "S3_UPLOAD_BUCKET",
        "S3_RESULTS_BUCKET",
        "DATABASE_SECRET_ARN",
        "ENVIRONMENT",
    }

    assert required_vars.issubset(env_names), f"Missing env vars: {required_vars - env_names}"


def test_job_definition_has_timeout(template):
    """Job definition should have timeout configured."""
    job_def = template["Resources"]["BatchJobDefinition"]
    timeout = job_def["Properties"]["Timeout"]

    assert "AttemptDurationSeconds" in timeout
    assert timeout["AttemptDurationSeconds"] == 14400  # 4 hours
