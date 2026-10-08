#!/usr/bin/env bash
# Build nativo do fork PrismML-Eng/llama.cpp com CUDA.
# Clona em runner-llm/third_party/llama.cpp (ignorado no git) e compila
# llama-server + llama-cli. Uso: ./runner-llm/scripts/build-native.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="${REPO_ROOT}/runner-llm/third_party/llama.cpp"
# Pin: release prism-b10743-adfffbe da origem. Sobrescreva com LLAMA_CPP_REV=<sha>.
REV="${LLAMA_CPP_REV:-adfffbe41}"
JOBS="${JOBS:-$(nproc)}"

for cmd in git cmake g++ nvcc; do
  command -v "${cmd}" >/dev/null 2>&1 || { echo "ERRO: '${cmd}' não encontrado no PATH." >&2; exit 1; }
done

if [[ ! -d "${SRC_DIR}/.git" ]]; then
  mkdir -p "$(dirname "${SRC_DIR}")"
  git clone --branch prism --single-branch \
    https://github.com/PrismML-Eng/llama.cpp "${SRC_DIR}"
fi
git -C "${SRC_DIR}" fetch origin
git -C "${SRC_DIR}" checkout "${REV}"

if [[ ! -f "${SRC_DIR}/build/CMakeCache.txt" ]]; then
  cmake -S "${SRC_DIR}" -B "${SRC_DIR}/build" \
    -DGGML_CUDA=ON -DLLAMA_BUILD_TESTS=OFF -DCMAKE_BUILD_TYPE=Release
fi
# Reaproveita o build/ existente (CUDA já configurado); evita reconfigurar.
cmake --build "${SRC_DIR}/build" -j"${JOBS}" --target llama-server llama-cli
"${SRC_DIR}/build/bin/llama-server" --version
echo "Build OK: ${SRC_DIR}/build/bin/llama-server"
