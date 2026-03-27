# 🚨 Copilot Rules (Strict Enforcement)

## 1. Mandatory Documentation Rule

### 🔴 Non-Negotiable

Every change MUST update **Admin Docs**.

### Applies To:

* Features
* Bug fixes
* Refactors
* API changes
* UI changes
* Database/schema updates

### Enforcement:

If documentation is not updated → mark as **INCOMPLETE**

---

## 2. Change Summary Requirement

Every change MUST include:

### Change Summary

* Feature/Module:
* Change Type: (Feature / Fix / Refactor)
* Description:
* Reason:
* Impact:
* Dependencies:

---

## 3. Finance Validation Rules

Copilot MUST enforce:

* Amount > 0
* Valid category/subcategory
* Valid date
* No data inconsistency

---

## 4. Expense Module Rule (Critical)

When "Bills" is selected:

* MUST show subcategory dropdown
* MUST include:

  * Utility Bills
  * Maintenance Bills
  * Others

If "Others":

* Free-text input is REQUIRED

---

## 5. API Rules

All APIs MUST:

* Be versioned
* Be documented
* Include:

  * Request schema
  * Response schema
  * Error handling

---

## 6. Database Rules

Any schema change MUST include:

* Migration script
* Backward compatibility consideration
* Documentation update

---

## 7. Error Handling Rule

* NO silent failures
* MUST return meaningful error messages
* MUST log financial operations

---

## 8. Security Rules

* Validate all inputs
* Prevent data leaks
* Protect financial data

---

## 9. Testing Rule

Every change MUST include:

* Unit tests (logic/calculations)
* Integration tests (flows/APIs)

---

## 10. Definition of Done (DoD)

A task is COMPLETE only if:

* ✅ Code implemented
* ✅ Admin Docs updated
* ✅ Tests added/updated
* ✅ Validations enforced
* ✅ Change summary included

---

## 11. Hard Fail Conditions

Copilot MUST flag or reject output if:

* ❌ Documentation missing
* ❌ Financial logic violated
* ❌ Validation missing
* ❌ API undocumented
* ❌ Schema changed without migration

---

## Final Rule

> "No documentation = No completion"
