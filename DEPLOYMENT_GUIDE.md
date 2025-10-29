# MegaAgent Pro - Production Deployment Guide

Complete guide for deploying MegaAgent Pro to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Security](#security)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, or RHEL 8+)
- **CPU**: Minimum 4 cores (8+ recommended for production)
- **RAM**: Minimum 8GB (16GB+ recommended for production)
- **Disk**: 50GB+ SSD storage
- **Network**: Stable internet connection for LLM API calls

### Required Software

- **Docker**: 24.0+ and Docker Compose 2.0+
- **Kubernetes**: 1.27+ (for K8s deployment)
- **PostgreSQL**: 15+ (provided in Docker Compose)
- **Redis**: 7+ (provided in Docker Compose)
- **Python**: 3.11+ (for local development)

### API Keys

Required:
- OpenAI API key (GPT-5 access) OR
- Anthropic API key (Claude access) OR
- Google Gemini API key

Optional:
- Telegram Bot Token (for Telegram interface)
- DocRaptor API key (for PDF generation)
- Adobe OCR API key (for document processing)

---

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd mega_agent_pro_codex_handoff

# Copy environment file
cp .env.production.example .env

# Edit .env with your actual values
nano .env
```

### 2. Configure Environment

Edit `.env` and set at minimum:

```bash
# Security (REQUIRED!)
SECURITY_JWT_SECRET_KEY=$(openssl rand -base64 32)

# Database (REQUIRED!)
DB_POSTGRES_PASSWORD=$(openssl rand -base64 24)
REDIS_PASSWORD=$(openssl rand -base64 24)

# LLM Provider (at least one REQUIRED!)
LLM_OPENAI_API_KEY=sk-your-key-here
# OR
LLM_ANTHROPIC_API_KEY=sk-ant-your-key-here
# OR
LLM_GEMINI_API_KEY=your-key-here

# CORS (IMPORTANT!)
SECURITY_CORS_ORIGINS=["https://yourdomain.com"]
```

### 3. Launch with Docker Compose

```bash
# Production deployment
docker-compose up -d

# Check logs
docker-compose logs -f api

# Verify health
curl http://localhost:8000/health
```

### 4. Verify Deployment

```bash
# Check all services are running
docker-compose ps

# Check API health
curl http://localhost:8000/health | jq

# Check liveness
curl http://localhost:8000/liveness

# Check readiness
curl http://localhost:8000/readiness
```

---

## Configuration

### Environment Variables

See `.env.production.example` for all available options.

#### Critical Settings

**Security** (Production):
```bash
SECURITY_JWT_SECRET_KEY=<strong-random-secret>
SECURITY_CORS_ORIGINS=["https://yourdomain.com"]
FEATURE_ENABLE_API_AUTH=true
FEATURE_ENABLE_RATE_LIMITING=true
```

**Database**:
```bash
DB_POSTGRES_HOST=postgres
DB_POSTGRES_USER=megaagent
DB_POSTGRES_PASSWORD=<strong-password>
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

**Logging**:
```bash
OBSERVABILITY_LOG_LEVEL=INFO
OBSERVABILITY_LOG_FORMAT=json
OBSERVABILITY_TRACING_ENABLED=true
```

### Feature Flags

Enable/disable features via environment variables:

```bash
# Core features
FEATURE_ENABLE_EVIDENCE_ANALYSIS=true
FEATURE_ENABLE_RAG_PIPELINE=true
FEATURE_ENABLE_WORKFLOW_ORCHESTRATION=true

# API features
FEATURE_ENABLE_API_AUTH=true
FEATURE_ENABLE_RATE_LIMITING=true

# Experimental (disable in production)
FEATURE_ENABLE_EXPERIMENTAL_FEATURES=false
```

---

## Docker Deployment

### Production (docker-compose.yml)

```bash
# Start all services
docker-compose up -d

# Scale API servers
docker-compose up -d --scale api=4

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (DANGER: destroys data!)
docker-compose down -v
```

### Development (docker-compose.dev.yml)

```bash
# Start development environment with hot-reload
docker-compose -f docker-compose.dev.yml up

# With development tools (PgAdmin, Redis Commander)
docker-compose -f docker-compose.dev.yml --profile tools up
```

### Individual Services

```bash
# API only
docker-compose up api

# With Telegram bot
docker-compose --profile telegram up

# With Nginx reverse proxy
docker-compose --profile production up
```

### Building Custom Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build api

# Build without cache
docker-compose build --no-cache

# Build specific Dockerfile target
docker build --target api -t megaagent/api:latest .
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Install Helm (for cert-manager)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 1. Create Namespace

```bash
kubectl create namespace megaagent
kubectl config set-context --current --namespace=megaagent
```

### 2. Create Secrets

```bash
# Create secrets from .env file
kubectl create secret generic megaagent-secrets \
  --from-literal=postgres-user=megaagent \
  --from-literal=postgres-password=$(openssl rand -base64 24) \
  --from-literal=redis-password=$(openssl rand -base64 24) \
  --from-literal=jwt-secret-key=$(openssl rand -base64 32) \
  --from-literal=openai-api-key=$LLM_OPENAI_API_KEY \
  --from-literal=anthropic-api-key=$LLM_ANTHROPIC_API_KEY
```

### 3. Deploy Services

```bash
# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl get pods
kubectl get svc
kubectl get ingress
```

### 4. Install Cert-Manager (for TLS)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create Let's Encrypt issuer
kubectl apply -f k8s/cert-issuer.yaml
```

### 5. Verify Deployment

```bash
# Check pod status
kubectl get pods -w

# Check logs
kubectl logs -f deployment/megaagent-api

# Check health endpoint
kubectl port-forward service/megaagent-api 8000:80
curl http://localhost:8000/health
```

---

## Monitoring & Observability

### Health Checks

```bash
# Liveness (is service alive?)
curl http://localhost:8000/liveness

# Readiness (is service ready to serve?)
curl http://localhost:8000/readiness

# Startup (has service finished starting?)
curl http://localhost:8000/startup

# Detailed health with dependencies
curl http://localhost:8000/health | jq
```

### Logs

```bash
# Docker Compose
docker-compose logs -f api

# Kubernetes
kubectl logs -f deployment/megaagent-api

# Follow logs for specific pod
kubectl logs -f <pod-name>

# Last 100 lines
kubectl logs --tail=100 deployment/megaagent-api
```

### Metrics

```bash
# Basic metrics endpoint
curl http://localhost:8000/metrics | jq

# Prometheus metrics (if enabled)
curl http://localhost:9090/metrics
```

### Distributed Tracing

If tracing is enabled (Jaeger):

```bash
# Access Jaeger UI
kubectl port-forward svc/jaeger-query 16686:16686

# Open http://localhost:16686 in browser
```

---

## Security

### SSL/TLS Configuration

For production, always use HTTPS:

**Docker with Nginx**:
```bash
# Generate SSL certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/private.key \
  -out nginx/ssl/certificate.crt

# Start with Nginx profile
docker-compose --profile production up -d
```

**Kubernetes with Cert-Manager**:
```yaml
# Automatically handled by cert-manager + Let's Encrypt
# See k8s/ingress.yaml
```

### Secrets Management

**Never commit secrets to git!**

```bash
# Generate strong secrets
openssl rand -base64 32  # For JWT secret
openssl rand -base64 24  # For passwords

# Use environment variables
export SECURITY_JWT_SECRET_KEY=$(openssl rand -base64 32)

# Or use .env file (not committed)
echo "SECURITY_JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
```

### API Authentication

```bash
# Generate API key for service accounts
curl -X POST http://localhost:8000/api/v1/admin/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "service-account-1"}'

# Use API key
curl http://localhost:8000/api/v1/evidence/analyze \
  -H "X-API-Key: sk_your_api_key_here"
```

### Rate Limiting

Configured in `.env`:
```bash
SECURITY_RATE_LIMIT_PER_MINUTE=60
SECURITY_RATE_LIMIT_PER_HOUR=1000
```

---

## Scaling

### Horizontal Scaling

**Docker Compose**:
```bash
# Scale to 4 API instances
docker-compose up -d --scale api=4

# Behind Nginx load balancer
docker-compose --profile production up -d --scale api=4
```

**Kubernetes**:
```bash
# Manual scaling
kubectl scale deployment megaagent-api --replicas=5

# Auto-scaling (HPA configured in k8s/deployment.yaml)
kubectl autoscale deployment megaagent-api \
  --min=3 --max=10 \
  --cpu-percent=70
```

### Vertical Scaling

**Increase resources** in `docker-compose.yml`:
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

Or in Kubernetes `deployment.yaml`:
```yaml
resources:
  limits:
    cpu: 4000m
    memory: 8Gi
```

### Database Connection Pooling

Configure in `.env`:
```bash
DB_POOL_SIZE=20        # Concurrent connections per worker
DB_MAX_OVERFLOW=40     # Additional connections when pool exhausted
```

---

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
docker-compose logs api

# Common causes:
# - Missing environment variables
# - Database connection failure
# - Port already in use

# Fix: Check .env file and database connectivity
```

#### 2. Database Connection Errors

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres pg_isready

# Check credentials
docker-compose exec postgres psql -U megaagent -d megaagent_pro
```

#### 3. High Memory Usage

```bash
# Check resource usage
docker stats

# Reduce workers or pool size
API_WORKERS=2
DB_POOL_SIZE=10
```

#### 4. Rate Limiting Issues

```bash
# Temporarily disable for debugging
FEATURE_ENABLE_RATE_LIMITING=false

# Or increase limits
SECURITY_RATE_LIMIT_PER_MINUTE=120
```

#### 5. LLM API Errors

```bash
# Verify API key
echo $LLM_OPENAI_API_KEY

# Check quota/billing
# Check network connectivity to LLM provider

# Enable detailed logging
OBSERVABILITY_LOG_LEVEL=DEBUG
```

### Health Check Failures

```bash
# Check health endpoint directly
curl -v http://localhost:8000/health | jq

# Check dependencies
curl http://localhost:8000/health | jq '.dependencies'

# Common issues:
# - Database not ready
# - Redis not connected
# - LLM API keys missing
```

### Performance Issues

```bash
# Enable performance logging
OBSERVABILITY_LOG_LEVEL=DEBUG

# Check slow queries
docker-compose exec postgres pg_stat_statements

# Monitor request latency
curl http://localhost:8000/metrics | jq '.performance'
```

---

## Backup & Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U megaagent megaagent_pro > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U megaagent megaagent_pro < backup.sql
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * cd /path/to/project && docker-compose exec postgres pg_dump -U megaagent megaagent_pro | gzip > backups/backup-$(date +\%Y\%m\%d).sql.gz
```

---

## Production Checklist

Before deploying to production:

- [ ] Set strong `SECURITY_JWT_SECRET_KEY`
- [ ] Set strong database passwords
- [ ] Configure CORS to specific domains
- [ ] Enable `FEATURE_ENABLE_API_AUTH=true`
- [ ] Enable `FEATURE_ENABLE_RATE_LIMITING=true`
- [ ] Disable debug mode: `DEBUG=false`
- [ ] Disable docs: `DOCS_URL=` (empty)
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring and alerting
- [ ] Configure automated backups
- [ ] Test disaster recovery procedures
- [ ] Review and test all environment variables
- [ ] Load test with expected traffic
- [ ] Set up log aggregation
- [ ] Configure resource limits
- [ ] Test health check endpoints
- [ ] Document runbook for on-call

---

## Support

For issues and questions:

- GitHub Issues: <repository-url>/issues
- Documentation: <repository-url>/docs
- Security issues: security@yourdomain.com

---

## License

See LICENSE file for details.
