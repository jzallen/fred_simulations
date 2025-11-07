# Anti-Patterns

**When to read this:** You're reviewing feature files and want to identify common mistakes, or you need guidance on what to avoid when writing scenarios.

---

## Common Anti-Patterns to Avoid

### Testing Implementation, Not Behavior

Focus on what the system does from the user's perspective, not how it works internally.

**Bad - tests how it works:**
```gherkin
Scenario: Password encryption
  When the system receives password "test123"
  Then the system calls bcrypt.hash()
    And stores the hash in the database
```

**Good - tests what happens:**
```gherkin
Scenario: Password security
  Given a user registers with password "test123"
  When the user logs in with "test123"
  Then authentication succeeds
  # Implementation details hidden
```

---

### Overly Technical Language

Write scenarios that business stakeholders can understand, not just developers.

**Bad:**
```gherkin
Scenario: API returns 201 status
  When POST request to /api/users with payload {...}
  Then response status code is 201
    And JSON schema validates
```

**Good:**
```gherkin
Scenario: New user account creation
  When an administrator creates a new user account
  Then the new user account is successfully created
    And the new user receives account credentials
```

---

### Too Many Scenarios in One Feature

It is typical to see 5 to 20 scenarios per Feature. If you have more than 20 scenarios, consider splitting into multiple feature files.

**Problem:** Feature files with 30, 40, or 50+ scenarios become difficult to navigate and understand.

**Solution:**
- Break down by sub-features
- Use separate feature files for different aspects
- Organize by business rules or user journeys

---

### Scenarios with Ambiguous Steps

Vague steps make it unclear what the expected behavior actually is.

**Bad:**
```gherkin
Then the user sees the links
# What links? Where? How many?
```

**Good:**
```gherkin
Then the user sees 3 related product links in the sidebar
```

---

### Dependent Scenarios

Scenarios that rely on previous scenarios to run create fragile test suites.

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

**Good:**
```gherkin
Scenario: Delete a draft post
  Given a draft post titled "My Draft" exists
  When the author deletes "My Draft"
  Then "My Draft" is removed from drafts
```

---

### UI-Centric Scenarios

Scenarios tied to specific UI elements are fragile and break when the UI changes.

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

**Good (behavior-focused):**
```gherkin
Scenario: User filters products by price
  Given the product catalog contains items in various price ranges
  When the user applies a price filter of $50-$100
  Then only products priced between $50 and $100 are shown
```

---

### Multiple Behaviors in One Scenario

Each scenario should test one specific behavior.

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

---

### Overly Long Scenarios

Scenarios with too many steps (>10) are hard to understand and maintain.

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

**Good:**
```gherkin
Scenario: User views order history
  Given the user has placed 3 orders
  When the user navigates to order history
  Then all 3 orders are displayed
    And orders are sorted by date (newest first)
```

---

### Inconsistent Perspective

Mixing first-person and third-person perspective creates confusion.

**Bad (inconsistent perspective):**
```gherkin
Given I am logged in
When the administrator creates an account
Then I should see a confirmation
# Mixed first and third person!
```

**Good:**
```gherkin
Given Alice is logged in as an administrator
When Alice creates a new user account
Then the new user receives a welcome email
```

---

### Vague or Generic Test Data

Using meaningless test data makes scenarios harder to understand.

**Bad (generic data):**
```gherkin
Given product1 costs $25.99
  And product2 costs $5.99
When the user adds items
Then total is correct
```

**Good (meaningful data):**
```gherkin
Given a product "Wireless Mouse" priced at $25.99
  And a product "USB Cable" priced at $5.99
When the user adds both products to the cart
Then the cart total is $31.98
```

---

### Using Future Tense

Behaviors are present-tense aspects of the system, not future predictions.

**Bad:**
```gherkin
Then the confirmation message will be displayed
```

**Good:**
```gherkin
Then the confirmation message is displayed
```

---

## Summary: What to Avoid

1. **Implementation details** - Focus on behavior, not how it's built
2. **Technical jargon** - Write for business stakeholders
3. **Too many scenarios** - Keep features focused (5-20 scenarios)
4. **Ambiguous steps** - Be specific and clear
5. **Dependent scenarios** - Each scenario should stand alone
6. **UI coupling** - Describe behavior, not buttons and fields
7. **Multiple behaviors** - One scenario = one behavior
8. **Long scenarios** - Keep step count under 10
9. **Inconsistent perspective** - Stick to third-person
10. **Generic data** - Use meaningful, realistic examples
11. **Future tense** - Write in present tense
