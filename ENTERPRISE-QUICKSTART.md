# Enterprise Features - Quick Start Guide

## Installation

### 1. Install Enterprise Dependencies

```bash
cd backend
pip install -r requirements.txt
# This includes the new psutil package for monitoring
```

### 2. Verify Installation

```bash
python -c "import concurrency; import middleware; import health_monitoring; print('✅ Enterprise modules loaded successfully')"
```

### 3. Run with Enterprise Features

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the app (enterprise features auto-enable if modules are available)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Or with reload for development:
uvicorn main:app --reload
```

The app will automatically detect and enable enterprise features during startup.

## Testing Enterprise Features

### 1. Check Health Status

```bash
# Basic health check (for load balancers)
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# Response:
# {
#     "status": "healthy",
#     "timestamp": "2026-03-23T10:30:45",
#     "checks": {...}
# }
```

### 2. Simulate Load to Test Rate Limiting

```bash
# This will show you rate limiting in action
for i in {1..100}; do
  curl -s http://localhost:8000/api/transactions -H "Authorization: Bearer test_token"
done
```

Expected: After the rate limit is hit, you'll receive 429 responses.

### 3. Monitor Concurrency

```bash
# Get concurrency status (requires valid auth token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/enterprise/concurrency-status

# Response shows:
# - Current and peak active requests
# - Active users count
# - Stalled operations (if any)
# - Circuit breaker state
```

### 4. Get Performance Metrics

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/enterprise/performance-metrics

# Response includes:
# - Request latency percentiles (p50, p95, p99)
# - Average, min, max latencies
# - All collected metrics
```

### 5. Test Circuit Breaker

The circuit breaker automatically engages after 5 consecutive failures and shows:

```json
{
    "status": 503,
    "detail": "Service temporarily unavailable"
}
```

To reset manually (admin only):

```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/enterprise/circuit-breaker/reset
```

## Frontend Integration

### Using EnterpriseAPIClient

The frontend automatically loads the enterprise client when available:

```javascript
// In app.html, after enterprise-client.js is loaded:

// Simple API call with retry logic
const transactions = await enterpriseClient.call(
    api.getTransactions,
    [filters],
    {
        timeout: 30000,
        onSuccess: (result, latency) => {
            console.log(`Loaded in ${latency.toFixed(0)}ms`);
        },
        onError: (error) => {
            showNotification(error.userMessage, 'error');
        }
    }
);

// Queue requests to prevent overwhelming server
enterpriseClient.queueCall(api.bulkImport, [data], 'imports');

// Check performance
console.log('📊 API Performance:', enterpriseClient.getMetrics());
// Output: {
//     "totalRequests": 1542,
//     "successfulRequests": 1540,
//     "failedRequests": 2,
//     "averageLatency": 45.2,
//     "successRate": "99.9%"
// }
```

### Handling Errors Gracefully

```javascript
try {
    const result = await enterpriseClient.call(
        api.saveTransaction,
        [transactionData],
        {
            timeout: 30000,
            deduplicationKey: 'transaction_' + transactionData.id
        }
    );
} catch (error) {
    // error is already classified by enterpriseErrorHandler
    if (error.isRetryable) {
        console.log('Will retry automatically...');
    } else {
        console.error('Critical error:', error.userMessage);
    }
}
```

## Multi-Instance Deployment

### Docker Compose Example

```yaml
version: '3.8'

services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: ledger_db
      MYSQL_USER: ledger_user
      MYSQL_PASSWORD: ledger_pass
    ports:
      - "3306:3306"
    volumes:
      - db_data:/var/lib/mysql

  api1:
    build: ./backend
    environment:
      DATABASE_URL: mysql+pymysql://ledger_user:ledger_pass@db:3306/ledger_db
    ports:
      - "8001:8000"
    depends_on:
      - db

  api2:
    build: ./backend
    environment:
      DATABASE_URL: mysql+pymysql://ledger_user:ledger_pass@db:3306/ledger_db
    ports:
      - "8002:8000"
    depends_on:
      - db

  api3:
    build: ./backend
    environment:
      DATABASE_URL: mysql+pymysql://ledger_user:ledger_pass@db:3306/ledger_db
    ports:
      - "8003:8000"
    depends_on:
      - db

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api1
      - api2
      - api3

volumes:
  db_data:
```

### Nginx Configuration

```nginx
upstream ledger_backend {
    least_conn;
    server api1:8000 max_fails=2 fail_timeout=30s;
    server api2:8000 max_fails=2 fail_timeout=30s;
    server api3:8000 max_fails=2 fail_timeout=30s;
}

server {
    listen 80;

    # Health check endpoint (no logging)
    location /health {
        access_log off;
        proxy_pass http://ledger_backend;
        proxy_connect_timeout 5s;
        proxy_read_timeout 5s;
    }

    # All other requests
    location / {
        proxy_pass http://ledger_backend;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        
        # Connection timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

### Run Multi-Instance Setup

```bash
# Start all services
docker-compose up -d

# Verify all instances are healthy
curl http://localhost/health
curl http://localhost/health/detailed

# Monitor concurrency across all instances
curl -H "Authorization: Bearer TOKEN" \
  http://localhost/api/enterprise/concurrency-status
```

## Monitoring & Alerts

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ledger'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

Run Prometheus:

```bash
docker run -d -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
```

### Key Metrics to Monitor

```promql
# Request rate
rate(ledger_total_requests[1m])

# Success rate
rate(ledger_successful_requests[1m]) / rate(ledger_total_requests[1m])

# Active requests
ledger_active_requests

# P95 latency
ledger_latency_p95_ms > 1000

# Circuit breaker status
ledger_circuit_breaker_state == 2  # OPEN

# Memory usage
ledger_memory_usage_percent > 80

# Database connections
ledger_db_active_connections > 25
```

## Performance Tuning

### Connection Pool Optimization

Adjust based on expected concurrent users:

```python
# For 10-50 concurrent users (default)
connection_pool = ConnectionPool(
    max_pool_size=20,
    max_overflow=10
)

# For 50-100 concurrent users
connection_pool = ConnectionPool(
    max_pool_size=40,
    max_overflow=20
)

# For 100+ concurrent users
connection_pool = ConnectionPool(
    max_pool_size=60,
    max_overflow=30
)
```

### Rate Limiting Tuning

Adjust based on typical user behavior:

```python
# For moderate usage
request_budget = RequestBudget(
    capacity=1000,      # Max 1000 tokens
    refill_rate=50.0    # 50 tokens/sec = 3000/min per user
)

# For high usage
request_budget = RequestBudget(
    capacity=2000,
    refill_rate=100.0   # 100 tokens/sec = 6000/min per user
)
```

## Troubleshooting

### Check if Enterprise Features are Enabled

```python
python -c "from main import ENTERPRISE_MODE; print(f'Enterprise Mode: {ENTERPRISE_MODE}')"
```

### View Detailed Health Status

```bash
curl http://localhost:8000/health/detailed | python -m json.tool
```

### Check for Stalled Operations

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/enterprise/deadlock-detection-enabled | python -m json.tool
```

### Monitor System Resources

```bash
# Memory usage
curl http://localhost:8000/health/detailed | jq '.checks.memory'

# Disk usage
curl http://localhost:8000/health/detailed | jq '.checks.disk'

# CPU usage
curl http://localhost:8000/health/detailed | jq '.checks.cpu'
```

## Logs

Enterprise features log to stdout with timestamps:

```
[INFO] Enabling enterprise middleware stack
[INFO] Database connection validated successfully
[INFO] Using enterprise connection pool: {...}
[DEBUG] CircuitBreaker call successful, resetting to CLOSED
[WARNING] Rate limit exceeded for user_123 on /api/transactions
[ERROR] Database health check failed: Connection timeout
```

## Next Steps

1. **Deploy to staging** with multi-instance setup
2. **Run load tests** to verify performance characteristics
3. **Configure monitoring** with Prometheus/Grafana
4. **Set up alerting** for critical metrics
5. **Test failover** scenarios
6. **Monitor production** health checks regularly
7. **Tune settings** based on actual usage patterns

See `ENTERPRISE-FEATURES.md` for complete documentation.
