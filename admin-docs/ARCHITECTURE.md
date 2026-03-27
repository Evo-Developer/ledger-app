# Ledger App - Enterprise Architecture Documentation

## Table of Contents
1. [C1 Context Diagram](#c1-context-diagram)
2. [C2 Container Diagram](#c2-container-diagram)
3. [C3 Component Diagram](#c3-component-diagram)
4. [System Deployment](#system-deployment)
5. [Scalability Strategy](#scalability-strategy)

---

## C1 - Context Diagram

### High-Level System Overview

The Ledger App operates in a multi-user environment with external integrations and support services.

**Actors:**
- **End Users**: Individual finance managers accessing the web platform
- **Admins**: System administrators managing users, audits, and system configuration
- **Integration Providers**: External services (Gmail, PhonePe, Groww, Paytm, Google Pay)
- **Database**: Persistent financial data storage
- **Message Queue**: Asynchronous task processing (email, reports, background jobs)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          External Services                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Gmail   │  │ PhonePe  │  │  Groww   │  │  Paytm   │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
├───────┼──────────────┼──────────────┼──────────────┼─────────────────┤
│       │              │              │              │                 │
│       └──────────────┼──────────────┼──────────────┘                 │
│                      ▼                                                │
│          ┌────────────────────────────┐                              │
│          │   Ledger App (FastAPI)     │                              │
│          │  - REST API Endpoints      │                              │
│          │  - Real-time Sync          │                              │
│          │  - Role-based Access       │                              │
│          │  - Audit Logging           │                              │
│          └────────┬───────────────────┘                              │
│                   │                                                  │
│    ┌──────────────┼──────────────┐                                   │
│    ▼              ▼              ▼                                   │
│  ┌────┐    ┌────────────┐   ┌─────────┐                             │
│  │Web │    │ Database   │   │  Cache  │                             │
│  │UI  │    │  MySQL 8.0 │   │  Redis  │                             │
│  └────┘    └────────────┘   └─────────┘                             │
│    ▲           (Users,            (Session,                         │
│    │          Transactions,      Encrypted                          │
│    │          Goals, etc)        Credentials)                       │
└────┼──────────────────────────────────────────────────────────────────┘
     │
  ┌──┴────────────────────┐
  │   End Users & Admins   │
  │  (Multi-tenant, RBAC)  │
  └───────────────────────┘
```

---

## C2 - Container Diagram

### Technology Stack & Container Boundaries

This diagram shows the major technology containers and their interactions.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              Internet Boundary                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │                    Web Browser (SPA)                             │      │
│  │  ┌────────────────────────────────────────────────────────┐    │      │
│  │  │  Frontend Application (Vanilla JS)                     │    │      │
│  │  │  - Dashboard, Forms, Charts (Chart.js)                 │    │      │
│  │  │  - Local Storage (encryption, persistence)             │    │      │
│  │  │  - API Client Layer (axios wrapper)                    │    │      │
│  │  └────────────────────────────────────────────────────────┘    │      │
│  └────────┬─────────────────────────────────────────────────────┬─┘      │
│           │         (HTTPS/TLS 1.3)      (WebSocket)           │        │
│           │                                                     │        │
├───────────┼─────────────────────────────────────────────────────┼────────┤
│           │                                                     │        │
│  ┌────────▼─────────────────────────────────────────────────────▼──┐    │
│  │              Core Application Server (FastAPI)                   │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │  API Gateway Layer                                       │   │    │
│  │  │  - Request Validation & Serialization (Pydantic)        │   │    │
│  │  │  - Rate Limiting (Sliding Window)                       │   │    │
│  │  │  - Request ID Correlation                              │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │  Application Services                                    │   │    │
│  │  │  - Transaction Processing                               │   │    │
│  │  │  - Investment Management                                │   │    │
│  │  │  - Goal Tracking                                        │   │    │
│  │  │  - Report Generation                                    │   │    │
│  │  │  - Concurrent Access Handler                           │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │  Middleware Stack                                        │   │    │
│  │  │  - Request Logging & Tracing                            │   │    │
│  │  │  - Error Handling & Recovery                            │   │    │
│  │  │  - Authentication (JWT/OAuth2)                          │   │    │
│  │  │  - Role-based Access Control (RBAC)                     │   │    │
│  │  │  - Circuit Breaker & Retry Logic                        │   │    │
│  │  │  - Connection Pool Management                           │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  └────────┬──────────────────────────────────────────────────┬──────┘    │
│           │                                                  │           │
├───────────┼──────────────────────────────────────────────────┼───────────┤
│           │                                                  │           │
│  ┌────────▼────────────┐  ┌──────────────┐  ┌──────────────▼──────┐    │
│  │  Primary Database   │  │   Redis      │  │  Background Tasks   │    │
│  │  (MySQL 8.0)        │  │   Cache      │  │  (Celery/RQ)        │    │
│  │                     │  │              │  │                     │    │
│  │  - Users            │  │ - Sessions   │  │ - Email Sending     │    │
│  │  - Transactions     │  │ - Encrypted  │  │ - Report Gen        │    │
│  │  - Financial Data   │  │   Credentials│  │ - Sync Tasks        │    │
│  │  - Audit Logs       │  │ - Cache      │  │ - Cleanup Jobs      │    │
│  │  - Replication      │  │   Layer      │  │                     │    │
│  │    (Read Replicas)  │  └──────────────┘  └─────────────────────┘    │
│  └─────────────────────┘                                                 │
│           │                                                              │
└───────────┼──────────────────────────────────────────────────────────────┘
            │
      ┌─────▼──────────┐
      │ Backup & Logs  │
      │ (S3/Storage)   │
      └────────────────┘
```

### Container Responsibilities

| Container | Technology | Responsibility | Scaling |
|-----------|-----------|-----------------|---------|
| **Web UI** | Vanilla JS, Chart.js | User interface, client-side logic | CDN distribution |
| **API Server** | FastAPI, Python 3.11+ | Business logic, route handling | Horizontal via load balancer |
| **Primary DB** | MySQL 8.0 | Persistent storage, transactions | Vertical + read replicas |
| **Cache Layer** | Redis | Session store, encrypted credentials | Redis Cluster |
| **Task Queue** | Celery/FastAPI Background | Background jobs, async operations | Worker scaling |
| **Auth System** | JWT + OAuth2 | Token generation, user validation | Stateless + cache |

---

## C3 - Component Diagram

### Backend System Components (Detailed View)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Layer                        │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    Route Handlers (main.py)                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │Transactions│ │Investments│ │  Goals   │  │ Reports  │       │   │
│  │  │  Routes   │  │  Routes   │  │ Routes   │  │ Routes   │       │   │
│  │  └──────┬───┘  └──────┬────┘  └──────┬───┘  └──────┬───┘       │   │
│  └─────────┼─────────────┼───────────────┼──────────────┼───────────┘   │
│            │             │               │              │               │
│  ┌─────────▼─────────────▼───────────────▼──────────────▼───────────┐   │
│  │                    Service Layer (DDD)                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │Transaction   │  │Investment    │  │Goal          │             │   │
│  │  │Service       │  │Service       │  │Service       │             │   │
│  │  │              │  │              │  │              │             │   │
│  │  │- Process     │  │- Create      │  │- Add Goal    │             │   │
│  │  │- Validate    │  │- Update      │  │- Track       │             │   │
│  │  │- Persist     │  │- Calculate   │  │- Calculate   │             │   │
│  │  │- Audit       │  │- Track ROI   │  │  Feasibility │             │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │   │
│  └─────────┼──────────────────┼────────────────┼───────────────────────┘   │
│            │                  │                │                         │
│  ┌─────────▼──────────────────▼────────────────▼───────────────────────┐  │
│  │              Concurrent Access Handler & Lock Manager               │  │
│  │                                                                     │  │
│  │  ┌─────────────────────┐        ┌──────────────────────────┐       │  │
│  │  │ Request ID Logger   │        │ Distributed Lock Service │       │  │
│  │  │                     │        │ (Redis-based)            │       │  │
│  │  │- Correlation IDs    │        │                          │       │  │
│  │  │- Request Tracking   │        │- Optimistic Locking      │       │  │
│  │  │- Audit Trail        │        │- Pessimistic Locking     │       │  │
│  │  │- Performance Metrics│        │- Deadlock Detection      │       │  │
│  │  └─────────────────────┘        │- Lock Timeout Handler    │       │  │
│  │                                  └──────────────────────────┘       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                  Resilience Layer (Fault Tolerance)            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │Circuit       │  │Retry         │  │Bulkhead      │          │   │
│  │  │Breaker       │  │Logic         │  │Pattern       │          │   │
│  │  │              │  │              │  │              │          │   │
│  │  │- Monitor DB  │  │- Exponential │  │- Thread Pool │          │   │
│  │  │- Fail Fast   │  │  Backoff     │  │- Isolation   │          │   │
│  │  │- Recovery    │  │- Max Retries │  │- Capacity    │          │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │   │
│  └─────────┼──────────────────┼────────────────┼──────────────────┘   │
└────────────┼──────────────────┼────────────────┼─────────────────────┘
             │                  │                │
    ┌────────▼──────┬───────────▼──────┬────────▼────────┐
    │                │                  │                │
    ▼                ▼                  ▼                ▼
┌────────┐   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Primary │   │Replica DB    │  │  Redis       │  │ Message      │
│ MySQL  │   │  (Read-only) │  │  Cache       │  │ Queue        │
│        │   │  (Async Sync │  │              │  │ (Task Jobs)  │
└────────┘   └──────────────┘  └──────────────┘  └──────────────┘
```

### Component Interactions

```
Frontend Request Flow:
  Browser → HTTPS → API Gateway → Rate Limiter → Auth Middleware 
  → Request Logger → Service Layer → Lock Manager → DB Operations
  → Response Builder → Cache Update → Client Response

Error Handling Flow:
  Exception Occurs → Circuit Breaker Check → Retry Attempt 
  → Backoff & Timeout → Fallback Response → Log & Alert 
  → Dashboard Health Update

Concurrent Access:
  Request 1 (Lock) → Acquire Distributed Lock → Execute → Release
  Request 2 (Wait) → Lock Contention → Exponential Backoff → Retry
  Request 3 (Cache) → Cache Hit → Serve from Redis → No DB Access
```

---

## System Deployment

### Production Architecture (High Availability)

```
                        ┌─────────────────┐
                        │  Load Balancer  │
                        │  (Nginx/HAProxy)│
                        └────────┬────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ FastAPI 1    │  │ FastAPI 2    │  │ FastAPI N    │
        │ (Port 8000)  │  │ (Port 8001)  │  │ (Port 800N)  │
        │ - Active     │  │ - Active     │  │ - Active     │
        │ - Health     │  │ - Health     │  │ - Health     │
        │   Check      │  │   Check      │  │   Check      │
        └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
               │                 │                 │
               │   Shared Resources               │
               └────────┬────────┬────────────────┘
                        │        │
        ┌───────────────┴───┐    │
        ▼                   ▼    ▼
    ┌─────────┐    ┌─────────────────┐
    │  MySQL  │    │ Redis Sentinel  │
    │ Primary │    │ (HA Cluster)    │
    │  + 2    │    │                 │
    │ Replicas│    │ - Master        │
    │ (Async) │    │ - Slaves (2)    │
    └─────────┘    │ - Auto-failover │
                   └─────────────────┘
```

### Docker Deployment

```yaml
Services:
  - api-v1: FastAPI service instance 1
  - api-v2: FastAPI service instance 2 (for upgrades)
  - mysql-primary: Master database
  - mysql-replica-1: Read replica
  - mysql-replica-2: Read replica
  - redis-master: Cache primary
  - redis-sentinel-1: Sentinel node
  - redis-sentinel-2: Sentinel node
  - redis-sentinel-3: Sentinel node
  - celery-worker-1: Background task workers
  - celery-worker-2: Celery beat scheduler
  - nginx: Reverse proxy & load balancer
```

---

## Scalability Strategy

### Horizontal Scaling

**API Servers:**
- Stateless FastAPI instances behind load balancer
- Health checks every 30 seconds
- Auto-scaling based on CPU (>70%) and memory (>80%)
- Max 10 instances per deployment zone

**Database:**
- Write to primary MySQL instance
- Read from replica nodes (up to 3 per zone)
- Automatic replication lag monitoring
- Replica failover to primary if lag exceeds 5 seconds

**Cache Layer:**
- Redis Cluster mode with 3 master shards
- 2 replicas per shard for failover
- Consistent hashing for key distribution
- Memory: 4GB → 16GB (auto-scale)

### Vertical Scaling

**When to scale up (per instance):**
- API Server CPU sustained >75% for 10 minutes
- Memory usage >85%
- Database connection pool > 90% utilization
- Queue depth > 1000 jobs

### Caching Strategy

```
Cache Hierarchy:
  Browser (localStorage) 
    ↓ (miss)
  Redis (Session, Encrypted Credentials, Frequent Queries)
    ↓ (miss)
  Database (MySQL Primary)
    ↓ (frequent access pattern)
  Database Replica (Read-heavy queries)

TTL Strategy:
  - User Sessions: 24 hours
  - Financial Aggregates: 5 minutes
  - Goals Progress: 10 minutes
  - Exchange Rates: 1 hour
  - Static Data: 24 hours
```

---

## Monitoring & Observability

### Key Metrics

- **Request Rate**: Requests per second per endpoint
- **Error Rate**: Failed requests (HTTP 4xx, 5xx)
- **P50/P95/P99 Latency**: Response time percentiles
- **Database Connection Pool**: Active/Max connections
- **Cache Hit Ratio**: Cache hits vs misses
- **Queue Depth**: Pending background jobs
- **Concurrent Users**: Active WebSocket connections

### Health Checks

```
Endpoint: GET /health
Response: {
  status: "healthy" | "degraded" | "unhealthy",
  timestamp: ISO8601,
  checks: {
    database: { status, latency_ms },
    cache: { status, latency_ms, memory_mb },
    queue: { status, pending_jobs },
    api: { status, request_count, error_rate }
  }
}
```

---

## Next Steps

1. Review deployment configurations in `DEPLOYMENT.md`
2. Check fault tolerance specifics in `FAULT-TOLERANCE.md`
3. See concurrent access patterns in `CONCURRENCY.md`
4. Review flowcharts in `FLOW-DIAGRAMS.md`
