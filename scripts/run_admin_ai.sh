#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/RAGadmin"

if [ ! -f .env ]; then
  echo "Missing RAGadmin/.env"
  echo "Copy .env.example to .env and fill DATABASE_URL, INTERNAL_API_KEY, DEEPSEEK_API_KEY and GEMINI_API_KEY."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
if [ ! -f .venv/.campuspulse_deps_installed ]; then
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  touch .venv/.campuspulse_deps_installed
fi

exec .venv/bin/python start_ai.py
