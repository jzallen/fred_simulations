# Gherkin Syntax

**When to read this:** You need to understand the basic structure of Gherkin files, learn the keywords, or reference file naming conventions.

---

## What is Gherkin?

Gherkin is the domain-specific language for writing behavior scenarios. It is a simple programming language, and its "code" is written into feature files (text files with a ".feature" extension).

Gherkin uses plain text written in natural language, removing jargon and filling the gap between business stakeholders and developers. It focuses on the definition of application behavior rather than technical implementation.

### Key Characteristics

Gherkin features include:
- Human-readable language that removes technical jargon
- Behavior-focused documentation representing application behavior under specific conditions
- Executable specifications that can be run as tests with tools like Cucumber
- Available in many languages with localized keyword equivalents

---

## Basic Structure

```gherkin
Feature: High-level description of feature
  Optional description that can span
  multiple lines to provide context

  Scenario: Description of specific behavior
    Given [context/precondition]
    When [action/event]
    Then [expected outcome]
```

---

## File Naming Convention

It is conventional to name a .feature file by taking the name of the Feature, converting it to lowercase and replacing the spaces with underlines.

**Examples:**
- `user_authentication.feature`
- `shopping_cart_checkout.feature`
- `password_reset_flow.feature`
- `feedback_when_entering_invalid_credit_card_details.feature`

---

## The Given-When-Then Structure

The Given-When-Then Gherkin notation is considered one of the best when it comes to making sure that a specification is comprehensive and precise, since its syntax allows us to phrase exactly what we want from business requirements and what we expect as an outcome.

### GIVEN (Context/Preconditions)

The Given clause sets up the initial state or context for the scenario. It describes the situation before the action takes place.

**Examples:**
```gherkin
Given the user is logged in
Given the shopping cart contains 3 items
Given a blog post titled "My First Post" exists
Given the user has a premium subscription
```

### WHEN (Action/Event)

The WHEN statement lists the type of user interaction or defines the trigger for the execution of this scenario. This is the action that causes something to happen.

**Examples:**
```gherkin
When the user clicks the "Checkout" button
When the user submits the registration form
When the user searches for "vintage camera"
When a new comment is posted
```

### THEN (Expected Outcome)

The THEN clause defines the conditions that determine whether or not the test is successful. If the conditions in this clause are met, the software works correctly.

**Examples:**
```gherkin
Then the user sees a confirmation message
Then the shopping cart is empty
Then search results are displayed
Then the comment appears at the top of the list
```

### AND / BUT (Additional Steps)

Use `And` and `But` to add additional conditions without repeating Given/When/Then.

```gherkin
Given the user is on the login page
  And the user has a valid account
When the user enters correct credentials
  And clicks the "Sign In" button
Then the user sees the dashboard
  And the user's name appears in the header
  But the admin panel is not visible
```

---

## Gherkin Keywords Reference

Each line that isn't a blank line has to start with a Gherkin keyword, followed by any text you like.

### Core Keywords

| Keyword | Purpose | Example |
|---------|---------|---------|
| `Feature:` | High-level description of feature | `Feature: User Authentication` |
| `Scenario:` | Specific behavior example | `Scenario: Successful login with valid credentials` |
| `Given` | Initial context/preconditions | `Given the user is on the login page` |
| `When` | Action or event | `When the user enters valid credentials` |
| `Then` | Expected outcome | `Then the user is logged in` |
| `And` | Additional step (same type) | `And the dashboard is displayed` |
| `But` | Negative additional step | `But the error message is not shown` |

### Advanced Keywords

| Keyword | Purpose | Usage |
|---------|---------|-------|
| `Background:` | Common setup for all scenarios | Runs before each scenario in the feature |
| `Scenario Outline:` | Template for multiple test cases | Used with Examples table |
| `Examples:` | Data table for Scenario Outline | Provides test data variations |
| `Rule:` | Business rule grouping (Gherkin 6+) | Groups related scenarios |
| `*` | Wildcard step keyword | Can replace Given/When/Then for lists |

---

## The Feature Section

```gherkin
Feature: User Login
  As a registered user
  I want to log into my account
  So that I can access my personalized dashboard

  This feature ensures secure access to user accounts
  and provides proper error handling for authentication failures.
```

To identify features in your system, you can use what is known as a feature injection template:
```
In order to <meet some goal>
as a <type of user>
I want <a feature>
```

**Feature description best practices:**
- Start with a clear, descriptive title
- Include the "As a... I want... So that..." format for context
- Add additional description for complex features
- Keep it high-level - don't describe implementation

---

## Using Background for Common Setup

The BACKGROUND statement in the Gherkin syntax allows you to define setup criteria that will be used for a group of Scenarios. These setup criteria can be defined once, then used repeatedly by other Scenarios.

```gherkin
Feature: Bank Account Withdrawals

  Background:
    Given a customer named "John" has an account
      And John's account balance is $500
      And the ATM has sufficient cash

  Scenario: Successful withdrawal within balance
    When John requests $100
    Then the ATM dispenses $100
      And John's account balance is $400

  Scenario: Withdrawal exceeds balance
    When John requests $600
    Then the ATM displays "Insufficient funds"
      And John's account balance remains $500
```

**When to use Background:**
- Multiple scenarios share the same setup steps
- Reduces repetition across scenarios
- Makes scenarios more focused on the unique behavior

---

## Scenario Outline for Data Variations

Scenario Outline allows you to run the same scenario multiple times with different sets of data. A scenario outline section is always followed by one or more sections of examples, which are a container for a table.

```gherkin
Feature: Password Validation

  Scenario Outline: Password strength requirements
    Given a user is registering an account
    When the user enters password "<password>"
    Then the system displays "<message>"
      And the password is marked as "<status>"

    Examples:
      | password    | message                          | status   |
      | abc         | Too short (minimum 8 characters) | invalid  |
      | abcdefgh    | No numbers or special characters | weak     |
      | Abcd123!    | Good password                    | valid    |
      | P@ssw0rd!   | Strong password                  | strong   |
```

**Use Scenario Outline when:**
- Testing the same behavior with different inputs
- Focus on unique equivalence classes rather than testing "everything"
- Data variations are important to the specification

---

## Grouping with Rules (Gherkin 6+)

The purpose of the Rule keyword is to represent one business rule that should be implemented. A Rule is used to group together several scenarios that belong to this business rule.

```gherkin
Feature: Account Access Control

  Rule: Free users can only access free content
    Scenario: Free user views free article
      Given a user with a free subscription
      When the user accesses a free article
      Then the article is displayed

    Scenario: Free user attempts to access premium content
      Given a user with a free subscription
      When the user attempts to access a premium article
      Then the user sees an upgrade prompt

  Rule: Premium users can access all content
    Scenario: Premium user views any article
      Given a user with a premium subscription
      When the user accesses any article
      Then the article is displayed
```
