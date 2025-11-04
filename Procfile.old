web: sh -c 'PYTHONPATH=/app /app/.venv/bin/pip install -q uvicorn fastapi && PYTHONPATH=/app /app/.venv/bin/python -m uvicorn --app-dir /app api.main:app --host 0.0.0.0 --port ${PORT}'
