# runner-llm — inferência local Bonsai 2 (fork PrismML llama.cpp)

Runner de inferência local do EduAgent-OS: fork `PrismML-Eng/llama.cpp`
(CUDA) + Bonsai 2 GGUF, servido via `llama-server` em modo router
(`--models-preset`), porta `8079`, compatível com `LLAMA_CPP_BASE_URL`
dos notebooks.

> Espelho versionável do setup em `/home/jocic/bonsai-llm` (não versionado).
> Pesos (`*.gguf`), fonte e `build/` do `llama.cpp` **não** vão para o git.

## Layout

```text
runner-llm/
├── Dockerfile               # build do fork (CUDA) + runtime do llama-server
├── docker-compose.yml       # serviço llm: GPU, porta 8079, volume ./models
├── .dockerignore
├── models/
│   ├── models.ini           # preset: só o modelo menor (PTQ1_0 + mmproj)
│   └── .gitkeep             # pesos baixados via script (ignorados no git)
└── scripts/
    ├── download-models.sh   # hf download (só PTQ1_0 + mmproj)
    ├── build-native.sh      # clone pinado do fork + build CUDA nativo
    ├── run-native.sh        # llama-server nativo (equivale ao start.sh)
    └── smoke-test.sh        # health + 1 completion curta no servidor
```

## Restrições duras (herdadas da origem)

- **Nunca trocar o fork por upstream stock.** O Bonsai 2 precisa dos kernels
  ternários + runtime Hadamard do fork: o stock recusa `PTQ1_0` ou gera lixo.
  Fork: `https://github.com/PrismML-Eng/llama.cpp`, branch `prism`,
  pin `adfffbe41` (`prism-b10743-adfffbe`; sobrescreva com `LLAMA_CPP_REV`).
- Sampling (`temp 1.0, top_p 0.95, top_k 20`) vive no metadado do GGUF —
  não duplicar no `models.ini`.
- Servidor sempre em `8079` (contrato com notebooks e `.env.example`).
  A porta `8082` citada no `AGENTS.md` da origem está obsoleta.
- Modelo servido: **só o menor**, `PTQ1_0` (5,6 GB) + `mmproj-Q8_0`
  (601 MB). O `PQ2_0`/`MTP` da origem foi descartado neste recorte.
  Alias `bonsai2-pq2-0` mantido no preset para compatibilidade com
  `LLAMA_CPP_MODEL` dos notebooks.

## Uso rápido — Docker

```bash
./scripts/download-models.sh
docker compose -f runner-llm/docker-compose.yml up --build
# ou: docker build -t eduagent-llm runner-llm
#     docker run --gpus all -p 8079:8079 -v ./runner-llm/models:/app/models eduagent-llm
./runner-llm/scripts/smoke-test.sh
```

Pré-requisitos: Docker + NVIDIA Container Toolkit, driver com CUDA ≥ 13.4
(RTX 3060 12 GB testada). Imagem de build: `nvidia/cuda:13.4.0-devel-ubuntu24.04`.

## Uso nativo (host com CUDA)

```bash
./runner-llm/scripts/download-models.sh
./runner-llm/scripts/build-native.sh     # clone em runner-llm/third_party/llama.cpp + cmake -DGGML_CUDA=ON
./runner-llm/scripts/run-native.sh       # serve em 0.0.0.0:8079
```

Requer `nvcc` (ex. `/opt/cuda/bin/nvcc`), `cmake`, `g++`, `git`.
Binários em `runner-llm/third_party/llama.cpp/build/bin/`.

## Smoke test

`scripts/smoke-test.sh` espera o servidor em `http://localhost:8079`,
checa `/health` e `/v1/models` e faz **uma** completion curta
(`max_tokens=64`, timeout 120 s). Não captura spinner do `llama-cli`.

## Referências

- Origem: `/home/jocic/bonsai-llm/{AGENTS.md,start.sh,models/models.ini}`.
- Pesos: `prism-ml/Ternary-Bonsai-2-27B-gguf` no Hugging Face.
- Contrato cliente: `LLAMA_CPP_BASE_URL=http://localhost:8079/v1`,
  `LLAMA_CPP_MODEL=bonsai2-pq2-0` (`.env.example` e notebooks).
