# Copilot Instructions for FinApp

## 🧭 Overview
This is the central instruction file. Refer to the modular files below for detailed guidance:

- backend.md → FastAPI architecture & coding
- database.md → MySQL design & performance
- api-guidelines.md → API standards
- security.md → Secure coding practices
- performance.md → Scalability & concurrency
- code-quality.md → Clean code, SOLID, linting
- testing.md → Testing strategy
- ui-guidelines.md → UI/UX consistency

---

## 🎯 Goal
Generate clean, scalable, secure, and production-ready code for a high-performance FinTech application.

---

# backend.md

## FastAPI Guidelines
- Use async/await for all I/O operations
- Use Pydantic for validation
- Structure project into routers, services, repositories
- Use dependency injection

## Architecture
- Follow SOLID principles
- Use service layer for business logic
- Keep controllers thin

---

# database.md

## MySQL Best Practices
- Use proper indexing
- Avoid N+1 queries
- Use connection pooling
- Normalize schema where appropriate

## Performance
- Optimize queries
- Use transactions for consistency
- Prefer optimized SQLAlchemy usage

---

# api-guidelines.md

## API Design
- Follow REST principles
- Use proper HTTP status codes
- Version APIs (/v1/...)
- Use pagination

## Validation
- Validate all inputs
- Use strict schemas

---

# security.md

## Security Rules
- Use environment variables for secrets
- Implement JWT/OAuth2
- Hash passwords (bcrypt)
- Prevent SQL injection
- Use HTTPS
- Apply rate limiting
- Restrict CORS

---

# performance.md

## Scalability
- Prefer async I/O
- Use caching (Redis)
- Use load balancing (Nginx)

## Concurrency
- Use async over threading
- Use thread pools for CPU-bound tasks
- Use task queues (Celery)

---

# code-quality.md

## Clean Code
- Keep functions small
- Avoid deep nesting
- Use meaningful names

## Naming
- snake_case (variables/functions)
- PascalCase (classes)
- UPPER_CASE (constants)

## Linting
- Use pylint
- Follow PEP8
- Use black & isort

---

# testing.md

## Testing Strategy
- Use pytest
- Unit + integration tests
- Mock dependencies
- Maintain 80%+ coverage

---

# ui-guidelines.md

## UI Rules
- Keep UI minimal
- Ensure responsiveness
- Use reusable components
- Maintain consistent spacing & typography


---

# finance-domain.md

## 💰 Core Financial Data Model

### Entities
- User
- Account (bank, wallet, credit)
- Transaction
- Category (income/expense)
- Ledger
- Balance Snapshot

### Transaction Rules
- Every transaction MUST have:
  - unique id
  - timestamp (UTC)
  - amount (decimal, no float)
  - type (DEBIT/CREDIT)
  - account_id
- Transactions must be immutable after creation (no updates, only reversals)
- Always store currency explicitly

### Double Entry Ledger System
- Every financial transaction must create **at least two entries**:
  - Debit entry
  - Credit entry
- Total debits MUST equal total credits
- Never allow imbalance

Example:
- Expense of ₹100
  - Debit: Expense Account
  - Credit: Bank Account

### Ledger Rules
- Maintain an append-only ledger
- Never delete ledger entries
- Each ledger entry must reference a transaction_id
- Ensure idempotency (avoid duplicate entries)

---

## 🔄 Reconciliation Rules

### Bank Reconciliation
- Match internal transactions with external bank data
- Flag unmatched transactions
- Support manual and automated reconciliation

### Consistency Checks
- Sum of ledger entries = account balance
- Periodic balance snapshots for audit

### Error Handling
- Use compensating transactions instead of deletes
- Maintain audit trail for every correction

---

## 📊 Financial Calculations

- Always use Decimal (never float)
- Handle rounding explicitly
- Support multi-currency conversion
- Maintain historical exchange rates

---

## 🔐 Financial Security

- Log all financial actions (audit logs)
- Prevent duplicate transactions (idempotency keys)
- Enforce strict validation on monetary inputs

---

## 🚀 Performance for Finance

- Index transaction tables heavily (user_id, date)
- Use partitioning for large datasets
- Use read replicas for analytics queries

---

## ❌ Avoid (Finance Specific)

- Using float for money
- Updating financial records directly
- Deleting transactions or ledger entries
- Skipping audit logs

---

## ✅ Goal (Finance Domain)

Ensure accuracy, auditability, and consistency of all financial data while supporting high-scale transaction processing.

---

## 🗄️ Suggested MySQL Schema (Simplified)

### accounts
- id (PK)
- user_id
- type (bank, wallet, credit)
- currency
- created_at

### transactions
- id (PK)
- user_id
- amount (DECIMAL)
- currency
- type (DEBIT/CREDIT)
- status
- created_at

### ledger_entries
- id (PK)
- transaction_id (FK)
- account_id (FK)
- entry_type (DEBIT/CREDIT)
- amount (DECIMAL)
- created_at

### balance_snapshots
- id (PK)
- account_id
- balance
- created_at

---

## 🌐 Sample FastAPI Endpoints

### Create Transaction
POST /v1/transactions
- Validate input
- Create transaction record
- Create corresponding ledger entries
- Ensure debit = credit

### Get Transactions
GET /v1/transactions
- समर्थन pagination
- Filter by date, category

### Reconcile Transactions
POST /v1/reconcile
- Match internal vs external records
- Mark reconciled/unreconciled

---

## ⚡ Event-Driven Architecture (Recommended)

- Use message queues (Kafka / RabbitMQ)
- Emit event: transaction_created
- Consumers:
  - ledger service
  - analytics service
  - notification service

---

## 🚨 Fraud & Anomaly Detection (Basic Rules)

- Flag unusually high transactions
- Detect rapid repeated transactions
- Detect location/device anomalies
- Maintain risk score per user

---

## 📈 Scaling Strategy

- Separate write DB and read replicas
- Use sharding for large transaction tables
- Cache frequently accessed balances
- Use async workers for heavy jobs

---

## 🧠 Advanced Guidelines

- Use idempotency keys for APIs
- Implement eventual consistency where needed
- Prefer append-only architecture
- Design for audit and compliance from day one

# Copilot Instruction: Mandatory Admin Documentation Updates

## Rule
For every code change, feature addition, bug fix, refactor, or configuration update, Copilot MUST ensure that corresponding documentation is updated in the Admin Docs.

## Scope of Documentation
Admin Docs include (but are not limited to):
- Feature descriptions
- API changes (endpoints, request/response structure)
- Data model updates
- Business logic changes
- UI/UX workflow changes
- Configuration or environment variable updates
- Known issues or limitations

## Expected Behavior
Whenever making or suggesting a change, Copilot should:

1. **Check Impact**
   - Determine if the change affects functionality, structure, or behavior.

2. **Update Documentation**
   - Add or update relevant sections in Admin Docs.
   - Ensure clarity, accuracy, and completeness.

3. **Create Missing Docs (if needed)**
   - If no documentation exists for a feature/module, create a new section.

4. **Maintain Structure**
   - Follow existing documentation format and hierarchy.
   - Use consistent headings, formatting, and naming conventions.

5. **Summarize Changes**
   - Add a brief "Change Summary" section including:
     - What changed
     - Why it changed
     - Impact

6. **Version Awareness**
   - Tag updates with version, date, or release note if applicable.

## Enforcement
- No code change should be considered complete without documentation updates.
- If documentation is not updated, Copilot must flag it as incomplete work.

## Example
If a new expense category feature is added:
- Update Admin Docs → Expense Module
- Add section: "Expense Categories"
- Include:
  - Category types (Utility, Maintenance, Others)
  - Behavior of "Others" (free-form input)
  - UI flow and validation rules

---

## Principle
> "If it changes the system, it must be documented."


# 🤖 Copilot Instructions (Finance Application)

## Purpose

Guide Copilot to generate **high-quality, production-grade, finance-safe code** aligned with business logic, documentation standards, and system architecture.

---

## 🧠 How Copilot Should Think

Before generating code, ALWAYS:

1. Understand the feature and its financial impact
2. Validate against finance domain rules
3. Check if documentation needs updates
4. Ensure consistency with existing architecture

---

## 💰 Finance Domain Context

### Core Relationships

* Income increases Balance
* Expenses decrease Balance
* Savings = Income - Expenses
* Savings Rate = Savings / Income
* Investments are part of Savings
* Liabilities are future obligations
* Balance = Income - Expenses - Liabilities + Returns

---

## 📊 Data Integrity Expectations

* Financial data must NEVER be silently modified
* Prefer immutable or versioned records
* Maintain audit trails for all transactions
* Avoid floating-point inaccuracies

---

## 🧩 Feature-Specific Context (Expense Module)

When implementing **Expense → Bills**:

* Show subcategory dropdown:

  * Utility Bills
  * Maintenance Bills
  * Others

* If "Others" selected:

  * Enable mandatory free-text input

---

## 🧱 Architecture Guidelines

* Follow modular design:

  * UI Layer
  * Business Logic Layer
  * Data Layer

* Avoid tight coupling

* Promote reusability

---

## 🔌 API Expectations

* Use versioned APIs (`/v1/...`)
* Define clear request/response structures
* Handle errors gracefully

---

## 🧪 Testing Expectations

* Add unit tests for calculations
* Add integration tests for workflows
* Cover edge cases:

  * zero income
  * high expenses
  * invalid inputs

---

## 📚 Documentation Awareness

Copilot must always check:

* Does this change affect:

  * API?
  * Data model?
  * UI?
  * Business logic?

If YES → documentation must be updated.

---

## 🎯 Output Quality

Generated code must be:

* Readable
* Maintainable
* Well-structured
* Properly validated
* Consistent with existing patterns

---

## 🚫 Avoid

* Hardcoded financial values
* Ambiguous naming
* Missing validations
* Undocumented logic

---

## ✅ Goal

Help build a **robust, auditable, and scalable finance system** — not just working code.
