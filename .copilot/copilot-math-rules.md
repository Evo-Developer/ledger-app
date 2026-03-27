# 🧮 Copilot Math Enforcement Rules (Finance App)

## 🎯 Purpose

Ensure ALL financial features are backed by **correct, consistent, and enforced mathematical logic**.

---

# 1. Core Financial Identity Rule (MANDATORY)

Copilot MUST ensure the system satisfies:

Balance = Income - Expenses - Liabilities + Returns

### Enforcement:

* Any feature affecting money MUST update at least one component of this equation
* If not → ❌ HARD FAIL: "Financial identity broken"

---

# 2. Mandatory Calculation Engine Rule

Copilot MUST NOT scatter calculations across code.

### REQUIRED:

* Centralized calculation layer/service:

  * `calculateBalance()`
  * `calculateSavings()`
  * `calculateSavingsRate()`
  * `calculateNetWorth()`

### Enforcement:

* Inline calculations → ❌ FAIL

---

# 3. Income Rules

Copilot MUST:

* Aggregate all income sources:
  Total Income = sum(all income entries)

* Support:

  * recurring income
  * expected vs actual comparison

### Validation:

* Amount > 0
* Date exists

---

# 4. Expense Rules

Copilot MUST:

* Aggregate all expenses:
  Total Expenses = sum(all expense entries)

* Maintain:

  * category totals
  * subcategory totals

---

# 5. Savings Rule (CRITICAL)

Copilot MUST ALWAYS implement:

Savings = Income - Expenses

### Enforcement:

* If savings is stored directly without calculation → ❌ FAIL

---

# 6. Savings Rate Rule (NON-NEGOTIABLE)

Copilot MUST implement:

Savings Rate = Savings / Income

### Edge Case:

* If Income = 0 → Savings Rate = 0

### Enforcement:

Missing this → ❌ HARD FAIL

---

# 7. Account Balance Rule

For every account:

Closing Balance = Opening Balance + Inflows - Outflows

### Enforcement:

* Transactions MUST update balances
* Mismatch → ❌ FAIL

---

# 8. Transfer Integrity Rule

Copilot MUST enforce:

* Transfer:

  * Debit from source account
  * Credit to destination account

* Net system effect:
  = 0

### Enforcement:

If transfer affects expenses → ❌ FAIL

---

# 9. Budget Math Rule

Copilot MUST calculate:

* Budget Utilization = Actual / Budget
* Remaining Budget = Budget - Actual

### Alerts:

* Trigger warning when utilization > threshold (e.g., 80%)

---

# 10. Cash Flow Rule

Copilot MUST compute:

Net Cash Flow = Total Inflow - Total Outflow

### MUST support:

* daily
* weekly
* monthly aggregation

---

# 11. Liability & EMI Rule

Copilot MUST implement:

* EMI calculation using:
  P, r, n

* Track:

  * principal paid
  * interest paid
  * outstanding balance

---

# 12. Investment Return Rule

Copilot MUST compute:

* Return = Current Value - Invested Amount
* Return % = Return / Invested Amount

---

# 13. Net Worth Rule (CRITICAL)

Copilot MUST implement:

Net Worth = Total Assets - Total Liabilities

### MUST include:

* cash
* investments
* savings

### Enforcement:

Missing net worth → ❌ FAIL

---

# 14. Forecasting Rule

Copilot SHOULD implement:

Future Balance = Current Balance + (Avg Income - Avg Expense) × time

---

# 15. Insight Math Rule

Copilot MUST support:

Change % = (Current - Previous) / Previous

### Used for:

* trend insights
* anomaly detection

---

# 16. Precision Rule (VERY IMPORTANT)

Copilot MUST:

* Use precise numeric types (decimal / bigint)
* NEVER use floating-point for money

### Enforcement:

Float usage → ❌ HARD FAIL

---

# 17. Division Safety Rule

Copilot MUST handle:

* Division by zero
* Null values

### Enforcement:

Unprotected division → ❌ FAIL

---

# 18. Consistency Validation Rule (SYSTEM-WIDE)

Copilot MUST validate:

1. Sum of all account balances = Total Balance
2. Income - Expenses = Savings
3. Assets - Liabilities = Net Worth

### Enforcement:

Mismatch → ❌ DATA INTEGRITY ERROR

---

# 19. Recalculation Rule

Copilot MUST:

* Recompute derived values (NOT store blindly):

  * savings
  * savings rate
  * net worth

### Enforcement:

Stored derived values without recompute → ❌ FAIL

---

# 20. Auditability Rule

Every calculation MUST be:

* Traceable
* Reproducible

### REQUIRED:

* Inputs clearly defined
* No hidden transformations

---

# 21. Performance Rule

Copilot SHOULD:

* Cache computed values where needed
* But MUST invalidate cache on data change

---

# 22. Documentation Rule (Linked)

Every formula implemented MUST be documented in:

Admin Docs → Financial Calculations

---

# 🚨 Hard Fail Summary

Copilot MUST reject output if:

* ❌ Savings not derived from Income - Expenses
* ❌ Savings rate missing
* ❌ Net worth missing
* ❌ Float used for money
* ❌ No centralized calculation layer
* ❌ Transfer logic incorrect
* ❌ No consistency validation

---

# 🧠 Final Principle

> "If the math is wrong, the product is wrong."
