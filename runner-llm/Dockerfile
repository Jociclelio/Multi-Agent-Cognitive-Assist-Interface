# syntax=docker/dockerfile:1
# Runner Bonsai 2: compila o fork PrismML-Eng/llama.cpp (branch prism, pinado)
# com CUDA e serve o preset models/models.ini na porta 8079.
# Pesos (*.gguf) NÃO são copiados: monte ./models em /app/models.
#
# ATENÇÃO: nunca trocar a base por llama.cpp upstream stock — o Bonsai 2
# precisa dos kernels ternários + runtime Hadamard do fork.

ARG CUDA_VERSION=13.4.0
ARG UBUNTU_VERSION=24.04
ARG LLAMA_CPP_REV=adfffbe41
ARG BASE_BUILD=docker.io/nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION}
ARG BASE_RUN=docker.io/nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

FROM ${BASE_BUILD} AS build
ARG LLAMA_CPP_REV
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git cmake build-essential libcurl4-openssl-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --branch prism --single-branch --depth 1 \
        https://github.com/PrismML-Eng/llama.cpp llama.cpp \
    && git -C llama.cpp fetch --depth 1 origin ${LLAMA_CPP_REV} \
    && git -C llama.cpp checkout ${LLAMA_CPP_REV} \
    && git -C llama.cpp rev-parse --short HEAD
WORKDIR /src/llama.cpp
RUN cmake -B build -DGGML_NATIVE=OFF -DGGML_CUDA=ON -DGGML_BACKEND_DL=ON \
        -DLLAMA_BUILD_TESTS=OFF -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --config Release -j"$(nproc)" \
        --target llama-server llama-cli
RUN mkdir -p /opt/runner/lib /opt/runner/bin \
    && cp -P build/bin/*.so* /opt/runner/lib/ 2>/dev/null || true \
    && cp build/bin/llama-server build/bin/llama-cli /opt/runner/bin/ \
    && /opt/runner/bin/llama-server --version

FROM ${BASE_RUN} AS run
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl libcurl4 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /opt/runner/bin/llama-server /opt/runner/bin/llama-cli /usr/local/bin/
COPY --from=build /opt/runner/lib/ /usr/local/lib/
RUN ldconfig
WORKDIR /app
COPY models/models.ini ./models/models.ini
# Diretório para o volume de pesos: models/Ternary-Bonsai-2-27B-gguf/*.gguf
VOLUME /app/models
EXPOSE 8079
ENV LD_LIBRARY_PATH=/usr/local/lib
ENTRYPOINT ["llama-server", "-s", "42", "--verbosity", "3", \
    "--models-preset", "models/models.ini", "--models-max", "1", \
    "--host", "0.0.0.0", "--port", "8079"]
