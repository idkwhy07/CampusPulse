#!/usr/bin/env bash
set -euo pipefail

STUDENT_URL="${CAMPUSPULSE_STUDENT_AI_URL:-http://127.0.0.1:8003}"
ADMIN_URL="${CAMPUSPULSE_ADMIN_AI_URL:-http://127.0.0.1:8001}"
ML_URL="${CAMPUSPULSE_ML_API_URL:-http://127.0.0.1:8002}"

printf '\n[1/3] Student RAG health\n'
curl -fsS "$STUDENT_URL/health" | python3 -m json.tool

printf '\n[2/3] Admin RAG health\n'
curl -fsS "$ADMIN_URL/health" | python3 -m json.tool

printf '\n[3/3] ML validation health\n'
curl -fsS "$ML_URL/health" | python3 -m json.tool

printf '\nPASS: all AI services are reachable.\n'
