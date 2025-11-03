---
name: bdd-gherkin-specification
description: Create Behavior-Driven Development (BDD) feature files using Gherkin syntax. Write clear, executable specifications that describe system behavior from the user's perspective. Use for requirements documentation, acceptance criteria, and living documentation.
version: 1.0.0
---

# BDD & Gherkin Specification

## What is Behavior-Driven Development?

Behavior-Driven Development (BDD) is a way of building software that starts with conversations, not code. Instead of writing technical specs that only developers understand, BDD encourages teams to describe how a feature should behave, using real-world examples that make sense to everyone involved.

BDD is first and foremost a methodology for capturing requirements in a way that expresses the behavior of the requirement. It is often used in conjunction with a user story to define not just what the feature is meant to do, and why it is beneficial, but also all the different ways that feature can be tested.

**BDD bridges the gap between:**
- Business stakeholders who define what needs to be built
- Developers who build the functionality
- Testers who verify it works correctly

**The core principle:** By turning business goals into shared examples, BDD helps teams avoid confusion, reduce rework, and build the right thing faster.

## What is Gherkin?

Gherkin is the domain-specific language for writing behavior scenarios. It is a simple programming language, and its "code" is written into feature files (text files with a ".feature" extension).

Gherkin uses plain text written in natural language, removing jargon and filling the gap between business stakeholders and developers. It focuses on the definition of application behavior rather than technical implementation.

### Key Characteristics

Gherkin features include:
- Human-readable language that removes technical jargon
- Behavior-focused documentation representing application behavior under specific conditions
- Executable specifications that can be run as tests with tools like Cucumber
- Available in many languages with localized keyword equivalents

## When to Use Gherkin Feature Files

**USE Gherkin when:**
- Defining acceptance criteria for user stories
- Creating living documentation that stays current with the system
- Bridging communication gaps between technical and non-technical stakeholders
- Specifying complex business rules with multiple scenarios
- Need for shared understanding before code is written
- Working in cross-functional teams (product, dev, test, business)
- Software engineers are far from the business and need clear guidance, or when backlog items need to be very clear

**DO NOT use Gherkin when:**
- Requirements are purely technical (internal architecture, refactoring)
- Team is small and co-located with constant communication
- Features are too simple to warrant formal specification
- Only developers will ever read the specifications

## Gherkin File Structure

### Basic Structure
```gherkin
Feature: High-level description of feature
  Optional description that can span
  multiple lines to provide context

  Scenario: Description of specific behavior
    Given [context/precondition]
    When [action/event]
    Then [expected outcome]
```

### File Naming Convention

It is conventional to name a .feature file by taking the name of the Feature, converting it to lowercase and replacing the spaces with underlines. For example, feedback_when_entering_invalid_credit_card_details.feature

**Examples:**
- `user_authentication.feature`
- `shopping_cart_checkout.feature`
- `password_reset_flow.feature`

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

## Writing Effective Feature Files

### The Feature Section
```gherkin
Feature: User Login
  As a registered user
  I want to log into my account
  So that I can access my personalized dashboard

  This feature ensures secure access to user accounts
  and provides proper error handling for authentication failures.
```

To identify features in your system, you can use what is known as a feature injection template:
In order to <meet some goal>
as a <type of user>
I want <a feature>

**Feature description best practices:**
- Start with a clear, descriptive title
- Include the "As a... I want... So that..." format for context
- Add additional description for complex features
- Keep it high-level - don't describe implementation

### Writing Good Scenarios

It is typical to see 5 to 20 scenarios per Feature to completely specify all the behaviors around that Feature.

**Example: Complete Feature File**
```gherkin
Feature: Shopping Cart Management
  As an online shopper
  I want to manage items in my shopping cart
  So that I can review and modify my purchases before checkout

  Scenario: Adding an item to an empty cart
    Given the user is viewing a product page
      And the shopping cart is empty
    When the user clicks "Add to Cart"
    Then the cart contains 1 item
      And the cart total reflects the product price

  Scenario: Removing an item from cart
    Given the shopping cart contains 2 items
    When the user removes the first item
    Then the cart contains 1 item
      And the cart total is updated accordingly

  Scenario: Updating item quantity
    Given the shopping cart contains "Wireless Mouse" with quantity 1
    When the user changes the quantity to 3
    Then the cart shows quantity 3 for "Wireless Mouse"
      And the line item total is multiplied by 3
```

## Declarative vs. Imperative Style

### Imperative Style (Avoid)

Imperative tests communicate details and are closely tied to the mechanics of the current UI, requiring more work to maintain. Any time the implementation changes, the tests need to be updated too.

**Imperative Example (Too detailed):**
```gherkin
Scenario: User logs in
  Given I am on the login page
  When I type "user@example.com" in the email field
    And I type "password123" in the password field
    And I press the "Submit" button
  Then I see "Welcome" on the home page
```

### Declarative Style (Preferred)

Declarative style describes the behaviour of the application, rather than the implementation details. Declarative scenarios read better as "living documentation" and help you focus on the value that the customer is getting.

**Declarative Example (Focus on behavior):**
```gherkin
Scenario: User logs in successfully
  Given Alice has a valid account
  When Alice logs in with valid credentials
  Then Alice sees her personalized dashboard
```

### The Key Difference

Scenarios should describe the intended behaviour of the system, not the implementation. In other words, they should describe what, not how.

**Ask yourself:** Does this scenario describe the expected behavior or the details of how it's implemented? If the answer is "Yes" to implementation details, then you should rework it avoiding implementation specific details.

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

## Best Practices

### 1. Keep Scenarios Focused and Concise

Scenarios should be short and sweet. I typically recommend that scenarios should have a single-digit step count (<10). Long scenarios are hard to understand, and they are often indicative of poor practices.

**Good:**
```gherkin
Scenario: User views order history
  Given the user has placed 3 orders
  When the user navigates to order history
  Then all 3 orders are displayed
    And orders are sorted by date (newest first)
```

**Bad (too many steps):**
```gherkin
Scenario: Complete order flow from search to confirmation
  Given the user is on the home page
  When the user searches for "laptop"
    And clicks on the first result
    And selects "Add to Cart"
    And views the cart
    And clicks "Checkout"
    And enters shipping information
    And selects shipping method
    And enters payment information
    And confirms the order
  Then the order confirmation page is displayed
  # This should be split into multiple scenarios!
```

### 2. Use Consistent Language and Perspective

Using the third-person perspective exclusively is more elegant and avoids confusion about whether "I" am "the user" or if there is a third party involved.

**Good:**
```gherkin
Given Alice is logged in as an administrator
When Alice creates a new user account
Then the new user receives a welcome email
```

**Bad (inconsistent perspective):**
```gherkin
Given I am logged in
When the administrator creates an account
Then I should see a confirmation
# Mixed first and third person!
```

### 3. Write Clear, Specific Outcomes

Use the Then steps to describe clear, measurable outcomes. Vague expectations make it difficult to specify an accurate automation of a test.

**Good:**
```gherkin
Then the user sees 5 search results
  And each result contains the word "camera"
  And results are sorted by relevance
```

**Bad (vague):**
```gherkin
Then the user sees some results
  And they look correct
```

### 4. Use Present Tense, Not Future

A behavior is a present-tense aspect of the product or feature. Thus, it is better to write Then steps in the present tense.

**Good:**
```gherkin
Then the confirmation message is displayed
```

**Bad:**
```gherkin
Then the confirmation message will be displayed
```

### 5. Avoid UI-Specific Details

**Good (behavior-focused):**
```gherkin
Scenario: User filters products by price
  Given the product catalog contains items in various price ranges
  When the user applies a price filter of $50-$100
  Then only products priced between $50 and $100 are shown
```

**Bad (UI-specific):**
```gherkin
Scenario: User filters products
  Given the user is on the products page
  When the user clicks the price dropdown
    And selects "$50-$100" from the dropdown menu
    And clicks the "Apply Filter" button
  Then the product grid refreshes
    And displays products in that price range
```

### 6. One Scenario, One Behavior

Each scenario should focus on a single, specific behavior. If you need multiple When-Then pairs, split into separate scenarios.

**Good (focused scenarios):**
```gherkin
Scenario: User with valid coupon receives discount
  Given a user has a valid 10% off coupon
  When the user applies the coupon at checkout
  Then the order total is reduced by 10%

Scenario: User with expired coupon sees error
  Given a user has an expired coupon
  When the user applies the coupon at checkout
  Then an error message states "Coupon has expired"
```

**Bad (multiple behaviors):**
```gherkin
Scenario: Coupon application
  Given a user has coupons
  When the user applies a valid coupon
  Then the discount is applied
  When the user applies an expired coupon
  Then an error is shown
  # This tests two different behaviors!
```

### 7. Make Scenarios Independent

Each scenario should be able to run independently without relying on other scenarios.

**Good:**
```gherkin
Scenario: Delete a draft post
  Given a draft post titled "My Draft" exists
  When the author deletes "My Draft"
  Then "My Draft" is removed from drafts
```

**Bad:**
```gherkin
Scenario: Create a draft post
  When the author creates a draft titled "My Draft"
  Then "My Draft" appears in drafts

Scenario: Delete the draft
  # Depends on previous scenario running first!
  When the author deletes "My Draft"
  Then "My Draft" is removed from drafts
```

### 8. Use Meaningful Test Data

BDD is specification by example – scenarios should be descriptive of the behaviors they cover, and any data written into the Gherkin should support that descriptive nature.

**Good (meaningful data):**
```gherkin
Given a product "Wireless Mouse" priced at $25.99
  And a product "USB Cable" priced at $5.99
When the user adds both products to the cart
Then the cart total is $31.98
```

**Bad (generic data):**
```gherkin
Given product1 costs $25.99
  And product2 costs $5.99
When the user adds items
Then total is correct
```

### 9. Write Self-Explanatory Scenarios

The Golden Rule of Gherkin is straightforward: treat other readers the way you want to be treated. Create feature files in a way everybody can comprehend them easily.

Anyone reading the scenario should understand:
- What is being tested
- Why it matters
- What the expected outcome is

### 10. Focus on High-Level Behavior

Keep scenarios high-level - Gherkin scenarios capture high-level behavior and do not capture implementation details. What the system does is interesting from the user's perspective, but not how it works.

## Common Anti-Patterns to Avoid

### ❌ Testing Implementation, Not Behavior
```gherkin
# Bad - tests how it works
Scenario: Password encryption
  When the system receives password "test123"
  Then the system calls bcrypt.hash()
    And stores the hash in the database

# Good - tests what happens
Scenario: Password security
  Given a user registers with password "test123"
  When the user logs in with "test123"
  Then authentication succeeds
  # Implementation details hidden
```

### ❌ Overly Technical Language
```gherkin
# Bad
Scenario: API returns 201 status
  When POST request to /api/users with payload {...}
  Then response status code is 201
    And JSON schema validates

# Good
Scenario: New user account creation
  When an administrator creates a new user account
  Then the new user account is successfully created
    And the new user receives account credentials
```

### ❌ Too Many Scenarios in One Feature

It is typical to see 5 to 20 scenarios per Feature. If you have more than 20 scenarios, consider splitting into multiple feature files.

### ❌ Scenarios with Ambiguous Steps
```gherkin
# Bad
Then the user sees the links
# What links? Where? How many?

# Good
Then the user sees 3 related product links in the sidebar
```

## Feature File Organization

### Organize by Feature Area
```
features/
├── authentication/
│   ├── user_login.feature
│   ├── password_reset.feature
│   └── two_factor_auth.feature
├── shopping/
│   ├── product_search.feature
│   ├── shopping_cart.feature
│   └── checkout.feature
└── account/
    ├── profile_management.feature
    └── order_history.feature
```

### Group Related Scenarios with Rules (Gherkin 6+)

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

## Complete Example: Well-Written Feature File
```gherkin
Feature: Product Search
  As a customer
  I want to search for products
  So that I can quickly find items I'm interested in purchasing

  Background:
    Given the product catalog contains the following items:
      | name              | category    | price   |
      | Wireless Mouse    | Electronics | $25.99  |
      | Desk Lamp         | Furniture   | $45.00  |
      | Coffee Mug        | Kitchen     | $12.99  |
      | Laptop Stand      | Electronics | $35.99  |

  Rule: Search returns matching products

    Scenario: Search by product name
      When the customer searches for "Mouse"
      Then the search results show "Wireless Mouse"
        And 1 product is returned

    Scenario: Search by category
      When the customer searches for "Electronics"
      Then the search results show 2 products
        And both products are in the Electronics category

  Rule: Search handles no results gracefully

    Scenario: Search with no matching products
      When the customer searches for "Telescope"
      Then no products are returned
        And a helpful message states "No products found"
        And search suggestions are provided

  Rule: Search can be refined

    Scenario: Filter search results by price range
      Given the customer has searched for "Electronics"
      When the customer applies a price filter of $20-$30
      Then only "Wireless Mouse" is shown in results
```

## Tips for Success

Good Gherkin syntax should feel more like a shared understanding than a technical document. Be specific, not vague - instead of "User logs in", write "User enters valid email and password". Stick to one action per step and make it readable for non-developers. Treat your feature file like living documentation.

**Remember:**
1. **Collaboration first** - Write scenarios with business stakeholders, not for them
2. **Living documentation** - Keep feature files updated as the system evolves
3. **Behavior, not implementation** - Describe what the system does, not how
4. **Clarity over completeness** - Better to have clear scenarios than exhaustive ones
5. **Examples matter** - Concrete examples are more valuable than abstract rules

## Using Feature Files as Specifications

Feature files serve multiple purposes:

1. **Requirements Documentation** - Capture what the system should do
2. **Acceptance Criteria** - Define when a feature is "done"
3. **Communication Tool** - Bridge between business and technical teams
4. **Living Documentation** - Stay current as system evolves
5. **Test Specifications** - Can be automated later (but that's optional)

The key insight: BDD isn't just about testing, it bridges the gap between business requirements and technical implementation.

## Conclusion

Gherkin ensures seamless collaboration between technical and non-technical teams by documenting expected behavior in a simple format. It aligns business goals with development, making communication more efficient and maintainable.

Good Gherkin specifications are:
- **Clear** - Anyone can understand them
- **Concise** - Focused on essential behavior
- **Consistent** - Use the same language throughout
- **Complete** - Cover the important scenarios
- **Current** - Updated as the system changes

Write specifications that make sense to business stakeholders while providing enough detail for developers to implement correctly. The goal is shared understanding, not exhaustive documentation.

---

## Quick Reference

### Feature File Template
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

### Keywords at a Glance

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
