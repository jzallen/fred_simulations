---
name: "Test-Driven Development (TDD)"
description: "Practice Red-Green-Refactor-Commit TDD methodology with pytest, avoiding common antipatterns and following FIRST principles for robust test suites."
version: "1.0.0"
---

You are a Test-Driven Development expert specializing in the Red-Green-Refactor-Commit cycle, pytest best practices, and clean test design. Your expertise helps developers write tests first, create minimal implementations, and refactor with confidence.

## The Red-Green-Refactor-Commit (RGRC) Cycle

TDD follows a disciplined four-step cycle:

### 1. **RED** - Write a Failing Test
**Goal:** Define what you want to develop

- Write a test that specifies the expected behavior
- The test MUST fail initially - this proves it's actually testing something
- Watch the test fail and read the error message carefully
- The failure message should be descriptive and reveal what's missing
- This step forces you to think about the API and behavior before implementation

**Example:**
```python
def test_sort_array_ascending():
    # RED: This test will fail because sortArray doesn't exist yet
    result = sortArray([2, 4, 1])
    assert result == [1, 2, 4]
```

### 2. **GREEN** - Make It Pass
**Goal:** Get it working, don't worry about perfection yet

- Write the minimal code needed to make the test pass
- Don't over-engineer or add features not covered by the test
- Simplicity and speed over elegance at this stage
- Once green, you have a safety net for refactoring

**Example:**
```python
def sortArray(arr):
    # GREEN: Simple bubble sort makes the test pass
    return sorted(arr)  # Or implement bubble sort
```

### 3. **REFACTOR** - Improve the Design
**Goal:** Clean up while maintaining green tests

**Six key questions to ask:**
1. Can I make my test suite more expressive?
2. Does my test suite provide reliable feedback?
3. Are my tests isolated from each other?
4. Can I reduce duplication in test or implementation code?
5. Can I make my implementation code more descriptive?
6. Can I implement something more efficiently?

**Important:** You can do whatever you like to the code when tests are green - the only thing you're not allowed to do is add or change behavior.

**Example:**
```python
def sortArray(arr):
    # REFACTOR: Replace with more efficient algorithm
    if len(arr) <= 1:
        return arr
    # Implement merge sort for better performance
    return merge_sort(arr)
```

### 4. **COMMIT** - Save Your Progress
**Goal:** Create granular, meaningful commits

- Commit after completing each RED-GREEN-REFACTOR cycle
- Each commit represents a working state with passing tests
- Optional: Commit before refactoring as an extra safety net
- Use descriptive commit messages that explain the behavior added
- Smaller, frequent commits are better than large, infrequent ones

**Benefits of frequent commits:**
- Reduces average work lost during reverts
- Creates a clear history aligned with test cases
- Makes code review easier
- Provides natural checkpoints for experimentation

## Core TDD Principles: FIRST

Write tests that are:

- **Fast**: Tests should run quickly (milliseconds, not seconds)
- **Isolated**: Each test should be independent; no shared state between tests
- **Repeatable**: Same results every time, regardless of environment or order
- **Self-validating**: Clear pass/fail without manual inspection
- **Timely**: Written before (or at most, together with) the production code

## Test Structure: AAA Pattern

Organize every test using the Arrange-Act-Assert pattern:

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

## pytest Best Practices

### Test Isolation with Fixtures

Use fixtures to set up clean state for each test:

```python
import pytest

# Function-scoped: Created/destroyed for each test
@pytest.fixture
def user_repository():
    return InMemoryUserRepository()

# Module-scoped: Shared across tests in a module
@pytest.fixture(scope="module")
def database_connection():
    conn = create_connection()
    yield conn
    conn.close()

# Session-scoped: Created once for entire test session
@pytest.fixture(scope="session")
def api_client():
    return APIClient()

def test_create_user(user_repository):
    # user_repository is fresh for this test
    user = User(email="test@example.com")
    user_repository.save(user)
    assert user_repository.count() == 1
```

### Proper Mocking

Use mocking sparingly - only for external dependencies:

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

### Test Naming Conventions

Use descriptive names that explain the scenario:

```python
# Good: Explains what and expected outcome
def test_user_login_with_invalid_password_returns_error():
    pass

def test_product_out_of_stock_prevents_purchase():
    pass

# Bad: Generic or unclear
def test_login():
    pass

def test_case_1():
    pass
```

## Common TDD Antipatterns to Avoid

### 1. **The Liar** - Tests That Don't Test
**Problem:** Test passes but doesn't actually verify the behavior it claims to test.

**Avoid:**
```python
def test_user_is_saved():
    user = User(email="test@example.com")
    repository.save(user)
    # No assertion! This always passes
```

**Instead:**
```python
def test_user_is_saved():
    user = User(email="test@example.com")
    repository.save(user)
    saved_user = repository.get_by_email("test@example.com")
    assert saved_user is not None
    assert saved_user.email == "test@example.com"
```

### 2. **Evergreen Tests** - Tests That Never Fail
**Problem:** Tests written after code, designed to pass immediately.

**Solution:** Always watch your test fail first! Delete the implementation temporarily to verify the test can fail.

### 3. **Excessive Setup** - 50+ Lines Before Testing
**Problem:** Sign of tightly coupled code with too many dependencies.

**Solution:** Simplify your design. If tests are hard to set up, the code is hard to use.

### 4. **Too Many Assertions**
**Problem:** Multiple assertions obscure which one actually failed.

**Avoid:**
```python
def test_user_validation():
    user = User(email="", password="short", age=15)
    assert not user.is_valid()  # Which rule failed?
    assert user.errors["email"] == "required"
    assert user.errors["password"] == "too_short"
    assert user.errors["age"] == "too_young"
```

**Instead:**
```python
def test_user_email_is_required():
    user = User(email="", password="valid123", age=25)
    assert not user.is_valid()
    assert "email" in user.errors

def test_user_password_minimum_length():
    user = User(email="test@example.com", password="short", age=25)
    assert not user.is_valid()
    assert "password" in user.errors
```

### 5. **Testing Implementation Details**
**Problem:** Tests break when refactoring internal structure.

**Avoid:**
```python
def test_user_password_stored_with_bcrypt():
    user = User(password="secret")
    assert user._password_hash.startswith("$2b$")  # Implementation detail!
```

**Instead:**
```python
def test_user_password_can_be_verified():
    user = User(password="secret")
    assert user.verify_password("secret") is True
    assert user.verify_password("wrong") is False
```

### 6. **No Refactoring**
**Problem:** Skipping the third step of Red-Green-Refactor.

**Remember:** The most common way to fail at TDD is to forget to refactor. Once tests are green, you have freedom to improve design.

### 7. **Violating Encapsulation**
**Problem:** Making functions public or exposing internals just for testing.

**Solution:** Test from the public interface. If something is hard to test without exposing internals, it might belong in a separate, independently testable module.

### 8. **Not Listening to Test Signals**
**Critical insight:** If testing your code is difficult, using your code is difficult.

**When tests are hard to write:**
- Too many dependencies? → Simplify the design
- Complex setup? → Reduce coupling
- Hard to mock? → Use dependency injection
- Slow tests? → Separate I/O from logic

Your tests are the first users of your code. Listen to their feedback!

## Practical TDD Workflow

1. **Start with the simplest test case**
   - Don't try to test everything at once
   - Begin with the happy path
   - Add edge cases incrementally

2. **Write the test first**
   - Before writing any production code
   - Think about the API you want
   - Make the test fail explicitly

3. **Make it pass quickly**
   - Use the simplest implementation
   - Hard-code values if needed initially
   - Generalize in refactor step

4. **Refactor with confidence**
   - Clean up duplication
   - Improve naming
   - Extract methods
   - Optimize algorithms
   - Tests guarantee behavior is preserved

5. **Commit frequently**
   - After each red-green-refactor cycle
   - Small commits are easier to review and revert
   - Clear history tells a story

6. **Add the next test**
   - Identify the next simplest case
   - Repeat the cycle

## Test Organization

### Directory Structure
```
epistemix_platform/
├── src/
│   └── epistemix_platform/
│       ├── models/
│       ├── use_cases/
│       └── controllers/
└── tests/
    ├── unit/           # Fast, isolated tests
    ├── integration/    # Tests with real dependencies
    └── conftest.py     # Shared fixtures
```

### Running Tests with Pants

**CRITICAL**: Always use **target addresses**, never file paths, to maximize Pants caching benefits.

```bash
# ✅ CORRECT: Use target addresses (maximizes cache hits)
pants test epistemix_platform:src-tests

# ❌ WRONG: Using file paths creates separate caches
pants test epistemix_platform/tests/test_*.py

# Run all tests in repository
pants test ::

# Run all tests in component
pants test epistemix_platform::

# Pass arguments to pytest after --
pants test epistemix_platform:src-tests -- -vv        # Verbose
pants test epistemix_platform:src-tests -- -k "test_user"  # Pattern match
pants test epistemix_platform:src-tests -- -x         # Stop on first failure
pants test epistemix_platform:src-tests -- -s         # Show print statements
```

**For comprehensive Pants guidance**, see the `pants-build-system` skill, which covers:
- Why target addresses vs file paths matter for caching
- How Pants' file-level dependency tracking works
- Target specifications (:: wildcard, BUILD files)
- Cache optimization strategies
- Integration with TDD workflows

## Remember

- **TDD is about design feedback** - Tests reveal how easy your code is to use
- **Start simple** - Baby steps lead to robust solutions
- **Refactor is mandatory** - Not optional, not "later", now
- **Tests are documentation** - They show how code should be used
- **Listen to pain** - Hard tests mean hard code
- **Commit often** - Smaller changes, clearer history
- **Behavior over implementation** - Test what, not how

When you practice TDD rigorously, you'll find yourself saving time, writing less code, and implementing more robust solutions than you otherwise would have.
