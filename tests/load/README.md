# Load Testing Guide

## Overview

This directory contains load testing configurations for MegaAgent Pro using Locust.

## Prerequisites

```bash
pip install locust
```

## Running Load Tests

### Basic Load Test

```bash
# Start Locust web interface
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Open browser at http://localhost:8089
# Configure number of users and spawn rate
```

### Headless Load Test

```bash
# Run without web UI
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html load_test_report.html
```

### Distributed Load Test

```bash
# Start master
locust -f tests/load/locustfile.py --master --host=http://localhost:8000

# Start workers (run on multiple machines)
locust -f tests/load/locustfile.py --worker --master-host=<master-ip>
```

## Test Scenarios

### 1. Normal Load Test
- Users: 50
- Spawn rate: 5/sec
- Duration: 10 minutes
- Goal: Verify normal operation

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 50 \
    --spawn-rate 5 \
    --run-time 10m \
    --headless
```

### 2. Stress Test
- Users: 500
- Spawn rate: 50/sec
- Duration: 5 minutes
- Goal: Find breaking point

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 500 \
    --spawn-rate 50 \
    --run-time 5m \
    --headless
```

### 3. Spike Test
- Users: 100 → 1000 (spike)
- Duration: 15 minutes
- Goal: Test recovery from sudden load

```bash
# Manually adjust users in web UI:
# Start with 100 users
# After 5 minutes, spike to 1000 users
# After 2 minutes, back to 100 users
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### 4. Endurance Test
- Users: 200
- Spawn rate: 10/sec
- Duration: 2 hours
- Goal: Test stability over time

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 200 \
    --spawn-rate 10 \
    --run-time 2h \
    --headless
```

## Performance Targets

### Response Time Targets
- P50: < 200ms
- P95: < 500ms
- P99: < 1000ms

### Throughput Targets
- Minimum: 100 req/sec
- Target: 500 req/sec
- Peak: 1000 req/sec

### Error Rate
- Normal load: < 0.1%
- Stress load: < 1%
- Spike load: < 5%

## Monitoring During Tests

### Metrics to Monitor
1. **Response Time**: P50, P95, P99
2. **Throughput**: Requests/second
3. **Error Rate**: Failed requests percentage
4. **Resource Usage**:
   - CPU utilization
   - Memory usage
   - Database connections
   - Cache hit rate

### Recommended Tools
- Locust Web UI (http://localhost:8089)
- Prometheus + Grafana
- Application logs
- Database monitoring

## Interpreting Results

### Good Performance
- Response times within targets
- Error rate < 0.1%
- Consistent throughput
- Stable resource usage

### Warning Signs
- Increasing response times
- Error rate > 1%
- Database connection pool exhaustion
- Memory leaks
- CPU throttling

### Critical Issues
- Cascading failures
- Timeouts
- Service crashes
- Data corruption

## Troubleshooting

### High Error Rate
1. Check application logs
2. Verify database connectivity
3. Check rate limiting configuration
4. Review recent code changes

### Slow Response Times
1. Enable profiling
2. Check database query performance
3. Review caching strategy
4. Analyze bottlenecks with APM tools

### Resource Exhaustion
1. Check memory leaks
2. Review connection pooling
3. Verify cleanup of resources
4. Consider horizontal scaling

## Best Practices

1. **Gradual Ramp-up**: Use appropriate spawn rates
2. **Realistic Workload**: Mirror production usage patterns
3. **Monitor Continuously**: Watch metrics during tests
4. **Test in Stages**: Normal → Stress → Spike → Endurance
5. **Document Results**: Keep baseline metrics
6. **Automate Testing**: Include in CI/CD pipeline

## Example CI/CD Integration

```yaml
# .github/workflows/load-test.yml
name: Load Test

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install locust
      - name: Run load test
        run: |
          locust -f tests/load/locustfile.py \
            --host=${{ secrets.TEST_HOST }} \
            --users 100 \
            --spawn-rate 10 \
            --run-time 5m \
            --headless \
            --html load_test_report.html
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: load_test_report.html
```

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review Grafana dashboards
- Contact DevOps team
