#!/bin/bash
# Quick Smoke Test Runner for Linux/Mac
# Tests full case cycle in ~2 minutes

set -e  # Exit on error

echo "======================================"
echo "  Quick Smoke Test - Full Case Cycle"
echo "======================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.11+"
    exit 1
fi

# Check if pytest is installed
if ! python3 -c "import pytest" &> /dev/null; then
    echo "Installing pytest..."
    pip3 install pytest pytest-asyncio
fi

echo "Running smoke tests..."
echo ""

# Run smoke tests
pytest tests/smoke/test_quick_cycle.py -v -s --tb=short

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "  ✅ SMOKE TEST PASSED"
    echo "======================================"
else
    echo ""
    echo "======================================"
    echo "  ❌ SMOKE TEST FAILED"
    echo "======================================"
    exit 1
fi
