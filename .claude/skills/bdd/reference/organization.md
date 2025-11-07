# Organization

**When to read this:** You need to structure your feature files in a project, organize by feature areas, or plan your testing directory layout.

---

## Feature File Organization

### Organize by Feature Area

Organize your feature files into directories that reflect the main functional areas of your application. This makes it easier to navigate and maintain your test suite as it grows.

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

---

## File Naming Convention

It is conventional to name a .feature file by taking the name of the Feature, converting it to lowercase and replacing the spaces with underlines.

**Examples:**
- `user_authentication.feature`
- `shopping_cart_checkout.feature`
- `password_reset_flow.feature`
- `feedback_when_entering_invalid_credit_card_details.feature`

**Naming best practices:**
- Use lowercase with underscores
- Be descriptive but concise
- Match the Feature name in the file
- Group related features in directories

---

## How Many Scenarios Per Feature?

It is typical to see **5 to 20 scenarios per Feature** to completely specify all the behaviors around that Feature.

**If you have more than 20 scenarios:**
- Consider splitting into multiple feature files
- Break down by sub-features
- Use separate files for different aspects
- Organize by business rules or user journeys

---

## Using Rules to Group Scenarios (Gherkin 6+)

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

**Benefits of using Rules:**
- Groups related scenarios under business rules
- Provides clearer structure within large features
- Makes it easier to understand the rules being tested
- Helps organize features with many scenarios

---

## Directory Structure Best Practices

### Small to Medium Projects

```
features/
├── user_management.feature
├── product_catalog.feature
├── shopping_cart.feature
└── checkout.feature
```

### Large Projects

```
features/
├── authentication/
│   ├── login.feature
│   ├── registration.feature
│   ├── password_reset.feature
│   └── two_factor.feature
├── products/
│   ├── search.feature
│   ├── filter.feature
│   ├── details.feature
│   └── recommendations.feature
├── shopping/
│   ├── cart_management.feature
│   ├── wishlist.feature
│   └── checkout.feature
├── orders/
│   ├── order_placement.feature
│   ├── order_tracking.feature
│   └── order_history.feature
└── admin/
    ├── user_management.feature
    ├── product_management.feature
    └── reports.feature
```

---

## Organizing Complex Features

### Option 1: Break Down by User Journey

```
features/
├── new_user_journey/
│   ├── 01_registration.feature
│   ├── 02_first_login.feature
│   ├── 03_profile_setup.feature
│   └── 04_first_purchase.feature
```

### Option 2: Break Down by Business Rule

```
features/
├── pricing/
│   ├── base_pricing.feature
│   ├── discounts.feature
│   ├── tax_calculation.feature
│   └── shipping_costs.feature
```

### Option 3: Break Down by User Role

```
features/
├── customer/
│   ├── browse_products.feature
│   └── place_order.feature
├── seller/
│   ├── manage_inventory.feature
│   └── view_sales.feature
└── admin/
    ├── user_management.feature
    └── system_configuration.feature
```

---

## Supporting Files Organization

If you have step definitions, support files, or test data, organize them alongside your features:

```
features/
├── authentication/
│   ├── login.feature
│   └── password_reset.feature
├── step_definitions/
│   ├── authentication_steps.rb
│   └── shopping_steps.rb
├── support/
│   ├── env.rb
│   └── helpers.rb
└── test_data/
    ├── users.json
    └── products.json
```

---

## Feature Organization Principles

1. **Group by business domain** - Not by technical layers
2. **Keep related scenarios together** - In the same feature or directory
3. **Use meaningful names** - That reflect business language
4. **Limit scenarios per file** - Aim for 5-20 scenarios per feature
5. **Scale your structure** - Start simple, add complexity as needed
6. **Mirror business organization** - Structure should match how business thinks about features

---

## When to Split a Feature File

Consider splitting a feature file when:

1. **More than 20 scenarios** - File is becoming unwieldy
2. **Multiple distinct behaviors** - Different aspects of a larger feature
3. **Different user roles** - Admin vs. regular user behaviors
4. **Different business rules** - Distinct rules that could stand alone
5. **Hard to navigate** - Team members struggle to find scenarios
6. **Long scroll time** - Takes significant time to scroll through

---

## Example: Well-Organized Project

```
features/
├── README.md                    # Overview of test organization
├── authentication/
│   ├── login.feature            # 6 scenarios
│   ├── logout.feature           # 3 scenarios
│   ├── password_reset.feature   # 8 scenarios
│   └── two_factor_auth.feature  # 5 scenarios
├── products/
│   ├── search.feature           # 12 scenarios
│   ├── filters.feature          # 10 scenarios
│   ├── product_details.feature  # 7 scenarios
│   └── reviews.feature          # 9 scenarios
├── shopping/
│   ├── cart_add_remove.feature  # 8 scenarios
│   ├── cart_update.feature      # 6 scenarios
│   ├── checkout.feature         # 15 scenarios
│   └── payment.feature          # 11 scenarios
└── account/
    ├── profile.feature          # 8 scenarios
    ├── addresses.feature        # 7 scenarios
    └── order_history.feature    # 5 scenarios
```
