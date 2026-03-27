# Enterprise Deployment Configuration

## Quick Start - Enterprise Setup

### Prerequisites
- Docker & Docker Compose (latest)
- Docker Swarm or Kubernetes 1.24+
- MySQL 8.0 installed separately (or managed service)
- Redis 7.0+ (or managed service)
- Python 3.11+
- Node.js 18+ (frontend build)

---

## Local Development with Enterprise Features

### 1. Environment Configuration

Create `.env.enterprise`:

```bash
# FastAPI Configuration
FASTAPI_ENV=development
FASTAPI_DEBUG=true
FASTAPI_WORKERS=4
FASTAPI_WORKER_CLASS=uvicorn.workers.UvicornWorker

# Database Configuration
DATABASE_URL=mysql+pymysql://ledger_user:secure_password@localhost:3306/ledger_db?charset=utf8mb4
DATABASE_POOL_SIZE=20
DATABASE_POOL_RECYCLE=3600
DATABASE_POOL_PRE_PING=true
DATABASE_ECHO_POOL=false
DATABASE_MAX_OVERFLOW=10

# Read Replicas (for read-heavy queries)
DATABASE_REPLICA_URLS=mysql+pymysql://ledger_user:secure_password@replica1:3306/ledger_db,mysql+pymysql://ledger_user:secure_password@replica2:3306/ledger_db
DATABASE_REPLICA_READ_TIMEOUT=5000

# Redis Configuration
REDIS_PRIMARY_URL=redis://localhost:6379/0
REDIS_SENTINEL_URLS=redis://sentinel1:26379,redis://sentinel2:26379,redis://sentinel3:26379
REDIS_SENTINEL_MASTER_NAME=ledger-master
REDIS_POOL_SIZE=50
REDIS_CONNECTION_TIMEOUT=5
REDIS_SOCKET_KEEPALIVE=true

# Concurrency Configuration
CONCURRENT_REQUESTS_LIMIT=1000
CONCURRENT_REQUESTS_PER_USER=50
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_REQUESTS=100

# Lock Configuration
DISTRIBUTED_LOCK_BACKEND=redis
LOCK_TIMEOUT_SECONDS=30
LOCK_RETRY_MAX_ATTEMPTS=3
LOCK_RETRY_BACKOFF_INITIAL_MS=100
LOCK_RETRY_BACKOFF_MAX_MS=5000

# Circuit Breaker Configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS=30
CIRCUIT_BREAKER_EXPECTED_EXCEPTION=Exception

# Retry Configuration
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2
RETRY_BACKOFF_MAX_MS=8000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_HANDLERS=console,file,syslog
LOG_FILE_PATH=/var/log/ledger-app/api.log
LOG_FILE_SIZE_MB=100
LOG_FILE_BACKUP_COUNT=10

# Monitoring Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8001
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production

# Background Tasks
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Security
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
ENCRYPTION_KEY=your-encryption-key-32-chars

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
CORS_ALLOW_CREDENTIALS=true

# Max Connections
MAX_CONNECTION_POOL_SIZE=100
MIN_CONNECTION_POOL_SIZE=10
```

### 2. Docker Compose - Enterprise Stack

Create `docker-compose.enterprise.yml`:

```yaml
version: '3.8'

services:
  # MySQL Primary Database
  mysql-primary:
    image: mysql:8.0
    container_name: ledger-mysql-primary
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: ledger_db
      MYSQL_USER: ledger_user
      MYSQL_PASSWORD: secure_password
    volumes:
      - mysql_data_primary:/var/lib/mysql
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    command: >
      --server-id=1
      --log-bin=mysql-bin
      --binlog-format=ROW
      --max-connections=200
      --max-allowed-packet=16M
      --query-cache-type=0
      --sql-mode="STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ledger-network

  # MySQL Read Replica 1
  mysql-replica-1:
    image: mysql:8.0
    container_name: ledger-mysql-replica-1
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_REPLICATION_USER: repl_user
      MYSQL_REPLICATION_PASSWORD: repl_password
    volumes:
      - mysql_data_replica1:/var/lib/mysql
    command: >
      --server-id=2
      --relay-log=mysql-relay-bin
      --relay-log-index=mysql-relay-bin.index
      --max-connections=200
      --skip-slave-start
      --read-only=ON
    depends_on:
      mysql-primary:
        condition: service_healthy
    links:
      - mysql-primary:mysql-primary
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ledger-network

  # MySQL Read Replica 2
  mysql-replica-2:
    image: mysql:8.0
    container_name: ledger-mysql-replica-2
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_REPLICATION_USER: repl_user
      MYSQL_REPLICATION_PASSWORD: repl_password
    volumes:
      - mysql_data_replica2:/var/lib/mysql
    command: >
      --server-id=3
      --relay-log=mysql-relay-bin
      --relay-log-index=mysql-relay-bin.index
      --max-connections=200
      --skip-slave-start
      --read-only=ON
    depends_on:
      mysql-primary:
        condition: service_healthy
    links:
      - mysql-primary:mysql-primary
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ledger-network

  # Redis Primary
  redis-primary:
    image: redis:7.0-alpine
    container_name: ledger-redis-primary
    command: redis-server --port 6379 --maxmemory 1gb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_data_primary:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ledger-network

  # Redis Replica 1
  redis-replica-1:
    image: redis:7.0-alpine
    container_name: ledger-redis-replica-1
    command: redis-server --port 6380 --slaveof redis-primary 6379 --maxmemory 1gb --maxmemory-policy allkeys-lru
    depends_on:
      - redis-primary
    volumes:
      - redis_data_replica1:/data
    ports:
      - "6380:6380"
    networks:
      - ledger-network

  # Redis Sentinel 1
  redis-sentinel-1:
    image: redis:7.0-alpine
    container_name: ledger-redis-sentinel-1
    command: redis-sentinel /sentinel.conf
    volumes:
      - ./config/sentinel1.conf:/sentinel.conf
      - sentinel_data_1:/data
    ports:
      - "26379:26379"
    depends_on:
      - redis-primary
    networks:
      - ledger-network

  # API Server Instance 1
  api-server-1:
    build:
      context: .
      dockerfile: backend/Dockerfile.enterprise
    container_name: ledger-api-1
    environment:
      - FASTAPI_ENV=production
      - FASTAPI_WORKERS=4
      - PORT=8000
      - INSTANCE_ID=api-1
    env_file:
      - .env.enterprise
    volumes:
      - ./backend:/app/backend
      - ./logs/api-1:/var/log/ledger-app
    ports:
      - "8000:8000"
    depends_on:
      - mysql-primary
      - redis-primary
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - ledger-network
    restart: unless-stopped

  # API Server Instance 2
  api-server-2:
    build:
      context: .
      dockerfile: backend/Dockerfile.enterprise
    container_name: ledger-api-2
    environment:
      - FASTAPI_ENV=production
      - FASTAPI_WORKERS=4
      - PORT=8001
      - INSTANCE_ID=api-2
    env_file:
      - .env.enterprise
    volumes:
      - ./backend:/app/backend
      - ./logs/api-2:/var/log/ledger-app
    ports:
      - "8001:8001"
    depends_on:
      - mysql-primary
      - redis-primary
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - ledger-network
    restart: unless-stopped

  # Celery Worker
  celery-worker:
    build:
      context: .
      dockerfile: backend/Dockerfile.enterprise
    container_name: ledger-celery-worker
    command: celery -A backend.tasks worker --loglevel=info --concurrency=4 --max-tasks-per-child=1000
    environment:
      - FASTAPI_ENV=production
    env_file:
      - .env.enterprise
    volumes:
      - ./backend:/app/backend
      - ./logs/celery:/var/log/ledger-app
    depends_on:
      - mysql-primary
      - redis-primary
    networks:
      - ledger-network
    restart: unless-stopped

  # Nginx Load Balancer
  nginx:
    image: nginx:alpine
    container_name: ledger-nginx
    volumes:
      - ./config/nginx-enterprise.conf:/etc/nginx/nginx.conf:ro
      - ./logs/nginx:/var/log/nginx
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api-server-1
      - api-server-2
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - ledger-network
    restart: unless-stopped

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: ledger-prometheus
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    networks:
      - ledger-network
    restart: unless-stopped

volumes:
  mysql_data_primary:
  mysql_data_replica1:
  mysql_data_replica2:
  redis_data_primary:
  redis_data_replica1:
  sentinel_data_1:
  prometheus_data:

networks:
  ledger-network:
    driver: bridge
```

### 3. Nginx Configuration (Enterprise Load Balancer)

Create `config/nginx-enterprise.conf`:

```nginx
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 65535;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main buffer=16k flush=5s;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               font/truetype font/opentype application/vnd.ms-fontobject 
               image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $http_x_forwarded_for zone=global_limit:10m rate=1000r/s;

    # Upstream backend servers
    upstream api_backend {
        least_conn;
        server api-server-1:8000 weight=1 max_fails=3 fail_timeout=30s;
        server api-server-2:8001 weight=1 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # Health check endpoint
    server {
        listen 80;
        server_name _;
        
        location /health {
            access_log off;
            return 200 '{"status":"ok"}';
            add_header Content-Type application/json;
        }

        location /metrics {
            access_log off;
            proxy_pass http://api-server-1:8000/metrics;
        }
    }

    # Main API server
    server {
        listen 80;
        server_name api.ledger.local;

        # Rate limiting
        limit_req zone=global_limit burst=2000 nodelay;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Request ID correlation
        map $http_x_request_id $request_id_value {
            default $http_x_request_id;
            "" $request_time-$msec;
        }
        
        proxy_set_header X-Request-ID $request_id_value;

        # API endpoints
        location / {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 10s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;

            # Buffering
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
            proxy_busy_buffers_size 8k;
        }

        # Health check
        location /health {
            access_log off;
            proxy_pass http://api_backend;
            proxy_connect_timeout 3s;
            proxy_read_timeout 3s;
        }
    }

    # HTTPS redirect (when SSL certificates available)
    server {
        listen 443 ssl http2;
        server_name api.ledger.local;

        ssl_certificate /etc/nginx/certs/ledger.crt;
        ssl_certificate_key /etc/nginx/certs/ledger.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # ... same configuration as http block ...
    }
}
```

### 4. Prometheus Configuration

Create `config/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'ledger-app'

scrape_configs:
  - job_name: 'api-servers'
    metrics_path: '/metrics'
    static_configs:
      - targets:
        - 'api-server-1:8000'
        - 'api-server-2:8001'
    scrape_interval: 15s
    scrape_timeout: 10s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

---

## Startup Commands

### Development Cluster

```bash
# Start enterprise stack
docker-compose -f docker-compose.enterprise.yml up -d

# Monitor logs
docker-compose -f docker-compose.enterprise.yml logs -f api-server-1 api-server-2 nginx

# Health check
curl http://localhost/health

# Access Prometheus
open http://localhost:9090

# Shutdown
docker-compose -f docker-compose.enterprise.yml down -v
```

### Production Kubernetes Deployment

```bash
# Build image
docker build -f backend/Dockerfile.enterprise -t ledger-app:latest .

# Deploy to K8s
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mysql-statefulset.yaml
kubectl apply -f k8s/redis-statefulset.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/celery-deployment.yaml
kubectl apply -f k8s/nginx-ingress.yaml
kubectl apply -f k8s/hpa.yaml  # Horizontal Pod Autoscaler
kubectl apply -f k8s/pdb.yaml  # Pod Disruption Budget

# Verify deployment
kubectl get pods -n ledger-app
kubectl logs -n ledger-app -f deployment/api-server

# Port forward for testing
kubectl port-forward -n ledger-app svc/api-server 8000:8000
```

---

## Next Steps

1. **Review** `ARCHITECTURE.md` for system design
2. **Study** `FLOW-DIAGRAMS.md` for detailed workflows
3. **Follow** `OPERATIONS-GUIDE.md` for monitoring & troubleshooting
4. **Configure** environment variables for your deployment
5. **Test** health endpoints and metrics collection
6. **Deploy** to your infrastructure (Docker, K8s, or managed cloud services)

For issues or questions, refer to the troubleshooting section in `OPERATIONS-GUIDE.md`.
