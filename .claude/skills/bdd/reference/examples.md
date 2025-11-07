# Examples

**When to read this:** You need complete, real-world examples of well-written feature files to use as templates or reference.

---

## Complete Example: Product Search

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

---

## Complete Example: Shopping Cart Management

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

## Complete Example: User Login

```gherkin
Feature: User Login
  As a registered user
  I want to log into my account
  So that I can access my personalized dashboard

  This feature ensures secure access to user accounts
  and provides proper error handling for authentication failures.

  Scenario: User logs in successfully
    Given Alice has a valid account
    When Alice logs in with valid credentials
    Then Alice sees her personalized dashboard

  Scenario: User logs in with incorrect password
    Given Alice has a valid account
    When Alice attempts to log in with an incorrect password
    Then Alice sees an error message "Invalid credentials"
      And Alice remains on the login page

  Scenario: User account is locked after multiple failed attempts
    Given Alice has a valid account
    When Alice fails to log in 5 times consecutively
    Then Alice's account is temporarily locked
      And Alice sees a message "Account locked. Try again in 15 minutes"
```

---

## Complete Example: Bank Account Withdrawals

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

---

## Complete Example: Password Validation

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

---

## Complete Example: Account Access Control

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

---

## Declarative vs Imperative Examples

### Imperative Example (Avoid)

```gherkin
Scenario: User logs in
  Given I am on the login page
  When I type "user@example.com" in the email field
    And I type "password123" in the password field
    And I press the "Submit" button
  Then I see "Welcome" on the home page
```

### Declarative Example (Preferred)

```gherkin
Scenario: User logs in successfully
  Given Alice has a valid account
  When Alice logs in with valid credentials
  Then Alice sees her personalized dashboard
```

---

## UI-Specific vs Behavior-Focused Examples

### UI-Specific (Avoid)

```gherkin
Scenario: User filters products
  Given the user is on the products page
  When the user clicks the price dropdown
    And selects "$50-$100" from the dropdown menu
    And clicks the "Apply Filter" button
  Then the product grid refreshes
    And displays products in that price range
```

### Behavior-Focused (Preferred)

```gherkin
Scenario: User filters products by price
  Given the product catalog contains items in various price ranges
  When the user applies a price filter of $50-$100
  Then only products priced between $50 and $100 are shown
```

---

## Focused vs Multiple Behaviors Examples

### Multiple Behaviors (Avoid)

```gherkin
Scenario: Coupon application
  Given a user has coupons
  When the user applies a valid coupon
  Then the discount is applied
  When the user applies an expired coupon
  Then an error is shown
  # This tests two different behaviors!
```

### Focused Scenarios (Preferred)

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

## Meaningful vs Generic Data Examples

### Generic Data (Avoid)

```gherkin
Given product1 costs $25.99
  And product2 costs $5.99
When the user adds items
Then total is correct
```

### Meaningful Data (Preferred)

```gherkin
Given a product "Wireless Mouse" priced at $25.99
  And a product "USB Cable" priced at $5.99
When the user adds both products to the cart
Then the cart total is $31.98
```
