# Best Practices

**When to read this:** You're writing feature files and want to ensure they're clear, maintainable, and effective. Reference this when reviewing or improving existing scenarios.

---

## 1. Keep Scenarios Focused and Concise

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

---

## 2. Use Consistent Language and Perspective

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

---

## 3. Write Clear, Specific Outcomes

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

---

## 4. Use Present Tense, Not Future

A behavior is a present-tense aspect of the product or feature. Thus, it is better to write Then steps in the present tense.

**Good:**
```gherkin
Then the confirmation message is displayed
```

**Bad:**
```gherkin
Then the confirmation message will be displayed
```

---

## 5. Avoid UI-Specific Details

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

---

## 6. One Scenario, One Behavior

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

---

## 7. Make Scenarios Independent

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

---

## 8. Use Meaningful Test Data

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

---

## 9. Write Self-Explanatory Scenarios

The Golden Rule of Gherkin is straightforward: treat other readers the way you want to be treated. Create feature files in a way everybody can comprehend them easily.

Anyone reading the scenario should understand:
- What is being tested
- Why it matters
- What the expected outcome is

---

## 10. Focus on High-Level Behavior

Keep scenarios high-level - Gherkin scenarios capture high-level behavior and do not capture implementation details. What the system does is interesting from the user's perspective, but not how it works.

---

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

---

## Writing Good Scenarios

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

---

## Tips for Success

Good Gherkin syntax should feel more like a shared understanding than a technical document. Be specific, not vague - instead of "User logs in", write "User enters valid email and password". Stick to one action per step and make it readable for non-developers. Treat your feature file like living documentation.

**Remember:**
1. **Collaboration first** - Write scenarios with business stakeholders, not for them
2. **Living documentation** - Keep feature files updated as the system evolves
3. **Behavior, not implementation** - Describe what the system does, not how
4. **Clarity over completeness** - Better to have clear scenarios than exhaustive ones
5. **Examples matter** - Concrete examples are more valuable than abstract rules
