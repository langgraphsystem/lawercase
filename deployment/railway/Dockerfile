# Railway deployment image for Telegram bot

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps needed for python packages (psycopg, pillow, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN useradd --create-home appuser \
    && mkdir -p /app/logs /app/tmp /app/out \
    && chown -R appuser:appuser /app

USER appuser

# Railway injects TELEGRAM_BOT_TOKEN and other env vars at runtime
ENV PYTHONPATH=/app

# Default poll interval; override via Railway CMD or env if needed
ENV BOT_POLL_INTERVAL=0.5

# Use telegram_interface.bot module directly instead of restart_bot.py
# which is excluded by .dockerignore
CMD ["python", "-m", "telegram_interface.bot"]
