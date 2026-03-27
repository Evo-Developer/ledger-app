# Enterprise-Grade Concurrency & Fault Tolerance

This document describes the enterprise-standard features implemented for handling multi-threading, concurrent connections, and fault tolerance in the Ledger Finance Application.

## Overview

The ledger app has been upgraded with production-ready enterprise features:

- **Multi-threading & Connection Pooling**: Optimized database connection management
- **Rate Limiting**: Per-user and per-endpoint request throttling
- **Circuit Breaker Pattern**: Graceful degradation and automatic recovery
- **Request Retry Logic**: Exponential backoff with jitter
- **Health Monitoring**: Comprehensive health checks and metrics
- **Deadlock Detection**: Automatic detection of stalled operations
- **User Session Management**: Concurrent access control per user
- **Load Balancer Support**: Health check endpoints for automatic failover

## Architecture

### Backend Components

#### 1. **Concurrency Module** (`backend/concurrency.py`)

Provides core concurrency management:

```python
# Connection Pool: Advanced SQLAlchemy connection pooling
connection_pool = ConnectionPool(
    max_pool_size=20,      # Minimum connections to maintain
    max_overflow=10,       # Additional connections for spikes
    pool_recycle=3600,     # Recycle connections after 1 hour
    pool_pre_ping=True     # Health check before use
)

# Circuit Breaker: Prevents cascading failures
circuit_breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60       # Attempt recovery after 60s
)

# Retry Policy: Exponential backoff with jitter
retry_policy = RetryPolicy(
    max_retries=3,
    base_delay=1.0,           # Start at 1 second
    max_delay=60.0,           # Cap at 60 seconds
    jitter=True               # Add randomness
)

# Request Budget: Token bucket rate limiting
request_budget = RequestBudget(
    capacity=1000,            # Max tokens per user
    refill_rate=50.0          # 50 tokens/second
)

# Session Manager: User isolation and access control
session_manager = UserSessionManager()

# Deadlock Detector: Monitor long-running operations
deadlock_detector = DeadlockDetector(timeout=30.0)
```

#### 2. **Middleware Stack** (`backend/middleware.py`)

HTTP middleware for request handling (processed in order):

1. **RequestTrackingMiddleware**: Tracks concurrent requests and metrics
   - Assigns unique request ID
   - Records active request count
   - Measures response times

2. **RateLimitMiddleware**: Enforces rate limits
   - Token bucket per user
   - Configurable limits per endpoint
   - Returns 429 Too Many Requests when exceeded

3. **TimeoutMiddleware**: Prevents hanging requests
   - File uploads: 60 seconds
   - File exports: 30 seconds
   - Bulk operations: 45 seconds
   - Default: 30 seconds

4. **CircuitBreakerMiddleware**: Graceful degradation
   - Opens after failure threshold
   - Returns 503 Service Unavailable
   - Attempts recovery after timeout

5. **UserIsolationMiddleware**: Security and isolation
   - Extracts user context
   - Prevents data leakage
   - Sanitizes responses

#### 3. **Health Monitoring** (`backend/health_monitoring.py`)

Comprehensive health checks:

```python
health_checker.get_health_status()
# Returns: {
#     "status": "healthy|degraded|unhealthy",
#     "checks": {
#         "database": {...},
#         "memory": {...},
#         "disk": {...},
#         "cpu": {...},
#         "uptime": {...}
#     },
#     "issues": [...]
# }
```

Thresholds:
- **Memory**: >75% warning, >90% critical
- **Disk**: >75% warning, >90% critical
- **CPU**: >75% warning, >90% critical
- **Database**: Connection failure = unhealthy

#### 4. **Metrics Collection** (`backend/health_monitoring.py`)

Tracks performance metrics:

```python
metrics_collector.record_metric("api_latency_ms", 125.5)
metrics_collector.get_metric_stats("api_latency_ms")
# Returns: {
#     "count": 1542,
#     "min": 5.2,
#     "max": 1250.8,
#     "avg": 45.7,
#     "latest": 125.5
# }
```

### Frontend Component

#### **EnterpriseAPIClient** (`frontend/enterprise-client.js`)

JavaScript client for resilient API communication:

```javascript
// Usage in app.html
const result = await enterpriseClient.call(
    api.getTransactions,
    [filters],
    {
        timeout: 30000,
        deduplicationKey: 'transactions_' + JSON.stringify(filters),
        onSuccess: (result, latency) => {
            console.log(`Success in ${latency}ms`);
        },
        onError: (error) => {
            showNotification(error.userMessage, 'error');
        }
    }
);

// Queue requests to prevent overload
enterpriseClient.queueCall(
    api.bulkImport,
    [data],
    'bulk_operations'
);

// Get metrics
console.log(enterpriseClient.getMetrics());
// {
//     "totalRequests": 1542,
//     "successfulRequests": 1540,
//     "failedRequests": 2,
//     "averageLatency": 45.2,
//     "successRate": "99.9%"
// }
```

Features:
- **Exponential Backoff**: Retry with increasing delays
- **Circuit Breaker**: Client-side failover
- **Timeout Protection**: Prevent hanging requests
- **Request Deduplication**: Reduce duplicate API calls
- **Queue Management**: Controlled request flow
- **Error Classification**: Categorize and handle errors

## Enterprise Endpoints

### Health & Monitoring (Protected by admin/superadmin roles)

#### `GET /health`
Basic health check for load balancers.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2026-03-23T10:30:45",
    "database": "healthy",
    "memory_ok": true,
    "disk_ok": true
}
```

#### `GET /health/detailed`
Detailed health with all subsystems.

**Response:**
```json
{
    "timestamp": "2026-03-23T10:30:45",
    "status": "healthy",
    "checks": {
        "database": {"status": "healthy", "message": "..."},
        "memory": {"status": "healthy", "percent_used": 62.5, ...},
        "disk": {"status": "healthy", "percent_used": 45.2, ...},
        "cpu": {"status": "healthy", "percent": 12.3, ...},
        "uptime": {"uptime_seconds": 86400, ...}
    },
    "issues": []
}
```

#### `GET /api/enterprise/concurrency-status`
Real-time concurrency and load metrics.

**Response:**
```json
{
    "timestamp": "2026-03-23T10:30:45",
    "concurrent_requests": {
        "current": 42,
        "peak": 156
    },
    "active_users": 8,
    "user_request_distribution": {
        "user_123": 5,
        "user_456": 3,
        "user_789": 2
    },
    "stalled_operations": 0,
    "circuit_breaker_state": "CLOSED"
}
```

#### `GET /api/enterprise/performance-metrics`
Detailed performance statistics.

**Response:**
```json
{
    "timestamp": "2026-03-23T10:30:45",
    "request_latency_metrics": {
        "p50": 45.2,
        "p95": 125.8,
        "p99": 250.3,
        "avg": 52.1,
        "min": 2.1,
        "max": 1250.0
    },
    "all_metrics": {...},
    "health_status": {...}
}
```

#### `POST /api/enterprise/circuit-breaker/reset`
Manually reset circuit breaker (superadmin only).

**Response:**
```json
{
    "message": "Circuit breaker reset successfully",
    "previous_state": "OPEN",
    "current_state": "CLOSED"
}
```

#### `GET /api/enterprise/session-stats`
Active session statistics.

**Response:**
```json
{
    "timestamp": "2026-03-23T10:30:45",
    "total_sessions": 12,
    "active_users": {"user_123": 2, "user_456": 1},
    "max_age_seconds": 86400
}
```

#### `POST /api/enterprise/deadlock-detection-enabled`
Check for stalled operations.

**Response:**
```json
{
    "timestamp": "2026-03-23T10:30:45",
    "stalled_operations_count": 0,
    "stalled_operations": [],
    "needs_investigation": false,
    "auto_recovery_timeout_seconds": 30
}
```

## Deployment Configuration

### Environment Variables

```bash
# Database connection (uses enterprise pooling)
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db

# Rate limiting (tokens per second per user)
RATE_LIMIT_CAPACITY=1000
RATE_LIMIT_REFILL_RATE=50

# Connection pool sizes
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600

# Timeouts (milliseconds)
REQUEST_TIMEOUT=30000
FILE_UPLOAD_TIMEOUT=60000
```

### Load Balancer Configuration

Use the `/health` endpoint for health checks:

**Nginx Example:**
```nginx
upstream ledger_backend {
    least_conn;
    server ledger1.example.com:8000 max_fails=3 fail_timeout=30s;
    server ledger2.example.com:8000 max_fails=3 fail_timeout=30s;
    server ledger3.example.com:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    
    location /health {
        access_log off;
        proxy_pass http://ledger_backend;
        proxy_connect_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    location / {
        proxy_pass http://ledger_backend;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Kubernetes Example:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ledger-api
spec:
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: ledger
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ledger-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ledger
  template:
    metadata:
      labels:
        app: ledger
    spec:
      containers:
      - name: ledger
        image: ledger:v1.0
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
```

## Monitoring & Alerting

### Prometheus Metrics

Scrape `/metrics` endpoint (Prometheus-compatible format):

```bash
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `ledger_active_requests`: Current active requests
- `ledger_total_requests`: Total requests since start
- `ledger_latency_ms`: Request latency
- `ledger_memory_mb`: Memory usage
- `ledger_circuit_breaker_state`: Circuit breaker status

### Alert Rules

Create alerts for:

```yaml
# Circuit breaker opened
- alert: CircuitBreakerOpen
  expr: ledger_circuit_breaker_state == 2
  for: 5m
  annotations:
    summary: "Circuit breaker is open"

# High memory usage
- alert: HighMemoryUsage
  expr: ledger_memory_usage_percent > 80
  for: 5m
  annotations:
    summary: "Memory usage above 80%"

# High latency
- alert: HighLatency
  expr: ledger_latency_p95_ms > 1000
  for: 10m
  annotations:
    summary: "P95 latency exceeds 1 second"
```

### Grafana Dashboards

Pre-built dashboard queries:

```
# Request rate
rate(ledger_total_requests[1m])

# Success rate
rate(ledger_successful_requests[1m]) / rate(ledger_total_requests[1m])

# Active connections
ledger_active_requests

# Memory trend
ledger_memory_mb

# Latency percentiles
ledger_latency_p50_ms
ledger_latency_p95_ms
ledger_latency_p99_ms
```

## Performance Characteristics

### Connection Pooling
- **Min Connections**: 20 (maintained)
- **Max Connections**: 30 (20 base + 10 overflow)
- **Connection Reuse**: 3600 seconds
- **Health Check**: Before each use

### Rate Limiting
- **Default Capacity**: 1000 tokens per user
- **Refill Rate**: 50 tokens/second
- **Endpoint Variations**:
  - Auth: 10 req/sec
  - Users: 50 req/sec
  - Transactions: 100 req/sec
  - Default: 150 req/sec

### Request Handling
- **Max Retries**: 3 attempts
- **Base Delay**: 1 second
- **Max Delay**: 60 seconds
- **Jitter**: Added to prevent thundering herd
- **Default Timeout**: 30 seconds

### Circuit Breaker
- **Failure Threshold**: 5 consecutive failures
- **Recovery Timeout**: 60 seconds
- **State Transitions**: CLOSED → OPEN → HALF_OPEN → CLOSED

## Troubleshooting

### High Latency

1. Check health: `curl /health/detailed`
2. Check concurrency: `GET /api/enterprise/concurrency-status`
3. Check metrics: `GET /api/enterprise/performance-metrics`
4. Review database connection pool usage
5. Scale horizontally with more instances

### Circuit Breaker Open

1. Check health: `curl /health/detailed`
2. Identify root cause (database, memory, disk)
3. Fix underlying issue
4. Manually reset: `POST /api/enterprise/circuit-breaker/reset`

### Rate Limited

1. Implement exponential backoff in client
2. Increase rate limit capacity if needed
3. Use request deduplication to reduce duplicates
4. Implement request queuing

### Memory Leaks

1. Check active sessions: `GET /api/enterprise/session-stats`
2. Monitor memory trend in `/metrics`
3. Clean up expired sessions (automatic daily)
4. Review request history for patterns

## Best Practices

1. **Always use `/health` for load balancer checks**
2. **Implement retry logic with exponential backoff on client**
3. **Queue bulk operations to prevent overwhelming server**
4. **Monitor circuit breaker state and system health**
5. **Use request deduplication for idempotent operations**
6. **Set appropriate timeouts for different operation types**
7. **Scale horizontally with multiple instances**
8. **Keep connection pool size appropriate for your load**
9. **Regularly review performance metrics**
10. **Test failover scenarios in staging**

## Future Enhancements

- [ ] Distributed caching with Redis
- [ ] Message queue for async operations (RabbitMQ/Celery)
- [ ] Database read replicas for load distribution
- [ ] Horizontal scaling with session affinity
- [ ] Distributed tracing (OpenTelemetry)
- [ ] ML-based anomaly detection
- [ ] Multi-region deployment
- [ ] Automatic scaling based on metrics
