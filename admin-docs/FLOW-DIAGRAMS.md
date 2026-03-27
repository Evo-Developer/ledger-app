# System Flow Diagrams & Flowcharts

## 1. Multi-User Request Handling Flow

### Concurrent Request Processing

```
Multiple simultaneous requests arrive:
  Request 1 (User A - Add Transaction)     Request 2 (User B - View Dashboard)
  Request 3 (Admin - Audit Review)         Request 4 (User A - Edit Goal)
         ↓                                            ↓
  ┌──────────────────────────────────────────────────────────────┐
  │                   API Gateway (Load Balancer)                 │
  │  - Route to available FastAPI instance                        │
  │  - Apply rate limiting (sliding window)                       │
  │  - Extract request context                                    │
  └──────┬────────────────────────────────────────────┬───────────┘
         │                                            │
    [FastAPI-1]                                  [FastAPI-2]
         │                                            │
    ┌────▼────────────────┐                   ┌──────▼──────────┐
    │ Request Handler     │                   │ Request Handler │
    │ (async)             │                   │ (async)         │
    │                     │                   │                 │
    │ 1. Validate JWT     │                   │ 1. Validate JWT │
    │ 2. Check Rate Limit │                   │ 2. Check Rate   │
    │ 3. RBAC Check       │                   │ 3. RBAC Check   │
    │ 4. Request ID Log   │                   │ 4. Request ID   │
    └────┬────────────────┘                   └──────┬──────────┘
         │                                           │
    ┌────▼─────────────────┐        ┌────────────────▼──────┐
    │ Concurrent Lock Mgr  │        │ Concurrent Lock Mgr   │
    │                      │        │                       │
    │ Check lock status    │        │ Check lock status     │
    │ on goal:123          │        │ on transaction:456    │
    │                      │        │                       │
    │ - Not locked → Acq   │        │ - Not locked → Acq    │
    │ - Locked → Backoff   │        │ - Locked → Backoff    │
    └────┬──────────────────┘        └────────────┬──────────┘
         │                                       │
    ┌────▼──────────────────────┐  ┌────────────▼────────┐
    │ Business Logic (async)     │  │ Service Layer       │
    │ - Validation               │  │ - Data Retrieval    │
    │ - Calculation              │  │ - Aggregation       │
    │ - State Update             │  │ - Read-Only         │
    └────┬──────────────────────┘  └────────────┬────────┘
         │                                     │
    ┌────▼──────────────────────┐  ┌──────────▼────────────┐
    │ Database Layer             │  │ Redis Cache Layer    │
    │ (with transaction support) │  │ (read-through)       │
    │                            │  │                      │
    │ BEGIN TRANSACTION          │  │ Cache HIT → Return   │
    │ UPDATE goals SET ...       │  │ Cache MISS → Query   │
    │ INSERT audit_log ...       │  │ DB & Populate Cache  │
    │ COMMIT                     │  │                      │
    └────┬──────────────────────┘  └──────────┬───────────┘
         │                                   │
    ┌────▼──────────────────┐  ┌─────────────▼────────┐
    │ Release Lock          │  │ Return Response      │
    │ Update Cache          │  │ (JSON)               │
    │ Release Connection    │  │                      │
    │ Return HTTP 200       │  │ HTTP 200/202/404/500 │
    └───────────────────────┘  └──────────────────────┘
```

---

## 2. Transaction Processing Flow

### Create/Update Transaction Flowchart

```
START: User submits transaction form
  ↓
STEP 1: VALIDATE INPUT
  ├─ Amount > 0? 
  │  └─ NO → Return Error 400
  ├─ Category exists?
  │  └─ NO → Return Error 400
  └─ Date not in future?
     └─ NO → Return Error 400
  ↓
STEP 2: ACQUIRE LOCK
  ├─ Request: Lock on user_id:X
  ├─ Timeout: 30 seconds
  ├─ Backoff: Exponential with jitter
  └─ Fail? → Return Error 503 (Service Unavailable)
  ↓
STEP 3: CHECK DUPLICATE (Concurrent Prevention)
  ├─ Query: Recent 5-min transactions same amount/category
  ├─ Existing? → Check if idempotent (request_id)
  └─ Match → Return cached response
  ↓
STEP 4: DATABASE TRANSACTION
  ├─ BEGIN
  ├─ INSERT transaction_log
  ├─ UPDATE user_balance
  ├─ INSERT audit_log
  ├─ COMMIT
  └─ Error? → ROLLBACK all changes
  ↓
STEP 5: CACHE UPDATE
  ├─ Update Redis: user:{id}:transactions
  ├─ Update Redis: user:{id}:balance
  └─ TTL: 5 minutes
  ↓
STEP 6: ASYNC TASKS
  ├─ Queue: Recalculate insights
  ├─ Queue: Update budget status
  ├─ Queue: Check threshold alerts
  └─ No wait for completion
  ↓
STEP 7: RELEASE LOCK
  ├─ Redis: DEL lock:transaction:user:X
  ├─ Any failure? → Log & continue
  └─ Don't block client
  ↓
STEP 8: RETURN RESPONSE
  └─ HTTP 201 + transaction_id
     (User sees immediate success)

END
```

---

## 3. Fault Recovery Flow

### Error Handling & Auto-Recovery

```
Request Processing Error Occurs
  ↓
CATEGORIZE ERROR:
  ├─ TIMEOUT (Connection/Query)
  │  └─ Circuit Breaker Check
  │     ├─ Open? (failed 5+ times) → Return cached fallback
  │     └─ Closed? → Retry
  ├─ CONSTRAINT_VIOLATION (Duplicate)
  │  └─ Idempotency Check
  │     ├─ Duplicate → Return existing response
  │     └─ New → Propagate error
  ├─ LOCK_TIMEOUT (Concurrent)
  │  └─ Exponential Backoff
  │     ├─ Retry up to 3 times
  │     ├─ Wait {2, 4, 8} seconds + jitter
  │     └─ Give up → Return 503
  ├─ CONNECTION_FAILED (DB/Cache)
  │  └─ Failover Check
  │     ├─ Replica available? → Use replica for reads
  │     ├─ Cache available? → Serve stale data
  │     └─ Both fail? → Circuit break & wait
  └─ UNKNOWN
     └─ Log stack trace → Return 500


RETRY LOGIC:

Request → Attempt 1 → FAIL
         ↓
       Backoff: Wait 2 sec + (0-500ms jitter)
         ↓
       Attempt 2 → FAIL
         ↓
       Backoff: Wait 4 sec + (0-500ms jitter)
         ↓
       Attempt 3 → FAIL
         ↓
       Backoff: Wait 8 sec + (0-500ms jitter)
         ↓
       Attempt 4 → FAIL
         ↓
       Return Error to Client


CIRCUIT BREAKER STATES:

┌─────────────────────────────────────────────────────────────┐
│  CLOSED (Normal Operation)                                  │
│  ├─ Request succeeds → stay CLOSED                          │
│  └─ 5 consecutive failures → transition OPEN               │
│     (Stop sending requests, fail fast)                      │
└─────────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────────┐
│  OPEN (Failing)                                             │
│  ├─ Requests immediately rejected                           │
│  ├─ Return cached/fallback response                         │
│  └─ After 30 seconds → transition HALF_OPEN               │
│     (Test if service recovered)                            │
└─────────────────────────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────────────────────────┐
│  HALF_OPEN (Testing)                                        │
│  ├─ Single request allowed                                  │
│  ├─ Success → transition CLOSED                             │
│  └─ Failure → transition OPEN (restart timer)               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Multi-User Concurrent Access Flow

### Pessimistic Locking Example

```
Timeline: Two users editing same goal simultaneously

USER A Timeline                          USER B Timeline
─────────────────────────────────────────────────────────
  t=0: GET goal:123
       Read: name="Vac", target=100k

                                          t=0.1: GET goal:123
                                               Read: name="Vac", target=100k

  t=1: Try EDIT goal:123
       POST /goals/123/update
       Acquire LOCK goal:123
       ✓ Lock acquired

                                          t=1.1: Try EDIT goal:123
                                                POST /goals/123/update
                                                Acquire LOCK goal:123
                                                ✗ Lock held by A
                                                Backoff: 100ms

  t=2: Validate new data
       name="Vacation 2026"
       target=150k

                                          t=1.2: Retry acquire lock
                                                ✗ Still held
                                                Backoff: 200ms + jitter

  t=3: DB transaction begins
       BEGIN TRANSACTION
       UPDATE goals ...
       INSERT audit_log ...
       COMMIT

                                          t=1.4: Retry acquire lock
                                                ✗ Still held
                                                Backoff: 400ms + jitter

  t=4: Released LOCK goal:123
       Return HTTP 200

                                          t=1.8: Retry acquire lock
                                                ✓ Lock acquired
                                                Proceed with edit

  t=5: Client cache updated

                                          t=2.1: Detect version mismatch
                                                Previous edit: version=2
                                                Database: version=3
                                                Return HTTP 409 (Conflict)
                                                Suggest refresh

                                          t=2.2: User sees: "Goal was updated"
                                                "Fetch latest? [Refresh]"
```

### Optimistic Locking (High Concurrency)

```
USER A (Read)                            USER B (Read)
─────────────────────────────────────────────────────────
  GET /goals/123
  Response: {
    goal_id: 123,
    name: "Vacation",
    target: 100000,
    version: 5           ← VERSION TAG
  }
                                         GET /goals/123
                                         Response: {
                                           goal_id: 123,
                                           name: "Vacation",
                                           target: 100000,
                                           version: 5
                                         }

  POST /goals/123/update
  Body: {
    name: "Vacation 2026",
    target: 150000,
    version: 5            ← Send matching version
  }
  ✓ version=5 in DB → UPDATE successful
  Response: version=6

                                         POST /goals/123/update
                                         Body: {
                                           name: "Summer Plans",
                                           target: 200000,
                                           version: 5   ← Outdated!
                                         }
                                         ✗ version in DB = 6 (mismatch)
                                         Return HTTP 409 (Conflict)
                                         Suggest: Re-fetch & retry
```

---

## 5. Database Replication Flow

### Write-Through & Read Distribution

```
Write Path (Only Primary):
  ┌────────────┐
  │  Client    │
  │  Request   │
  └─────┬──────┘
        │
        ▼
  ┌────────────────────────┐
  │  API Server            │
  │  (Connection Pool: 20) │
  └─────┬──────────────────┘
        │
        ▼
  ┌──────────────────┐
  │ WRITE to Primary │
  │   (MySQL)        │
  │                  │
  │ INSERT/UPDATE/   │
  │ DELETE txn       │
  │                  │
  │ ✓ Ack → Commit   │
  └────┬─────────────┘
       │
  ┌────▼─────────────────────────────────┐
  │ Async Replication (Binlog Stream)    │
  ├────┬───────────────┬────────────────┤
  │    ▼               ▼                ▼
  │ Replica-1      Replica-2       Replica-3
  │ (Read)         (Read)          (Read/Backup)
  │ Lag: <1s       Lag: <2s        Lag: <5s

Read Path (Primary or Replica):
  ┌────────────┐
  │  Client    │
  │  GET       │
  └─────┬──────┘
        │
        ▼
  ┌──────────────────────┐
  │  Redis Cache Check   │
  │  key: query:hash     │
  └────┬───────────┬─────┘
       │ HIT       │ MISS
       ▼           ▼
    Return     ┌──────────────────────┐
    Cached     │ Read Distribution    │
    Response   │                      │
              │ If recent write (<2s):
              │   → Use Primary (sync)
              │
              │ Otherwise:
              │   → Use Replica
              │     (least lag)
              │
              │ All fail?
              │   → Query Primary
              │   → Update cache
              └────┬─────────────────┘
                   │
                   ▼
              Return Result
```

---

## 6. Session Management & Auth Flow

### JWT Token Lifecycle

```
LOGIN FLOW:
┌──────────────┐
│  Username    │
│  Password    │
└────┬─────────┘
     ▼
┌────────────────────┐
│ Verify Credentials │
│ (bcrypt check)     │
└────┬───────────────┘
     │
     ✓ Valid
     ▼
┌─────────────────────────────────────────────┐
│ Generate JWT Token                          │
│ ├─ Header: {alg: HS256, typ: JWT}          │
│ ├─ Payload: {                               │
│ │   user_id: 123,                           │
│ │   email: user@example.com,                │
│ │   roles: ["user"],                        │
│ │   iat: NOW,                               │
│ │   exp: NOW + 24h                          │
│ │ }                                         │
│ └─ Signature: HMAC-SHA256(                 │
│    base64url(header) + "." +                │
│    base64url(payload),                      │
│    SECRET_KEY                               │
│  )                                          │
└────┬────────────────────────────────────────┘
     ▼
┌─────────────────────────────────────────┐
│ Store in Redis                          │
│ key: token:{token_hash}                 │
│ value: {user_id, created_at, ...}       │
│ TTL: 24 hours                           │
└────┬────────────────────────────────────┘
     ▼
┌─────────────────────────────────────────┐
│ Return to Client                        │
│ Set-Cookie: token=JWT; HttpOnly; Secure│
│ (Also in response body for SPA)         │
└─────────────────────────────────────────┘


AUTHENTICATED REQUEST FLOW:
┌──────────────────────┐
│  Include JWT Token   │
│  Authorization:      │
│  Bearer <JWT>        │
└────┬─────────────────┘
     ▼
┌────────────────────────────────┐
│ API Middleware                 │
│ 1. Extract token from header   │
└────┬───────────────────────────┘
     ▼
┌────────────────────────────────┐
│ 2. Redis Check                 │
│    Is token blacklisted?       │
│    ✓ No → continue             │
│    ✗ Yes → Reject (401)        │
└────┬───────────────────────────┘
     ▼
┌────────────────────────────────┐
│ 3. Verify Signature            │
│    HMAC-SHA256 valid?          │
│    ✓ Yes → continue            │
│    ✗ No → Reject (401)         │
└────┬───────────────────────────┘
     ▼
┌────────────────────────────────┐
│ 4. Check Expiration            │
│    exp > current_time?         │
│    ✓ Yes → continue            │
│    ✗ No → Reject (401)         │
└────┬───────────────────────────┘
     ▼
┌────────────────────────────────┐
│ 5. Extract Claims              │
│    user_id, roles, etc.        │
└────┬───────────────────────────┘
     ▼
┌────────────────────────────────┐
│ 6. Attach to Request Context   │
│    request.user = {            │
│      id: 123,                  │
│      roles: ["user"],          │
│      ...                       │
│    }                           │
└────┬───────────────────────────┘
     ▼
┌────────────────────────────────┐
│ 7. Proceed with Handler        │
│    (User authenticated)        │
└────────────────────────────────┘


LOGOUT/BLACKLIST FLOW:
┌──────────────────┐
│ User clicks      │
│ Logout button    │
└────┬─────────────┘
     ▼
┌─────────────────────────────────┐
│ POST /auth/logout               │
│ Include current JWT token       │
└────┬────────────────────────────┘
     ▼
┌─────────────────────────────────┐
│ Backend Action:                 │
│ Add token to blacklist         │
│ Redis key: blacklist:{hash}    │
│ TTL: token expiration time     │
└────┬────────────────────────────┘
     ▼
┌─────────────────────────────────┐
│ Clear HTTP-Only Cookie         │
│ Set-Cookie: token=; Max-Age=0  │
└─────────────────────────────────┘
```

---

## 7. Goal Progress Calculation Flow

### Real-Time Goal Tracking

```
CALCULATE GOAL PROGRESS:

START: Goal tracking request arrives
  ↓
FETCH GOAL METADATA (from cache or DB)
  ├─ goal_id
  ├─ target_amount
  ├─ start_date
  ├─ target_date
  └─ linked_investments[] array
  ↓
FOR EACH LINKED INVESTMENT:
  │
  ├─ Query: Investment balance
  │  ├─ Mutual Funds
  │  │  └─ Current NAV
  │  ├─ Stocks
  │  │  └─ Current Price × Quantity
  │  └─ Fixed Deposits
  │     └─ Principal + Accrued Interest
  │
  ├─ Check: Recent transactions (high water mark)
  │  ├─ SIP contributions
  │  ├─ Lump sum additions
  │  └─ Withdrawals
  │
  └─ Calculate: Effective current value
     ├─ Base: Previous month balance
     ├─ Add: This month contributions
     ├─ Subtract: This month withdrawals
     ├─ Adjust: Market valuation changes
     └─ Cache: 10-minute TTL
  ↓
SUM ALL INVESTMENTS
  current_value = Σ(all linked investment current values)
  ↓
CALCULATE METRICS:
  ├─ Progress %: (current_value / target_amount) × 100
  ├─ Remaining: max(0, target_amount - current_value)
  ├─ Days Left: (target_date - today).days
  ├─ Monthly Required: (remaining / months_left) if months_left > 0
  │
  └─ Feasibility Status:
     ├─ IF progress % ≥ 100: "MET" ✓
     ├─ ELSE IF (progress % / months_pct) ≥ 1.0: "ON_TRACK" →
     ├─ ELSE: "AT_RISK" ⚠️
     └─ IF target_date < today: "OVERDUE" ✗
  ↓
UPDATE CACHE:
  Redis key: goal:{id}:progress
  Value: {
    current: {value},
    target: {value},
    percentage: {%},
    status: "ON_TRACK",
    months_left: {num},
    monthly_required: {value},
    last_updated: {timestamp}
  }
  TTL: 10 minutes
  ↓
RETURN TO CLIENT:
  ├─ Progress bar: current/target
  ├─ Status indicator: ON_TRACK/AT_RISK/MET
  ├─ Monthly investment required: $X
  └─ Timeline: Complete by {date}

END
```

---

## 8. Background Job Processing Flow

### Async Task Queue (Celery/RQ)

```
ENQUEUE BACKGROUND JOB:

Frontend Action
  (e.g., Adding transaction)
       ↓
Backend API Handler
       ↓
    Business Logic
       ↓
  After Success ✓
       │
       ├─ Enqueue: recalculate_insights
       ├─ Enqueue: update_budget_status
       ├─ Enqueue: send_email_summary
       └─ Enqueue: sync_external_apis
       │
       └─ Return HTTP 200 to client
         (Don't wait for jobs)


EXECUTE BACKGROUND JOB:

Job Queue (Redis)
  {
    task_id: "uuid",
    task_name: "recalculate_insights",
    user_id: 123,
    args: {...},
    scheduled_at: ISO8601,
    max_retries: 3
  }
     ↓
Worker Pool (Celery Workers)
     ├─ Worker 1
     ├─ Worker 2
     └─ Worker 3
     ↓
   DEQUEUE JOB
     ↓
   ACQUIRE LOCK (prevent duplicate)
     ├─ Lock exists? → Skip job
     └─ No lock? → Proceed
     ↓
   EXECUTE TASK
     ├─ Recalculate metrics (DB query)
     ├─ Update cache (Redis)
     ├─ Broadcast to clients (WebSocket/polling)
     └─ Insert audit log
     ↓
   ON SUCCESS:
     ├─ Update job status: COMPLETED
     ├─ Set result in Redis
     ├─ Notify client (if polling)
     └─ Cleanup resources
     ↓
   ON FAILURE:
     ├─ Update job status: FAILED
     ├─ Log error & stack trace
     ├─ Retry? (exponential backoff)
     │  ├─ Retry 1: Wait 60 seconds
     │  ├─ Retry 2: Wait 5 minutes
     │  └─ Retry 3: Wait 30 minutes
     └─ After max retries: Alert admins
```

---

## 9. Load Balancing & Failover

### Health Check & Auto-Failover Timeline

```
NORMAL OPERATION:

Load Balancer
     ↓
  ┌─┴─┐
  │   │  (Primary routing)
  ▼   ▼
FastAPI-1 ✓   FastAPI-2 ✓   FastAPI-3 ✓
Health: UP    Health: UP    Health: UP


HEALTH CHECK TRIGGER:

Every 30 seconds:
  ├─ GET /health → FastAPI-1
  ├─ GET /health → FastAPI-2
  └─ GET /health → FastAPI-3


FAILURE SCENARIO:

t=0:00  Requests flowing normally
        FastAPI-1 handling 30% traffic
        FastAPI-2 handling 35% traffic
        FastAPI-3 handling 35% traffic

t=0:30  Health check runs:
        FastAPI-1 ✓ OK
        FastAPI-2 ✓ OK
        FastAPI-3 ✓ OK

t=2:15  Database connection timeout occurs on FastAPI-2
        (Primary MySQL connection pool exhausted)

t=2:30  Health check finds FastAPI-2 UNHEALTHY
        ├─ Response time: 15000ms (timeout)
        ├─ Status: 503 Service Unavailable
        ├─ Threshold exceeded (5 consecutive failures)
        └─ Mark as DOWN

t=2:31  Load Balancer Action:
        ├─ Stop sending new requests to FastAPI-2
        ├─ Wait 5 seconds for in-flight requests
        ├─ Force close connections
        ├─ Drain pending queue
        └─ Redistribute traffic:
           - FastAPI-1: 30% → 50%
           - FastAPI-3: 35% → 50%

t=3:00  Regular health check again:
        FastAPI-1 ✓ OK
        FastAPI-2 ? Retry (still unhealthy)
        FastAPI-3 ✓ OK

t=3:30  FastAPI-2 still DOWN
        Readiness probe: FAILED
        Circuit breaker: OPEN

t=4:00  FastAPI-2 auto-restart triggered
        ├─ Clear connection pool
        ├─ Reload configuration
        ├─ Reconnect to DB
        └─ Warm up cache

t=4:30  Health check: FastAPI-2 responds
        ├─ Response time: 200ms (normal)
        ├─ Status: 200 OK
        └─ Database responsive

t=4:45  Gradual traffic reintroduction:
        ├─ FastAPI-1: 50% → 40%
        ├─ FastAPI-2: 0% → 20% (ramp up)
        └─ FastAPI-3: 50% → 40%

t=5:00  Monitor FastAPI-2 stability:
        ├─ No errors in 5 health checks? → Continue
        ├─ Error rate < 1%? → Increase traffic
        └─ If issues: → Revert to OFF

t=5:30  Back to normal distribution:
        FastAPI-1: ~33%
        FastAPI-2: ~33%
        FastAPI-3: ~33%
```

---

## 10. Data Consistency Under Concurrent Edits

### Last-Write-Wins with Version Tags

```
SCENARIO: Two users edit user profile simultaneously

USER A (Browser 1)              USER B (Browser 2)
────────────────────────────────────────────────

GET /profile
Response:
  ✓ name: "John"
  ✓ email: "john@old.com"
  ✓ version: 10

                                GET /profile
                                Response:
                                  ✓ name: "John"
                                  ✓ email: "john@old.com"
                                  ✓ version: 10

Form: "John Doe"
      "john@new.com"

POST /profile/update
Body: {
  name: "John Doe",
  email: "john@new.com",
  version: 10
}

✓ DB check: version=10 matches
✓ Update successful
✓ New version: 11

Return 200 OK + version:11

                                Form: "J. Smith"
                                      "john@smith.com"

                                POST /profile/update
                                Body: {
                                  name: "J. Smith",
                                  email: "john@smith.com",
                                  version: 10
                                }

                                ✗ DB check: version≠10
                                  DB version: 11
                                Return 409 CONFLICT

                                Body: {
                                  error: "Profile was updated",
                                  current_version: 11,
                                  server_data: {
                                    name: "John Doe",
                                    email: "john@new.com"
                                  }
                                }

Client sees success             Client sees conflict:
User A's changes saved          "Your changes conflict
to server                       with another update.
                               Fetch latest version?"

                                User B clicks "Refresh"
                                ↓
                                GET /profile
                                New version: 11
                                ↓
                                Shows: "John Doe"
                                        "john@new.com"
                                ↓
                                User B can now edit
                                with fresh data
```

