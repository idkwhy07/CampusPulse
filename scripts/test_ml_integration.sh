#!/usr/bin/env bash
set -euo pipefail

ML_URL="${CAMPUSPULSE_ML_API_URL:-http://127.0.0.1:8002}"
GO_URL="${CAMPUSPULSE_GO_URL:-http://127.0.0.1:8080}"

printf '\n[1/4] ML health\n'
curl -fsS "$ML_URL/health" | python3 -m json.tool

printf '\n[2/4] Direct ML prediction\n'
curl -fsS -X POST "$ML_URL/predict" \
  -H 'Content-Type: application/json' \
  -d '{"Type":"Mạng / Đường truyền","Describe":"wifi tầng 4 bắt được mà load mãi không xong"}' \
  | python3 -m json.tool

printf '\n[3/4] Go -> ML health proxy\n'
curl -fsS "$GO_URL/api/ai/health" | python3 -m json.tool

printf '\n[4/4] Integration endpoints are ready\n'
echo "PASS: ML API and Go ML client are reachable."
