# Task 002: Manifesto/hardware e gate de modelo Bonsai 2 (mapa §3.1, §13.1)

Estado: aguardando revisão
Depende de: 001
Origem: nenhuma

## Prompt
Implementar o gate de modelo do mapa §3.1 e §13.1: candidato `prism-ml/Ternary-Bonsai-2-27B-gguf`, revisão `b072e1d3b35a0a630cece372c2127528e0994386`, arquivo inicial `Ternary-Bonsai-2-27B-PTQ1_0.gguf`, SHA publicado `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3`. Conferir SHA local, licença e NOTICE. Runtime obrigatório: fork `PrismML-Eng/llama.cpp`, release candidata `prism-b10743-adfffbe`, capacidade verificada e fixada por hash (não presumir compatibilidade do stock llama.cpp). Implementar o adaptador `generate(messages, schema, sampler, deadline, seed) -> GenerationResult` (texto final, contagens, finish_reason, erro tipado; pensamento não é fonte de evidência) e servidor loopback com um slot e fila de quatro pedidos. Rodar os gates de aceite: carregamento offline, tokenizer, JSON e ferramentas negadas; primeiro modo non-thinking com sampling `.7/.8/20/min_p=0`; comparar thinking `1/.95/20/.05` apenas em desenvolvimento. JSON schema solicitado somente se o fork suportar; parse/schema/política permanecem obrigatórios. Se o candidato não carregar ou falhar gates: marcar `MODEL_NOT_ADMITTED`, sem substituição silenciosa. Registrar versões reais (pacotes, modelo, tokenizer) em `manifest.json` e atualizar `uv.lock`.

Se o download/carregamento for inviável no hardware local (tamanho, VRAM/RSS), registrar o impedimento documentado com os passos reproduzíveis e o estado do gate como pendente de hardware — não fingir sucesso nem trocar de modelo.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §3.1 (modelo) e §13.1 (primeira etapa da sequência com gate próprio).
- `config/default.yaml` (task 001) — limites de janela e timeouts usados nos gates.

## Corretude
- [x] C1 — Adaptador `generate` implementado com a assinatura do mapa e erro tipado; servidor loopback com um slot e fila de quatro; nenhum acesso à rede além do download pinado.
- [x] C2 — Gates executados com evidência registrada (comandos, saída, SHA conferido); resultado `MODEL_ADMITTED` com perfil non-thinking (ou `MODEL_NOT_ADMITTED`/pendente de hardware documentado, sem substituição).
- [x] C3 — `manifest.json` registra versões reais de pacotes, modelo, tokenizer e hash do runtime; `uv.lock` atualizado.
- [x] C4 — Mapa intocado; commits de entrega e registro separados; temporários em `/tmp/opencode`; submódulo não tocado.

## Execução
- Modelo: GLM-5.3-Flash (via ~/sd2-llm.sh; provider `sd2`, model id `GLM-5.3-Flash`)
- Base: fca2ad0b95c1f10e6ea61e5681ed54fd6c66c056 (árvore limpa)
- Entrega: dfe18a97e12d8a3476d143d3fc121ab68929633a (commit de entrega único; código + manifest)
- Arquivos da entrega: `eduagent/services/model_adapter.py` (adaptador `generate` + erros tipados + `LoopbackGenerationServer` 1 slot/fila 4), `tests/gates/task002_gate_modelo.py` (gate de aceite G1–G8 + T1 opcional), `manifest.json` (versões reais). `uv.lock` INALTERADO: nenhuma dependência nova (adaptador usa só stdlib; `uv lock --check` → "Resolved 168 packages"); sem `uv.lock` novo, nada a atualizar.
- Evidências:
  - **Gate (C2)**: `python tests/gates/task002_gate_modelo.py --base-url http://127.0.0.1:8093/v1 --model bonsai2-ptq1-0 --gguf runner-llm/models/.../Ternary-Bonsai-2-27B-PTQ1_0.gguf --seed 0 --deadline-s 600 --out /tmp/opencode/task002/gate_report.json` → **VEREDITO: MODEL_ADMITTED, 8/8 checks PASS** (relatório completo em `/tmp/opencode/task002/gate_report.json`, não versionado):
    - G1 carregamento offline loopback (health ok, modelo servido); G2 SHA-256 do GGUF conferido = `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` (idêntico ao publicado); G3 `/tokenize`+`/detokenize` idempotentes (28 tokens, round-trip exato); G4 non-thinking `.7/.8/20/min_p=0` (presence 1.5/repeat 1.0 do perfil instruct): finish_reason `stop`, 39 prompt/49 completion tokens, texto final coerente, thinking separado do texto; G5 JSON schema conforme (resposta válida, campos/enum corretos); G6 ferramentas negadas → `TOOL_DENIED`; G7 deadline 0 → `TIMEOUT`; G8 um slot + fila de 4: 5 pedidos aceitos, 6º recusado com `RESOURCE_LIMIT`.
    - Runtime do gate: container efêmero `eduagent-gate-002` (imagem `llama.cpp-prismml:latest`, image ID `sha256:d88136167019e9dfa08e53fd9d962982ce6043f5d3b668bab59acd5f863a6991`) com o GGUF montado read-only, `--jinja -np 1 -c 8192 -t 6 -s 42 --alias bonsai2-ptq1-0`, **CPU-only (`-ngl 0`)** — a GPU (RTX 3060 12 GiB) estava ocupada por processo do usuário alheio à task (~11 GiB), sem autorização para interferir; o suporte CPU ao PTQ1_0 é justamente o commit da tag candidata (`adfffbe41`: "x86: SSE2/SSSE3 vec_dot for PTQ1_0"). Container encerrado e removido após o gate.
    - Licença/NOTICE (mapa §3.1): LICENSE = Apache-2.0; NOTICE.txt = "copyright 2026-present Prism ML, Inc., Apache 2.0; construído a partir de Qwen3.8-27B, Copyright 2026 Alibaba Cloud, Apache 2.0" (arquivos da revisão baixados em `/tmp/opencode/task002/`).
  - **Runtime fixado por hash (mapa §3.1)**: tag candidata `prism-b10743-adfffbe` → commit `adfffbe41b2cabcd51fff326ab045662265062bb` (confirmado via `git ls-remote --tags` do fork e no clone local `runner-llm/third_party/llama.cpp`); binário executado no gate: commit `84445367f` (`--version`: "0.2.0-dev (build 1, commit 8444536)"; `/props` build_info `b1-8444536`), descendente DIRETO de `adfffbe41` no branch `prism` (distância 1 commit; `git merge-base --is-ancestor` verificado) — diferença: kernel SYCL oneDNN, sem impacto no caminho CUDA/CPU usado. Stock llama.cpp não presumido: model card confirma que PTQ1_0 exige o fork.
  - **manifest.json (C3)**: registrado com versões reais — modelo (repo/revisão/arquivo/SHA256/licença/NOTICE), tokenizer (n_vocab 248320, n_ctx_train 262144, n_embd 5120, BOS `<s>`, EOS `<|im_end|>`, verificado no G3), runtime (fork, tag candidata + commit, binário 84445367f, image ID, fixação por hash), capacidades (json_schema verificada no G5; ferramentas negadas por política apesar de `supports_tools=true` do template — gate G6), `perfil_admitido_no_gate_002` (non-thinking `.7/.8/20/min_p=0` + presence 1.5/repeat 1.0, rotulado como default de ensaio), perfil thinking `1/.95/20/.05` marcado como SOMENTE comparativo em desenvolvimento, pacotes reais (langgraph 1.2.16, pydantic 2.14.1, docling 2.141.0, torch 2.14.1+cpu, etc., Python 3.12.13, sqlite3 stdlib 3.53.1), referência ao relatório do gate e pendências.
  - **Comparativo thinking NÃO executado** (T1 opcional): orçamento de tokens de pensamento inviável na execução CPU do gate; registrado como pendência de desenvolvimento no manifest.json — não bloqueia a admissão (mapa §3.1: non-thinking primeiro, thinking só comparativo).
  - **Intocabilidade (C4)**: `fase2/documentos/04_mapa_completo_do_sistema.md`, plano 04 e submodule `docs/playground-llmagenticsystem` sem qualquer alteração (`git status` limpo entre commits); temporários exclusivamente em `/tmp/opencode/task002/`.

## Notas

### Dificuldade esperada
6/10 — Dependência de runtime externo (fork), download grande e gates de hardware; risco de inviabilidade local deve virar bloqueio documentado, não improviso.

### Dificuldade sentida
6/10 — O risco principal era hardware, não código: a GPU estava ocupada por processo do usuário, mas o gate seguiu viável em CPU (`-ngl 0`), sustentado pelo commit exato da tag candidata que introduz kernels CPU para PTQ1_0 — exigiu verificação de ancestralidade de commits do fork (tag candidata `prism-b10743-adfffbe` vs binário `84445367f` disponível) para não presumir compatibilidade. A lentidão da CPU (≈1,6 s/token) forçou duas rodadas de depuração do próprio gate (rota `/tokenize` fora do prefixo `/v1`; condição de admissão da fila que permitia estouro antes do worker acordar) e reexecuções de ~5 min cada; `max_tokens` e deadline dos gates foram reduzidos como orçamento de ensaio, documentados no manifest sem alterar os defaults do sistema. Nenhuma substituição de modelo, nenhum resultado apresentado como medido.

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
