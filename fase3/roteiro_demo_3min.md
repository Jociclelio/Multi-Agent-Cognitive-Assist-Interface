# Roteiro de Demonstração em Vídeo (Máx. 3 Minutos) — Fase 3 (EduAgent-OS v0.1)

> **Disciplina:** MO810A/MC959A — Sistemas Multiagentes com Modelos de Linguagem (IC/UNICAMP — 2026)  
> **Dupla:** Rafael Attilio Agricola (`RA 249245`) e Jociclelio Castro Macedo Junior (`RA 231722`)  
> **Duração máxima obrigatória:** **3 minutos (180 segundos)**  
> **Objetivo do vídeo:** Demonstrar a execução completa ponta a ponta da solução **EduAgent-OS v0.1**, explicando brevemente cada passo e evidenciando a interação coordenada entre os **5 agentes** (**Curador**, **Bibliotecário**, **Tutor**, **Monitor** e **Planejador**), o grafo `EduAgentGraph`, o uso de ferramentas determinísticas (`Docling`, `BM25 + BGE-M3 + RRF`, `CP-SAT`, `icalendar`) e o banco bitemporal `SQLite WAL`.

---

## 1. Preparação Rápida Antes de Iniciar a Gravação (Fora do Tempo do Vídeo)

Deixe dois terminais abertos na raiz do repositório e o navegador posicionado em `http://127.0.0.1:8094`:

```bash
# Terminal 1 — Runtime local do LLM (Bonsai 2 27B PTQ1_0 em 127.0.0.1:8079)
# Caso utilize o container local registrado no manifest.json:
docker start eduagent-llm-prism || \
  ./runner-llm/build/bin/llama-server \
    -m runner-llm/models/Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PTQ1_0.gguf \
    --host 127.0.0.1 --port 8079 -np 1 -c 32768 --alias bonsai2-ptq1-0

# Terminal 2 — Preparar o estado inicial do ensaio (passo 0) e subir a Interface Gráfica Local
uv run python eval/ensaio_longitudinal.py --root /tmp/opencode/demo_fase3 --step setup
uv run eduagent --serve-ui --data-root /tmp/opencode/demo_fase3/data --port 8094 --open-browser
```

*(Alternativa 100% terminal: você também pode demonstrar a execução passo a passo de `eval/ensaio_longitudinal.py` ao lado da Interface Gráfica Local aberta em `http://127.0.0.1:8094`).*

---

## 2. Cronograma Minuto a Minuto da Gravação (0:00 a 3:00)

### Bloco 1 (`0:00 – 0:30` | 30 s) — Arquitetura em Operação, Diagnóstico e Gates (`W12`)
- **Na tela:** Mostrar rapidamente o painel **Configurações / Diagnóstico** na Web UI (`http://127.0.0.1:8094`) ou a saída de `uv run eduagent --data-root /tmp/opencode/demo_fase3/data doctor`.
- **O que destacar na fala:**
  - Apresentar o **EduAgent-OS v0.1**, sistema multiagente 100% local orquestrado em `LangGraph` com 5 agentes (**Curador**, **Bibliotecário**, **Tutor**, **Monitor** e **Planejador**) sobre `SQLite WAL` (`domain.sqlite` e `checkpoints.sqlite`).
  - Mostrar os gates ativos: modelo local `Ternary-Bonsai-2-27B-PTQ1_0` admitido (`MODEL_ADMITTED`), fuso horário IANA detectado automaticamente (`America/Sao_Paulo`), soberania offline (`network_enabled: false`, `CONNECTOR_DISABLED`).

### Bloco 2 (`0:30 – 1:10` | 40 s) — Agente Curador: Ingestão Documental, RAG Híbrido e Gate de Fato Ambíguo (`W01`)
- **Na tela:** Na visão **Biblioteca**, criar/selecionar a disciplina `MO810 — Sistemas Multiagentes` e enviar o documento de aula (ou executar o passo `ingest`), abrindo em seguida a aba **Operações**.
- **O que destacar na fala:**
  - O **Curador** invoca a ferramenta `Docling` em subprocesso isolado (`spawn`, teto de `4 GiB`), extrai blocos com página/ordem lógica, gera chunks e publica o índice híbrido lexical (`BM25`) + denso (`BAAI/bge-m3`, fusão `RRF k=60`).
  - Quando encontra uma data ou prazo ambíguo no documento, o grafo **não promove o fato silenciosamente**: pausa em `waiting_user` (`interrupt`). Confirmamos o fato na fila de **Operações** (`/turns/{id}/resume`) e a versão documental passa para `active`, habilitando o selo verde **"Pronta para estudar"**.

### Bloco 3 (`1:10 – 1:55` | 45 s) — Agente Bibliotecário + Agente Tutor: Consulta Fundamentada e Escada Socrática (`W02`, `W03`, `W05`)
- **Na tela:** No painel central da disciplina, executar uma pergunta (`/ask`) e iniciar um exercício (`/practice`), clicar em **Pedir Pista (`L1 -> L2`)** e abrir a **Gaveta Direita de Evidências**.
- **O que destacar na fala:**
  - Antes do Tutor agir, o **Bibliotecário** monta o `MemoryPack` bitemporal (`occurred_at` vs. `recorded_at`, teto de `2.048` tokens) e o Curador entrega o `EvidencePack` do mesmo `domain_revision`.
  - O **Tutor** seleciona dinamicamente a *skill* YAML (`explain`, `quiz`, `graduated_hint`), publica o `LearningItem` com gabarito e rubrica desacoplados no banco e encerra o turno em `waiting_student`.
  - Nas pistas `L1` e `L2`, a barreira socrática sanitiza `expected_answer: null`, impedindo vazamento do gabarito antes de `L3` ou `revealed=true`, enquanto a gaveta lateral exibe os chunks e citações canônicas `[doc_id@versao:pagina:bloco]`.

### Bloco 4 (`1:55 – 2:25` | 30 s) — Agente Monitor + Redutor Determinístico de Competência (`W04`)
- **Na tela:** Submeter a resposta do estudante (`/submit` com a explicação sobre deduplicação por `operation_id`) e alternar para a visão **Progresso**.
- **O que destacar na fala:**
  - O **Monitor** avalia a submissão contra a rubrica analítica (níveis `0`, `1`, `2`) ancorada em *spans* literais da resposta do aluno (ou abstém com `FORMAL_DIVERGENCE` se houver inconsistência formal).
  - O redutor determinístico atualiza o estado qualitativo do tópico (`insufficient -> mixed -> favorable` após 3 acertos independentes em famílias distintas), mantendo `estimate = null` (sem porcentagem numérica não calibrada) e gerando demandas de revisão (`assessment_review_policy_v1`).

### Bloco 5 (`2:25 – 3:00` | 35 s) — Agente Planejador + Solver CP-SAT + Exportação `.ics` e Resiliência (`W06`, `W08`, `W11`)
- **Na tela:** Acionar **Gerar Plano (`/plan`)**, aprovar o preview na fila de **Operações**, baixar o arquivo `.ics` na visão **Calendário**, mostrar o **Timer Pomodoro *fail-closed*** no topo e exibir um trace em `trace --last`.
- **O que destacar na fala:**
  - O **Planejador** converte as demandas formativas e prazos confirmados em um modelo de programação por restrições resolvido pelo **CP-SAT (Google OR-Tools)** em slots de 15 minutos e 5 estágios lexicográficos.
  - Um **verificador independente em minutos contínuos** valida ausência de sobreposição antes de abrir o gate de aprovação humana (`waiting_approval`).
  - Após aprovação (com recibo idempotente por `operation_id`), o serviço exporta o arquivo iCalendar **RFC 5545 (`.ics`)** com `UID` estável, e o **Timer Pomodoro** sincroniza com o bloco planejado sem nunca concluir a atividade automaticamente sem confirmação explícita do estudante.

---

## 3. Comandos Rápidos de CLI (Caso Queira Mostrar o Terminal em Paralelo)

```bash
# 1. Diagnóstico do sistema e admissão de gates
uv run eduagent --data-root /tmp/opencode/demo_fase3/data doctor

# 2. Executar ou inspecionar o ensaio longitudinal completo (passos 0 a 15)
uv run python eval/ensaio_longitudinal.py \
  --root /tmp/opencode/demo_fase3 \
  --model-url http://127.0.0.1:8079/v1 \
  --model-id bonsai2-ptq1-0 \
  --embedder-dir runner-llm/models/bge-m3 \
  --step all

# 3. Consultar o último trace OpenTelemetry local gravado
uv run eduagent --data-root /tmp/opencode/demo_fase3/data trace --last
```

