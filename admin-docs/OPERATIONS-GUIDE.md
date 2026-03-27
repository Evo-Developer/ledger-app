# Enterprise Operations & Monitoring Guide

## Table of Contents
1. [Health Monitoring](#health-monitoring)
2. [Performance Metrics](#performance-metrics)
3. [Incident Response](#incident-response)
4. [Scaling Procedures](#scaling-procedures)
5. [Capacity Planning](#capacity-planning)

---

## Health Monitoring

### System Health Dashboard

```
┌────────────────────────────────────────────────────────────┐
│                   SYSTEM HEALTH                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  API Services          Database              Cache        │
│  ✓ 3/3 Healthy        ✓ Primary OK          ✓ Active    │
│  Load: 45%            Replication: 0.8s      Memory: 60% │
│                                                            │
│  Request Rate: 1,240 req/s                 Queue Jobs: 45│
│  Error Rate: <0.1%                         Workers: 6    │
│  Avg Latency: 142ms (P95: 450ms)          Pending: 12   │
│                                                            │
│  Last Incident: 3 days ago (2min downtime)               │
│  Uptime: 99.96% (30-day SLA: 99.9%)                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Health Check Endpoint

```
GET /health/detailed

Response (200 OK):
{
  "status": "healthy",
  "timestamp": "2026-03-23T15:45:30Z",
  "uptime_seconds": 86400,
  "version": "2.1.0",
  "environment": "production",
  "checks": {
    "database": {
      "status": "ok",
      "latency_ms": 5,
      "connections_active": 18,
      "connections_max": 20,
      "replication_lag_ms": 840
    },
    "cache": {
      "status": "ok",
      "latency_ms": 2,
      "memory_bytes_used": 629145600,
      "memory_bytes_max": 1073741824,
      "hit_rate_percent": 87.3,
      "eviction_rate_percent": 0.1
    },
    "queue": {
      "status": "ok",
      "pending_jobs": 12,
      "max_queue_depth": 1000,
      "workers_active": 6,
      "processing_rate_per_sec": 2.3
    },
    "api": {
      "status": "ok",
      "request_rate_per_sec": 1240,
      "error_rate_percent": 0.05,
      "p50_latency_ms": 85,
      "p95_latency_ms": 450,
      "p99_latency_ms": 2100
    },
    "external_services": {
      "gmail": {
        "status": "ok",
        "latency_ms": 320,
        "last_sync": "2026-03-23T15:40:00Z"
      }
    }
  }
}
```

---

## Performance Metrics

### Real-Time Metrics Collection

```
┌─────────────────────────────────────────────────────┐
│           Prometheus Metrics Scrape                │
│        (Every 15 seconds from /metrics)             │
└─────────────────────────────────────────────────────┘

Custom Metrics:

ledger_app_request_total{endpoint, method, status}
  ├─ /transactions POST 201: 1,245,320
  ├─ /goals GET 200: 3,201,045
  ├─ /goals PUT 200: 541,230
  └─ /investments POST 500: 342

ledger_app_request_duration_seconds{endpoint, quantile}
  ├─ /transactions (p50): 0.085s
  ├─ /transactions (p95): 0.450s
  └─ /transactions (p99): 2.100s

ledger_app_db_query_duration_seconds{query_type}
  ├─ SELECT: 0.015s
  ├─ INSERT: 0.025s
  ├─ UPDATE: 0.035s
  └─ DELETE: 0.020s

ledger_app_cache_hits_total: 12,345,678
ledger_app_cache_misses_total: 1,567,890
  → Hit ratio: 88.7%

ledger_app_concurrent_requests: 245
ledger_app_active_connections_db: 18
ledger_app_active_workers: 6
ledger_app_queue_depth: 12

ledger_app_lock_wait_time_seconds{resource}
  ├─ goal_123: 0.045s
  ├─ investment_456: 0.012s
  └─ user_789: 0.003s
```

### Dashboard Queries (Grafana)

```
1. Request Rate (req/s):
   rate(ledger_app_request_total[5m])

2. Error Rate (%):
   rate(ledger_app_request_total{status=~"5..|4.."}[5m]) /
   rate(ledger_app_request_total[5m]) * 100

3. P95 Latency (ms):
   histogram_quantile(0.95,
     rate(ledger_app_request_duration_seconds_bucket[5m])) * 1000

4. Database Connection Pool Usage (%):
   (ledger_app_active_connections_db / 20) * 100

5. Cache Hit Ratio:
   ledger_app_cache_hits_total / 
   (ledger_app_cache_hits_total + ledger_app_cache_misses_total) * 100

6. Queue Depth:
   ledger_app_queue_depth

7. Memory Usage (%):
   (process_resident_memory_bytes / 1073741824) * 100
```

---

## Incident Response

### Incident Severity Levels

#### P1 (Critical) - Immediate Impact
- **Indicators**: Service completely down, error rate >50%, all endpoints timing out
- **Response Time**: On-call engineer paged immediately
- **Actions**:
  1. Page on-call dev + ops
  2. Declare incident
  3. Start incident channel
  4. Begin diagnostics
  5. Communicate status to users
- **Escalation**: CTO after 15 minutes if not resolved

#### P2 (High) - Severe Degradation
- **Indicators**: Error rate 10-50%, specific endpoint down, >500ms latency
- **Response Time**: Engineer responds within 15 minutes
- **Actions**:
  1. Create incident ticket
  2. Diagnose root cause
  3. Attempt auto-recovery
  4. Consider manual failover
  5. Update status page
- **Escalation**: Engineering manager if >30 min

#### P3 (Medium) - Partial Impact
- **Indicators**: Error rate 1-10%, intermittent issues, <20% user impact
- **Response Time**: Engineer responds within 1 hour
- **Actions**:
  1. Log incident
  2. Investigate during business hours
  3. Implement permanent fix for next release
  4. Monitor and adjust alerting

#### P4 (Low) - Minor Issues
- **Indicators**: Error rate <1%, no user-facing impact, dashboard only
- **Response Time**: Next business day
- **Actions**:
  1. Add to backlog
  2. Schedule for next sprint
  3. Monitor trends

### Incident Response Playbook

#### Database Connection Pool Exhaustion

```
SYMPTOM:
  - Error: "QueuePool timeout"
  - Latency spike: 15,000ms+
  - Error rate jumps to >30%

ROOT CAUSE POSSIBILITIES:
  1. Runaway queries (long-running transaction)
  2. Connection leak (not returned to pool)
  3. Load spike (legitimate high traffic)
  4. Deadlock (two transactions waiting on each other)

INVESTIGATION:
  1. Check metrics:
     SELECT COUNT(*) FROM INFORMATION_SCHEMA.PROCESSLIST;
     ├─ Normal: 15-18 connections
     └─ Issue: 20+ connections, many sleeping

  2. Identify slow queries:
     SELECT * FROM INFORMATION_SCHEMA.SLOW_LOG
     WHERE start_time > NOW() - INTERVAL 5 MINUTE
     ORDER BY query_time DESC;

  3. Check for locks:
     SHOW FULL PROCESSLIST;
     Look for state: "waiting for table metadata lock"

RECOVERY STEPS:

Immediate (0-5 min):
  1. Scale API servers:
     kubectl scale deployment api-server --replicas=5
  2. Increase DB connections temporarily:
     mysql> SET GLOBAL max_connections = 200;
  3. Monitor recovery within 2 minutes

Short-term (5-15 min):
  1. Query suspect connections:
     SHOW PROCESSLIST;
  2. Kill long-running non-critical queries:
     KILL QUERY 12345;
  3. Check for connection leaks in code
  4. Review recent deployments

Long-term (>15 min):
  1. Database connection pool tuning
  2. Query optimization
  3. Caching strategy review
  4. Capacity planning

POSTMORTEM:
  - Root cause: (query, traffic, other)
  - Duration: X minutes
  - Impact: N users affected
  - Prevention: (monitoring, alerting, code changes)
```

#### Redis Cache Failure

```
SYMPTOM:
  - Error: "Connection refused" to Redis
  - Latency spike: 5,000-15,000ms
  - Database queries spike 10x

RECOVERY STEPS:

Check Redis status:
  redis-cli ping
  → If no response, Redis is down

Immediate actions:
  1. Check disk space:
     df -h /var/lib/redis
     └─ If full, delete old logs/backups

  2. Check Redis process:
     ps aux | grep redis-server
     └─ If not running: systemctl start redis-server

  3. Check Redis logs:
     tail -50 /var/log/redis/redis-server.log

  4. Restart if safe:
     systemctl restart redis-server

  5. Monitor memory:
     redis-cli INFO memory
     ├─ used_memory_mb should be < 700MB
     └─ If high: Check for memory leaks

FALLBACK:
  When Redis is down:
  ├─ API should work with degraded performance
  ├─ All queries go to DB (slower)
  └─ Session store to fallback (file-based)

Restore Service:
  1. Once Redis up: Clear old cache
     redis-cli FLUSHDB
  2. Warm cache from DB
     /scripts/warm-cache.py
  3. Monitor for 10 minutes
```

#### High Database Replication Lag

```
SYMPTOM:
  - Replication lag > 5 seconds
  - Read queries returning stale data
  - Alerts: "Replication lag critical"

CAUSES:
  1. Heavy writes on primary (DDL/DML)
  2. Network issues between primary & replica
  3. Replica under-resourced (CPU/IO)
  4. Oversized transactions

CHECK LAG:
  SHOW SLAVE STATUS;
  → Seconds_Behind_Master > 5

RECOVER:

Immediate:
  1. Redirect read traffic to primary:
     ├─ Update connection string
     └─ Route all reads temporarily
  
  2. Check replica IO thread:
     SHOW SLAVE STATUS\G | grep "Slave_IO_Running:"
     └─ If "No": reconnect replica

Investigate:
  1. Check master binlog:
     SHOW MASTER STATUS;
  
  2. Check replica processing:
     SHOW SLAVE STATUS\G | grep "Slave_SQL_Running_State:"
  
  3. Monitor replica:
     vmstat 1 10
     iostat 1 10
     ├─ Look for CPU/IO saturation
     └─ Consider upgrading replica instance

Optimize:
  1. Parallel replication (MySQL 8.0+):
     SET GLOBAL slave_parallel_workers=4;
  
  2. Reduce binlog size:
     SET GLOBAL binlog_cache_size=32768;

Monitor:
  - Alarm when lag > 5 seconds
  - Alert when lag > 30 seconds
  - Dashboard graph for last 24 hours
```

---

## Scaling Procedures

### Horizontal API Scaling (Add More Servers)

```
TRIGGER: CPU > 70% OR Memory > 80% for 10 minutes

PROCEDURE:

1. Pre-flight check (1 minute):
   ├─ Check database connection pool available
   ├─ Check cache layer responsive
   └─ Verify load balancer ready

2. Add new instance (2-3 minutes):
   ├─ Create new EC2/Docker container
   ├─ Pull latest image (if applicable)
   ├─ Start with limited traffic first
   └─ Run health checks

3. Warm up (2 minutes):
   ├─ Prime connections to DB
   ├─ Load cache layer
   ├─ Connect to message queue
   └─ Verify responsive (<500ms health check)

4. Route traffic (1 minute):
   ├─ Add to load balancer pool
   ├─ Start receiving 5% of traffic
   ├─ Monitor for errors
   └─ Gradually increase: 5% → 20% → 50% → 100%

5. Stabilize (5 minutes):
   ├─ Monitor latency (should drop)
   ├─ Check error rate (should stay <0.1%)
   ├─ Verify CPU usage (should drop to <50% per instance)
   └─ Confirm all instances in "healthy" state

ROLLBACK (if needed):
  1. Remove new instance from load balancer
  2. Drain connections (wait 30 seconds)
  3. Terminate instance
  4. Investigate issue
  5. Fix and redeploy

AUTOSCALING CONFIG:
  Min instances: 2
  Max instances: 10
  Target CPU: 60%
  Target Memory: 70%
  Scale-up cooldown: 2 minutes
  Scale-down cooldown: 10 minutes
```

### Database Scaling (Add Replica)

```
TRIGGER: 
  - Replication lag > 5 seconds consistently
  - Read latency >500ms
  - Replica CPU >85%

PROCEDURE:

1. Prepare new replica (5 minutes):
   ├─ Provision new machine (same specs as current replicas)
   ├─ Install MySQL 8.0
   ├─ Configure as replica
   └─ Set up monitoring

2. Initial sync (10-30 minutes):
   ├─ Take backup of primary (BACKUP WITH LOCK)
   ├─ Restore to new replica
   ├─ Position to correct binlog offset
   ├─ Start replication
   └─ Monitor for lag

3. Verify (5 minutes):
   ├─ Check replication running
   ├─ Verify no errors:
        SHOW SLAVE STATUS\G
   ├─ Compare data integrity
   └─ Monitor lag (should be <1 second)

4. Route read traffic (gradual):
   ├─ Add to read pool: 10%
   ├─ Monitor for 2 minutes
   ├─ Increase: 10% → 25% → 50% → 100%
   └─ Final distribution: balanced across all replicas

MONITORING:
  - Lag should be <2 seconds after warm-up
  - CPU should drop on existing replicas
  - Read latency should improve
```

### Cache Layer Scaling

```
TRIGGER:
  - Cache hit rate drops below 85%
  - Memory usage >85%
  - Eviction rate increases

PROCEDURE:

1. Increase memory per Redis node:
   ├─ Current: 4GB
   ├─ Target: 8GB (horizontal) or 16GB (vertical)
   └─ Impact: Fewer evictions, better hit rate

2. Add more Redis nodes:
   ├─ Cluster mode: Add node to cluster
   ├─ Rebalance slots among nodes
   ├─ Reshard data (progressive, no downtime)
   └─ Monitor: Hash slot coverage 100%

3. Adjust TTL strategy if needed:
   ├─ Sessions: 24h (keep longer)
   ├─ Query results: 5-10m (shorter if memory pressure)
   ├─ Priority: Keep user data, evict aggregates first

IMPLEMENTATION:
  Redis Cluster setup:
  ├─ 3 master nodes (4GB each)
  ├─ 3 replica nodes (standby)
  ├─ Total: 12GB active cache
  └─ Hashslot: 16384 slots distributed
```

---

## Capacity Planning

### 6-Month Growth Projection

```
Current Metrics (March 2026):
  ├─ Users: 1,000 active, 5,000 total
  ├─ Transactions/day: 50,000
  ├─ Peak RPS: 1,240 req/s
  ├─ Storage: 50GB
  └─ API instances: 3

Growth Assumptions:
  ├─ User growth: 40% QoQ
  ├─ Transaction volume: +50% QoQ
  ├─ Peak traffic: +60% QoQ
  └─ Data growth: +35% QoQ


3-MONTH PROJECTION (June 2026):
  ├─ Users: ~1,400 active, 7,000 total
  ├─ Transactions/day: 75,000
  ├─ Peak RPS: 2,000 req/s → Need 5 API instances
  ├─ Storage: 67GB
  ├─ DB connections: 25 (increase pool to 30)
  ├─ Cache memory: 6GB (upgrade to 8GB)
  └─ Action: Add 2 API instances, upgrade cache


6-MONTH PROJECTION (September 2026):
  ├─ Users: ~1,960 active, 9,800 total
  ├─ Transactions/day: 112,500
  ├─ Peak RPS: 3,200 req/s → Need 8 API instances
  ├─ Storage: 90GB (approaching DB limits)
  ├─ DB read replica lag: Monitor closely
  ├─ Cache: 10GB needed (add Redis node)
  ├─ Action: Add 3 more API instances
  │         Add read replica #3
  │         Partition data if >100GB
  └─ Consider multi-zone deployment


12-MONTH PROJECTION (March 2027):
  ├─ Users: 3,840 active, 19,200 total
  ├─ Transactions/day: 225,000
  ├─ Peak RPS: 6,400 req/s → 16 API instances
  ├─ Storage: 135GB (plan for sharding)
  ├─ Database: Consider read/write split + sharding
  ├─ Cache: 12GB (Redis cluster with 3 master nodes)
  ├─ Action: Multi-region deployment
  │         Database sharding by user_id or date
  │         CDN for static assets
  │         Consider managed database service
  └─ Engineering: Distributed tracing, advanced monitoring
```

### Resource Allocation Table

| Component | Current | 3-Month | 6-Month | 12-Month |
|-----------|---------|---------|---------|----------|
| **API Instances** | 3 | 5 | 8 | 16 |
| **Database Primary** | 8GB RAM, 100GB SSD | Same | Same | 16GB RAM, 200GB SSD |
| **Read Replicas** | 2 | 2 | 3 | 4 |
| **Redis Memory** | 4GB | 8GB | 10GB | 12GB |
| **Storage Total** | 50GB | 67GB | 90GB | 135GB |
| **Max Concurrent** | 500 users | 700 | 1000 | 2000 |
| **Peak RPS** | 1,240 | 2,000 | 3,200 | 6,400 |

### Cost Projections

```
Infrastructure costs (AWS/GCP):

3-Month Budget:
  ├─ Compute (5 API servers @ $0.20/hr): $7,200/month
  ├─ Database (2 replicas): $3,600/month
  ├─ Cache (Redis managed): $1,200/month
  ├─ Storage (90GB): $2,700/month
  └─ Monitoring & misc: $1,500/month
  
  Total: ~$16,200/month

6-Month Budget:
  ├─ Compute (8 API servers): $11,500/month
  ├─ Database (3 replicas): $5,400/month
  ├─ Cache (upgrade): $2,400/month
  ├─ Storage (120GB): $3,600/month
  └─ Monitoring & misc: $2,100/month
  
  Total: ~$25,000/month

12-Month Budget:
  ├─ Compute (16 API servers): $23,000/month
  ├─ Database (4 replicas, sharded): $9,600/month
  ├─ Cache (cluster): $4,800/month
  ├─ Storage (180GB): $5,400/month
  ├─ CDN & security: $3,200/month
  └─ Monitoring & misc: $4,000/month
  
  Total: ~$50,000/month
```

### SLA Targets

```
Service Level Agreement:

Availability:
  - Target: 99.9% (43 minutes downtime/month)
  - Measured: Monthly uptime excluding planned maintenance
  - Calculation: (Uptime / Total Time) × 100

Response Time:
  - P50 (median): <200ms
  - P95: <500ms
  - P99: <2000ms

Error Rate:
  - Target: <0.1% (1 error per 1000 requests)
  - Measured: (Failed requests / Total requests) × 100

Data Durability:
  - RPO (Recovery Point Objective): <1 minute
  - RTO (Recovery Time Objective): <5 minutes

Credits:
  - 99.5-99.9% uptime: 10% credit
  - 99.0-99.5% uptime: 25% credit
  - <99.0% uptime: 50% credit
  - Maximum: 30% of monthly bill
```

