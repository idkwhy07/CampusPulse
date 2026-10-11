#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/ml_service"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi

if [ ! -f .venv/.campuspulse_deps_installed ]; then
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  touch .venv/.campuspulse_deps_installed
fi

exec .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8002
