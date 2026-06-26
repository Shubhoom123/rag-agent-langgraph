#!/bin/bash
# RAG Agent — Knowledge Base Seeder
# Run from anywhere in the project:
#   ./backend/scripts/seed.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting knowledge base seeder..."
echo "Backend: $BACKEND_DIR"
echo ""

cd "$BACKEND_DIR" || exit 1

# Activate venv if it exists
if [ -f "../venv/bin/activate" ]; then
  source "../venv/bin/activate"
  echo "✓ Activated venv"
elif [ -f "venv/bin/activate" ]; then
  source "venv/bin/activate"
  echo "✓ Activated venv"
fi

python scripts/seed_vectorstore.py