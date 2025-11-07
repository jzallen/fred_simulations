# TDD Workflow Guide

**When to read this:** When starting a new feature using TDD, learning the Red-Green-Refactor-Commit cycle, or organizing test code.

This guide provides detailed workflow steps, practical examples, and test organization strategies for practicing Test-Driven Development.

---

## Table of Contents

1. [The Red-Green-Refactor-Commit Cycle](#the-red-green-refactor-commit-cycle)
2. [FIRST Principles](#first-principles)
3. [Practical TDD Workflow](#practical-tdd-workflow)
4. [Test Organization](#test-organization)
5. [Complete Workflow Example](#complete-workflow-example)

---

## The Red-Green-Refactor-Commit Cycle

TDD follows a disciplined four-step cycle that ensures quality, maintainability, and confidence in your code.

### 1. RED - Write a Failing Test

**Goal:** Define what you want to develop

#### What to Do:
- Write a test that specifies the expected behavior
- The test MUST fail initially - this proves it's actually testing something
- Watch the test fail and read the error message carefully
- The failure message should be descriptive and reveal what's missing
- This step forces you to think about the API and behavior before implementation

#### Why It Matters:
- Proves the test can actually catch bugs
- Defines the interface you want (API design)
- Creates executable documentation of expected behavior
- Prevents "evergreen tests" that never fail

#### Example:
```python
def test_sort_array_ascending():
    # RED: This test will fail because sortArray doesn't exist yet
    result = sortArray([2, 4, 1])
    assert result == [1, 2, 4]
```

**Expected failure message:**
```
NameError: name 'sortArray' is not defined
```

#### Key Questions:
- What behavior do I want to implement?
- What should the API look like?
- What's the simplest test case I can write?
- Does the test fail for the right reason?

---

### 2. GREEN - Make It Pass

**Goal:** Get it working, don't worry about perfection yet

#### What to Do:
- Write the minimal code needed to make the test pass
- Don't over-engineer or add features not covered by the test
- Simplicity and speed over elegance at this stage
- Once green, you have a safety net for refactoring

#### Why It Matters:
- Validates that your test can pass
- Provides working code as quickly as possible
- Creates a safety net before optimization
- Keeps focus on solving one problem at a time

#### Example:
```python
def sortArray(arr):
    # GREEN: Simple implementation makes the test pass
    return sorted(arr)  # Use Python's built-in sort
```

**Test output:**
```
test_sort_array_ascending PASSED
```

#### The "Simplest Thing" Mindset:

Sometimes the simplest implementation is almost trivial:

```python
# First test
def test_get_greeting_returns_hello():
    assert get_greeting() == "Hello"

# Simplest implementation (yes, really!)
def get_greeting():
    return "Hello"
```

This feels silly, but it's valid TDD! Add more tests to drive out the general solution:

```python
# Second test forces generalization
def test_get_greeting_with_name_returns_personalized_greeting():
    assert get_greeting("Alice") == "Hello, Alice"

# Now we need a real implementation
def get_greeting(name=None):
    if name:
        return f"Hello, {name}"
    return "Hello"
```

#### Key Questions:
- What's the simplest code that makes this test pass?
- Am I adding features not covered by tests?
- Does the test actually pass now?
- Am I ready to refactor?

---

### 3. REFACTOR - Improve the Design

**Goal:** Clean up while maintaining green tests

#### What to Do:

**Six key questions to ask:**
1. Can I make my test suite more expressive?
2. Does my test suite provide reliable feedback?
3. Are my tests isolated from each other?
4. Can I reduce duplication in test or implementation code?
5. Can I make my implementation code more descriptive?
6. Can I implement something more efficiently?

#### Why It Matters:
- Improves design while preserving behavior
- Reduces technical debt immediately
- Makes code more maintainable
- Leverages the safety net of green tests

#### Important:
You can do whatever you like to the code when tests are green - the only thing you're not allowed to do is add or change behavior.

#### Example:
```python
def sortArray(arr):
    # REFACTOR: Replace with more efficient algorithm
    if len(arr) <= 1:
        return arr
    # Implement merge sort for better performance
    return merge_sort(arr)
```

**Test still passes:**
```
test_sort_array_ascending PASSED
```

#### Common Refactoring Opportunities:

**Extract Method:**
```python
# Before
def process_order(order):
    total = 0
    for item in order.items:
        total += item.price * item.quantity
    tax = total * 0.08
    return total + tax

# After
def process_order(order):
    subtotal = calculate_subtotal(order)
    tax = calculate_tax(subtotal)
    return subtotal + tax

def calculate_subtotal(order):
    return sum(item.price * item.quantity for item in order.items)

def calculate_tax(subtotal):
    return subtotal * 0.08
```

**Remove Duplication:**
```python
# Before - duplication in tests
def test_user_login_success():
    repository = InMemoryUserRepository()
    user = User(email="test@example.com", password="secret")
    repository.save(user)
    # ...

def test_user_login_failure():
    repository = InMemoryUserRepository()
    user = User(email="test@example.com", password="secret")
    repository.save(user)
    # ...

# After - extracted fixture
@pytest.fixture
def authenticated_user():
    repository = InMemoryUserRepository()
    user = User(email="test@example.com", password="secret")
    repository.save(user)
    return user, repository
```

**Improve Naming:**
```python
# Before
def calc(x, y):
    return x * y * 0.08

# After
def calculate_sales_tax(price, quantity):
    subtotal = price * quantity
    return subtotal * 0.08
```

#### Key Questions:
- Is there duplication I can remove?
- Can I make the code more readable?
- Are variable/function names clear?
- Can I simplify complex logic?
- Is there a more efficient algorithm?
- Are my tests as clean as my code?

---

### 4. COMMIT - Save Your Progress

**Goal:** Create granular, meaningful commits

#### What to Do:
- Commit after completing each RED-GREEN-REFACTOR cycle
- Each commit represents a working state with passing tests
- Optional: Commit before refactoring as an extra safety net
- Use descriptive commit messages that explain the behavior added
- Smaller, frequent commits are better than large, infrequent ones

#### Why It Matters:

**Benefits of frequent commits:**
- Reduces average work lost during reverts
- Creates a clear history aligned with test cases
- Makes code review easier
- Provides natural checkpoints for experimentation
- Tells a story of how the feature was built

#### Example Commit Messages:

```bash
# After RED-GREEN
git commit -m "feat: Add sortArray function with basic implementation"

# After REFACTOR
git commit -m "refactor: Replace bubble sort with merge sort for better performance"

# Another RED-GREEN cycle
git commit -m "feat: Add support for custom sort comparator"
```

#### Commit Frequency Strategies:

**Strategy 1: Commit after each cycle**
```
RED → GREEN → COMMIT → REFACTOR → COMMIT
```

**Strategy 2: Commit after refactor only**
```
RED → GREEN → REFACTOR → COMMIT
```

Both are valid. Choose what works for your team.

#### Key Questions:
- Are all tests passing?
- Is this a logical checkpoint?
- Does my commit message clearly explain what changed?
- Is the commit small enough to review easily?

---

## FIRST Principles

Write tests that follow FIRST principles for a robust test suite.

### F - Fast

**Tests should run quickly (milliseconds, not seconds)**

#### Why:
- Slow tests discourage running them frequently
- Fast feedback loop is essential for TDD
- Developer productivity depends on quick test cycles

#### How:
- Avoid I/O operations (disk, network, database) in unit tests
- Use in-memory implementations
- Mock external dependencies
- Keep test setup minimal

#### Example:

**Slow:**
```python
def test_user_registration():
    # Slow: Creates real database connection
    db = PostgreSQLDatabase("postgresql://localhost/test")
    db.execute("CREATE TABLE users ...")
    repository = UserRepository(db)
    # ...
    db.execute("DROP TABLE users")
```

**Fast:**
```python
def test_user_registration():
    # Fast: In-memory implementation
    repository = InMemoryUserRepository()
    # ... test runs in milliseconds
```

---

### I - Isolated

**Each test should be independent; no shared state between tests**

#### Why:
- Tests can run in any order
- Parallel test execution is possible
- Failures are easier to debug
- No cascading failures

#### How:
- Use fixtures to provide fresh state
- Avoid global variables
- Don't depend on test execution order
- Clean up after each test

#### Example:

**Not Isolated:**
```python
# BAD: Shared state
user_count = 0

def test_create_user():
    global user_count
    user_count += 1
    assert user_count == 1  # Breaks if run after test_create_admin

def test_create_admin():
    global user_count
    user_count += 1
    assert user_count == 1  # Breaks if run after test_create_user
```

**Isolated:**
```python
# GOOD: Each test is independent
def test_create_user(user_repository):
    user = User(email="test@example.com")
    user_repository.save(user)
    assert user_repository.count() == 1

def test_create_admin(user_repository):
    admin = Admin(email="admin@example.com")
    user_repository.save(admin)
    assert user_repository.count() == 1
```

---

### R - Repeatable

**Same results every time, regardless of environment or order**

#### Why:
- Builds confidence in tests
- No flaky tests
- Works on any machine
- Deterministic behavior

#### How:
- Avoid relying on system time or random values
- Don't depend on external services
- Use mocks for non-deterministic behavior
- Control all inputs

#### Example:

**Not Repeatable:**
```python
def test_user_age():
    # BAD: Result changes over time
    user = User(birth_year=2000)
    assert user.age == 24  # Fails in 2026!
```

**Repeatable:**
```python
def test_user_age():
    # GOOD: Explicit, controlled input
    user = User(birth_year=2000)
    age = user.calculate_age(current_year=2024)
    assert age == 24  # Always true
```

---

### S - Self-Validating

**Clear pass/fail without manual inspection**

#### Why:
- No ambiguity in results
- Can be automated
- Immediate feedback
- No human interpretation needed

#### How:
- Always use assertions
- Don't require manual inspection of output
- Make expected values explicit
- Use clear assertion messages

#### Example:

**Not Self-Validating:**
```python
def test_calculate_total():
    result = calculate_total([10, 20, 30])
    print(f"Total: {result}")  # BAD: Requires manual inspection
```

**Self-Validating:**
```python
def test_calculate_total():
    result = calculate_total([10, 20, 30])
    assert result == 60  # GOOD: Clear pass/fail
```

---

### T - Timely

**Written before (or at most, together with) the production code**

#### Why:
- Ensures tests can fail (not evergreen)
- Drives better API design
- Prevents implementation bias
- Forces thinking about requirements first

#### How:
- Write test first (RED)
- Then write minimal code to pass (GREEN)
- Finally refactor (REFACTOR)
- Never write code without a failing test first

#### Example:

**Timely (TDD way):**
```
1. Write test for feature X (RED)
2. Implement feature X (GREEN)
3. Refactor (REFACTOR)
4. Commit
```

**Not Timely (traditional way):**
```
1. Implement feature X
2. Write test for feature X (always passes - evergreen!)
```

---

## Practical TDD Workflow

A step-by-step guide to practicing TDD in real-world scenarios.

### 1. Start with the Simplest Test Case

- Don't try to test everything at once
- Begin with the happy path
- Add edge cases incrementally

#### Example: Building a Calculator

**Start simple:**
```python
# Test 1: Most basic case
def test_add_two_positive_numbers():
    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5
```

**Then add complexity:**
```python
# Test 2: Edge case
def test_add_zero():
    calc = Calculator()
    result = calc.add(5, 0)
    assert result == 5

# Test 3: Negative numbers
def test_add_negative_numbers():
    calc = Calculator()
    result = calc.add(-2, -3)
    assert result == -5

# Test 4: Mixed signs
def test_add_positive_and_negative():
    calc = Calculator()
    result = calc.add(10, -3)
    assert result == 7
```

---

### 2. Write the Test First

- Before writing any production code
- Think about the API you want
- Make the test fail explicitly

#### Example:

```python
# STEP 1: Write the test (it will fail)
def test_validate_email_format():
    validator = EmailValidator()
    assert validator.is_valid("test@example.com") is True
    assert validator.is_valid("invalid-email") is False
```

Run the test:
```bash
$ pants test epistemix_platform:src-tests -- -k test_validate_email
# NameError: EmailValidator is not defined
```

---

### 3. Make It Pass Quickly

- Use the simplest implementation
- Hard-code values if needed initially
- Generalize in refactor step

#### Example:

```python
# STEP 2: Minimal implementation
class EmailValidator:
    def is_valid(self, email):
        # Simple check - just enough to pass
        return "@" in email and "." in email
```

Run the test:
```bash
$ pants test epistemix_platform:src-tests -- -k test_validate_email
# PASSED
```

---

### 4. Refactor with Confidence

- Clean up duplication
- Improve naming
- Extract methods
- Optimize algorithms
- Tests guarantee behavior is preserved

#### Example:

```python
# STEP 3: Refactor with better implementation
import re

class EmailValidator:
    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    def is_valid(self, email):
        return bool(re.match(self.EMAIL_REGEX, email))
```

Run the test:
```bash
$ pants test epistemix_platform:src-tests -- -k test_validate_email
# PASSED - behavior preserved after refactor
```

---

### 5. Commit Frequently

- After each red-green-refactor cycle
- Small commits are easier to review and revert
- Clear history tells a story

#### Example:

```bash
# After GREEN
git add .
git commit -m "feat: Add EmailValidator with basic validation"

# After REFACTOR
git add .
git commit -m "refactor: Use regex for more robust email validation"
```

---

### 6. Add the Next Test

- Identify the next simplest case
- Repeat the cycle

#### Example:

```python
# Test 5: More edge cases
def test_validate_email_rejects_missing_domain():
    validator = EmailValidator()
    assert validator.is_valid("test@") is False

def test_validate_email_rejects_missing_username():
    validator = EmailValidator()
    assert validator.is_valid("@example.com") is False
```

---

## Test Organization

How to structure and organize your test code for maintainability and clarity.

### Directory Structure

```
epistemix_platform/
├── src/
│   └── epistemix_platform/
│       ├── models/           # Domain models
│       ├── use_cases/        # Business logic
│       ├── controllers/      # API controllers
│       └── repositories/     # Data access
└── tests/
    ├── unit/                 # Fast, isolated tests
    │   ├── test_models.py
    │   ├── test_use_cases.py
    │   └── test_repositories.py
    ├── integration/          # Tests with real dependencies
    │   ├── test_api_endpoints.py
    │   └── test_database.py
    ├── conftest.py           # Shared fixtures
    └── __init__.py
```

### Unit vs Integration Tests

**Unit Tests:**
- Test single units in isolation
- Fast (milliseconds)
- No I/O operations
- Use mocks for dependencies
- Run frequently during development

```python
# epistemix_platform/tests/unit/test_user_model.py
def test_user_password_verification():
    user = User(email="test@example.com", password="secret")
    assert user.verify_password("secret") is True
    assert user.verify_password("wrong") is False
```

**Integration Tests:**
- Test multiple components together
- Slower (seconds)
- May use real database/network
- Test actual integration points
- Run before commits/pushes

```python
# epistemix_platform/tests/integration/test_user_repository.py
def test_save_and_retrieve_user(database_connection):
    repository = UserRepository(database_connection)
    user = User(email="test@example.com")

    repository.save(user)
    retrieved = repository.get_by_email("test@example.com")

    assert retrieved.email == user.email
```

### Shared Fixtures (conftest.py)

Use `conftest.py` to share fixtures across multiple test files:

```python
# epistemix_platform/tests/conftest.py
import pytest

@pytest.fixture
def user_repository():
    """Shared fixture for all tests"""
    return InMemoryUserRepository()

@pytest.fixture(scope="module")
def database_connection():
    """Module-scoped database connection"""
    conn = create_test_database()
    yield conn
    conn.close()
```

Tests in any file can use these fixtures:

```python
# epistemix_platform/tests/unit/test_user_service.py
def test_register_user(user_repository):
    # Fixture automatically available
    service = UserService(user_repository)
    result = service.register("test@example.com", "password")
    assert result.success
```

### Test File Naming

Follow consistent naming conventions:

```
test_<module_name>.py
test_<feature_name>.py
```

Examples:
```
test_user_model.py
test_email_validator.py
test_order_processing.py
test_api_authentication.py
```

### Test Class Organization (Optional)

Group related tests in classes:

```python
class TestUserAuthentication:
    def test_login_with_valid_credentials_succeeds(self):
        pass

    def test_login_with_invalid_password_fails(self):
        pass

    def test_login_with_unknown_email_fails(self):
        pass

class TestUserRegistration:
    def test_register_with_valid_data_creates_user(self):
        pass

    def test_register_with_duplicate_email_fails(self):
        pass
```

Benefits:
- Groups related tests together
- Can share fixtures at class level
- Clearer test organization

**Note:** Class-based organization is optional. Many teams prefer flat function-based tests.

---

## Complete Workflow Example

Let's build a simple feature using TDD from start to finish.

### Feature: User Registration

**Requirements:**
- Users can register with email and password
- Email must be valid format
- Password must be at least 8 characters
- Email must be unique
- Send welcome email after registration

### Cycle 1: Basic Registration

**RED - Write failing test:**
```python
# tests/unit/test_user_registration.py
def test_register_user_with_valid_data_creates_user():
    # ARRANGE
    repository = InMemoryUserRepository()
    user_data = {
        "email": "alice@example.com",
        "password": "secure_password"
    }

    # ACT
    result = register_user(user_data, repository)

    # ASSERT
    assert result.success is True
    assert result.user.email == "alice@example.com"
    assert repository.count() == 1
```

**Run test:**
```bash
$ pants test epistemix_platform:src-tests -- -k test_register_user
# NameError: name 'register_user' is not defined
```

**GREEN - Minimal implementation:**
```python
# src/epistemix_platform/use_cases/user_registration.py
class RegistrationResult:
    def __init__(self, success, user=None, errors=None):
        self.success = success
        self.user = user
        self.errors = errors or []

def register_user(user_data, repository):
    user = User(
        email=user_data["email"],
        password=user_data["password"]
    )
    repository.save(user)
    return RegistrationResult(success=True, user=user)
```

**Run test:**
```bash
$ pants test epistemix_platform:src-tests -- -k test_register_user
# PASSED
```

**COMMIT:**
```bash
git add .
git commit -m "feat: Add basic user registration"
```

---

### Cycle 2: Email Validation

**RED - Write failing test:**
```python
def test_register_user_with_invalid_email_fails():
    # ARRANGE
    repository = InMemoryUserRepository()
    user_data = {
        "email": "invalid-email",
        "password": "secure_password"
    }

    # ACT
    result = register_user(user_data, repository)

    # ASSERT
    assert result.success is False
    assert "email" in result.errors
    assert repository.count() == 0
```

**Run test:**
```bash
$ pants test epistemix_platform:src-tests -- -k test_register_user_with_invalid_email
# AssertionError: assert True is False (test fails - needs email validation)
```

**GREEN - Add validation:**
```python
import re

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def register_user(user_data, repository):
    # Validate email
    if not is_valid_email(user_data["email"]):
        return RegistrationResult(
            success=False,
            errors=["email: invalid format"]
        )

    user = User(
        email=user_data["email"],
        password=user_data["password"]
    )
    repository.save(user)
    return RegistrationResult(success=True, user=user)
```

**Run tests:**
```bash
$ pants test epistemix_platform:src-tests -- -k test_register_user
# All tests PASSED
```

**REFACTOR - Extract validator:**
```python
# src/epistemix_platform/validators/email_validator.py
import re

class EmailValidator:
    PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    def is_valid(self, email):
        return bool(re.match(self.PATTERN, email))

# src/epistemix_platform/use_cases/user_registration.py
def register_user(user_data, repository, email_validator=None):
    email_validator = email_validator or EmailValidator()

    if not email_validator.is_valid(user_data["email"]):
        return RegistrationResult(
            success=False,
            errors=["email: invalid format"]
        )

    user = User(
        email=user_data["email"],
        password=user_data["password"]
    )
    repository.save(user)
    return RegistrationResult(success=True, user=user)
```

**Run tests:**
```bash
$ pants test epistemix_platform:src-tests -- -k test_register_user
# All tests PASSED
```

**COMMIT:**
```bash
git add .
git commit -m "feat: Add email validation to user registration"
```

---

### Cycle 3: Password Length

**RED - Write failing test:**
```python
def test_register_user_with_short_password_fails():
    # ARRANGE
    repository = InMemoryUserRepository()
    user_data = {
        "email": "alice@example.com",
        "password": "short"
    }

    # ACT
    result = register_user(user_data, repository)

    # ASSERT
    assert result.success is False
    assert "password" in result.errors[0]
    assert repository.count() == 0
```

**GREEN - Add password validation:**
```python
def register_user(user_data, repository, email_validator=None):
    email_validator = email_validator or EmailValidator()
    errors = []

    # Validate email
    if not email_validator.is_valid(user_data["email"]):
        errors.append("email: invalid format")

    # Validate password
    if len(user_data["password"]) < 8:
        errors.append("password: must be at least 8 characters")

    if errors:
        return RegistrationResult(success=False, errors=errors)

    user = User(
        email=user_data["email"],
        password=user_data["password"]
    )
    repository.save(user)
    return RegistrationResult(success=True, user=user)
```

**REFACTOR - Extract password validator:**
```python
# src/epistemix_platform/validators/password_validator.py
class PasswordValidator:
    MIN_LENGTH = 8

    def is_valid(self, password):
        return len(password) >= self.MIN_LENGTH

# Update register_user
def register_user(
    user_data,
    repository,
    email_validator=None,
    password_validator=None
):
    email_validator = email_validator or EmailValidator()
    password_validator = password_validator or PasswordValidator()
    errors = []

    if not email_validator.is_valid(user_data["email"]):
        errors.append("email: invalid format")

    if not password_validator.is_valid(user_data["password"]):
        errors.append("password: must be at least 8 characters")

    if errors:
        return RegistrationResult(success=False, errors=errors)

    user = User(
        email=user_data["email"],
        password=user_data["password"]
    )
    repository.save(user)
    return RegistrationResult(success=True, user=user)
```

**COMMIT:**
```bash
git add .
git commit -m "feat: Add password length validation"
```

---

### Continue the Cycle

Keep adding tests and implementing features:

**Cycle 4: Unique email constraint**
**Cycle 5: Send welcome email**
**Cycle 6: Error handling**

Each cycle follows: RED → GREEN → REFACTOR → COMMIT

---

## Summary

**The TDD Workflow:**

1. **RED** - Write a failing test first
2. **GREEN** - Make it pass with minimal code
3. **REFACTOR** - Improve the design
4. **COMMIT** - Save your progress

**FIRST Principles:**
- **F**ast - Tests run in milliseconds
- **I**solated - Independent, no shared state
- **R**epeatable - Same results every time
- **S**elf-validating - Clear pass/fail
- **T**imely - Written before production code

**Key Practices:**
- Start with the simplest test case
- Write the test first (always!)
- Make it pass quickly
- Refactor with confidence
- Commit frequently
- Add the next test
- Organize tests clearly

**Remember:**
- TDD is about design feedback - tests reveal how easy your code is to use
- Start simple - baby steps lead to robust solutions
- Refactor is mandatory - not optional, not "later", now
- Tests are documentation - they show how code should be used
- Listen to pain - hard tests mean hard code
- Commit often - smaller changes, clearer history

When you practice TDD rigorously, you'll find yourself saving time, writing less code, and implementing more robust solutions than you otherwise would have.
