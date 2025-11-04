#!/bin/bash
# ============================================================================
# Document Monitor - Quick Start Script (macOS/Linux)
# ============================================================================

echo ""
echo "========================================================================"
echo " MEGA AGENT PRO - Document Generation Monitor"
echo "========================================================================"
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo "[ERROR] Python is not installed or not in PATH"
        echo "Please install Python 3.11+ from https://www.python.org/"
        exit 1
    else
        PYTHON_CMD="python3"
    fi
else
    PYTHON_CMD="python"
fi

echo "[INFO] Python found:"
$PYTHON_CMD --version
echo ""

# Check if uvicorn is installed
if ! $PYTHON_CMD -c "import uvicorn" &> /dev/null; then
    echo "[WARNING] uvicorn not found. Installing..."
    $PYTHON_CMD -m pip install uvicorn
    echo ""
fi

# Check if FastAPI is installed
if ! $PYTHON_CMD -c "import fastapi" &> /dev/null; then
    echo "[WARNING] FastAPI not found. Installing..."
    $PYTHON_CMD -m pip install fastapi
    echo ""
fi

echo "========================================================================"
echo " Starting FastAPI Server..."
echo "========================================================================"
echo ""
echo " Development server with hot-reload enabled"
echo " API endpoints: http://localhost:8000/api/*"
echo " Web interface: http://localhost:8000/index.html"
echo " API docs: http://localhost:8000/docs"
echo ""
echo " Press Ctrl+C to stop the server"
echo "========================================================================"
echo ""

# Start the server
$PYTHON_CMD -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
