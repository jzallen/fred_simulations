# Target Specifications in Pants

## When to Read This

Read this reference when you need to understand:
- How to address targets in BUILD files
- The difference between `:` and `::` syntax
- How to structure BUILD files for optimal caching
- Target naming conventions and best practices
- How to create and organize multiple test targets

## What is a Target?

A **target** is an addressable unit of metadata describing code in your project. Targets are defined in `BUILD` files and have:

- **Type**: What kind of target (e.g., `python_tests`, `pex_binary`, `python_sources`)
- **Name**: A unique identifier within the BUILD file
- **Sources**: File patterns the target owns
- **Dependencies**: Other targets this target depends on
- **Configuration**: Target-specific settings

## Target Addressing

### Format

Targets use the format: `path/to/directory:target-name`

**Examples:**
```bash
epistemix_platform:src-tests              # Target named "src-tests" in epistemix_platform/BUILD
epistemix_platform/tests:test-utils       # Target named "test-utils" in epistemix_platform/tests/BUILD
simulation_runner:simulation-runner-cli   # Target named "simulation-runner-cli" in simulation_runner/BUILD
```

### Components of a Target Address

```
epistemix_platform/tests:unit-tests
│                        │
│                        └─ Target name (from BUILD file)
│
└─ Directory path (relative to project root)
```

## The :: Wildcard

The `::` syntax means "this directory and **all subdirectories**".

### Recursive Target Selection

```bash
# All targets in entire repository
pants test ::

# All targets in epistemix_platform and subdirectories
pants test epistemix_platform::

# All targets in tests subdirectory and below
pants test epistemix_platform/tests::

# Multiple directories
pants test epistemix_platform:: simulation_runner::
```

### When to Use ::

Use `::` when you want:
- **Broad execution**: Run all tests in a component
- **Convenience**: Avoid listing individual targets
- **Future-proofing**: Automatically include new targets as they're added

### How :: Interacts with Caching

When you run `pants test epistemix_platform::`:
1. Pants finds all test targets under `epistemix_platform/`
2. Executes each target
3. Caches results per-target
4. On subsequent runs, only re-runs affected targets

**This is why using target addresses (even with ::) is better than file paths.**

## Single : for Specific Targets

Use single `:` to address a specific named target.

### Syntax

```bash
# Specific target in a BUILD file
pants test epistemix_platform:src-tests

# Multiple specific targets
pants test epistemix_platform:src-tests epistemix_platform:infrastructure-tests

# Targets across different directories
pants test epistemix_platform:src-tests simulation_runner:src-tests tcr:src-tests
```

### When to Use Single :

Use single `:` when you:
- **Need precision**: Run only one specific target
- **Have multiple targets in same directory**: Select one among many
- **Want explicit control**: Make clear which target you're running

## BUILD File Structure

### Location

BUILD files are placed in directories containing targets:

```
epistemix_platform/
├── BUILD                     # Targets for this directory
├── src/
│   └── epistemix_platform/
│       └── BUILD             # Targets for source code
└── tests/
    └── BUILD                 # Targets for tests
```

### Basic BUILD File Example

```python
# epistemix_platform/BUILD

python_tests(
    name="src-tests",
    sources=[
        "tests/**/test_*.py",
        "tests/test_*.py",
    ],
    dependencies=[
        "./src/epistemix_platform:lib",
        "./tests:test-utils",
        ":test-reqs#pytest",
        ":test-reqs#pytest-mock",
    ],
)

pex_binary(
    name="epistemix-cli",
    entry_point="epistemix_platform.cli.main:main",
    dependencies=[
        "./src/epistemix_platform:lib",
    ],
)

python_requirements(
    name="test-reqs",
    source="test-requirements.txt",
)
```

## python_tests Target Structure

The `python_tests` target is the most common for test execution.

### Complete Example

```python
python_tests(
    name="src-tests",           # Target name (addressable as epistemix_platform:src-tests)
    sources=[                   # Glob patterns for test files
        "tests/**/test_*.py",   # All test files in subdirectories
        "tests/test_*.py",      # Test files in tests/ root
    ],
    dependencies=[              # What this target depends on
        "./src/epistemix_platform:lib",  # Production code
        "./tests:test-utils",            # Test utilities
        ":test-reqs#pytest",             # pytest from requirements
        ":test-reqs#pytest-mock",        # pytest-mock from requirements
    ],
    resolve="epistemix_platform_env",    # Which Python resolve to use
    timeout=300,                         # Test timeout in seconds
)
```

### Field Breakdown

#### name (required)

Short, descriptive identifier for the target:
- Use `kebab-case` (e.g., `src-tests`, `integration-tests`)
- Should describe what tests it contains
- Must be unique within the BUILD file

#### sources (required)

Glob patterns for files owned by this target:

```python
sources=[
    "tests/**/*.py",           # All Python files in tests/ recursively
    "tests/**/test_*.py",      # Only test files (test_ prefix)
    "tests/unit/**/*.py",      # All files in tests/unit/
    "tests/test_*.py",         # Test files in tests/ root only
]
```

**Best Practice:** Be specific to avoid conflicts with other targets in same directory.

#### dependencies (optional)

Other targets this target depends on:

```python
dependencies=[
    # Relative path to production code
    "./src/epistemix_platform:lib",

    # Relative path to test utilities
    "./tests:test-utils",

    # Dependencies from python_requirements
    ":test-reqs#pytest",
    ":test-reqs#pytest-mock",

    # Absolute path (from project root)
    "//epistemix_platform/src:lib",
]
```

**Dependency Inference:** Pants automatically infers most dependencies by analyzing imports. Explicit dependencies are only needed for:
- Non-Python resources
- Ambiguous cases
- Override default inference

#### resolve (optional)

Which Python dependency set to use:

```python
resolve="epistemix_platform_env"    # Default resolve
resolve="infrastructure_env"        # Infrastructure tools
resolve="tcr_env"                   # TCR-specific dependencies
```

If not specified, uses the default resolve from `pants.toml`.

#### timeout (optional)

Maximum seconds for test execution:

```python
timeout=300    # 5 minutes
timeout=60     # 1 minute
timeout=1800   # 30 minutes
```

Default is typically 60 seconds. Increase for slow integration tests.

#### batch_compatibility_tag (optional)

Mark tests that can be batched together:

```python
batch_compatibility_tag="expensive-fixtures"
```

See "Test Batching" section in advanced-topics.md for details.

## Multiple Test Targets

Projects often have multiple test targets for different purposes.

### Organizing by Test Type

```python
# Unit tests (fast, isolated)
python_tests(
    name="unit-tests",
    sources=["tests/unit/**/*.py"],
    timeout=60,
)

# Integration tests (slower, with real dependencies)
python_tests(
    name="integration-tests",
    sources=["tests/integration/**/*.py"],
    timeout=300,
)

# End-to-end tests (slowest, full system)
python_tests(
    name="e2e-tests",
    sources=["tests/e2e/**/*.py"],
    timeout=600,
)
```

**Benefits:**
- Run fast tests first: `pants test epistemix_platform:unit-tests`
- Run comprehensive suite: `pants test epistemix_platform::`
- Cache separately: Changes to unit tests don't invalidate e2e cache

### Organizing by Dependency Resolve

```python
# Main application tests
python_tests(
    name="src-tests",
    sources=["tests/**/test_*.py"],
    resolve="epistemix_platform_env",
)

# Infrastructure tests (uses different dependencies)
python_tests(
    name="infrastructure-tests",
    sources=["infrastructure/tests/**/*.py"],
    resolve="infrastructure_env",
)
```

**Use case:** Infrastructure tests need Sceptre/CloudFormation libraries that application tests don't need.

### Organizing by Component

```python
# Model layer tests
python_tests(
    name="model-tests",
    sources=["tests/models/**/*.py"],
)

# Repository layer tests
python_tests(
    name="repository-tests",
    sources=["tests/repositories/**/*.py"],
)

# API layer tests
python_tests(
    name="api-tests",
    sources=["tests/api/**/*.py"],
)
```

## Target Naming Conventions

### Recommended Patterns

**For Tests:**
- `src-tests` - Main application tests
- `unit-tests` - Unit tests only
- `integration-tests` - Integration tests
- `infrastructure-tests` - Infrastructure/deployment tests
- `pact-tests` - Contract tests

**For Binaries:**
- `epistemix-cli` - Command-line interface
- `simulation-runner-cli` - Simulation runner CLI
- `tcr-cli` - TCR tool CLI

**For Libraries:**
- `lib` - Main library code
- `test-utils` - Test utilities/fixtures

**For Requirements:**
- `reqs` - Production requirements
- `test-reqs` - Test requirements
- `dev-reqs` - Development requirements

### Naming Guidelines

1. **Use kebab-case**: `src-tests` not `src_tests` or `srcTests`
2. **Be descriptive**: Name should indicate what the target contains
3. **Use standard suffixes**: `-tests`, `-cli`, `-lib` help identify type
4. **Avoid redundancy**: `epistemix_platform:epistemix-platform-tests` is redundant
5. **Keep it short**: Target names appear frequently in commands

## Finding Targets

### List All Targets

```bash
# All targets in repository
pants list ::

# All targets in a component
pants list epistemix_platform::

# All targets in a directory
pants list epistemix_platform/tests::
```

### Find Targets by Type

```bash
# All test targets
pants list :: --filter-target-type=python_tests

# All binary targets
pants list :: --filter-target-type=pex_binary

# All source targets
pants list :: --filter-target-type=python_sources
```

### Find Target Owning a File

```bash
# Which target owns this file?
pants list epistemix_platform/tests/test_models.py

# Output example:
# epistemix_platform:src-tests
```

**Use case:** You have a file path and need to know which target to run.

## Inspecting Target Metadata

Use `pants peek` to see full target details:

```bash
pants peek epistemix_platform:src-tests
```

**Output (JSON):**
```json
[
  {
    "address": "epistemix_platform:src-tests",
    "target_type": "python_tests",
    "dependencies": [
      "./src/epistemix_platform:lib",
      "./tests:test-utils",
      ":test-reqs#pytest"
    ],
    "sources": [
      "tests/**/test_*.py",
      "tests/test_*.py"
    ],
    "resolve": "epistemix_platform_env",
    "timeout": 300
  }
]
```

## Advanced Target Patterns

### Negative Patterns

Exclude specific targets:

```bash
# Run all tests except infrastructure tests
pants test :: --filter-target-type=python_tests '!epistemix_platform:infrastructure-tests'
```

### Tag-Based Selection

Add tags to targets:

```python
python_tests(
    name="slow-tests",
    sources=["tests/slow/**/*.py"],
    tags=["slow", "integration"],
)
```

Filter by tags:
```bash
# Run tests with specific tag
pants test :: --tag=slow

# Exclude tests with tag
pants test :: --tag='-slow'
```

## Common Patterns

### Running All Tests
```bash
pants test ::
```

### Running Component Tests
```bash
pants test epistemix_platform::
pants test simulation_runner::
pants test tcr::
```

### Running Specific Target
```bash
pants test epistemix_platform:src-tests
```

### Running Multiple Specific Targets
```bash
pants test epistemix_platform:unit-tests epistemix_platform:integration-tests
```

### Running Tests in Subdirectory
```bash
pants test epistemix_platform/tests::
pants test epistemix_platform/tests/unit::
```

## Best Practices

1. **Use target addresses, not file paths** - Maximizes cache effectiveness
2. **Create separate targets for different test types** - Enables selective execution
3. **Use descriptive target names** - Makes commands self-documenting
4. **Keep sources patterns specific** - Avoid overlap between targets
5. **Leverage :: for broad operations** - Let Pants optimize execution
6. **Use consistent naming conventions** - Improves team coordination
7. **Organize targets logically** - Group by layer, type, or speed
8. **Document complex targets** - Add comments in BUILD files

## Project-Specific Targets

### Epistemix Platform

```bash
# Main tests
pants test epistemix_platform:src-tests

# Infrastructure tests (different resolve)
pants test epistemix_platform:infrastructure-tests

# All epistemix tests
pants test epistemix_platform::
```

### Simulation Runner

```bash
# Main tests
pants test simulation_runner:src-tests

# All simulation runner tests
pants test simulation_runner::
```

### TCR

```bash
# Main tests
pants test tcr:src-tests

# All TCR tests
pants test tcr::
```

### All Tests

```bash
# Everything
pants test ::
```
