# pytest Best Practices Guide

**When to read this:** When writing tests with pytest, setting up test fixtures, using mocks, or organizing test code.

This comprehensive guide covers pytest best practices, fixtures, mocking patterns, and test organization strategies.

---

## Table of Contents

1. [Test Structure: AAA Pattern](#test-structure-aaa-pattern)
2. [Fixtures and Test Isolation](#fixtures-and-test-isolation)
3. [Fixture Scopes](#fixture-scopes)
4. [Proper Mocking](#proper-mocking)
5. [Test Naming Conventions](#test-naming-conventions)
6. [Running Tests with Pants](#running-tests-with-pants)

---

## Test Structure: AAA Pattern

Every test should follow the **Arrange-Act-Assert** pattern for clarity and consistency.

### The Pattern

```python
def test_user_registration():
    # ARRANGE: Set up test data and dependencies
    user_data = {"email": "test@example.com", "password": "secret123"}
    repository = InMemoryUserRepository()

    # ACT: Perform the action being tested
    result = register_user(user_data, repository)

    # ASSERT: Verify the outcome
    assert result.email == "test@example.com"
    assert repository.count() == 1
```

### Why AAA?

- **Clarity:** Each test section has a clear purpose
- **Readability:** Others can quickly understand what's being tested
- **Maintainability:** Easy to modify individual sections
- **Debugging:** When a test fails, you can quickly identify which phase failed

### Detailed Breakdown

#### Arrange
Set up the test scenario:
- Create test data
- Initialize dependencies (repositories, services, etc.)
- Configure mocks or test doubles
- Establish preconditions

```python
# ARRANGE
user_data = {
    "email": "alice@example.com",
    "password": "secure_password",
    "age": 25
}
repository = InMemoryUserRepository()
validator = UserValidator(min_age=18)
```

#### Act
Execute the code under test:
- Call the function/method being tested
- Perform a single action
- Keep this section minimal (usually one line)

```python
# ACT
result = register_user(user_data, repository, validator)
```

#### Assert
Verify the outcome:
- Check return values
- Verify state changes
- Validate side effects
- Confirm mock calls (if applicable)

```python
# ASSERT
assert result.success is True
assert result.user.email == "alice@example.com"
assert repository.count() == 1
saved_user = repository.get_by_email("alice@example.com")
assert saved_user is not None
```

### Visual Separation

Use blank lines to visually separate the three sections:

```python
def test_order_total_calculation():
    # ARRANGE
    items = [
        OrderItem(price=10.00, quantity=2),
        OrderItem(price=5.00, quantity=3)
    ]
    order = Order(items=items)

    # ACT
    total = order.calculate_total()

    # ASSERT
    assert total == 35.00
```

---

## Fixtures and Test Isolation

Fixtures are pytest's way of providing reusable setup and teardown logic for tests.

### Basic Fixture

```python
import pytest

@pytest.fixture
def user_repository():
    """Provides a fresh repository for each test"""
    return InMemoryUserRepository()

def test_create_user(user_repository):
    # user_repository is fresh for this test
    user = User(email="test@example.com")
    user_repository.save(user)
    assert user_repository.count() == 1

def test_delete_user(user_repository):
    # user_repository is fresh again (no data from previous test)
    user = User(email="test@example.com")
    user_repository.save(user)
    user_repository.delete(user.email)
    assert user_repository.count() == 0
```

### Why Fixtures?

- **Isolation:** Each test gets fresh state
- **Reusability:** Share setup code across multiple tests
- **Clarity:** Setup logic has a descriptive name
- **Automatic cleanup:** Fixtures handle teardown automatically

### Fixture with Setup and Teardown

Use `yield` to provide cleanup:

```python
@pytest.fixture
def database_connection():
    # SETUP: Code before yield runs before the test
    conn = create_database_connection()
    conn.begin_transaction()

    yield conn  # Provide the connection to the test

    # TEARDOWN: Code after yield runs after the test
    conn.rollback()
    conn.close()

def test_insert_user(database_connection):
    database_connection.execute("INSERT INTO users ...")
    # Transaction is automatically rolled back after test
```

### Fixture Composition

Fixtures can depend on other fixtures:

```python
@pytest.fixture
def database():
    return Database(connection_string="...")

@pytest.fixture
def user_repository(database):
    return UserRepository(database)

@pytest.fixture
def user_service(user_repository):
    return UserService(user_repository)

def test_register_user(user_service):
    # user_service automatically gets database and repository
    result = user_service.register("test@example.com", "password")
    assert result.success
```

---

## Fixture Scopes

Fixtures can have different scopes to control when they're created and destroyed.

### Available Scopes

1. **function** (default) - Created for each test function
2. **class** - Created once per test class
3. **module** - Created once per test module (file)
4. **package** - Created once per package
5. **session** - Created once per entire test session

### Function Scope (Default)

Created and destroyed for each test:

```python
@pytest.fixture  # scope="function" is default
def user_repository():
    return InMemoryUserRepository()

def test_first(user_repository):
    user_repository.save(User(email="test1@example.com"))
    assert user_repository.count() == 1

def test_second(user_repository):
    # Fresh repository - count is 0, not 1
    assert user_repository.count() == 0
```

**Use for:**
- In-memory data structures
- Mocks and test doubles
- Anything that should be fresh for each test

### Module Scope

Shared across all tests in a file:

```python
@pytest.fixture(scope="module")
def database_connection():
    """Expensive connection created once per module"""
    print("Creating database connection...")
    conn = create_connection()
    yield conn
    print("Closing database connection...")
    conn.close()

def test_first(database_connection):
    # Connection is created
    database_connection.execute("SELECT 1")

def test_second(database_connection):
    # Same connection instance is reused
    database_connection.execute("SELECT 2")

# Connection is closed after all tests in the module
```

**Use for:**
- Expensive resources (database connections, API clients)
- Read-only shared data
- Resources that are safe to share

**Warning:** Be careful of shared state! Module-scoped fixtures should not accumulate state between tests.

### Session Scope

Created once for the entire test run:

```python
@pytest.fixture(scope="session")
def api_client():
    """Single API client for entire test session"""
    client = APIClient()
    client.authenticate()
    return client

def test_api_endpoint_one(api_client):
    response = api_client.get("/users")
    assert response.status == 200

def test_api_endpoint_two(api_client):
    # Same client instance
    response = api_client.get("/posts")
    assert response.status == 200
```

**Use for:**
- Very expensive one-time setup (test databases, Docker containers)
- Read-only configuration
- Shared resources across all tests

### Class Scope

Created once per test class:

```python
@pytest.fixture(scope="class")
def calculator():
    return Calculator()

class TestCalculator:
    def test_add(self, calculator):
        assert calculator.add(2, 3) == 5

    def test_subtract(self, calculator):
        # Same calculator instance
        assert calculator.subtract(5, 3) == 2
```

**Use for:**
- Grouping related tests that can share setup
- Less common than function or module scope

### Scope Decision Guide

| Scope | Lifespan | Use When | Risk |
|-------|----------|----------|------|
| function | Each test | Default choice, fresh state | None - fully isolated |
| module | Per file | Expensive setup, read-only | Shared state can leak |
| class | Per class | Grouped related tests | Shared state can leak |
| session | Entire run | Very expensive (databases, containers) | State leaks across all tests |

**Default Rule:** Use function scope unless you have a specific reason not to.

---

## Proper Mocking

Use mocking sparingly - only for external dependencies and I/O operations.

### When to Mock

**DO mock:**
- External APIs and services
- Database connections
- File system operations
- Network calls
- Email services
- Time/randomness (for deterministic tests)

**DON'T mock:**
- Your own business logic
- Simple data structures
- Pure functions
- Internal objects (use real instances instead)

### Basic Mock Usage

```python
from unittest.mock import Mock, patch

def test_send_welcome_email():
    # ARRANGE: Mock external email service
    mock_emailer = Mock()
    user = User(email="test@example.com")

    # ACT
    send_welcome_email(user, mock_emailer)

    # ASSERT: Verify the mock was called correctly
    mock_emailer.send.assert_called_once_with(
        to="test@example.com",
        subject="Welcome!"
    )
```

### Mock Return Values

```python
def test_user_lookup_by_email():
    # ARRANGE
    mock_api = Mock()
    mock_api.get_user.return_value = {"id": 123, "email": "test@example.com"}

    # ACT
    user = fetch_user_by_email("test@example.com", api=mock_api)

    # ASSERT
    assert user["id"] == 123
    mock_api.get_user.assert_called_once_with(email="test@example.com")
```

### Mock Side Effects

```python
def test_handles_api_timeout():
    # ARRANGE
    mock_api = Mock()
    mock_api.get_user.side_effect = TimeoutError("Connection timed out")

    # ACT & ASSERT
    with pytest.raises(TimeoutError):
        fetch_user_by_email("test@example.com", api=mock_api)
```

### Patching

Use `patch` to replace objects during tests:

```python
@patch('my_module.send_email')
def test_user_registration_sends_email(mock_send_email):
    # ARRANGE
    user_data = {"email": "test@example.com", "password": "secret"}

    # ACT
    register_user(user_data)

    # ASSERT
    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args
    assert call_args[0][0] == "test@example.com"
```

### Context Manager Patching

```python
def test_user_registration_sends_email():
    with patch('my_module.send_email') as mock_send_email:
        # ARRANGE
        user_data = {"email": "test@example.com", "password": "secret"}

        # ACT
        register_user(user_data)

        # ASSERT
        mock_send_email.assert_called_once()
```

### Mock Assertions

Common assertion methods:

```python
mock.assert_called()                    # Called at least once
mock.assert_called_once()               # Called exactly once
mock.assert_called_with(arg1, arg2)     # Last call had these args
mock.assert_called_once_with(arg1)      # Called once with these args
mock.assert_not_called()                # Never called
mock.assert_any_call(arg1)              # Any call had these args

# Check call count
assert mock.call_count == 3

# Inspect all calls
assert len(mock.call_args_list) == 2
first_call = mock.call_args_list[0]
```

### Prefer Dependency Injection Over Patching

**Instead of patching:**
```python
# Hard to test - send_email is imported at module level
def register_user(email):
    send_email(email, "Welcome!")
    return User(email=email)

# Test requires patching
@patch('my_module.send_email')
def test_register_user(mock_send_email):
    register_user("test@example.com")
    mock_send_email.assert_called()
```

**Better with dependency injection:**
```python
# Easy to test - emailer is injected
def register_user(email, emailer):
    emailer.send(email, "Welcome!")
    return User(email=email)

# Test with a simple mock
def test_register_user():
    mock_emailer = Mock()
    user = register_user("test@example.com", mock_emailer)
    mock_emailer.send.assert_called_once()
```

---

## Test Naming Conventions

Use descriptive names that explain the scenario and expected outcome.

### Good Naming Pattern

**Format:** `test_<unit>_<scenario>_<expected_outcome>`

```python
# Explains what's tested, the condition, and the result
def test_user_login_with_invalid_password_returns_error():
    pass

def test_product_out_of_stock_prevents_purchase():
    pass

def test_order_total_with_discount_code_reduces_price():
    pass

def test_email_validator_with_invalid_format_returns_false():
    pass
```

### Good Examples

```python
# Clear and specific
def test_transfer_with_insufficient_funds_raises_error():
    pass

def test_search_with_empty_query_returns_all_results():
    pass

def test_file_upload_with_large_file_rejects_upload():
    pass

def test_cache_get_with_expired_entry_returns_none():
    pass
```

### Bad Examples

```python
# Too generic
def test_login():
    pass

def test_validation():
    pass

# Unclear
def test_case_1():
    pass

def test_user_test():
    pass

# Not descriptive
def test_error():
    pass

def test_it_works():
    pass
```

### Naming Guidelines

1. **Be specific:** State what's being tested
2. **Include the scenario:** What conditions are we testing under?
3. **State the expected outcome:** What should happen?
4. **Use underscores:** Separate words for readability
5. **No need to abbreviate:** Longer names are fine if they're clear

### Alternative Naming Pattern

Some teams prefer a more sentence-like structure:

```python
def test_should_reject_login_when_password_is_invalid():
    pass

def test_should_return_empty_list_when_no_results_found():
    pass
```

Choose one pattern and be consistent across your codebase.

---

## Running Tests with Pants

**CRITICAL:** Always use **target addresses**, never file paths, to maximize Pants caching benefits.

### Why Target Addresses Matter

Pants creates separate caches for different invocation styles:
- File paths: Each file gets its own cache
- Target addresses: All matching tests share cache

**Use target addresses to avoid cache duplication and get faster test runs!**

### Basic Test Commands

```bash
# ✅ CORRECT: Use target addresses (maximizes cache hits)
pants test epistemix_platform:src-tests

# ❌ WRONG: Using file paths creates separate caches
pants test epistemix_platform/tests/test_*.py
```

### Common Test Invocations

```bash
# Run all tests in repository
pants test ::

# Run all tests in a component
pants test epistemix_platform::
pants test simulation_runner::

# Run specific test target
pants test epistemix_platform:src-tests
```

### Passing Arguments to pytest

Use `--` to pass arguments directly to pytest:

```bash
# Verbose output
pants test epistemix_platform:src-tests -- -vv

# Run tests matching a pattern
pants test epistemix_platform:src-tests -- -k "test_user"

# Stop on first failure
pants test epistemix_platform:src-tests -- -x

# Show print statements
pants test epistemix_platform:src-tests -- -s

# Run specific test file (by path, after --)
pants test epistemix_platform:src-tests -- epistemix_platform/tests/test_user.py

# Run specific test function
pants test epistemix_platform:src-tests -- epistemix_platform/tests/test_user.py::test_user_creation

# Show test duration
pants test epistemix_platform:src-tests -- --durations=10

# Run in parallel (if pytest-xdist installed)
pants test epistemix_platform:src-tests -- -n auto
```

### Combining Options

```bash
# Verbose, stop on first failure, show print statements
pants test epistemix_platform:src-tests -- -vv -x -s

# Run pattern match with parallel execution
pants test epistemix_platform:src-tests -- -k "integration" -n auto
```

### Common pytest Flags

| Flag | Description |
|------|-------------|
| `-v` | Verbose (show test names) |
| `-vv` | More verbose (show more details) |
| `-s` | Show print statements |
| `-x` | Stop on first failure |
| `-k "pattern"` | Run tests matching pattern |
| `--lf` | Run last failed tests |
| `--ff` | Run failures first, then others |
| `-n auto` | Parallel execution (requires pytest-xdist) |
| `--durations=N` | Show N slowest tests |
| `--pdb` | Drop into debugger on failure |
| `-m marker` | Run tests with specific marker |

### Test Markers

Use markers to categorize tests:

```python
import pytest

@pytest.mark.slow
def test_large_dataset_processing():
    pass

@pytest.mark.integration
def test_database_connection():
    pass

@pytest.mark.unit
def test_pure_function():
    pass
```

Run specific markers:

```bash
# Run only unit tests
pants test epistemix_platform:src-tests -- -m unit

# Skip slow tests
pants test epistemix_platform:src-tests -- -m "not slow"

# Run integration tests only
pants test epistemix_platform:src-tests -- -m integration
```

### Watch Mode (with pytest-watch)

For TDD workflow, use watch mode to automatically re-run tests:

```bash
# Requires pytest-watch: pip install pytest-watch
ptw epistemix_platform/tests -- -x -s
```

### Coverage Reports

```bash
# Run with coverage (requires pytest-cov)
pants test epistemix_platform:src-tests -- --cov=epistemix_platform --cov-report=html

# View coverage in terminal
pants test epistemix_platform:src-tests -- --cov=epistemix_platform --cov-report=term-missing
```

---

## Complete Example

Putting it all together:

```python
import pytest
from unittest.mock import Mock

# FIXTURES

@pytest.fixture
def user_repository():
    """Provides fresh in-memory repository for each test"""
    return InMemoryUserRepository()

@pytest.fixture(scope="module")
def email_validator():
    """Shared email validator for all tests in module"""
    return EmailValidator()

@pytest.fixture
def mock_email_service():
    """Mock email service for testing notifications"""
    return Mock()

# TESTS

def test_register_user_with_valid_data_creates_user(user_repository, email_validator):
    # ARRANGE
    user_data = {
        "email": "alice@example.com",
        "password": "secure_password"
    }

    # ACT
    result = register_user(user_data, user_repository, email_validator)

    # ASSERT
    assert result.success is True
    assert user_repository.count() == 1
    saved_user = user_repository.get_by_email("alice@example.com")
    assert saved_user is not None

def test_register_user_with_invalid_email_returns_error(user_repository, email_validator):
    # ARRANGE
    user_data = {
        "email": "invalid-email",
        "password": "secure_password"
    }

    # ACT
    result = register_user(user_data, user_repository, email_validator)

    # ASSERT
    assert result.success is False
    assert "email" in result.errors
    assert user_repository.count() == 0

def test_register_user_sends_welcome_email(user_repository, email_validator, mock_email_service):
    # ARRANGE
    user_data = {
        "email": "alice@example.com",
        "password": "secure_password"
    }

    # ACT
    register_user(user_data, user_repository, email_validator, mock_email_service)

    # ASSERT
    mock_email_service.send.assert_called_once_with(
        to="alice@example.com",
        subject="Welcome!",
        body=pytest.approx_contains("alice@example.com")  # Flexible matching
    )
```

---

## Further Resources

For comprehensive Pants guidance, see the `pants-build-system` skill, which covers:
- Why target addresses vs file paths matter for caching
- How Pants' file-level dependency tracking works
- Target specifications (:: wildcard, BUILD files)
- Cache optimization strategies
- Integration with TDD workflows

---

## Summary

**Key pytest best practices:**

1. **Use AAA pattern** - Arrange, Act, Assert for every test
2. **Prefer function-scoped fixtures** - Default to fresh state
3. **Mock only external dependencies** - Don't mock your own code
4. **Use descriptive test names** - Explain scenario and expected outcome
5. **Run tests with target addresses** - Maximize Pants caching
6. **Keep tests isolated** - No shared state between tests
7. **One logical assertion per test** - Clear failure messages

**Remember:** Good tests are fast, isolated, repeatable, self-validating, and timely (FIRST principles).
