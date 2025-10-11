# MegaAgent Pro - Production Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Deployment Options](#deployment-options)
4. [Configuration](#configuration)
5. [Monitoring & Observability](#monitoring--observability)
6. [Security](#security)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum (Dev/Test)**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB SSD
- OS: Linux (Ubuntu 22.04+ recommended)

**Recommended (Production)**
- CPU: 8+ cores
- RAM: 16+ GB
- Storage: 200+ GB NVMe SSD
- OS: Linux (Ubuntu 22.04+ LTS)

### Software Dependencies

```bash
# Python 3.11+
python --version  # Should be >= 3.11

# PostgreSQL 15+
psql --version

# Redis 7+
redis-cli --version

# Docker & Docker Compose (if using containers)
docker --version
docker-compose --version

# Kubernetes (if using K8s)
kubectl version --client
```

### API Keys & Credentials

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic Claude API key
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret key (generate with `openssl rand -hex 32`)

---

## Infrastructure Setup

### Option 1: Docker Compose (Recommended for Single Server)

#### 1. Clone Repository

```bash
git clone https://github.com/your-org/mega_agent_pro.git
cd mega_agent_pro
```

#### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Required `.env` variables:
```bash
# Database
DB_PASSWORD=your_secure_password_here

# Application
SECRET_KEY=your_secret_key_here
ENVIRONMENT=production
LOG_LEVEL=INFO

# AI Services
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Monitoring
GRAFANA_PASSWORD=your_grafana_password
```

#### 3. Build and Deploy

```bash
# Build image
docker-compose -f deployment/docker/docker-compose.production.yml build

# Start services
docker-compose -f deployment/docker/docker-compose.production.yml up -d

# Check status
docker-compose -f deployment/docker/docker-compose.production.yml ps

# View logs
docker-compose -f deployment/docker/docker-compose.production.yml logs -f app
```

#### 4. Initialize Database

```bash
# Run migrations
docker-compose -f deployment/docker/docker-compose.production.yml exec app \
    python -m alembic upgrade head

# Create admin user
docker-compose -f deployment/docker/docker-compose.production.yml exec app \
    python scripts/create_admin_user.py
```

#### 5. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# API test
curl http://localhost:8000/api/v1/status
```

### Option 2: Kubernetes (Recommended for Scalability)

#### 1. Prepare Cluster

```bash
# Verify cluster access
kubectl cluster-info
kubectl get nodes

# Create namespace
kubectl create namespace megaagent-prod

# Set default namespace
kubectl config set-context --current --namespace=megaagent-prod
```

#### 2. Configure Secrets

```bash
# Create secrets from .env file
kubectl create secret generic megaagent-secrets \
    --from-literal=database-url="postgresql://user:password@postgres-service:5432/megaagent" \
    --from-literal=secret-key="your-secret-key" \
    --from-literal=openai-api-key="sk-..." \
    --from-literal=anthropic-api-key="sk-ant-..."

# Verify
kubectl get secrets
```

#### 3. Deploy Application

```bash
# Apply ConfigMap and Secrets
kubectl apply -f deployment/kubernetes/configmap.yaml

# Deploy application
kubectl apply -f deployment/kubernetes/deployment.yaml

# Deploy database (if not external)
kubectl apply -f deployment/kubernetes/postgres.yaml
kubectl apply -f deployment/kubernetes/redis.yaml

# Check deployment
kubectl get deployments
kubectl get pods
kubectl get services
```

#### 4. Setup Ingress

```bash
# Install ingress controller (if not present)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Apply ingress rules
kubectl apply -f deployment/kubernetes/ingress.yaml

# Get external IP
kubectl get ingress
```

#### 5. Enable Auto-scaling

```bash
# HPA is already configured in deployment.yaml
# Verify HPA
kubectl get hpa

# Check metrics
kubectl top pods
kubectl top nodes
```

---

## Configuration

### Application Configuration

**config/production.yaml**
```yaml
environment: production
debug: false
log_level: INFO

database:
  pool_size: 20
  max_overflow: 10
  pool_timeout: 30
  pool_recycle: 3600

cache:
  ttl: 3600
  max_size: 10000
  redis_db: 0

llm:
  default_model: gpt-4
  timeout: 60
  max_retries: 3
  rate_limit: 100

security:
  cors_origins:
    - https://yourdomain.com
  rate_limit: 100/minute
  session_timeout: 3600
```

### Database Configuration

```sql
-- Production optimizations
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '10MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';

-- Reload configuration
SELECT pg_reload_conf();
```

### Redis Configuration

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

---

## Monitoring & Observability

### Grafana Dashboards

Access: `http://your-domain:3000`

Default credentials:
- Username: `admin`
- Password: `${GRAFANA_PASSWORD}`

**Available Dashboards:**
1. **System Overview** - CPU, Memory, Network
2. **Application Metrics** - Request rate, Latency, Errors
3. **Database Performance** - Connections, Query time
4. **LLM Usage** - API calls, Costs, Token usage
5. **Security Events** - Failed logins, Injection attempts

### Prometheus Metrics

Access: `http://your-domain:9090`

**Key Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `llm_api_calls_total` - LLM API calls
- `cache_hits_total` - Cache hit rate
- `db_connections_active` - Active DB connections

### Log Aggregation

**Structured Logging:**
```python
# Logs are in JSON format
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "service": "megaagent-api",
  "trace_id": "abc-123",
  "message": "Request processed",
  "duration_ms": 150
}
```

**Log Locations:**
- Application: `/app/logs/app.log`
- Access: `/var/log/nginx/access.log`
- Error: `/var/log/nginx/error.log`

---

## Security

### SSL/TLS Configuration

```bash
# Generate SSL certificate (Let's Encrypt)
certbot certonly --standalone -d yourdomain.com

# Update nginx configuration
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of config
}
```

### Firewall Rules

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# iptables
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -j DROP
```

### Secret Management

**Kubernetes Secrets:**
```bash
# Use sealed secrets for GitOps
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml

# Seal a secret
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
```

**Docker Secrets:**
```bash
# Create secret
echo "my_secret_password" | docker secret create db_password -

# Use in compose
services:
  db:
    secrets:
      - db_password
secrets:
  db_password:
    external: true
```

---

## Backup & Recovery

### Database Backup

```bash
# Automated daily backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="megaagent_backup_${DATE}.sql.gz"

# Create backup
docker-compose exec -T postgres pg_dump -U user megaagent | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep only last 30 days
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp "${BACKUP_DIR}/${FILENAME}" s3://your-bucket/backups/
```

**Cron Schedule:**
```cron
# Run daily at 2 AM
0 2 * * * /path/to/backup_script.sh >> /var/log/backup.log 2>&1
```

### Database Restore

```bash
# Stop application
docker-compose stop app

# Restore database
gunzip < backup_file.sql.gz | docker-compose exec -T postgres psql -U user megaagent

# Start application
docker-compose start app
```

### Disaster Recovery Plan

1. **RTO (Recovery Time Objective)**: < 1 hour
2. **RPO (Recovery Point Objective)**: < 24 hours

**Recovery Steps:**
1. Provision new infrastructure
2. Restore database from latest backup
3. Deploy application from Docker image
4. Verify health checks
5. Update DNS/Load balancer
6. Monitor for issues

---

## Troubleshooting

### Common Issues

#### 1. High Memory Usage

**Symptoms:** OOM errors, slow response times

**Solutions:**
```bash
# Check memory usage
docker stats

# Increase memory limits
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G

# Kubernetes
resources:
  limits:
    memory: "4Gi"
```

#### 2. Database Connection Pool Exhausted

**Symptoms:** `FATAL: remaining connection slots are reserved`

**Solutions:**
```python
# Increase pool size
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20

# Or in PostgreSQL
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

#### 3. Slow API Responses

**Symptoms:** High P95/P99 latencies

**Diagnostics:**
```bash
# Enable profiling
export ENABLE_PROFILING=true

# Check slow queries
docker-compose exec postgres psql -U user -d megaagent \
    -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Review cache hit rate
redis-cli info stats | grep keyspace_hits
```

**Solutions:**
- Add database indexes
- Increase cache TTL
- Enable query optimization
- Scale horizontally

#### 4. Service Won't Start

**Check logs:**
```bash
# Docker
docker-compose logs app

# Kubernetes
kubectl logs -l app=megaagent --tail=100

# System logs
journalctl -u megaagent -n 100
```

**Common causes:**
- Missing environment variables
- Database connection failure
- Port already in use
- Insufficient permissions

---

## Performance Tuning

### Application Tuning

```python
# config/production.py
WORKERS = cpu_count() * 2 + 1
WORKER_CLASS = "uvicorn.workers.UvicornWorker"
KEEPALIVE = 5
TIMEOUT = 30
GRACEFUL_TIMEOUT = 30
```

### Database Tuning

```sql
-- Add indexes for frequent queries
CREATE INDEX CONCURRENTLY idx_cases_client_id ON cases(client_id);
CREATE INDEX CONCURRENTLY idx_documents_case_id ON documents(case_id);
CREATE INDEX CONCURRENTLY idx_audit_timestamp ON audit_logs(timestamp DESC);

-- Vacuum and analyze
VACUUM ANALYZE;
```

### Caching Strategy

```python
# Aggressive caching for production
CACHE_CONFIG = {
    "query_results": {"ttl": 3600, "max_size": 10000},
    "embeddings": {"ttl": 86400, "max_size": 50000},
    "llm_responses": {"ttl": 7200, "max_size": 5000},
}
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor error logs
- Check disk space
- Review security alerts

**Weekly:**
- Database vacuum and analyze
- Review slow queries
- Check backup integrity

**Monthly:**
- Update dependencies
- Review and rotate logs
- Performance testing
- Security audit

### Update Procedure

```bash
# 1. Backup database
./scripts/backup_database.sh

# 2. Pull latest code
git pull origin main

# 3. Build new image
docker-compose build

# 4. Run migrations
docker-compose run app alembic upgrade head

# 5. Rolling restart
docker-compose up -d --no-deps --build app

# 6. Verify health
curl http://localhost:8000/health
```

---

## Support & Resources

- **Documentation**: https://docs.megaagent.pro
- **Issue Tracker**: https://github.com/your-org/megaagent-pro/issues
- **Community**: https://discord.gg/megaagent
- **Email**: support@megaagent.pro

---

**Last Updated**: 2025-01-15
**Version**: 1.0.0
