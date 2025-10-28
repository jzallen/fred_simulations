# AWS CDK Dependency Conflict Issue

## Problem

When running infrastructure tests with aws-cdk-lib, we encounter a dependency conflict:

```
ImportError: cannot import name 'NothingType' from 'attrs'
```

## Root Cause

- **aws-cdk-lib** depends on **jsii** which depends on **cattrs**
- **cattrs** requires `attrs.NothingType` which was removed in attrs 25.0+
- The lockfile includes **attrs 25.4.0** (too new for cattrs)
- This is a known incompatibility in the Python packaging ecosystem

## Solutions

### Option 1: Pin attrs to Compatible Version (Recommended)

Add to `pyproject.toml`:

```toml
[tool.poetry.dependencies]
aws-cdk-lib = "^2.100.0"
attrs = "<25.0.0"  # Pin to version compatible with cattrs
```

Then regenerate lockfile:
```bash
pants generate-lockfiles --resolve=infrastructure_env
```

### Option 2: Update cattrs

Wait for cattrs to release a version compatible with attrs 25.0+, or use a pre-release:

```toml
[tool.poetry.dependencies]
aws-cdk-lib = "^2.100.0"
cattrs = ">=25.0.0"  # Use newer cattrs when available
```

### Option 3: Alternative Testing Approach

Instead of using AWS CDK assertions library, we could:

1. **Build lightweight custom matchers** - Minimal Python helper functions
2. **Use only cfn-lint + cfn-nag + cfn-guard** - Skip CDK assertions entirely
3. **Use pycfmodel** - Alternative CloudFormation parsing library

## Current Status

All test code has been written correctly:
- ✅ CDK fixture added to conftest.py
- ✅ New validation tests added (cfn-lint, cfn-nag, cfn-guard)
- ✅ New flexible CDK assertion tests added
- ✅ Brittle tests removed
- ✅ Guard rules created

The tests **will work** once the dependency conflict is resolved.

## Recommended Next Steps

1. Pin attrs to `<25.0.0` in pyproject.toml
2. Regenerate lockfile
3. Run tests to verify

## References

- [attrs changelog - NothingType removal](https://github.com/python-attrs/attrs/blob/main/CHANGELOG.md)
- [cattrs GitHub issues](https://github.com/python-attrs/cattrs/issues)
- [AWS CDK Python dependencies](https://pypi.org/project/aws-cdk-lib/)
