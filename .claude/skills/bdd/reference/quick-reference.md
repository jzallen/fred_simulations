# Quick Reference

**When to read this:** You need a fast lookup of Gherkin syntax, keywords, or a template to start writing a feature file.

---

## Feature File Template

```gherkin
Feature: [Feature Name]
  [Optional: As a... I want... So that...]

  [Optional multi-line description]

  Background:
    Given [common setup that applies to all scenarios]

  Scenario: [Scenario name describing specific behavior]
    Given [context/precondition]
      And [additional context]
    When [action/trigger]
      And [additional action]
    Then [expected outcome]
      And [additional outcome]
      But [negative assertion]

  Scenario Outline: [Template for multiple test cases]
    Given [context with "<parameter>"]
    When [action with "<parameter>"]
    Then [outcome with "<parameter>"]

    Examples:
      | parameter | other_param |
      | value1    | result1     |
      | value2    | result2     |
```

---

## Keywords at a Glance

- `Feature:` - What you're specifying
- `Scenario:` - Specific example of behavior
- `Given` - Starting context
- `When` - Action that triggers behavior
- `Then` - Expected result
- `And/But` - Additional steps
- `Background:` - Shared setup for all scenarios
- `Scenario Outline:` - Template with data variations
- `Examples:` - Data table for outline
- `Rule:` - Business rule grouping

---

## Core Keywords

| Keyword | Purpose | Example |
|---------|---------|---------|
| `Feature:` | High-level description of feature | `Feature: User Authentication` |
| `Scenario:` | Specific behavior example | `Scenario: Successful login with valid credentials` |
| `Given` | Initial context/preconditions | `Given the user is on the login page` |
| `When` | Action or event | `When the user enters valid credentials` |
| `Then` | Expected outcome | `Then the user is logged in` |
| `And` | Additional step (same type) | `And the dashboard is displayed` |
| `But` | Negative additional step | `But the error message is not shown` |

---

## Advanced Keywords

| Keyword | Purpose | Usage |
|---------|---------|-------|
| `Background:` | Common setup for all scenarios | Runs before each scenario in the feature |
| `Scenario Outline:` | Template for multiple test cases | Used with Examples table |
| `Examples:` | Data table for Scenario Outline | Provides test data variations |
| `Rule:` | Business rule grouping (Gherkin 6+) | Groups related scenarios |
| `*` | Wildcard step keyword | Can replace Given/When/Then for lists |

---

## Given-When-Then Quick Guide

### GIVEN (Context/Preconditions)
Sets up the initial state before the action.

```gherkin
Given the user is logged in
Given the shopping cart contains 3 items
Given a blog post titled "My First Post" exists
```

### WHEN (Action/Event)
The action that causes something to happen.

```gherkin
When the user clicks the "Checkout" button
When the user submits the registration form
When the user searches for "vintage camera"
```

### THEN (Expected Outcome)
The expected result that determines success.

```gherkin
Then the user sees a confirmation message
Then the shopping cart is empty
Then search results are displayed
```

---

## Quick Tips

### DO:
- Use declarative style (what, not how)
- Keep scenarios focused (< 10 steps)
- Use present tense
- Be specific and clear
- Use meaningful test data
- Make scenarios independent
- Write for business stakeholders

### DON'T:
- Include implementation details
- Use technical jargon
- Make scenarios depend on each other
- Mix multiple behaviors in one scenario
- Use vague assertions
- Couple to specific UI elements
- Write scenarios longer than 10 steps

---

## File Naming Convention

Convert feature name to lowercase with underscores:

- `User Authentication` → `user_authentication.feature`
- `Shopping Cart Checkout` → `shopping_cart_checkout.feature`
- `Password Reset Flow` → `password_reset_flow.feature`

---

## Common Patterns

### Simple Scenario
```gherkin
Scenario: User views order history
  Given the user has placed 3 orders
  When the user navigates to order history
  Then all 3 orders are displayed
```

### With Background
```gherkin
Background:
  Given the user is logged in
  And the user has a premium account

Scenario: Access premium content
  When the user views a premium article
  Then the article is displayed
```

### Scenario Outline
```gherkin
Scenario Outline: Login validation
  When the user logs in with "<username>" and "<password>"
  Then the result is "<outcome>"

  Examples:
    | username | password  | outcome |
    | alice    | correct   | success |
    | bob      | incorrect | failure |
```

### With Rules
```gherkin
Rule: Free users can only access free content
  Scenario: Free user views free article
    Given a user with a free subscription
    When the user accesses a free article
    Then the article is displayed
```

---

## How Many Scenarios?

- **Typical:** 5-20 scenarios per feature
- **Too few (< 5):** Consider combining with related features
- **Too many (> 20):** Consider splitting into multiple files

---

## Quick Decision Tree

**Q: Is this a new business feature?**
- Yes → Create new .feature file

**Q: Does this scenario relate to an existing feature?**
- Yes → Add to existing .feature file

**Q: Does the feature have more than 20 scenarios?**
- Yes → Split into multiple files or use Rules

**Q: Do multiple scenarios share the same setup?**
- Yes → Use Background

**Q: Do you need to test the same behavior with different data?**
- Yes → Use Scenario Outline

---

## Checklist for Good Scenarios

- [ ] Scenario name is clear and descriptive
- [ ] Uses third-person perspective consistently
- [ ] Focused on one specific behavior
- [ ] Steps are in present tense
- [ ] No UI-specific details (buttons, fields, etc.)
- [ ] No implementation details (APIs, database, etc.)
- [ ] Test data is meaningful and realistic
- [ ] Scenario can run independently
- [ ] Less than 10 steps total
- [ ] Clear, specific outcomes in Then steps

---

## When to Use Gherkin

**USE when:**
- Defining acceptance criteria for user stories
- Bridging communication gaps
- Specifying complex business rules
- Creating living documentation
- Working in cross-functional teams

**DON'T USE when:**
- Requirements are purely technical
- Team is small and co-located
- Features are too simple
- Only developers will read it

---

## Remember the Golden Rule

**Treat other readers the way you want to be treated.**

Write scenarios that anyone on your team—business stakeholders, developers, testers—can understand without technical knowledge.
