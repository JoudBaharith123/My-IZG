#!/bin/bash

# Start Backend Server Script
# Usage: ./start_backend.sh

echo "🚀 Starting Intelligent Zone Generator Backend..."
echo ""

# Path to venv in parent directory
VENV_PATH="../.venv"

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "Please create it first:"
    echo "  cd /root/openai_projects/Binder_intelligent_zone_generator_v1"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r Intelligent_zone_generator/requirements.txt"
    exit 1
else
    echo "✅ Virtual environment found at $VENV_PATH"
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Set PYTHONPATH to src directory
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Start server
echo "🌐 Starting uvicorn server on http://0.0.0.0:8000"
echo "📡 API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
