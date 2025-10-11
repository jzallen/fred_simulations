# Architectural Decisions for API Gateway + Lambda Infrastructure

## Overview

This document captures the key architectural decisions made for the FRED-29 implementation of API Gateway + Lambda infrastructure.

## Decision Log

### 1. Lambda Container Image vs. ZIP Package

**Decision**: Use container-based Lambda function (PackageType: Image)

**Rationale**:
- Flask application already containerized with Lambda Web Adapter
- Easier to maintain consistency between local development and Lambda
- Better support for complex dependencies (psycopg2, boto3, etc.)
- No 50MB ZIP package size limit
- Familiar deployment workflow for team

**Trade-offs**:
- Slightly slower cold starts (~200ms additional)
- Requires ECR repository management
- More complex CI/CD pipeline

### 2. API Gateway REST API vs. HTTP API

**Decision**: Use REST API (AWS::ApiGateway::RestApi)

**Rationale**:
- More mature and feature-complete
- Better integration with AWS WAF for security
- Supports resource policies for VPC endpoints
- More granular request/response transformations
- Better CloudWatch metrics and logging
- Usage plans and API keys support

**Trade-offs**:
- Slightly higher cost (~$3.50 per million requests vs. $1.00)
- More complex configuration
- HTTP API has lower latency (~20ms less)

**Note**: HTTP API could be considered for future optimization if cost becomes a concern.

### 3. VPC Integration for Lambda

**Decision**: Deploy Lambda inside VPC with private subnets

**Rationale**:
- Required for direct RDS connection (better security)
- Avoids public RDS endpoint
- Better network isolation
- Supports VPC security groups for fine-grained access control
- Aligns with AWS Well-Architected Framework security pillar

**Trade-offs**:
- Requires NAT Gateway for Lambda to access AWS services (additional cost ~$30/month)
- More complex network configuration
- Potential cold start impact (mitigated by keeping functions warm)

**Configuration Requirements**:
- Use private subnets only (not public)
- Ensure NAT Gateway exists for internet access
- Configure VPC endpoints for S3/DynamoDB if needed (cost optimization)

### 4. Lambda Memory and Timeout Configuration

**Decision**: 3008 MB memory, 60-second timeout

**Rationale**:
- 3GB memory provides ~2 vCPU allocation (optimal for Flask application)
- 60-second timeout accommodates database queries and S3 operations
- Memory allocation affects CPU allocation in Lambda (1769MB = 1 vCPU, 3008MB ≈ 2 vCPU)
- Cost-effective balance between performance and expense

**Benchmarking**:
- Health check: ~50ms
- Job creation: ~200ms
- Complex queries: ~500-1000ms
- S3 presigned URL generation: ~100ms

**Future Optimization**:
- Monitor actual usage with CloudWatch metrics
- Consider reducing to 2048MB if CPU utilization is low
- Use Lambda Power Tuning tool for optimal configuration

### 5. IAM Permissions Model

**Decision**: Separate Lambda execution role with least privilege policies

**Rationale**:
- Follows AWS best practices for IAM
- Granular permissions for each resource type
- Easier to audit and maintain
- Supports compliance requirements

**Permissions Granted**:
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
- S3: PutObject, GetObject, DeleteObject, ListBucket (specific bucket only)
- RDS: DescribeDBInstances, DescribeDBClusters (read-only metadata)
- VPC: CreateNetworkInterface, DescribeNetworkInterfaces, DeleteNetworkInterface
- Managed Policy: AWSLambdaVPCAccessExecutionRole

**Not Granted**:
- RDS data plane access (uses database credentials instead)
- S3 admin operations (PutBucketPolicy, DeleteBucket)
- IAM operations
- KMS operations (not needed for AES256 encryption)

### 6. API Gateway Stage Configuration

**Decision**: Single stage per environment with versioned deployments

**Rationale**:
- Stage name "v1" aligns with API versioning strategy
- Separate deployments for dev/staging/production
- Stage variables support environment-specific configuration
- CloudWatch logging and tracing enabled per stage

**Stage Settings**:
- Development: INFO logging, DataTrace enabled, low throttling
- Staging: INFO logging, DataTrace enabled, moderate throttling
- Production: ERROR logging, DataTrace disabled, high throttling

### 7. CORS Configuration

**Decision**: CORS handled at API Gateway level with OPTIONS methods

**Rationale**:
- Reduces Lambda invocations for preflight requests
- Lower latency for browser requests
- More efficient than handling CORS in application code
- API Gateway mock integration for OPTIONS (no Lambda cost)

**Configuration**:
- Development: Localhost origins (3000, 5000)
- Staging: Staging domain only
- Production: Production domains only
- Headers: Content-Type, X-Amz-Date, Authorization, X-Api-Key
- Methods: GET, POST, OPTIONS

### 8. CloudWatch Logging Strategy

**Decision**: Separate log groups for Lambda and API Gateway with retention policies

**Rationale**:
- Easier troubleshooting with separate log streams
- Different retention periods based on environment
- Development: 7 days (cost optimization)
- Production: 30 days (compliance and debugging)
- Structured logging with request IDs for tracing

**Log Format**:
- API Gateway: Standard access log format with request ID
- Lambda: Application logs with correlation IDs

### 9. Security Group Architecture

**Decision**: Lambda creates its own security group, RDS accepts Lambda SG as source

**Rationale**:
- Decouples Lambda and RDS deployments
- Lambda security group managed within Lambda stack
- RDS security group accepts Lambda SG via ingress rule
- Supports multiple Lambda functions accessing same RDS
- Follows least privilege network access

**Configuration**:
- Lambda SG: Egress to 0.0.0.0/0 on 443 (HTTPS) and 5432 (PostgreSQL)
- RDS SG: Ingress from Lambda SG on 5432

### 10. API Gateway Throttling

**Decision**: Environment-specific throttling limits

**Rationale**:
- Protects backend from abuse
- Different limits for different environments
- Development: 50 req/s, 100 burst
- Staging: 250 req/s, 500 burst
- Production: 1000 req/s, 2000 burst

**Monitoring**:
- CloudWatch alarms for throttling events
- API Gateway usage plans for tracking
- Consider implementing API keys for client-specific limits

### 11. Deployment Dependencies

**Decision**: Explicit stack dependencies in Sceptre configs

**Rationale**:
- Ensures correct deployment order
- Prevents partial deployments
- Clear dependency graph
- Sceptre handles dependency resolution

**Dependency Order**:
1. Lambda Execution Role (no dependencies)
2. Lambda Function (depends on: role, ECR, RDS, S3)
3. API Gateway (depends on: Lambda Function)
4. Lambda Permission (depends on: Lambda Function, API Gateway)
5. API Gateway Deployment (depends on: API Gateway)

### 12. Environment Variable Management

**Decision**: Database password via environment variables, connection details via CloudFormation parameters

**Rationale**:
- Secrets (passwords) not stored in CloudFormation templates
- Connection details derived from stack outputs
- Sceptre environment_variable resolver for runtime secrets
- Supports Secrets Manager migration in future

**Future Enhancement**:
- Migrate to AWS Secrets Manager for password rotation
- Use Lambda environment variable encryption with KMS
- Implement Parameter Store for configuration management

## Rejected Alternatives

### Application Load Balancer + ECS Fargate

**Rejected**: ALB + ECS Fargate instead of API Gateway + Lambda

**Reason**:
- Higher minimum cost (~$20/month for ALB + ~$15/month for Fargate)
- More complex infrastructure management
- Requires container orchestration
- Lambda scales to zero when not in use (cost optimization)
- API Gateway provides built-in features (throttling, API keys, usage plans)

### Lambda Provisioned Concurrency

**Rejected**: Provisioned concurrency for Lambda

**Reason**:
- Additional cost (~$15/month per provisioned instance)
- Development environment doesn't require low latency
- Cold start mitigation can be achieved with keep-warm strategies
- Can be added later if needed for production

### API Gateway Custom Domain

**Deferred**: Custom domain name for API Gateway

**Reason**:
- Not required for MVP
- Requires Route53 hosted zone and certificate
- Can be added post-deployment
- Default API Gateway URL sufficient for development/staging

## Monitoring and Observability

### CloudWatch Metrics

Key metrics to monitor:
- Lambda: Invocations, Duration, Errors, Throttles, ConcurrentExecutions
- API Gateway: Count, Latency, IntegrationLatency, 4XXError, 5XXError
- RDS: DatabaseConnections, CPUUtilization, FreeableMemory

### CloudWatch Alarms (Recommended)

1. Lambda Errors > 10 in 5 minutes
2. API Gateway 5XX errors > 5% of requests
3. API Gateway Latency > 2 seconds (p99)
4. Lambda Duration > 50 seconds (near timeout)
5. RDS CPU > 80% for 5 minutes

### X-Ray Tracing

- Enabled on API Gateway stage
- Lambda automatic instrumentation
- Distributed tracing for request flow

## Cost Optimization Strategies

1. **Lambda Memory Tuning**: Use Lambda Power Tuning tool to find optimal memory allocation
2. **VPC Endpoints**: Add VPC endpoints for S3 to avoid NAT Gateway data transfer charges
3. **CloudWatch Log Retention**: Reduce retention in non-production environments
4. **API Gateway Caching**: Consider enabling caching for read-heavy endpoints
5. **Reserved Concurrency**: Set reserved concurrency to prevent runaway costs

## Security Considerations

1. **Secrets Management**: Migrate to AWS Secrets Manager for password rotation
2. **API Gateway Authorizer**: Add Lambda authorizer or Cognito for authentication
3. **WAF Integration**: Add AWS WAF for DDoS and application-layer protection
4. **VPC Flow Logs**: Enable VPC flow logs for network analysis
5. **CloudTrail**: Enable CloudTrail for API auditing

## Future Enhancements

1. **Multi-Region Deployment**: Add Route53 and cross-region replication
2. **Blue-Green Deployments**: Use Lambda aliases and weighted routing
3. **API Versioning**: Support multiple API versions (v1, v2) with routing
4. **GraphQL API**: Consider AppSync for more flexible API layer
5. **Event-Driven Architecture**: Add EventBridge for async processing

## Compliance and Governance

- All resources tagged with Environment, Service, Component
- Cost allocation tags for chargeback
- CloudFormation drift detection enabled
- Automated compliance checks with AWS Config
- Backup policies for RDS and S3

## References

- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [API Gateway Best Practices](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter)
