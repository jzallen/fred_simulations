# Pants Command Reference

## When to Read This

Read this reference when you need:
- Quick lookup of Pants command syntax and options
- Examples of common command patterns
- Understanding the difference between Pants goals
- Reference for passing arguments to underlying tools (pytest, ruff, etc.)

## Core Goals

### test - Run Tests

Execute Python tests using pytest under the hood.

**Basic Usage:**
```bash
# Run all tests in repository
pants test ::

# Run all tests in a component
pants test epistemix_platform::

# Run specific test target
pants test epistemix_platform:src-tests

# Run tests in a subdirectory
pants test epistemix_platform/tests::
```

**Key Options:**
```bash
# Test only code affected by changes
pants test --changed-since=main
pants test --changed-since=HEAD~1

# Force all tests to run (ignore cache)
pants test --force epistemix_platform:src-tests

# Show detailed output
pants test --debug epistemix_platform:src-tests
```

**Passing Arguments to pytest:**

Use `--` to separate Pants arguments from pytest arguments:

```bash
# Verbose output
pants test epistemix_platform:src-tests -- -vv

# Run specific test by name pattern
pants test epistemix_platform:src-tests -- -k test_user_login

# Stop on first failure
pants test epistemix_platform:src-tests -- -x

# Show print statements (no capture)
pants test epistemix_platform:src-tests -- -s

# Run with coverage
pants test epistemix_platform:src-tests -- --cov=epistemix_platform --cov-report=html

# Combine multiple pytest options
pants test epistemix_platform:src-tests -- -vv -x -k test_user

# Run with pytest-xdist parallel execution
pants test epistemix_platform:src-tests -- -n auto
```

### fmt - Format Code

Format code using Ruff formatter (Black-compatible).

**Basic Usage:**
```bash
# Format all code
pants fmt ::

# Format specific component
pants fmt epistemix_platform::

# Format only changed files
pants fmt --changed-since=HEAD

# Format specific directories
pants fmt epistemix_platform/src::
pants fmt simulation_runner::
```

**Key Options:**
```bash
# Show what would be formatted without making changes
pants fmt --check ::

# Format only Python files (when project has multiple languages)
pants fmt --only=ruff ::
```

### lint - Lint Code

Lint code using Ruff (replaces pylint, flake8, isort, etc.).

**Basic Usage:**
```bash
# Lint all code
pants lint ::

# Lint specific component
pants lint epistemix_platform::

# Lint only changed files
pants lint --changed-since=HEAD

# Lint specific directories
pants lint epistemix_platform/src::
```

**Key Options:**
```bash
# Only report issues, don't fail the build
pants lint --only=ruff ::

# Lint with specific rule set (configured in pyproject.toml)
pants lint epistemix_platform::
```

**Combined Format and Lint:**
```bash
# Run both fmt and lint together (efficient)
pants fmt lint ::
pants fmt lint --changed-since=HEAD
pants fmt lint epistemix_platform::
```

### package - Build Artifacts

Build PEX binaries and other artifacts.

**Basic Usage:**
```bash
# Build specific PEX binary
pants package epistemix_platform:epistemix-cli
pants package simulation_runner:simulation-runner-cli
pants package tcr:tcr-cli

# Build all packages
pants package ::

# Build Docker images
pants package //:simulation-runner
pants package //:epistemix-api
pants package //:migration-runner
```

**Output Location:**

Built artifacts are placed in `dist/` directory:
- `dist/epistemix_platform/epistemix-cli.pex`
- `dist/simulation_runner/simulation-runner-cli.pex`
- `dist/tcr/tcr-cli.pex`

### generate-lockfiles - Update Dependencies

Generate or update Python dependency lockfiles.

**Basic Usage:**
```bash
# Update all lockfiles
pants generate-lockfiles

# Update specific resolve
pants generate-lockfiles --resolve=epistemix_platform_env
pants generate-lockfiles --resolve=infrastructure_env
pants generate-lockfiles --resolve=tcr_env
```

**When to Use:**
- After adding dependencies to `requirements.txt`
- After updating dependency versions
- When lockfile becomes stale or corrupted

**Lockfile Locations:**
- `epistemix_platform/epistemix_platform_env.lock`
- `epistemix_platform/infrastructure/infrastructure_env.lock`
- `tcr/tcr_env.lock`

### export - Export to Virtual Environment

Export dependencies to a virtual environment for IDE/editor support.

**Basic Usage:**
```bash
# Export specific resolve
pants export --resolve=epistemix_platform_env

# Export all resolves
pants export
```

**Output Location:**

Virtual environments are created in `dist/export/python/virtualenvs/`

**When to Use:**
- Setting up IDE (VS Code, PyCharm) with correct dependencies
- Running tools outside Pants that need dependencies
- Debugging dependency issues

### dependencies - View Dependencies

Show dependencies for a target.

**Basic Usage:**
```bash
# Show direct dependencies
pants dependencies epistemix_platform:src-tests

# Show all transitive dependencies
pants dependencies --transitive epistemix_platform:src-tests

# Show dependencies in a tree format
pants dependencies --transitive epistemix_platform:src-tests | grep -E '^\s+'

# Find what depends on a target (reverse dependencies)
pants dependents epistemix_platform/src:lib
```

**Understanding Output:**
```bash
# Example output:
epistemix_platform/src/epistemix_platform:lib
epistemix_platform/tests:test-utils
epistemix_platform:test-reqs#pytest
epistemix_platform:test-reqs#pytest-mock
```

### list - List Targets

List targets matching a specification.

**Basic Usage:**
```bash
# List all targets in repository
pants list ::

# List all targets in a component
pants list epistemix_platform::

# List targets in a specific directory
pants list epistemix_platform/tests::

# List targets that own a specific file
pants list epistemix_platform/tests/test_models.py
```

**Filtering:**
```bash
# List only test targets
pants list :: --filter-target-type=python_tests

# List only binary targets
pants list :: --filter-target-type=pex_binary

# List only source targets
pants list :: --filter-target-type=python_sources
```

**Useful Patterns:**
```bash
# Count total targets
pants list :: | wc -l

# Find targets matching a name pattern
pants list :: | grep test

# List targets in multiple components
pants list epistemix_platform:: simulation_runner::
```

### peek - Inspect Target Metadata

Show detailed metadata for a target.

**Basic Usage:**
```bash
# Inspect specific target
pants peek epistemix_platform:src-tests

# Inspect multiple targets
pants peek epistemix_platform:src-tests simulation_runner:src-tests

# Inspect all targets in a directory
pants peek epistemix_platform::
```

**Understanding Output:**

Output is JSON showing:
- Target address
- Target type
- Dependencies
- Sources (file patterns)
- Configuration options
- Resolve information

**Example:**
```json
[
  {
    "address": "epistemix_platform:src-tests",
    "target_type": "python_tests",
    "dependencies": [
      "./src/epistemix_platform:lib",
      "./tests:test-utils"
    ],
    "sources": [
      "tests/**/test_*.py",
      "tests/test_*.py"
    ],
    "resolve": "epistemix_platform_env"
  }
]
```

## Global Options

These options work with most Pants commands:

```bash
# Use specific directory as working directory
pants --pants-workdir=/tmp/pants-cache test ::

# Adjust concurrency (number of parallel processes)
pants --process-execution-local-parallelism=8 test ::

# Enable debug logging
pants --level=debug test epistemix_platform:src-tests

# Disable cache
pants --no-local-cache test epistemix_platform:src-tests
```

## Cache Management

```bash
# Clean all cached data (use sparingly)
pants clean-all

# Warm cache by running all tests
pants test ::

# Check cache statistics
pants --stats-record-option-scopes test ::
```

## Project-Specific Targets

### Epistemix Platform
```bash
# Main application tests
pants test epistemix_platform:src-tests

# Infrastructure tests (different resolve)
pants test epistemix_platform:infrastructure-tests

# Build CLI
pants package epistemix_platform:epistemix-cli

# Build test runner for VS Code
pants package epistemix_platform:epistemix_platform_test_runner
```

### Simulation Runner
```bash
# Run tests
pants test simulation_runner:src-tests

# Build CLI
pants package simulation_runner:simulation-runner-cli
```

### TCR (Test && Commit || Revert)
```bash
# Run tests
pants test tcr:src-tests

# Build CLI
pants package tcr:tcr-cli
```

## Common Workflows

### Pre-commit Check
```bash
# Format and lint changed files
pants fmt lint --changed-since=HEAD
```

### Pre-push Check
```bash
# Format and lint everything
pants fmt lint ::

# Run all tests
pants test ::
```

### CI Pipeline
```bash
# Test only affected code
pants test --changed-since=main

# Format check without making changes
pants fmt --check ::

# Lint everything
pants lint ::
```

### Local Development Iteration
```bash
# Edit code
vim epistemix_platform/src/epistemix_platform/models/user.py

# Run affected tests (Pants caches unaffected tests)
pants test epistemix_platform:src-tests

# Format changed files
pants fmt --changed-since=HEAD
```

### Building for Deployment
```bash
# Build all PEX binaries
pants package epistemix_platform:epistemix-cli
pants package simulation_runner:simulation-runner-cli

# Build Docker images
pants package //:simulation-runner
pants package //:epistemix-api
pants package //:migration-runner
```

## Tips and Best Practices

1. **Always use target addresses, never file paths** for test execution
2. **Use `::` wildcard** for broad operations, let Pants optimize
3. **Leverage `--changed-since`** to speed up CI pipelines
4. **Run `pants test ::` periodically** to warm the cache
5. **Combine goals when possible** (e.g., `pants fmt lint ::`)
6. **Use `--` separator** when passing arguments to underlying tools
7. **Inspect with `list` and `peek`** to understand target structure
8. **Export resolves** to keep IDE dependencies in sync
