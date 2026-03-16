#!/usr/bin/env bash
# Start the Home Finder backend API
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ] && [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "⚠️  ANTHROPIC_API_KEY not set. Create a .env file or export the variable."
  echo "   Example: echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env"
  exit 1
fi

# Install dependencies if needed
pip install -q -r requirements.txt

echo "🚀 Starting Home Finder API on http://localhost:8000"
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
