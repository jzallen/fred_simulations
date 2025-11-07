# TDD Integration with Pants

## When to Read This

Read this reference when you want to:
- Practice Test-Driven Development (TDD) with Pants
- Understand how Pants caching integrates with Red-Green-Refactor
- Optimize your TDD workflow for maximum speed
- Use pytest arguments effectively during TDD
- Set up efficient watch-mode development

## TDD Overview

Test-Driven Development follows the **Red-Green-Refactor** cycle:

1. **Red**: Write a failing test
2. **Green**: Write minimal code to make it pass
3. **Refactor**: Improve the code while keeping tests green

**Key principle:** Run tests frequently (every 30-60 seconds).

## Why Pants Excels at TDD

### 1. Fast Feedback Loop

**Pants caching** means subsequent test runs are near-instant:

```bash
# First run: 5 seconds (cold cache)
pants test epistemix_platform:src-tests -- -k test_new_feature

# Second run after small change: 0.5 seconds (warm cache)
pants test epistemix_platform:src-tests -- -k test_new_feature
```

### 2. File-Level Dependency Tracking

**Pants only re-runs affected tests:**

```bash
# Edit user.py
vim epistemix_platform/src/epistemix_platform/models/user.py

# Only tests importing user.py re-run
pants test epistemix_platform:src-tests
# 3 files re-run, 17 cached → ~3 seconds instead of 15 seconds
```

### 3. Consistent Test Execution

**Same environment every time:**
- No "works on my machine" issues
- Hermetic test execution
- Reproducible results

## TDD Workflow with Pants

### Phase 1: Red (Failing Test)

**1. Write the test first:**

```python
# epistemix_platform/tests/test_user.py
def test_user_full_name():
    user = User(first_name="John", last_name="Doe")
    assert user.full_name() == "John Doe"
```

**2. Run the test (expect failure):**

```bash
pants test epistemix_platform:src-tests -- -k test_user_full_name
```

**Output:**
```
AttributeError: 'User' object has no attribute 'full_name'
✗ test_user_full_name FAILED
```

**Key Points:**
- Use `-k` to run specific test by name
- Use same target address consistently (`epistemix_platform:src-tests`)
- Verify the test fails for the right reason

### Phase 2: Green (Minimal Implementation)

**1. Implement minimal code:**

```python
# epistemix_platform/src/epistemix_platform/models/user.py
class User:
    def __init__(self, first_name: str, last_name: str):
        self.first_name = first_name
        self.last_name = last_name

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
```

**2. Run the test again (expect success):**

```bash
pants test epistemix_platform:src-tests -- -k test_user_full_name
```

**Output:**
```
✓ test_user_full_name PASSED
```

**Key Points:**
- Same command as Red phase
- Pants uses cache for unaffected tests
- Fast feedback (~1-2 seconds)

### Phase 3: Refactor (Improve Code)

**1. Refactor the implementation:**

```python
# epistemix_platform/src/epistemix_platform/models/user.py
from dataclasses import dataclass

@dataclass
class User:
    first_name: str
    last_name: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
```

**2. Run all tests to ensure nothing broke:**

```bash
pants test epistemix_platform:src-tests
```

**Output:**
```
✓ test_user_full_name PASSED
✓ test_user_creation PASSED
✓ test_user_validation PASSED
... (17 more from cache)
```

**Key Points:**
- Drop `-k` to run full suite
- Pants caches unaffected tests
- Confidence that refactoring didn't break anything

## Optimal TDD Commands

### During Red-Green Cycle (Single Test)

**Focus on one test:**
```bash
pants test epistemix_platform:src-tests -- -k test_user_full_name
```

**Benefits:**
- Fast execution (only one test)
- Clear pass/fail signal
- Minimal noise in output

### During Refactor (Full Suite)

**Run all tests:**
```bash
pants test epistemix_platform:src-tests
```

**Benefits:**
- Verifies no regressions
- Uses cache for unaffected tests
- Still fast (~5 seconds typical)

### Multiple Related Tests

**Pattern matching:**
```bash
# Run all user-related tests
pants test epistemix_platform:src-tests -- -k test_user

# Run all authentication tests
pants test epistemix_platform:src-tests -- -k test_auth
```

## Effective pytest Arguments for TDD

### -k: Run Specific Tests

**By name:**
```bash
pants test epistemix_platform:src-tests -- -k test_user_full_name
```

**By pattern:**
```bash
# All tests with "user" in name
pants test epistemix_platform:src-tests -- -k test_user

# All tests with "create" or "update"
pants test epistemix_platform:src-tests -- -k "test_create or test_update"
```

### -x: Stop on First Failure

**During Red phase:**
```bash
pants test epistemix_platform:src-tests -- -x
```

**Benefit:** Stops immediately when test fails, no need to scroll through output.

### -v / -vv: Verbose Output

**Standard verbose:**
```bash
pants test epistemix_platform:src-tests -- -v
```

**Extra verbose:**
```bash
pants test epistemix_platform:src-tests -- -vv
```

**Shows:**
- Test names and results
- Full assertion details
- Detailed failure messages

### -s: Show Print Statements

**See debug output:**
```bash
pants test epistemix_platform:src-tests -- -s -k test_user_full_name
```

**Use case:** When you add `print()` statements for debugging.

### --lf: Run Last Failed

**Re-run only failed tests:**
```bash
pants test epistemix_platform:src-tests -- --lf
```

**Workflow:**
1. Run all tests: `pants test epistemix_platform:src-tests`
2. Some fail
3. Fix code
4. Run only failed: `pants test epistemix_platform:src-tests -- --lf`

**Note:** Pants caching makes this less necessary than in regular pytest.

### --tb=short: Shorter Tracebacks

**Concise failure output:**
```bash
pants test epistemix_platform:src-tests -- --tb=short
```

**Options:**
- `--tb=short`: One-line per failure
- `--tb=line`: Very compact
- `--tb=long`: Full traceback (default)

### Combining Arguments

**Red phase (debugging):**
```bash
pants test epistemix_platform:src-tests -- -vv -s -x -k test_user_full_name
```
- Very verbose
- Show prints
- Stop on first failure
- Run specific test

**Green phase (verification):**
```bash
pants test epistemix_platform:src-tests -- -v -k test_user_full_name
```
- Verbose
- Run specific test

**Refactor phase (full check):**
```bash
pants test epistemix_platform:src-tests
```
- All tests
- Use cache
- Default output

## Watch Mode Development

Pants doesn't have built-in watch mode, but you can use external tools.

### Using watchexec

**Install:**
```bash
cargo install watchexec-cli
# or
brew install watchexec
```

**Watch for changes and run tests:**
```bash
watchexec -e py -w epistemix_platform/src -w epistemix_platform/tests \
  -- pants test epistemix_platform:src-tests
```

**With specific test:**
```bash
watchexec -e py -w epistemix_platform \
  -- pants test epistemix_platform:src-tests -- -k test_user_full_name
```

### Using entr

**Install:**
```bash
brew install entr
# or
apt-get install entr
```

**Watch for changes:**
```bash
find epistemix_platform -name '*.py' | entr pants test epistemix_platform:src-tests
```

### Using pytest-watch (ptw)

**Note:** Works best with Poetry/pip, less ideal with Pants.

**Alternative:** Use Pants' fast caching instead of watch mode.

## Multi-File TDD Workflow

When working on a feature spanning multiple files:

### Example: User Registration Feature

**Files involved:**
- `models/user.py`
- `repositories/user_repository.py`
- `use_cases/register_user.py`
- `api/routes/auth.py`

**Workflow:**

**1. Test model (Red):**
```bash
pants test epistemix_platform:src-tests -- -k test_user_model
```

**2. Implement model (Green):**
```bash
vim epistemix_platform/src/epistemix_platform/models/user.py
pants test epistemix_platform:src-tests -- -k test_user_model
```

**3. Test repository (Red):**
```bash
pants test epistemix_platform:src-tests -- -k test_user_repository
```

**4. Implement repository (Green):**
```bash
vim epistemix_platform/src/epistemix_platform/repositories/user_repository.py
pants test epistemix_platform:src-tests -- -k test_user_repository
```

**5. Test use case (Red):**
```bash
pants test epistemix_platform:src-tests -- -k test_register_user
```

**6. Implement use case (Green):**
```bash
vim epistemix_platform/src/epistemix_platform/use_cases/register_user.py
pants test epistemix_platform:src-tests -- -k test_register_user
```

**7. Test API (Red):**
```bash
pants test epistemix_platform:src-tests -- -k test_auth_routes
```

**8. Implement API (Green):**
```bash
vim epistemix_platform/src/epistemix_platform/api/routes/auth.py
pants test epistemix_platform:src-tests -- -k test_auth_routes
```

**9. Refactor (run all):**
```bash
pants test epistemix_platform:src-tests
```

**Key Point:** Throughout this workflow, Pants caches unaffected tests, so each step is fast.

## TDD with Clean Architecture Layers

This project uses clean architecture. TDD workflow follows layer dependencies:

### Layer Order (Outside-In TDD)

**1. Domain/Models (no dependencies):**
```bash
pants test epistemix_platform:src-tests -- -k test_models
```

**2. Repositories (depend on models):**
```bash
pants test epistemix_platform:src-tests -- -k test_repositories
```

**3. Use Cases (depend on repositories):**
```bash
pants test epistemix_platform:src-tests -- -k test_use_cases
```

**4. API/Controllers (depend on use cases):**
```bash
pants test epistemix_platform:src-tests -- -k test_api
```

### Benefits

- **Clear dependency direction**: Inner layers don't know about outer layers
- **Independent testing**: Each layer tested in isolation
- **Fast feedback**: Pants only re-runs affected layers

## Common Patterns

### Test One, Run All

During TDD, frequently run full suite to catch regressions:

```bash
# Work on specific test
pants test epistemix_platform:src-tests -- -k test_new_feature

# ... iterate ...

# Run full suite before commit
pants test epistemix_platform:src-tests
```

**Frequency:** Every 3-5 Red-Green cycles, run full suite.

### Separate Fast and Slow Tests

```bash
# During TDD: Run fast unit tests
pants test epistemix_platform:unit-tests -- -k test_user

# Before commit: Run all tests including slow integration
pants test epistemix_platform::
```

### Use Tags for Test Categories

```python
# BUILD file
python_tests(
    name="unit-tests",
    sources=["tests/unit/**/*.py"],
    tags=["unit", "fast"],
)

python_tests(
    name="integration-tests",
    sources=["tests/integration/**/*.py"],
    tags=["integration", "slow"],
)
```

**During TDD:**
```bash
# Fast feedback with unit tests
pants test :: --tag=unit

# Comprehensive check with all tests
pants test ::
```

## Performance Tips for TDD

### 1. Always Use Same Target

**Consistent:**
```bash
pants test epistemix_platform:src-tests -- -k test_user
pants test epistemix_platform:src-tests -- -k test_user
pants test epistemix_platform:src-tests -- -k test_user
```

**Benefit:** Builds same cache key, maximum cache hits.

### 2. Use -k Instead of File Paths

**Good:**
```bash
pants test epistemix_platform:src-tests -- -k test_user_full_name
```

**Bad:**
```bash
pants test epistemix_platform/tests/test_user.py::test_user_full_name
```

**Why:** Target-based invocation uses cache, file paths don't.

### 3. Leverage Dependency Tracking

Edit a file, run tests, Pants knows what to re-test:

```bash
# Edit user.py
vim epistemix_platform/src/epistemix_platform/models/user.py

# Pants re-runs only tests importing user.py
pants test epistemix_platform:src-tests
```

**No manual tracking needed!**

### 4. Keep pytest Arguments Consistent

**Within a TDD session, use same args:**

```bash
# Session start
pants test epistemix_platform:src-tests -- -v -k test_user

# ... edit code ...

# Same args
pants test epistemix_platform:src-tests -- -v -k test_user
```

**Why:** Different pytest args = different cache keys.

## Example TDD Session

**Goal:** Add email validation to User model

**1. Red - Write failing test:**

```python
# epistemix_platform/tests/test_user.py
def test_user_email_validation():
    with pytest.raises(ValueError):
        User(first_name="John", last_name="Doe", email="invalid")
```

```bash
pants test epistemix_platform:src-tests -- -k test_user_email_validation
# ✗ FAILED (no validation exists)
```

**2. Green - Minimal implementation:**

```python
# epistemix_platform/src/epistemix_platform/models/user.py
import re

@dataclass
class User:
    first_name: str
    last_name: str
    email: str

    def __post_init__(self):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", self.email):
            raise ValueError("Invalid email")
```

```bash
pants test epistemix_platform:src-tests -- -k test_user_email_validation
# ✓ PASSED
```

**3. More tests - Edge cases:**

```python
def test_user_email_valid():
    user = User(first_name="John", last_name="Doe", email="john@example.com")
    assert user.email == "john@example.com"

def test_user_email_empty():
    with pytest.raises(ValueError):
        User(first_name="John", last_name="Doe", email="")
```

```bash
pants test epistemix_platform:src-tests -- -k test_user_email
# ✓ test_user_email_validation PASSED
# ✓ test_user_email_valid PASSED
# ✗ test_user_email_empty FAILED (empty string matches regex)
```

**4. Fix implementation:**

```python
def __post_init__(self):
    if not self.email or not re.match(r"[^@]+@[^@]+\.[^@]+", self.email):
        raise ValueError("Invalid email")
```

```bash
pants test epistemix_platform:src-tests -- -k test_user_email
# ✓ All 3 tests PASSED
```

**5. Refactor - Extract validator:**

```python
# epistemix_platform/src/epistemix_platform/models/validators.py
def validate_email(email: str) -> str:
    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError("Invalid email")
    return email

# epistemix_platform/src/epistemix_platform/models/user.py
@dataclass
class User:
    first_name: str
    last_name: str
    email: str

    def __post_init__(self):
        self.email = validate_email(self.email)
```

```bash
pants test epistemix_platform:src-tests
# ✓ test_user_email_validation PASSED
# ✓ test_user_email_valid PASSED
# ✓ test_user_email_empty PASSED
# ✓ ... 17 other tests PASSED (from cache)
```

**Total time:** ~15 seconds for entire TDD session.

## Best Practices Summary

1. **Use consistent target addresses** - Same target throughout TDD cycle
2. **Use `-k` for test selection** - Not file paths
3. **Run one test during Red-Green** - Fast feedback
4. **Run full suite during Refactor** - Catch regressions
5. **Keep pytest args stable** - Better cache utilization
6. **Leverage Pants caching** - Trust that it works
7. **Use `-x` to stop on first failure** - Faster debugging
8. **Separate fast and slow tests** - Run fast tests more frequently
9. **Run full suite before commit** - Final verification
10. **Let Pants track dependencies** - Don't manually determine what to test

## Troubleshooting

### Tests Run Slower Than Expected

**Check:**
1. Are you using target addresses? (not file paths)
2. Are pytest arguments consistent?
3. Is cache warm? (run `pants test ::` once)

### Cache Not Helping During TDD

**Common causes:**
1. Changing pytest arguments between runs
2. Mixing target addresses and file paths
3. Tests modifying source files (non-hermetic)

**Solution:** Use same target and args throughout session.

### Can't Find Specific Test

**Use pytest's verbose output:**
```bash
pants test epistemix_platform:src-tests -- -v
```

**Look for test names**, then use `-k`:
```bash
pants test epistemix_platform:src-tests -- -k test_name
```
