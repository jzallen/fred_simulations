# RDS Security Configuration

## Overview
The RDS PostgreSQL instance is configured with layered security controls to prevent unauthorized access while maintaining developer productivity.

## Security Features

### Network Security
- **No public internet access** (0.0.0.0/0) - removed the security vulnerability
- **VPC-restricted access** - allows connections only from:
  - Default VPC CIDR (172.31.0.0/16) for future Kubernetes workloads
  - Specific developer IPs (when configured)
- **Security group ingress rules** are created conditionally based on parameters

### Current Configuration

#### For Developers
1. Get your current IP address:
   ```bash
   curl ifconfig.me
   ```

2. Update the Sceptre config (`infrastructure/config/dev/rds-postgres.yaml`):
   ```yaml
   parameters:
     DeveloperIP: "YOUR.IP.ADDRESS/32"  # e.g., "203.0.113.45/32"
     EnableVPCAccess: "true"  # Keep enabled for K8s
   ```

3. Deploy the update:
   ```bash
   cd epistemix_platform/infrastructure
   sceptre update dev/rds-postgres
   ```

#### For Kubernetes/ECS
- Automatically allowed via VPC CIDR (172.31.0.0/16)
- No additional configuration needed for pods/tasks in the same VPC

### Access Methods

#### Direct Connection (from allowed IPs)
```bash
psql "postgresql://epistemixuser:PASSWORD@<rds-endpoint>:5432/epistemixdb"
```

#### Via Session Manager (no IP configuration needed)
1. Launch an EC2 instance in the same VPC
2. Connect via Session Manager:
   ```bash
   aws ssm start-session --target <instance-id>
   ```
3. Connect to RDS from the instance

### Security Levels by Environment

| Environment | PubliclyAccessible | Allowed IPs | Recommended Access |
|------------|-------------------|-------------|-------------------|
| Development | true | Developer IP + VPC | Direct or Session Manager |
| Staging | true | VPC only | Session Manager or VPN |
| Production | false | VPC only | Private subnets + VPN |

### Future Enhancements

1. **IAM Database Authentication** (planned)
   - Eliminate password management
   - Use temporary tokens
   - Integrate with K8s service accounts

2. **AWS Secrets Manager Rotation** (planned)
   - Automatic password rotation
   - Already storing credentials in Secrets Manager

3. **VPC PrivateLink** (for production)
   - Complete network isolation
   - No public IP address

### Troubleshooting

#### Cannot connect from laptop
1. Verify your IP is correctly set in `DeveloperIP` parameter
2. Check if your IP has changed (ISPs often use dynamic IPs)
3. Ensure the security group was updated after parameter change

#### Connection from Kubernetes fails
1. Verify pods are running in the default VPC
2. Check that `EnableVPCAccess` is set to "true"
3. Confirm the VPC CIDR is 172.31.0.0/16 (default VPC)

### Security Best Practices
- Never use 0.0.0.0/0 in production
- Regularly review and remove unused IP allowlist entries
- Use IAM roles instead of passwords where possible
- Enable CloudTrail logging for RDS API calls
- Use encrypted connections (SSL/TLS) in production