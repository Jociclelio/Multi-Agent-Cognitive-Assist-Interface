#!/usr/bin/env bash
# Smoke test do servidor em http://localhost:8079 (Docker ou nativo).
# Checa /health, /v1/models e faz 1 completion curta. Não usa llama-cli
# (o spinner dele polui stdout com GBs de '\r'; nunca capture na íntegra).
# Uso: ./runner-llm/scripts/smoke-test.sh
set -euo pipefail

BASE="${LLAMA_CPP_BASE_URL:-http://localhost:8079/v1}"
HOST="${BASE%/v1}"
MODEL="${LLAMA_CPP_MODEL:-bonsai2-pq2-0}"

echo "== /health =="
curl -sf "${HOST}/health" && echo

echo "== /v1/models =="
curl -sf "${BASE}/models" | head -c 2000; echo

echo "== 1 completion curta (${MODEL}) =="
curl -sf --max-time 120 "${BASE}/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Responda só: ok\"}],\"max_tokens\":64,\"temperature\":1.0,\"top_p\":0.95,\"top_k\":20}" \
  | head -c 2000; echo

echo "SMOKE OK"
