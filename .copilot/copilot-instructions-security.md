# 🚨 Copilot Security Rules (Password Enforcement)

## 1. Password Length Rule (MANDATORY)

* Minimum length = 12 characters

### Enforcement:

If password length < 12 → ❌ HARD FAIL

---

## 2. Complexity Rule

Password MUST include:

* 1 uppercase letter
* 1 lowercase letter
* 1 number
* 1 special character

### Enforcement:

Missing any → ❌ FAIL

---

## 3. Password Expiry Rule (CRITICAL)

* Password expires after 90 days

### Enforcement:

* Login MUST check expiry
* If expired:

  * Block access
  * Force password reset

If not implemented → ❌ HARD FAIL

---

## 4. Expiry Check Rule

Copilot MUST ensure:

* Expiry is checked:

  * During login
  * During token validation (if applicable)

---

## 5. Password Storage Rule

* MUST hash passwords using:

  * bcrypt OR argon2

### Enforcement:

Plain text storage → ❌ HARD FAIL

---

## 6. Password Change Rule

On password update:

* Update:

  * `password_last_changed_at`
  * `password_expiry_at = now + 90 days`

---

## 7. Reset Flow Rule

Copilot MUST implement:

* Secure token-based reset
* Token expiry (e.g., 15–30 minutes)

---

## 8. Reuse Prevention Rule (Recommended)

* Prevent last 3–5 passwords reuse

---

## 9. Brute Force Protection Rule

Copilot SHOULD implement:

* Rate limiting
* Account lock after N failed attempts

---

## 10. Audit Rule

Log:

* Password changes
* Failed login attempts
* Forced resets

---

## 11. API Enforcement Rule

All auth APIs MUST:

* Validate password policy
* Enforce expiry rules

---

## 12. Definition of Done (Security)

Feature is complete only if:

* ✅ Password policy enforced
* ✅ Expiry logic implemented
* ✅ Secure hashing used
* ✅ Reset flow implemented
* ✅ Audit logs added
* ✅ Documentation updated

---

## 🚨 Hard Fail Conditions

Copilot MUST reject output if:

* ❌ Password < 12 chars
* ❌ No expiry enforcement
* ❌ No forced reset after 90 days
* ❌ Password stored in plain text
* ❌ No expiry check on login

---

## 🧠 Final Principle

> "Authentication is only as strong as its weakest password policy."
