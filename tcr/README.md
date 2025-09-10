# TCR (Test && Commit || Revert)

A Python implementation of the TCR development pattern to constrain AI-assisted development and encourage smaller, more focused commits.

## Overview

TCR enforces a simple workflow:
1. Watch for file changes
2. Run tests automatically
3. If tests pass: commit changes
4. If tests fail: revert changes

This pattern is particularly useful when working with AI code assistants like Claude Code, as it:
- Constrains the AI to make smaller, incremental changes
- Ensures all changes pass tests before being committed
- Reduces review burden by creating smaller, focused commits
- Maintains a working codebase at all times

## Installation

```bash
poetry install
```

## Usage

### Start TCR Mode

```bash
poetry run tcr start
```

Or with a custom configuration:

```bash
poetry run tcr start --config tcr.yaml
```

### Stop TCR Mode

Press `Ctrl+C` to stop TCR mode.

## Configuration

Create a `tcr.yaml` file to customize TCR behavior:

```yaml
tcr:
  enabled: true
  watch_paths:
    - epistemix_platform/
    - simulations/
  ignore_paths:
    - "*.pyc"
    - "__pycache__"
    - ".git"
    - "*.egg-info"
  test_command: "poetry run pytest -xvs"
  test_timeout: 30
  commit_prefix: "TCR"
  revert_on_failure: true
  debounce_seconds: 2
```

### Configuration Options

- `enabled`: Enable/disable TCR (default: true)
- `watch_paths`: List of paths to watch for changes
- `ignore_paths`: List of patterns to ignore
- `test_command`: Command to run tests
- `test_timeout`: Maximum time in seconds for tests to run
- `commit_prefix`: Prefix for auto-generated commit messages
- `revert_on_failure`: Whether to revert changes on test failure
- `debounce_seconds`: Wait time between change detection and test execution

## How It Works

1. **File Watching**: Uses the `watchdog` library to monitor specified directories for changes
2. **Test Execution**: Runs the configured test command when changes are detected
3. **Git Integration**: Automatically commits on success or reverts on failure
4. **Debouncing**: Waits a configurable time before running tests to batch rapid changes

## Benefits

- **Atomic Commits**: Every commit represents a working state
- **Continuous Testing**: Tests run automatically on every change
- **Reduced Cognitive Load**: Smaller changes are easier to understand and review
- **AI Constraint**: Limits AI assistants to incremental, tested improvements
- **Safety Net**: Failed changes are automatically reverted

## Requirements

- Python 3.11+
- Git repository
- Configured test suite

## Development

Run tests:
```bash
poetry run pytest
```

Format code:
```bash
poetry run black tcr/
```

Lint code:
```bash
poetry run flake8 tcr/
```

## License

MIT