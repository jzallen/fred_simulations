# TDD Anti-Patterns Reference

**When to read this:** When reviewing test code, investigating flaky tests, or learning what to avoid when writing tests.

This document details the 8 most common TDD anti-patterns, their problems, and solutions.

---

## 1. The Liar - Tests That Don't Test

**Problem:** Test passes but doesn't actually verify the behavior it claims to test.

### Avoid This:
```python
def test_user_is_saved():
    user = User(email="test@example.com")
    repository.save(user)
    # No assertion! This always passes
```

### Do This Instead:
```python
def test_user_is_saved():
    user = User(email="test@example.com")
    repository.save(user)
    saved_user = repository.get_by_email("test@example.com")
    assert saved_user is not None
    assert saved_user.email == "test@example.com"
```

### Key Points:
- Always include assertions that verify the expected behavior
- Test the observable outcome, not just that code runs without errors
- If there's no assertion, the test is lying about what it verifies

---

## 2. Evergreen Tests - Tests That Never Fail

**Problem:** Tests written after code, designed to pass immediately. They provide false confidence because they've never proven they can catch bugs.

### Why It's Problematic:
- You don't know if the test actually validates anything
- The test might be checking the wrong thing
- It may pass even when the feature is broken

### Solution:
- **Always watch your test fail first!**
- Write the test before the implementation
- If you write tests after code, temporarily delete or break the implementation to verify the test can fail
- A test that has never failed has never proven its value

### The TDD Rule:
> You cannot write a test without first seeing it fail. If you haven't seen it red, you haven't tested anything.

---

## 3. Excessive Setup - 50+ Lines Before Testing

**Problem:** Tests require massive setup (50+ lines) before getting to the actual test. This is a sign of tightly coupled code with too many dependencies.

### What It Signals:
- Your code has too many dependencies
- Classes are doing too much (violating Single Responsibility Principle)
- Poor separation of concerns
- Tight coupling between components

### Example of the Problem:
```python
def test_process_order():
    # 50+ lines of setup...
    db = Database("connection_string")
    email_service = EmailService(api_key="...")
    payment_gateway = PaymentGateway(merchant_id="...")
    inventory_service = InventoryService(db)
    shipping_service = ShippingService(api_key="...")
    tax_calculator = TaxCalculator(region="US", db=db)
    discount_engine = DiscountEngine(db, email_service)
    order_processor = OrderProcessor(
        db, email_service, payment_gateway,
        inventory_service, shipping_service,
        tax_calculator, discount_engine
    )
    # Finally, the test...
    result = order_processor.process(order_data)
    assert result.success
```

### Solution - Simplify Your Design:
```python
@pytest.fixture
def order_processor():
    # Simplified dependencies using in-memory implementations
    return OrderProcessor(
        repository=InMemoryOrderRepository(),
        emailer=MockEmailer()
    )

def test_process_order(order_processor):
    # ARRANGE: Minimal, focused setup
    order = Order(items=[...])

    # ACT
    result = order_processor.process(order)

    # ASSERT
    assert result.success
```

### Key Principles:
- If tests are hard to set up, the code is hard to use
- Use dependency injection to reduce coupling
- Create simpler in-memory test doubles instead of full infrastructure
- Extract complex setup into well-named fixtures
- Consider if your class is doing too much

---

## 4. Too Many Assertions

**Problem:** Multiple assertions in a single test obscure which one actually failed and test multiple behaviors at once.

### Avoid This:
```python
def test_user_validation():
    user = User(email="", password="short", age=15)
    assert not user.is_valid()  # Which rule failed?
    assert user.errors["email"] == "required"
    assert user.errors["password"] == "too_short"
    assert user.errors["age"] == "too_young"
```

**Problems:**
- When the first assertion fails, you never see if the others would have failed
- Multiple failure reasons make debugging harder
- Test name can't accurately describe what's being tested
- Violates Single Responsibility Principle for tests

### Do This Instead:
```python
def test_user_email_is_required():
    user = User(email="", password="valid123", age=25)
    assert not user.is_valid()
    assert "email" in user.errors

def test_user_password_minimum_length():
    user = User(email="test@example.com", password="short", age=25)
    assert not user.is_valid()
    assert "password" in user.errors

def test_user_age_must_be_adult():
    user = User(email="test@example.com", password="valid123", age=15)
    assert not user.is_valid()
    assert "age" in user.errors
```

### Guidelines:
- **One logical assertion per test** (related assertions about the same concept are OK)
- Test name should clearly state what's being verified
- When a test fails, you should immediately know what broke
- Multiple tests run fast - there's no performance reason to combine them

### Exception - Related Assertions Are OK:
```python
def test_user_registration_creates_user_with_email():
    result = register_user({"email": "test@example.com"})
    # These assertions verify the same concept (user creation)
    assert result.email == "test@example.com"
    assert result.id is not None
    assert result.created_at is not None
```

---

## 5. Testing Implementation Details

**Problem:** Tests break when refactoring internal structure, even though external behavior hasn't changed.

### Avoid This:
```python
def test_user_password_stored_with_bcrypt():
    user = User(password="secret")
    assert user._password_hash.startswith("$2b$")  # Implementation detail!
    assert len(user._salt) == 16  # Internal structure!
```

**Why It's Bad:**
- Tests become brittle - they break during refactoring
- You can't change implementation without changing tests
- Tests don't verify actual user-facing behavior
- Violates encapsulation by depending on private details

### Do This Instead:
```python
def test_user_password_can_be_verified():
    user = User(password="secret")
    assert user.verify_password("secret") is True
    assert user.verify_password("wrong") is False
```

### The Principle:
**Test behavior, not implementation. Test the "what", not the "how".**

### More Examples:

**Bad - Testing Internal State:**
```python
def test_cache_uses_dictionary():
    cache = Cache()
    cache.set("key", "value")
    assert isinstance(cache._data, dict)  # Implementation detail
    assert "key" in cache._data  # Internal structure
```

**Good - Testing Behavior:**
```python
def test_cache_retrieves_stored_values():
    cache = Cache()
    cache.set("key", "value")
    assert cache.get("key") == "value"

def test_cache_returns_none_for_missing_keys():
    cache = Cache()
    assert cache.get("missing") is None
```

### Benefits:
- Free to refactor implementation without touching tests
- Tests document how users interact with the code
- More stable test suite
- Tests remain valuable as code evolves

---

## 6. No Refactoring

**Problem:** Skipping the third step of Red-Green-Refactor. This is the most common way to fail at TDD.

### The Forgotten Step:
Many developers get stuck in a Red-Green-Red-Green cycle, never cleaning up their code or tests.

### Why It Happens:
- Pressure to move fast ("we'll clean it up later")
- Not understanding that green tests give you freedom to refactor
- Fear of breaking working code
- Forgetting that refactoring is part of TDD, not optional

### The Truth:
> **The most common way to fail at TDD is to forget to refactor.**

### What Refactoring Means:

**Six key questions to ask when tests are green:**
1. Can I make my test suite more expressive?
2. Does my test suite provide reliable feedback?
3. Are my tests isolated from each other?
4. Can I reduce duplication in test or implementation code?
5. Can I make my implementation code more descriptive?
6. Can I implement something more efficiently?

### The Safety Net:
Once tests are green, you have freedom to improve design. The only thing you're not allowed to do is add or change behavior.

### Example Refactoring Opportunities:

**After Green - Duplicated Test Setup:**
```python
# Before refactoring
def test_user_can_login():
    repository = InMemoryUserRepository()
    user = User(email="test@example.com", password="secret")
    repository.save(user)
    result = login(user.email, "secret", repository)
    assert result.success

def test_user_login_fails_with_wrong_password():
    repository = InMemoryUserRepository()
    user = User(email="test@example.com", password="secret")
    repository.save(user)
    result = login(user.email, "wrong", repository)
    assert not result.success
```

**After Refactoring:**
```python
@pytest.fixture
def logged_in_user():
    repository = InMemoryUserRepository()
    user = User(email="test@example.com", password="secret")
    repository.save(user)
    return user, repository

def test_user_can_login(logged_in_user):
    user, repository = logged_in_user
    result = login(user.email, "secret", repository)
    assert result.success

def test_user_login_fails_with_wrong_password(logged_in_user):
    user, repository = logged_in_user
    result = login(user.email, "wrong", repository)
    assert not result.success
```

### Remember:
- Refactor immediately while the code is fresh in your mind
- Green tests are your safety net - use them!
- Small, frequent refactorings are easier than big rewrites later
- "Later" never comes - refactor now

---

## 7. Violating Encapsulation

**Problem:** Making functions public or exposing internals just for testing.

### The Temptation:
```python
class OrderProcessor:
    def process(self, order):
        validated = self._validate_order(order)  # Private method
        if validated:
            self._calculate_total(order)  # Private method
            self._apply_discount(order)   # Private method
            return self._save_order(order) # Private method

# Don't do this:
class OrderProcessor:
    # Making private methods public just for testing
    def validate_order(self, order):  # Now public!
        ...
    def calculate_total(self, order):  # Now public!
        ...
```

### Why It's Wrong:
- Exposes implementation details that should be hidden
- Creates a larger public API to maintain
- Couples tests to internal structure
- Violates encapsulation principles

### Solution 1 - Test Through Public Interface:
```python
def test_order_processing_validates_items():
    processor = OrderProcessor()
    invalid_order = Order(items=[])  # Invalid - no items

    result = processor.process(invalid_order)

    assert not result.success
    assert "validation" in result.error.lower()
```

### Solution 2 - Extract to Separate Module:
If internal logic is complex enough to need dedicated testing, it probably belongs in its own module:

```python
# order_validator.py - Now independently testable
class OrderValidator:
    def validate(self, order):
        if not order.items:
            return ValidationResult(False, "No items")
        return ValidationResult(True)

# order_processor.py
class OrderProcessor:
    def __init__(self, validator: OrderValidator):
        self.validator = validator

    def process(self, order):
        result = self.validator.validate(order)
        if not result.success:
            return ProcessResult(False, result.error)
        # ...
```

**Now you can test `OrderValidator` independently:**
```python
def test_validator_rejects_empty_orders():
    validator = OrderValidator()
    result = validator.validate(Order(items=[]))
    assert not result.success
```

### The Principle:
> If something needs testing but is private, consider if it deserves to be a separate, public component.

---

## 8. Not Listening to Test Signals

**Critical Insight:** If testing your code is difficult, using your code is difficult.

### The Warning Signs:

**Your tests are the first users of your code. Listen to their feedback!**

| Test Pain | What It Signals | Solution |
|-----------|----------------|----------|
| Too many dependencies | Poor separation of concerns | Simplify the design, use dependency injection |
| Complex setup | Tight coupling | Reduce dependencies, extract smaller components |
| Hard to mock | Concrete dependencies | Use interfaces/protocols, dependency injection |
| Slow tests | Mixing I/O with logic | Separate pure logic from I/O operations |
| Flaky tests | Hidden dependencies, shared state | Ensure test isolation, remove global state |
| Tests break often | Testing implementation details | Test behavior, not internals |

### Example - Test Pain Revealing Design Issues:

**The Pain:**
```python
def test_generate_report():
    # Ugh, need to set up a real database, email server, file system...
    db = create_test_database()
    email_server = start_test_email_server()
    file_system = create_test_file_system()
    config = load_config_file()
    logger = setup_logger()

    report_generator = ReportGenerator(db, email_server, file_system, config, logger)

    report = report_generator.generate(user_id=123)
    # This test is painful to write and slow to run
```

**What It's Telling You:**
- `ReportGenerator` has too many responsibilities
- It's tightly coupled to infrastructure
- The design makes it hard to test AND hard to use

**Listen and Improve:**
```python
# Separated concerns - pure logic from I/O
class ReportBuilder:
    """Pure logic - easy to test"""
    def build(self, user_data: dict) -> Report:
        return Report(
            title=f"Report for {user_data['name']}",
            data=self._format_data(user_data)
        )

class ReportGenerator:
    """Orchestration - depends on interfaces"""
    def __init__(
        self,
        user_repository: UserRepository,  # Interface
        report_builder: ReportBuilder,
        report_sender: ReportSender  # Interface
    ):
        self.user_repository = user_repository
        self.builder = report_builder
        self.sender = report_sender

    def generate(self, user_id: int):
        user_data = self.user_repository.get(user_id)
        report = self.builder.build(user_data)
        self.sender.send(report)
        return report
```

**Now Testing Is Easy:**
```python
def test_report_builder_formats_user_data():
    builder = ReportBuilder()
    report = builder.build({"name": "Alice", "sales": 1000})

    assert report.title == "Report for Alice"
    assert "1000" in report.data

def test_report_generator_orchestrates_workflow():
    mock_repo = Mock(spec=UserRepository)
    mock_repo.get.return_value = {"name": "Alice", "sales": 1000}

    generator = ReportGenerator(
        user_repository=mock_repo,
        report_builder=ReportBuilder(),
        report_sender=Mock(spec=ReportSender)
    )

    result = generator.generate(user_id=123)

    assert result.title == "Report for Alice"
    mock_repo.get.assert_called_once_with(123)
```

### The Fundamental Truth:

> **When tests are hard to write, the code is hard to use.**

### Common Signals and Solutions:

**Signal: "I need to mock 10 different things"**
- **Problem:** Too many dependencies
- **Solution:** Simplify the design, consider if the class is doing too much

**Signal: "My test setup is longer than my test"**
- **Problem:** Complex initialization, tight coupling
- **Solution:** Use dependency injection, create simpler test doubles

**Signal: "I can't test this without a database/network/filesystem"**
- **Problem:** Logic mixed with I/O
- **Solution:** Separate pure logic from side effects

**Signal: "Tests break when I refactor"**
- **Problem:** Testing implementation details
- **Solution:** Test behavior through public interfaces

**Signal: "Tests are slow"**
- **Problem:** Real I/O operations in tests
- **Solution:** Use in-memory implementations, mock external services

### The TDD Mindset:

Tests aren't just about finding bugs. They're a design tool that gives you immediate feedback on the usability and quality of your code.

**Embrace the pain. Let it guide you to better design.**

---

## Summary

The 8 anti-patterns to avoid:

1. **The Liar** - Tests without proper assertions
2. **Evergreen Tests** - Tests that never fail (written after code)
3. **Excessive Setup** - Tests requiring 50+ lines of setup
4. **Too Many Assertions** - Testing multiple behaviors in one test
5. **Testing Implementation Details** - Coupling tests to internals
6. **No Refactoring** - Skipping the third step of TDD
7. **Violating Encapsulation** - Making things public just for tests
8. **Not Listening to Test Signals** - Ignoring design feedback from test pain

**Remember:** These anti-patterns are symptoms of deeper design issues. Fix the root cause, not just the test.
