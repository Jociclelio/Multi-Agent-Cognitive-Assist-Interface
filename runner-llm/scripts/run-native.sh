#!/usr/bin/env bash
# Serve o runner nativo (equivale ao start.sh da origem).
# Uso: ./runner-llm/scripts/run-native.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER_DIR="${REPO_ROOT}/runner-llm"
BIN="${RUNNER_DIR}/third_party/llama.cpp/build/bin/llama-server"
PORT="${PORT:-8079}"

[[ -x "${BIN}" ]] || { echo "ERRO: binário não encontrado: ${BIN}. Rode build-native.sh antes." >&2; exit 1; }
[[ -f "${RUNNER_DIR}/models/Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PTQ1_0.gguf" ]] \
  || echo "AVISO: pesos ausentes — rode download-models.sh antes." >&2

cd "${RUNNER_DIR}"
exec "${BIN}" -s 42 --verbosity 3 \
  --models-preset models/models.ini --models-max 1 \
  --host 0.0.0.0 --port "${PORT}"
