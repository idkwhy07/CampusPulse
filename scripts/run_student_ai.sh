#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/python_service"

if [ ! -f .env ]; then
  echo "Missing python_service/.env"
  echo "Copy .env.example to .env and fill DEEPSEEK_API_KEY + GEMINI_API_KEY."
  exit 1
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8003
fi

# Fallback: create a venv and install dependencies directly from pyproject.toml
# (editable install fails when there are multiple top-level packages).
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
if [ ! -f .venv/.campuspulse_deps_installed ]; then
  .venv/bin/python -m pip install --upgrade pip
  # Install only dependencies (not the project itself) to avoid setuptools flat-layout error
  .venv/bin/python -m pip install --no-build-isolation --no-deps -e . 2>/dev/null || true
  .venv/bin/python -m pip install $(python3 -c "
import tomllib, pathlib
d = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
print(' '.join(d['project']['dependencies']))
")
  touch .venv/.campuspulse_deps_installed
fi
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8003
