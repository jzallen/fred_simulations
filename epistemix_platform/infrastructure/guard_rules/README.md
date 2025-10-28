# CloudFormation Guard Rules

This directory contains policy-as-code rules written in AWS CloudFormation Guard DSL for validating infrastructure templates against organizational policies.

## Overview

**CloudFormation Guard** is a policy-as-code evaluation tool from AWS that validates JSON and YAML formatted data (like CloudFormation templates) against rules you define using a declarative DSL.

- **Official Documentation**: https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html
- **GitHub Repository**: https://github.com/aws-cloudformation/cloudformation-guard
- **License**: Apache 2.0 (FOSS)

## Directory Structure

```
guard_rules/
├── README.md (this file)
├── s3/                 # S3 bucket security policies
├── ecr/                # ECR repository policies
├── rds/                # RDS database policies
├── lambda/             # Lambda function policies
├── api_gateway/        # API Gateway policies
└── ec2/                # EC2 instance policies
```

## Guard DSL Basics

### Basic Rule Structure

```
rule rule_name {
    # Select resources to validate
    let resources = Resources.*[ Type == 'AWS::S3::Bucket' ]

    # Only apply rule when resources exist
    when %resources !empty {
        # Assertions
        %resources.Properties.BucketEncryption exists
    }
}
```

### Common Patterns

#### 1. Check Property Exists

```
rule s3_encryption_enabled {
    let buckets = Resources.*[ Type == 'AWS::S3::Bucket' ]
    when %buckets !empty {
        %buckets.Properties.BucketEncryption exists
    }
}
```

#### 2. Check Property Value

```
rule rds_not_public {
    let rds_instances = Resources.*[ Type == 'AWS::RDS::DBInstance' ]
    when %rds_instances !empty {
        %rds_instances.Properties.PubliclyAccessible == false
    }
}
```

#### 3. Check Property in List

```
rule encryption_algorithm_valid {
    let buckets = Resources.*[ Type == 'AWS::S3::Bucket' ]
    when %buckets !empty {
        %buckets.Properties.BucketEncryption.ServerSideEncryptionConfiguration[*] {
            ServerSideEncryptionByDefault.SSEAlgorithm in ['AES256', 'aws:kms']
        }
    }
}
```

#### 4. Nested Property Assertions

```
rule public_access_blocked {
    let buckets = Resources.*[ Type == 'AWS::S3::Bucket' ]
    when %buckets !empty {
        %buckets.Properties.PublicAccessBlockConfiguration {
            BlockPublicAcls == true
            BlockPublicPolicy == true
            IgnorePublicAcls == true
            RestrictPublicBuckets == true
        }
    }
}
```

#### 5. Custom Error Messages

```
rule s3_encryption_enabled {
    let buckets = Resources.*[ Type == 'AWS::S3::Bucket' ]

    when %buckets !empty {
        %buckets.Properties.BucketEncryption exists <<
            Violation: S3 bucket must have encryption enabled
            Fix: Add BucketEncryption configuration with AES256 or aws:kms
        >>
    }
}
```

## Running Guard Validation

### Command Line

```bash
# Validate template against rules
cfn-guard validate \
  --data templates/s3/s3-upload-bucket.json \
  --rules guard_rules/s3/s3_security_rules.guard

# Validate multiple templates
cfn-guard validate \
  --data templates/ \
  --rules guard_rules/

# Show test mode (detailed output)
cfn-guard validate \
  --data template.json \
  --rules rules.guard \
  --show-summary all
```

### In Python Tests

```python
import subprocess
from pathlib import Path

def test_template_passes_guard_policies(template_path, rules_path):
    """Verify template passes organizational policies."""
    result = subprocess.run(
        ['cfn-guard', 'validate',
         '--data', str(template_path),
         '--rules', str(rules_path)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Policy violations:\n{result.stdout}"
```

## Writing Effective Rules

### Best Practices

1. **One Rule Per Policy** - Keep rules focused on a single concern
2. **Clear Names** - Use descriptive rule names (`s3_encryption_enabled` not `rule1`)
3. **Custom Messages** - Always provide violation messages with fix guidance
4. **Guard Clauses** - Use `when` to skip rules when resources don't exist
5. **Reusable** - Write generic rules that work across templates

### Testing Rules

Test rules in isolation before using in test suite:

```bash
# Test rule against known-good template (should pass)
cfn-guard validate \
  --data templates/s3/s3-upload-bucket.json \
  --rules guard_rules/s3/s3_security_rules.guard

# Test rule against template missing encryption (should fail)
cfn-guard validate \
  --data test_fixtures/s3_no_encryption.json \
  --rules guard_rules/s3/s3_security_rules.guard
```

## Rule Organization

### Template-Specific Rules

Each resource type has its own directory with security-focused rules:

- **s3/s3_security_rules.guard** - Encryption, public access, versioning
- **ecr/ecr_security_rules.guard** - Image scanning, encryption
- **rds/rds_security_rules.guard** - Public access, encryption, backups
- **lambda/lambda_security_rules.guard** - IAM roles, VPC, environment vars
- **api_gateway/api_gateway_security_rules.guard** - CORS, throttling, logging
- **ec2/ec2_security_rules.guard** - Security groups, IAM profiles

### Cross-Cutting Rules (Future)

Create shared rules for organization-wide policies:

- **common/tagging_rules.guard** - Required tags (Environment, Project, ManagedBy)
- **common/naming_rules.guard** - Resource naming conventions
- **common/encryption_rules.guard** - Encryption at rest requirements

## Resources

- [Guard Language Specification](https://docs.aws.amazon.com/cfn-guard/latest/ug/clauses.html)
- [Guard Examples](https://github.com/aws-cloudformation/cloudformation-guard/tree/main/guard-examples)
- [Writing Guard Rules](https://docs.aws.amazon.com/cfn-guard/latest/ug/writing-rules.html)
- [Guard Rule Gen](https://docs.aws.amazon.com/cfn-guard/latest/ug/rule-gen.html) - Generate rules from templates

## Installation

### Download Binary

```bash
# Linux x86_64
curl -LO https://github.com/aws-cloudformation/cloudformation-guard/releases/download/3.0.0/cfn-guard-linux-x86_64.tar.gz
tar -xzf cfn-guard-linux-x86_64.tar.gz
sudo mv cfn-guard /usr/local/bin/
cfn-guard --version
```

### Or use Installation Script

```bash
curl --proto '=https' --tlsv1.2 -sSf \
  https://raw.githubusercontent.com/aws-cloudformation/cloudformation-guard/main/install-guard.sh | sh
```

### Pants Integration (Future)

We plan to manage cfn-guard as a Pants-managed binary in the future. For now, install manually.

## Suppressing Findings

Guard doesn't have built-in suppression like cfn-nag. To skip specific rules:

1. **Comment out the rule** in the .guard file (not ideal)
2. **Use conditional logic** to skip resources:

```
rule s3_encryption_enabled {
    let buckets = Resources.*[ Type == 'AWS::S3::Bucket' ]
    let buckets_requiring_encryption = %buckets[ Tags[?Key == 'SkipEncryption'] empty ]

    when %buckets_requiring_encryption !empty {
        %buckets_requiring_encryption.Properties.BucketEncryption exists
    }
}
```

3. **Document exceptions** in comments within the rule file
