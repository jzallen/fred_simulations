# Advanced Topics

## When to Read This

Read this reference when you need to understand:
- Test batching configuration and trade-offs
- Multiple Python dependency resolves (resolves)
- CI/CD pipeline optimization
- Using `--changed-since` effectively
- Advanced dependency management
- Performance tuning and troubleshooting

## Test Batching

### Default Behavior: One Process Per File

By default, Pants runs **each test file in a separate process**.

**Example:**
```bash
pants test epistemix_platform:src-tests
# If src-tests has 20 test files, Pants spawns 20 processes
```

**Pros:**
- **Fine-grained caching**: Each file cached independently
- **Better parallelism**: Distributes work across all CPU cores
- **Isolation**: Test failures don't affect other files

**Cons:**
- **Fixture overhead**: Package/session-scoped fixtures execute per file
- **Setup costs**: Each process pays interpreter startup cost

### When Fixtures Are Expensive

If you have expensive session/package-scoped fixtures:

```python
# conftest.py
@pytest.fixture(scope="session")
def database():
    """Set up test database - expensive operation."""
    db = create_test_database()
    run_migrations(db)
    seed_test_data(db)
    yield db
    teardown_database(db)
```

**Default behavior:** This fixture runs **once per test file**, not once per test suite.

### Enabling Test Batching

Mark tests as batch-compatible:

```python
python_tests(
    name="src-tests",
    sources=["tests/**/*.py"],
    batch_compatibility_tag="expensive-fixtures",
)
```

Configure batch size in `pants.toml`:

```toml
[test]
batch_size = 10
```

**Behavior:**
- Tests are grouped into batches of 10 files
- Each batch runs in single pytest process
- Session-scoped fixtures run once per batch

### Batching Trade-offs

**Benefits:**
- Session fixtures run less frequently
- Reduced process overhead
- Lower memory usage

**Costs:**
- **Coarser caching**: If any file in batch changes, entire batch re-runs
- **Less parallelism**: Fewer processes to distribute across CPUs
- **Potential coupling**: Tests in same batch share process state

### Optimal Batch Size

**Small batches (5-10 files):**
- Better cache granularity
- More parallelism
- More fixture executions

**Large batches (20-50 files):**
- Fewer fixture executions
- Coarser cache granularity
- Less parallelism

**Recommendation:** Start with 10 and adjust based on:
- Fixture setup cost
- Number of test files
- Available CPU cores

### Example Configuration

```python
# Fast unit tests - don't batch (default)
python_tests(
    name="unit-tests",
    sources=["tests/unit/**/*.py"],
    # No batch_compatibility_tag - runs one file per process
)

# Integration tests with expensive database fixture - batch them
python_tests(
    name="integration-tests",
    sources=["tests/integration/**/*.py"],
    batch_compatibility_tag="database-tests",
)
```

```toml
# pants.toml
[test]
batch_size = 15  # 15 files per batch for tagged tests
```

## Multiple Python Resolves

### What is a Resolve?

A **resolve** is a set of Python dependencies with a dedicated lockfile.

Think of it as an **isolated Python environment** for a specific purpose.

### Why Multiple Resolves?

**Separation of Concerns:**
- Application code dependencies
- Infrastructure/deployment tools
- Developer tools

**Example from this project:**

```toml
[python.resolves]
epistemix_platform_env = "epistemix_platform/epistemix_platform_env.lock"
infrastructure_env = "epistemix_platform/infrastructure/infrastructure_env.lock"
tcr_env = "tcr/tcr_env.lock"
```

**Use cases:**

1. **epistemix_platform_env**: Flask, SQLAlchemy, Pydantic, pytest
   - Main application dependencies
   - Used by most targets

2. **infrastructure_env**: Sceptre, Boto3, CloudFormation templates
   - Infrastructure deployment tools
   - Only used by infrastructure tests and scripts

3. **tcr_env**: Specific dependencies for TCR tool
   - Isolated from main application
   - No risk of version conflicts

### Benefits of Separation

**1. Avoid Dependency Conflicts**
```
epistemix_platform_env: Boto3 1.28.0 (stable, application needs)
infrastructure_env: Boto3 1.34.0 (latest, infrastructure tools need)
```

No conflict! Each resolve has its own version.

**2. Smaller Lockfiles**
- `epistemix_platform_env.lock`: ~200 dependencies
- `infrastructure_env.lock`: ~50 dependencies
- `tcr_env.lock`: ~10 dependencies

Smaller lockfiles = faster dependency resolution.

**3. Clearer Dependencies**

```python
# Application test - uses epistemix_platform_env
python_tests(
    name="src-tests",
    sources=["tests/**/*.py"],
    resolve="epistemix_platform_env",
)

# Infrastructure test - uses infrastructure_env
python_tests(
    name="infrastructure-tests",
    sources=["infrastructure/tests/**/*.py"],
    resolve="infrastructure_env",
)
```

**Clear separation:** Application tests can't accidentally import infrastructure tools.

### Working with Resolves

#### Generating Lockfiles

```bash
# Generate all lockfiles
pants generate-lockfiles

# Generate specific resolve
pants generate-lockfiles --resolve=epistemix_platform_env
pants generate-lockfiles --resolve=infrastructure_env
pants generate-lockfiles --resolve=tcr_env
```

**When to regenerate:**
- After adding dependencies to requirements.txt
- After updating dependency versions
- After resolving conflicts

#### Exporting Resolves

```bash
# Export for IDE/editor
pants export --resolve=epistemix_platform_env

# Export all resolves
pants export
```

**Output:** Virtual environment in `dist/export/python/virtualenvs/`

**Use case:** Configure IDE to use exported virtualenv for autocomplete and type checking.

#### Specifying Resolve in Targets

```python
# Uses default resolve (epistemix_platform_env)
python_tests(
    name="src-tests",
    sources=["tests/**/*.py"],
)

# Explicitly uses infrastructure_env
python_tests(
    name="infrastructure-tests",
    sources=["infrastructure/tests/**/*.py"],
    resolve="infrastructure_env",
)

# Uses tcr_env
pex_binary(
    name="tcr-cli",
    entry_point="tcr.cli:main",
    resolve="tcr_env",
)
```

### Default Resolve

Configure in `pants.toml`:

```toml
[python]
default_resolve = "epistemix_platform_env"
```

Targets without explicit `resolve=` field use the default.

## CI/CD Pipeline Optimization

### Using --changed-since

The `--changed-since` flag tells Pants to only process targets affected by changes.

**Syntax:**
```bash
pants test --changed-since=COMMIT_REF
```

**Examples:**
```bash
# Test code affected by changes since main branch
pants test --changed-since=main

# Test code affected by changes since origin/main
pants test --changed-since=origin/main

# Test code affected by last commit
pants test --changed-since=HEAD~1

# Test code affected by last 5 commits
pants test --changed-since=HEAD~5
```

### How --changed-since Works

**1. Pants Determines Changed Files**

```bash
git diff --name-only main...HEAD
```

**2. Pants Finds Affected Targets**

For each changed file, Pants:
- Finds targets that **own** the file
- Finds targets that **depend on** those targets
- Builds transitive dependency graph

**3. Pants Runs Only Affected Targets**

Only runs tests/builds for targets in the affected set.

### CI/CD Example Workflow

**Branch Build:**
```bash
# In CI, test only code changed in this branch
pants test --changed-since=origin/main
pants lint --changed-since=origin/main
```

**Main Build:**
```bash
# On main branch, run everything to warm cache
pants test ::
pants lint ::
```

### Advanced --changed-since Usage

**Multiple Goals:**
```bash
# Test and lint changed code
pants test lint --changed-since=main
```

**Specific Commit Range:**
```bash
# Test changes between two commits
pants test --changed-since=abc123f
```

**With Tag:**
```bash
# Test slow tests only if affected by changes
pants test --changed-since=main --tag=slow
```

### Cache Benefits in CI

When using remote cache:

**Developer Workflow:**
```bash
# Local: Run tests, upload to remote cache
pants test epistemix_platform:src-tests
```

**CI Pipeline:**
```bash
# CI: Download from remote cache, only run affected tests
pants test --changed-since=origin/main
```

**Result:** CI builds are much faster because:
1. Unchanged tests use remote cache from local dev
2. Only changed tests actually execute

## Dependency Management

### Viewing Dependencies

```bash
# Direct dependencies
pants dependencies epistemix_platform:src-tests

# Transitive dependencies (everything it depends on)
pants dependencies --transitive epistemix_platform:src-tests

# Reverse dependencies (what depends on this)
pants dependents epistemix_platform/src:lib
```

### Dependency Inference

Pants automatically infers dependencies from imports:

```python
# epistemix_platform/tests/test_models.py
from epistemix_platform.models.user import User
from epistemix_platform.repositories import IUserRepository
```

**Pants automatically adds:**
- `epistemix_platform/models:lib` (owns user.py)
- `epistemix_platform/repositories:lib` (owns IUserRepository)

**No manual BUILD file updates needed!**

### Override Inference

Sometimes you need explicit dependencies:

```python
python_tests(
    name="src-tests",
    sources=["tests/**/*.py"],
    dependencies=[
        # Explicit dependency not inferred from imports
        "./test_data:fixtures",
    ],
)
```

### Excluding Dependencies

```python
python_tests(
    name="src-tests",
    sources=["tests/**/*.py"],
    dependencies=[
        # Include all inferred dependencies EXCEPT this one
        "!./optional_module:lib",
    ],
)
```

## Performance Tuning

### Parallelism

Configure CPU usage:

```toml
# pants.toml
[GLOBAL]
process_execution_local_parallelism = 8  # Use 8 cores
```

Or via command line:
```bash
pants --process-execution-local-parallelism=8 test ::
```

**Default:** Uses all available CPU cores.

**When to adjust:**
- Lower on shared machines (be a good citizen)
- Higher on powerful machines with many cores

### Test Timeouts

Set reasonable timeouts to catch hanging tests:

```python
python_tests(
    name="unit-tests",
    sources=["tests/unit/**/*.py"],
    timeout=60,  # 1 minute
)

python_tests(
    name="integration-tests",
    sources=["tests/integration/**/*.py"],
    timeout=300,  # 5 minutes
)
```

**Default:** 60 seconds

**Adjustment:**
- Lower for fast unit tests (30s)
- Higher for slow integration tests (300-600s)

### Cache Directory Location

Move cache to faster disk:

```toml
# pants.toml
[GLOBAL]
local_store_dir = "/mnt/fast-ssd/.cache/pants"
```

**Use case:** If home directory is on slow NFS, use local SSD for cache.

### Logging and Debug

Enable verbose logging:

```bash
# Debug level
pants --level=debug test epistemix_platform:src-tests

# Show all processes
pants --print-stacktrace test epistemix_platform:src-tests
```

## Advanced Target Patterns

### Exclude Patterns

```bash
# Run all tests except slow ones
pants test :: --filter-target-type=python_tests --tag='-slow'

# Test everything except infrastructure
pants test :: '!epistemix_platform:infrastructure-tests'
```

### Tag-Based Filtering

Add tags to targets:

```python
python_tests(
    name="slow-integration-tests",
    sources=["tests/slow/**/*.py"],
    tags=["slow", "integration"],
)

python_tests(
    name="fast-unit-tests",
    sources=["tests/unit/**/*.py"],
    tags=["fast", "unit"],
)
```

**Filter by tags:**
```bash
# Run slow tests only
pants test :: --tag=slow

# Run fast tests only
pants test :: --tag=fast

# Run unit tests only
pants test :: --tag=unit

# Run everything except slow tests
pants test :: --tag='-slow'
```

## Environment Variables

### Setting for Tests

**In BUILD file:**
```python
python_tests(
    name="src-tests",
    sources=["tests/**/*.py"],
    extra_env_vars=[
        "DATABASE_URL",
        "AWS_REGION",
    ],
)
```

**At runtime:**
```bash
export DATABASE_URL="postgresql://test"
pants test epistemix_platform:src-tests
```

### Setting for PEX Binaries

```python
pex_binary(
    name="epistemix-cli",
    entry_point="epistemix_platform.cli.main:main",
    env={
        "EPISTEMIX_ENV": "production",
    },
)
```

## Troubleshooting

### Tests Fail in Pants but Pass Locally

**Possible causes:**

1. **Missing dependencies**
   ```bash
   # Check inferred dependencies
   pants dependencies epistemix_platform:src-tests

   # Add missing dependency
   python_tests(
       name="src-tests",
       dependencies=["./missing:lib"],
   )
   ```

2. **Environment variables**
   ```python
   python_tests(
       name="src-tests",
       extra_env_vars=["DATABASE_URL"],
   )
   ```

3. **Working directory assumptions**
   ```python
   # Tests assume running from project root
   # Pants runs from hermetic sandbox

   # Fix: Use pathlib and __file__
   from pathlib import Path
   TEST_DATA = Path(__file__).parent / "test_data.json"
   ```

### Slow Test Execution

**Diagnosis:**
```bash
# Show timing per test file
pants test epistemix_platform:src-tests -- -vv --durations=10
```

**Solutions:**

1. **Enable batching** for expensive fixtures
2. **Split targets** into fast and slow
3. **Increase parallelism** if CPU underutilized
4. **Profile tests** to find bottlenecks

### Cache Not Working

**Diagnosis:**
```bash
# Force cache miss to see execution time
pants test --force epistemix_platform:src-tests

# Normal run (should be much faster)
pants test epistemix_platform:src-tests
```

**Solutions:**

1. **Use target addresses** instead of file paths
2. **Consistent pytest args** (don't vary `-v`, `-s`)
3. **Check for non-hermetic tests** (modify source tree)
4. **Verify stable dependencies** (no random test data)

## Remote Execution

For large teams, Pants supports **remote execution**:

```toml
# pants.toml
[GLOBAL]
remote_execution = true
remote_store_address = "grpc://remote-cache.example.com:1234"
remote_execution_address = "grpc://remote-exec.example.com:1234"
```

**Benefits:**
- Share compute resources across team
- Faster builds on developer machines
- Consistent build environment

**Setup:** Requires infrastructure (BuildBarn, BuildGrid, or Google RBE).

## Best Practices Summary

1. **Use test batching** when fixtures are expensive
2. **Separate resolves** for different concerns
3. **Use `--changed-since` in CI** to speed up pipelines
4. **Set appropriate timeouts** for different test types
5. **Tag tests** for selective execution
6. **Configure parallelism** based on available resources
7. **Monitor cache hit rates** to ensure optimization
8. **Use remote cache** for team collaboration
9. **Profile slow tests** and optimize or separate them
10. **Keep resolves minimal** to speed dependency resolution
