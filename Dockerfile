# Multi-stage Dockerfile for MegaAgent Pro
# Optimized for production deployment with health checks
# Build date: 2025-11-13 - Force cache invalidation for structlog fix

# ============================================================================
# Stage 1: Base
# ============================================================================
FROM python:3.11-slim AS base

# Cache-busting argument - change this to force rebuild
ARG BUILD_DATE=2025-11-13
ENV BUILD_DATE=${BUILD_DATE}

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1


# ============================================================================
# Stage 2: Builder
# ============================================================================
FROM base AS builder

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        git \
        libopenjp2-7-dev \
        libjpeg-dev \
        zlib1g-dev \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf-2.0-dev \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel

# Install Pillow first with JPEG2000 support (needs libopenjp2-7-dev from above)
RUN /opt/venv/bin/pip install --no-cache-dir 'Pillow>=10.0.0,<11.0.0' \
    && /opt/venv/bin/python -c "from PIL import features; print('JPEG2000 support:', features.check_codec('jpg_2000'))"

# Install remaining dependencies
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Download spaCy language model (used for legal NLP)
RUN /opt/venv/bin/python -m spacy download en_core_web_sm || echo "spaCy model download skipped"

# Copy application code
COPY . /app


# ============================================================================
# Stage 3: Runtime (API Server)
# ============================================================================
FROM base AS api

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
        libopenjp2-7 \
        libjpeg62-turbo \
        zlib1g \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libssl3 \
        libxml2 \
        libxslt1.1 \
        fonts-liberation \
        fonts-dejavu-core \
        ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    ENV=production

# Copy application code
COPY --from=builder /app /app

# Create app user and directories
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/logs /app/tmp /app/out /app/data \
    && chown -R appuser:appuser /app

USER appuser

# Expose API port (Railway will override with $PORT)
EXPOSE 8000

# Health check for API (Railway uses healthcheckPath instead)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run API server with dynamic port support
CMD ["bash", "-lc", "python -m uvicorn --app-dir /app api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1} --log-level info --proxy-headers --forwarded-allow-ips '*'"]


# ============================================================================
# Stage 4: Runtime (Telegram Bot)
# ============================================================================
FROM base AS bot

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        libffi8 \
        libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /app

# Create app user and directories
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/logs /app/tmp /app/out /app/data \
    && chown -R appuser:appuser /app

USER appuser

# Run Telegram bot
CMD ["python", "-m", "telegram_interface.bot"]


# ============================================================================
# Stage 5: Runtime (Worker)
# ============================================================================
FROM base AS worker

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        libffi8 \
        libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /app

# Create app user and directories
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/logs /app/tmp /app/out /app/data \
    && chown -R appuser:appuser /app

USER appuser

# Worker health-check ensures background loop can execute a smoke run.
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -m core.workers.task_worker smoke || exit 1

# Run background worker (if needed)
CMD ["python", "-m", "core.workers.task_worker", "start"]
