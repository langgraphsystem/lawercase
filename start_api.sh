#!/bin/bash
# Start script for Railway deployment
# Uses PORT environment variable if available, defaults to 8000

PORT=${PORT:-8000}
WORKERS=${WORKERS:-4}

echo "Starting MegaAgent Pro API on port $PORT with $WORKERS workers..."

# Pick the right Python from common venv locations (Docker or Nixpacks)
if [ -x "/opt/venv/bin/python" ]; then
  PYTHON_BIN="/opt/venv/bin/python"
elif [ -x "/app/.venv/bin/python" ]; then
  PYTHON_BIN="/app/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python)"
fi

if [ -z "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="/app"
else
  case ":$PYTHONPATH:" in
    *":/app:"*) ;;
    *) export PYTHONPATH="/app:$PYTHONPATH" ;;
  esac
fi

"$PYTHON_BIN" - <<'PYCHK' >/dev/null 2>&1
try:
    import uvicorn  # type: ignore
except Exception:
    raise SystemExit(1)
PYCHK
if [ $? -ne 0 ]; then
  echo "[startup] uvicorn not found; installing minimal deps (uvicorn, fastapi)..."
  "$PYTHON_BIN" -m pip install --no-cache-dir \
    "uvicorn>=0.29.0,<1.0.0" \
    "fastapi>=0.110.0,<1.0.0" || {
    echo "[startup] Failed to install uvicorn/fastapi" >&2
    exit 1
  }
fi

exec "$PYTHON_BIN" -m uvicorn api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips '*'
