# Admin Documentation Index

## 📚 Complete Enterprise Architecture Documentation

This directory contains comprehensive documentation for the Ledger App enterprise deployment, including C1/C2/C3 architecture diagrams, system flow diagrams, monitoring procedures, and operational guides.

---

## 📋 Documentation Files

### 1. **ARCHITECTURE.md** - System Design & Architecture
   - **C1 Context Diagram**: High-level system overview with external actors and integrations
   - **C2 Container Diagram**: Technology stack and major component boundaries
   - **C3 Component Diagram**: Detailed backend system components and their interactions
   - **System Deployment**: Production high-availability architecture
   - **Scalability Strategy**: Horizontal & vertical scaling approaches
   - **Monitoring & Observability**: Key metrics and health check endpoints

   **When to use**: Understanding system architecture, deployment design, component interactions

### 2. **FLOW-DIAGRAMS.md** - System Workflows & Flowcharts
   - **Multi-User Request Handling**: Concurrent request processing flow
   - **Transaction Processing**: Detailed transaction creation/update flowchart
   - **Fault Recovery**: Error handling and auto-recovery flows
   - **Concurrent Access**: Pessimistic vs Optimistic locking patterns
   - **Database Replication**: Write-through and read distribution flows
   - **Session Management**: JWT token lifecycle and authentication flows
   - **Goal Progress Calculation**: Real-time goal tracking logic
   - **Background Job Processing**: Async task queue and worker execution
   - **Load Balancing**: Health check and auto-failover procedures
   - **Data Consistency**: Last-Write-Wins concurrency pattern

   **When to use**: Understanding how specific processes work, debugging flow issues, designing new features

### 3. **OPERATIONS-GUIDE.md** - Monitoring, Incidents & Capacity
   - **Health Monitoring**: System health dashboard and health check endpoints
   - **Performance Metrics**: Real-time metrics collection, Prometheus queries
   - **Incident Response**: Severity levels, playbooks, root cause analysis
   - **Scaling Procedures**: Horizontal API scaling, database scaling, cache layer scaling
   - **Capacity Planning**: 6-month growth projections, resource allocation, cost analysis
   - **SLA Targets**: Availability, response time, error rate goals

   **When to use**: Monitoring systems, responding to incidents, planning capacity growth, tracking performance

### 4. **DEPLOYMENT.md** - Enterprise Setup & Configuration
   - **Quick Start**: Prerequisites and environment setup
   - **Environment Configuration**: Complete .env.enterprise template
   - **Docker Compose Stack**: Full enterprise deployment with multiple services
   - **Nginx Configuration**: Load balancer setup with rate limiting
   - **Prometheus Configuration**: Monitoring setup
   - **Startup Commands**: Commands to run development cluster and K8s production deployment

   **When to use**: Setting up environments, deploying to new infrastructure, configuring services

### 5. **COMPLIANCE-BASELINE.md** - PCI DSS, SOX, HIPAA Readiness
   - **Control Matrix**: Mapped readiness across PCI DSS, SOX, and HIPAA domains
   - **Implemented Controls**: Security headers, CORS hardening, request-size limits, password policy, registration throttling
   - **Evidence Pack**: Required artifacts for assessor reviews and internal audits
   - **Gap Register**: Remaining controls and implementation priorities

   **When to use**: Audit preparation, compliance planning, control ownership and remediation tracking

---

## 🏗️ Architecture Overview

### System Context (C1)
```
End Users / Admins
        ↓
    Web Browser (SPA)
        ↓
    FastAPI Backend (Multi-instance, load-balanced)
        ↓ (Read/Write)
    Database (MySQL Primary + Replicas)
    
    + Redis Cache Layer
    + Celery Background Workers
    + External Integrations (Gmail, PhonePe, Groww, etc.)
```

### Major Components (C2)
```
API Gateway (Nginx Load Balancer)
    ├─ API Server 1 (FastAPI)
    ├─ API Server 2 (FastAPI)
    └─ API Server N (FastAPI)
         ↓
    Service Layer (Business Logic)
         ↓
    ├─ MySQL Primary (Write)
    ├─ MySQL Replica 1 (Read)
    ├─ MySQL Replica 2 (Read)
    ├─ Redis Cluster (Cache & Sessions)
    └─ Celery Workers (Background Tasks)
```

### Failure Modes & Recovery
```
Circuit Breaker Pattern:
  CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing) → CLOSED

Retry Logic:
  Attempt 1 → Wait 2s → Attempt 2 → Wait 4s → Attempt 3 → Wait 8s → Fail

Concurrent Access:
  Lock Acquisition → Business Logic → Lock Release
  If lock held: Exponential backoff + retry

Database Failover:
  Primary Down → Use Replica for reads → Alert ops → Manual promotion
```

---

## 🚀 Quick Reference

### Health Check
```bash
curl http://localhost/health/detailed
```

### Key Metrics to Monitor
| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | >1% | Page on-call engineer |
| P95 Latency | >500ms | Scale API servers |
| DB Replication Lag | >5s | Redirect reads to primary |
| Cache Hit Rate | <85% | Increase cache memory |
| Queue Depth | >1000 | Add more workers |

### Common Incidents & Resolution

#### Database Connection Pool Exhaustion
See: **OPERATIONS-GUIDE.md** → Incident Response → Database Connection Pool Exhaustion

#### Redis Cache Failure
See: **OPERATIONS-GUIDE.md** → Incident Response → Redis Cache Failure

#### High Database Replication Lag
See: **OPERATIONS-GUIDE.md** → Incident Response → High Database Replication Lag

---

## 🔄 Request Processing Pipeline

```
1. Request arrives at Nginx (load balancer)
   ↓
2. Route to available FastAPI instance
   ↓
3. API Gateway:
   - Validate request
   - Extract JWT token
   - Check rate limits
   - Add request ID
   ↓
4. Middleware:
   - Authenticate user
   - Check RBAC permissions
   - Log request start
   ↓
5. Service Layer:
   - Validate business rules
   - Acquire distributed lock (if needed)
   ↓
6. Data Access:
   - Query cache (Redis)
   - Query database (MySQL)
   - Check replicas for read-heavy queries
   ↓
7. Response:
   - Build response object
   - Update cache
   - Release lock
   - Log request end
   ↓
8. Client receives response (JSON)
```

---

## 🔐 Concurrency Handling

### Optimistic Locking (Default)
- Used for: Goals, Investments, Budgets
- Mechanism: Version tags on each update
- Conflict: Return HTTP 409, client retries with fresh data
- Best for: Low conflict scenarios, high read/write ratio

### Pessimistic Locking (High Contention)
- Used for: Critical financial operations
- Mechanism: Distributed locks via Redis
- Timeout: 30 seconds with exponential backoff
- Best for: High conflict scenarios, critical updates

---

## 📊 Monitoring Dashboard

**URL**: http://localhost:9090 (Prometheus)

**Key Panels**:
1. Request Rate (req/s)
2. Error Rate (%)
3. P95 Latency (ms)
4. Database Connections (active/max)
5. Cache Hit Ratio (%)
6. Queue Depth (jobs)
7. Memory Usage (%)

---

## 🔧 Configuration Management

### Environment Variables by Deployment Type

**Development** (`.env`):
- Single database, no replication
- Redis on localhost
- 1-2 API instances
- Simplified logging (INFO level)

**Staging** (`.env.staging`):
- Replicated database setup
- Redis cluster (basic)
- 2-3 API instances
- Advanced logging

**Enterprise/Production** (`.env.enterprise`):
- Primary + 2+ read replicas
- Redis Sentinel with failover
- 3+ API instances (auto-scaling up to 10)
- Full monitoring & alerting

---

## 📈 Scaling Timeline

| Stage | Users | Transactions/day | Peak RPS | API Instances | DB Replicas | Action |
|-------|-------|-----------------|----------|---------------|-----------.|---------|
| Current | 1,000 | 50,000 | 1,240 | 3 | 2 | Monitor |
| 3 months | 1,400 | 75,000 | 2,000 | 5 | 2 | Scale up API |
| 6 months | 1,960 | 112,500 | 3,200 | 8 | 3 | Add replica |
| 12 months | 3,840 | 225,000 | 6,400 | 16 | 4 | Consider sharding |

---

## ✅ Pre-Deployment Checklist

- [ ] Environment variables configured (`.env.enterprise`)
- [ ] Database credentials rotated and secured
- [ ] Redis Sentinel configured with 3 nodes
- [ ] SSL/TLS certificates provisioned
- [ ] Monitoring (Prometheus) configured
- [ ] Backup & recovery procedures tested
- [ ] Load balancer health checks verified
- [ ] Auto-scaling policies set
- [ ] Incident response team trained
- [ ] Runbooks documented and validated

---

## 🚨 Emergency Contacts & Escalation

**On-Call Rotation**:
- L1 (First Response): Platform team
- L2 (Escalation): Engineering Lead
- L3 (Critical): CTO

**Page On-Call When**:
- Service completely down (P1)
- Error rate >50% (P1)
- Database primary fails (P1)
- Cache layer completely down (P1)

---

## 📚 Additional Resources

### Running Tests
```bash
# Integration tests
cd backend && pytest tests/integration/ -v

# Load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Health check tests
./scripts/health-check.sh
```

### Common Commands
```bash
# View logs
docker-compose -f docker-compose.enterprise.yml logs -f [service-name]

# Scale API servers
docker-compose -f docker-compose.enterprise.yml up -d --scale api-server-1=5

# Database backup
mysqldump -u ledger_user -p ledger_db > backup-$(date +%Y%m%d).sql

# Check MySQL replication
mysql -h replica1 -u root -p -e "SHOW SLAVE STATUS\G"

# Monitor Redis
redis-cli -h redis-primary INFO stats
```

---

## 📞 Support

For questions or issues:
1. Check relevant documentation file above
2. Search incident playbooks in **OPERATIONS-GUIDE.md**
3. Review flowcharts in **FLOW-DIAGRAMS.md**
4. Consult deployment guides in **DEPLOYMENT.md**
5. Contact platform engineering team

---

## 📝 Change Summary (March 2026)

- Feature/Module: Frontend navigation consistency for dashboard tiles and left quick access
- Change Type: Fix
- Description: Replaced the top quick-tab strip with a grouped left-side quick access panel, added a collapse toggle with persisted state, introduced an icon-only collapsed rail, moved editable section content into the adjacent right column so it no longer drops below the sidebar, and removed the redundant Navigate menu.
- Reason: Users wanted persistent quick access on the left instead of a dense horizontal shortcut row.
- Impact: Improved navigation discoverability and scanning; primary sections and dashboard shortcuts are now grouped in a dedicated left-side access panel that can collapse into an icon rail while the editing area stays adjacent on the right with no duplicate dropdown menu.
- Dependencies: Frontend-only change in app.html using existing handlers (handleOverviewTileClick and showForecastSummaryPopup).

---

**Last Updated**: March 27, 2026  
**Version**: 2.3.1  
**Maintained By**: Platform Engineering Team
