#!/usr/bin/env bash
# Baixa só o modelo menor (PTQ1_0 + mmproj) do Hugging Face.
# Uso: ./runner-llm/scripts/download-models.sh  (a partir da raiz do repo)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODEL_DIR="${REPO_ROOT}/runner-llm/models/Ternary-Bonsai-2-27B-gguf"
HF_REPO="prism-ml/Ternary-Bonsai-2-27B-gguf"
FILES=(
  "Ternary-Bonsai-2-27B-PTQ1_0.gguf"
  "Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf"
)

if ! command -v hf >/dev/null 2>&1 && ! command -v huggingface-cli >/dev/null 2>&1; then
  echo "ERRO: 'hf' ou 'huggingface-cli' não encontrado." >&2
  echo "Instale com: pip install -U 'huggingface_hub[cli]'  (provê o comando 'hf')" >&2
  exit 1
fi
DL=(hf download)
command -v hf >/dev/null 2>&1 || DL=(huggingface-cli download)

mkdir -p "${MODEL_DIR}"
for f in "${FILES[@]}"; do
  if [[ -f "${MODEL_DIR}/${f}" ]]; then
    echo "OK (já existe, pulando): ${f}"
    continue
  fi
  echo "Baixando ${HF_REPO}/${f} ..."
  "${DL[@]}" "${HF_REPO}" "${f}" --local-dir "${MODEL_DIR}"
done

ls -lh "${MODEL_DIR}"
echo "Download concluído: PTQ1_0 + mmproj em ${MODEL_DIR}"
