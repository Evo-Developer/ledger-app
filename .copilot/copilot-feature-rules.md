# 🚨 Copilot Feature Enforcement Rules (Finance App)

## 🎯 Purpose

Ensure all critical finance features are **systematically implemented, validated, and not skipped** during development.

---

# 1. Core Feature Coverage Rule (MANDATORY)

Copilot MUST ensure the system includes ALL core financial modules:

* Income
* Expenses
* Accounts
* Transfers
* Savings
* Liabilities
* Investments
* Dashboard

### Enforcement:

If any module is missing → flag as:
❌ **"Core financial module missing"**

---

# 2. Income Tracking Rules

Copilot MUST enforce:

* Support for multiple income sources
* Recurring income capability
* Expected vs actual tracking

### Validation:

* Amount > 0
* Date required
* Source/category required

---

# 3. Expense Tracking Rules

Copilot MUST ensure:

* Category + subcategory structure
* Support for:

  * One-time expenses
  * Recurring expenses
* Payment method tracking

### Mandatory Fields:

* Amount
* Category
* Date
* Account

---

# 4. Bills Subcategory Rule (CRITICAL – NON-NEGOTIABLE)

When Expense Category = "Bills":

### MUST INCLUDE:

* Subcategories:

  * Utility Bills
  * Maintenance Bills
  * Others

### Conditional Logic:

* If "Others":

  * Free-text input MUST be enabled
  * Free-text input MUST be REQUIRED

### Enforcement:

Missing this → ❌ HARD FAIL

---

# 5. Account & Balance Rules

Copilot MUST ensure:

* Multiple accounts supported:

  * Bank
  * Wallet
  * Credit card

* Each transaction MUST:

  * Be linked to an account
  * Update balance correctly

---

# 6. Transfer Rules

* Transfers between accounts:

  * MUST NOT be treated as expenses
  * MUST update both accounts correctly

---

# 7. Savings & Metrics Rules (CRITICAL)

Copilot MUST auto-implement:

* Savings calculation:
  Savings = Income - Expenses

* Savings Rate:
  Savings Rate = Savings / Income

### Enforcement:

If savings rate is missing → ❌ FAIL

---

# 8. Budgeting Rules

Copilot MUST include:

* Category-level budgets
* Budget vs actual comparison

### Alerts:

* Warn when nearing/exceeding budget

---

# 9. Cash Flow Tracking

Copilot MUST support:

* Monthly trends
* Daily/weekly breakdown
* Burn rate calculation

---

# 10. Liabilities Tracking

Copilot MUST include:

* Loan tracking:

  * Principal
  * Interest
  * EMI
  * Due dates

* Outstanding balance tracking

---

# 11. Investment Tracking

Copilot MUST support:

* Asset categories:

  * Stocks
  * Mutual Funds
  * Fixed Deposits

* Track:

  * Invested amount
  * Current value
  * Returns

---

# 12. Dashboard Rule (MANDATORY)

Copilot MUST ensure dashboard includes:

* Total balance
* Income vs expenses
* Category breakdown
* Savings trend

### Enforcement:

Missing dashboard metrics → ❌ FAIL

---

# 13. Net Worth Rule (ADVANCED BUT REQUIRED)

Copilot MUST implement:

Net Worth = Assets - Liabilities

### Track over time:

* Historical trend

---

# 14. Insight Engine Rule (DIFFERENTIATOR)

Copilot SHOULD generate logic for:

* Spending insights
* Savings drop alerts
* Optimization suggestions

Example:

* “Spending increased by 20% in Food”

---

# 15. Forecasting Rule

Copilot SHOULD include:

* End-of-month balance prediction
* Cash shortage alerts

---

# 16. Audit & Traceability Rule

Copilot MUST enforce:

* Every financial change must be logged:

  * Old value
  * New value
  * Timestamp

### Enforcement:

No audit trail → ❌ FAIL

---

# 17. Security Rule

* Validate all inputs
* No sensitive data exposure
* Secure handling of financial data

---

# 18. Data Integrity Rule

Copilot MUST:

* Prevent silent updates
* Ensure consistency across:

  * Accounts
  * Transactions
  * Reports

---

# 19. UX Efficiency Rule

Copilot SHOULD ensure:

* Fast expense entry
* Smart defaults
* Minimal user friction

---

# 20. Documentation Rule (Linked Enforcement)

Every feature implemented MUST:

* Update Admin Docs
* Include Change Summary

---

# 21. Definition of Feature Completion

A feature is COMPLETE only if:

* ✅ Logic implemented
* ✅ UI handled
* ✅ Validations added
* ✅ Metrics updated
* ✅ Reflected in dashboard
* ✅ Documented

---

# 🚨 Hard Fail Summary

Copilot MUST reject output if:

* ❌ Savings rate not implemented
* ❌ Bills subcategory rule missing
* ❌ No account linkage
* ❌ No audit trail
* ❌ No documentation update
* ❌ Dashboard not updated

---

# 🧠 Final Principle

> "Tracking is not enough. Every feature must contribute to financial clarity, accuracy, or decision-making."
