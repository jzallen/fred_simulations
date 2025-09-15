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

## Installation and Build

TCR uses Pants as its build system to create a standalone executable. To build and install:

```bash
# Build the TCR executable using Pants
pants package tcr:tcr-cli

# The executable will be created in dist/tcr/tcr-cli.pex
# You can then run it directly:
./dist/tcr/tcr-cli.pex start
```

Alternatively, for development, you can use Poetry:

```bash
poetry install
poetry run python -m tcr.tcr start
```

## Usage

### Start TCR Mode

Using the built executable:
```bash
./dist/tcr/tcr-cli.pex start
```

Or during development:
```bash
poetry run python -m tcr.tcr start
```

With a custom configuration:
```bash
./dist/tcr/tcr-cli.pex start --config tcr.yaml
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
  test_command: "poetry run pytest -xvs"
  test_timeout: 30
  commit_prefix: "TCR"
  revert_on_failure: true
  debounce_seconds: 2
```

### Configuration Options

- `enabled`: Enable/disable TCR (default: true)
- `watch_paths`: List of paths to watch for changes
- `test_command`: Command to run tests
- `test_timeout`: Maximum time in seconds for tests to run
- `commit_prefix`: Prefix for auto-generated commit messages
- `revert_on_failure`: Whether to revert changes on test failure
- `debounce_seconds`: Wait time between change detection and test execution

Note: TCR automatically respects your `.gitignore` file. It uses `git status` to determine if files have changed, so any patterns in `.gitignore` are implicitly excluded from triggering the TCR loop.

### Important Note on Watch Paths

**Avoid adding test directories to `watch_paths`!** This is intentional and important for the TCR workflow. By excluding test files from the watch paths:
- You can modify tests without triggering the TCR loop
- This allows you to write or update tests first, then implement the code to make them pass
- It prevents infinite loops where test changes trigger test runs
- It follows the TDD (Test-Driven Development) approach where tests are written before implementation

Example configuration that excludes tests:
```yaml
tcr:
  watch_paths:
    - epistemix_platform/controllers/  # Watches source code only
    # Do NOT add: epistemix_platform/tests/
```

## How It Works

1. **File Watching**: Uses the `watchdog` library to monitor specified directories for changes
2. **Change Detection**: Uses `git status` to determine if tracked files have changed (respecting `.gitignore`)
3. **Test Execution**: Runs the configured test command when changes are detected
4. **Git Integration**: Automatically commits on success or reverts on failure
5. **Debouncing**: Waits a configurable time before running tests to batch rapid changes

## Benefits

- **Atomic Commits**: Every commit represents a working state
- **Continuous Testing**: Tests run automatically on every change
- **Reduced Cognitive Load**: Smaller changes are easier to understand and review
- **AI Constraint**: Limits AI assistants to incremental, tested improvements
- **Safety Net**: Failed changes are automatically reverted
- **TDD Support**: Excluding tests from watch paths enables test-first development
- **Git-Aware**: Automatically ignores files that Git ignores

## Logging

TCR maintains detailed logs to help you debug issues and understand its behavior:

- **Log Location**: `~/tcr.log`
- **Log Rotation**: When the log file reaches its size limit, it's rotated with numbered backups:
  - `tcr.log` - Current active log file
  - `tcr.log.1` - Most recent backup
  - `tcr.log.2` - Second most recent backup
  - And so on...

To monitor TCR activity in real-time:
```bash
tail -f ~/tcr.log
```

To check recent TCR activity:
```bash
tail -n 50 ~/tcr.log
```

The logs include:
- File change detection events
- Test execution results
- Git operations (commits and reverts)
- Error messages and stack traces
- Timing information for each operation

## Requirements

- Python 3.11+
- Git repository
- Configured test suite
- Pants build system (for creating executable)

## Development

### Building the Executable

```bash
# Build the PEX executable
pants package tcr:tcr-cli

# Test the built executable
./dist/tcr/tcr-cli.pex --help
```

### Running Tests

```bash
# Using Pants
pants test tcr:tests:

# Using Poetry
poetry run pytest tcr/tests/
```

### Code Quality

Format code:
```bash
poetry run black tcr/
```

Lint code:
```bash
poetry run flake8 tcr/
poetry run pylint tcr/
```

## Architecture

The TCR tool is structured as follows:
- `tcr.py`: Main module containing the TCR handler and file watcher
- `BUILD`: Pants build configuration defining the PEX binary
- `tests/`: Unit tests for TCR functionality

The Pants build system packages everything into a standalone PEX (Python Executable) file that can be distributed and run without requiring users to install dependencies.

## License

MIT