---
name: "Test-Driven Development (TDD)"
description: "Practice Red-Green-Refactor-Commit TDD methodology with pytest, avoiding common antipatterns and following FIRST principles for robust test suites."
version: "2.0.0"
---

# Test-Driven Development (TDD)

You are a Test-Driven Development expert helping developers practice the Red-Green-Refactor-Commit cycle with pytest, creating clean test suites that drive design decisions.

## The Red-Green-Refactor-Commit Cycle

TDD follows a disciplined four-step cycle:

### 1. RED - Write a Failing Test
**Goal:** Define what you want to develop

- Write a test specifying expected behavior
- Test MUST fail initially (proves it's testing something)
- Read the error message carefully
- Think about API and behavior before implementation

### 2. GREEN - Make It Pass
**Goal:** Get it working, don't worry about perfection yet

- Write minimal code to make test pass
- Don't over-engineer or add untested features
- Simplicity and speed over elegance
- Once green, you have a safety net for refactoring

### 3. REFACTOR - Improve the Design
**Goal:** Clean up while maintaining green tests

Six key questions:
1. Can I make my test suite more expressive?
2. Does my test suite provide reliable feedback?
3. Are my tests isolated from each other?
4. Can I reduce duplication?
5. Can I make my implementation more descriptive?
6. Can I implement something more efficiently?

**Important:** You can do whatever you like when tests are green—except add or change behavior.

### 4. COMMIT - Save Your Progress
**Goal:** Create granular, meaningful commits

- Commit after completing each RED-GREEN-REFACTOR cycle
- Each commit represents a working state with passing tests
- Smaller, frequent commits better than large, infrequent ones

> **Detailed workflow guide**: [workflow-guide.md](reference/workflow-guide.md)

## Core Principles: FIRST

Write tests that are:
- **Fast** - Run in milliseconds, not seconds
- **Isolated** - Independent, no shared state
- **Repeatable** - Same results every time
- **Self-validating** - Clear pass/fail without manual inspection
- **Timely** - Written before (or with) production code

## Test Structure: AAA Pattern

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

> **Complete pytest guide**: [pytest-guide.md](reference/pytest-guide.md)

## Running Tests with Pants

**CRITICAL**: Always use **target addresses**, never file paths.

```bash
# ✅ CORRECT: Use target addresses (maximizes cache hits)
pants test epistemix_platform:src-tests

# ❌ WRONG: Using file paths creates separate caches
pants test epistemix_platform/tests/test_*.py

# Pass arguments to pytest after --
pants test epistemix_platform:src-tests -- -vv        # Verbose
pants test epistemix_platform:src-tests -- -k "test_user"  # Pattern
pants test epistemix_platform:src-tests -- -x         # Stop on failure
pants test epistemix_platform:src-tests -- -s         # Show print statements
```

> **For comprehensive Pants guidance**: See `pants-build-system` skill

## Key Anti-Patterns to Avoid

1. **The Liar** - Tests that don't actually verify behavior
2. **Evergreen Tests** - Tests written after code, designed to pass
3. **Excessive Setup** - 50+ lines before testing (sign of tight coupling)
4. **Too Many Assertions** - Multiple assertions obscure failures
5. **Testing Implementation** - Tests break when refactoring internals
6. **No Refactoring** - Skipping the third step (most common TDD failure)
7. **Violating Encapsulation** - Making things public just for testing
8. **Not Listening** - Hard tests mean hard code

> **Detailed anti-patterns with solutions**: [anti-patterns.md](reference/anti-patterns.md)

## Available Resources

### Core Documentation

- **[workflow-guide.md](reference/workflow-guide.md)** - Step-by-step TDD workflow
  - Complete RGRC cycle explained
  - FIRST principles detailed
  - Practical workflow steps
  - Test organization strategies
  - Complete end-to-end example
  - Read when: Learning TDD or establishing workflow

- **[pytest-guide.md](reference/pytest-guide.md)** - pytest best practices
  - AAA pattern in depth
  - Fixtures with all scopes
  - Mocking patterns
  - Test naming conventions
  - Running tests with Pants
  - Read when: Writing tests or using pytest features

- **[anti-patterns.md](reference/anti-patterns.md)** - Common mistakes and solutions
  - All 8 anti-patterns explained
  - What to avoid and why
  - What to do instead
  - Warning signs
  - Read when: Reviewing tests or troubleshooting issues

## Quick Tips

- **Start with simplest test case** - Happy path first, edge cases incrementally
- **Write test first** - Before any production code
- **Make it pass quickly** - Simple implementation, even hard-coding
- **Refactor with confidence** - Tests guarantee behavior preserved
- **Commit frequently** - After each red-green-refactor cycle
- **Listen to pain** - Hard tests mean hard code

## Test Organization

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

## Practical TDD Workflow

1. **Start with simplest test case**
2. **Write test first** - Think about desired API
3. **Make it pass quickly** - Simplest implementation
4. **Refactor with confidence** - Clean up, improve design
5. **Commit frequently** - After each cycle
6. **Add next test** - Repeat

## Critical Insights

- **TDD is about design feedback** - Tests reveal how easy your code is to use
- **Start simple** - Baby steps lead to robust solutions
- **Refactor is mandatory** - Not optional, not "later", now
- **Tests are documentation** - They show how code should be used
- **Listen to pain** - Hard tests mean hard code
- **Commit often** - Smaller changes, clearer history
- **Behavior over implementation** - Test what, not how

## When Tests Are Hard to Write

This is valuable feedback:
- **Too many dependencies?** → Simplify the design
- **Complex setup?** → Reduce coupling
- **Hard to mock?** → Use dependency injection
- **Slow tests?** → Separate I/O from logic

Your tests are the first users of your code. Listen to their feedback!

## Remember

TDD rigorously practiced leads to:
- Time saved (less debugging, fewer bugs)
- Less code written (only what's needed)
- More robust solutions (driven by tests)
- Better design (testable code is well-designed code)

The most common way to fail at TDD is to forget to refactor. Once tests are green, you have freedom to improve design—use it.

---

**For comprehensive guidance, explore the reference/ directory based on your current need.**
