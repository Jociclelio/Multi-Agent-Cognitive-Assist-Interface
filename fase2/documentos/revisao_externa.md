# Revisão externa do pacote metodológico (rodada com três modelos)

**Data:** 2026-10-13. **Modo da rodada:** paralelo — revisão somente leitura, sem disputa de recursos compartilhados; cada revisor em sessão nova, sem acesso ao parecer dos demais.

**Alvo:** árvore atual de `fase2/` — documentos 01–11 e `auditoria_de_consistencia.md`, pesquisas `03a/03b/07a/07b` com os quatro `references_*.bib`, `fase2_metodologia.tex`, `references.bib`. Sem SHAs de commit fornecidos (entrega não versionada nesta sessão); o revisor GLM conferiu `SHA256SUMS.txt` (31/31) contra a árvore.

## ### Revisão

| Revisor | Modelo | Nota | Corretude | Decisão sugerida |
|---|---|---:|---|---|
| `task-reviewer-glm` | sd2/GLM-5.3-Flash | 8,5 | OK com ressalvas | corrigir |
| `task-reviewer-muse` | opencode/muse-spark-1.3-contributor-free | 8,5 | OK com ressalvas | fechar (com subtasks de pinagem opcionais) |
| `task-reviewer-terra` | openai/gpt-5.6-terra | 8,0 | OK com ressalvas | corrigir |

**Síntese com atribuição.** Os três confirmam: hierarquia normativa (mapas 04/8 sobre pesquisas) aplicável; honestidade documental (nenhum resultado apresentado como medido); bibliografia/LaTeX corretos (44/56 chaves, `\bibliography{references}` único, claims compatíveis com o alcance de leitura da auditoria 10); sem achado P0.

Achados convergentes (atribuição entre parênteses):

- **Drift DDL × regras normativas (P1)** — o DDL da §5 do mapa4 não reflete as decisões posteriores: `items` sem `user_id`, ausência de `domain_revision`, `artifact_dependencies`, `assessment_topics`, colunas de revisão/ocorrência em `logical_blocks`, e unicidade `(attempt_id, assessor_version)` em vez de `(attempt_id, assessment_revision)` (GLM 1–2; Terra 1 e 4). É o achado mais grave: o mapa4 se declara autocontido.
- **Metas de consultas contraditórias (P1)** — "120 consultas por partição" (etapa6/tex) versus "80 por disciplina por split" (mapa8 §12.1), com 6.000 runs calculadas sobre 120 totais; afeta custo, estratos e potência (Terra 3).
- **Gates de admissão do modelo sem critérios mensuráveis (P1)** — `MODEL_NOT_ADMITTED` sem casos/thresholds declarados (GLM 3).
- **Rota ausente para aceitação de revisão de assessment (P1)** — estado vigente exige "aceito explicitamente", mas não há intenção/contrato; W04/W10 não cobrem o caminho que o oráculo O09 exercita (GLM 4).
- **Reprodução do RAG e OCR (P1)** — motor OCR sem candidato/versão; hashes de BGE-M3/reranker não publicados; regra de dupla contagem de tokens (embedding vs Bonsai) indefinida (Muse A01–A03).
- **Baseline SA e margens (P1/P2)** — "esforço comparável" do SA não pré-registrado no freeze (risco de baseline fraco); margem de skills não declarada como quantidade própria; regra conjunta do mapa8 §9 menos operacional que a do tex (Muse A08–A09; GLM 6, 8, 9).
- **Menores (P2)** — autenticação local não especificada (Muse A05); DTSTAMP "segue RFC" impreciso (Muse A06); verificador fora do orçamento de 10 s (Muse A07); RSS/VRAM como cota inferior (Muse A10); ambiguidade "inclusive assistido" no mapa8 (GLM 5); `CanonicalSnapshot` sem schema (GLM 7); rubrica sem `topic_ids` no schema resumido do GoldRecord (Terra 2).

**Divergências.** Apenas na decisão: Muse considerou o pacote fechável com subtasks de pinagem; GLM e Terra recomendam corrigir antes de tratar os mapas como referência única. Não há contradição de fato entre os pareceres; a diferença decorre do peso dado ao drift DDL.

**Critérios pendentes legítimos (confirmados pelos três):** hardware/pins/hash do Bonsai 2, corpus autorizado e ouro humano, calibração/margens/potência via piloto, conteúdo dos prompts/skills (maior insumo de autoria ainda inexistente), conector web e sync Google, BKT em shadow, exclusão lógica (não forense).

## Decisão e encaminhamento

**Decisão: corrigir** (2 de 3 revisores; entrega preservada; sem reversão necessária — não há artefatos de implementação a desfazer). Nota final consolidada: **8,3/10** — especificação madura e honesta, penalizada por drift documental interno que pode induzir implementação divergente.

Correções delimitadas para uma subtask única de revisão documental, sem reabrir decisões de arquitetura:

1. Republicar o DDL do mapa4 §5 consolidado com §15 aplicada (user_id/ownership, `domain_revision`, `artifact_dependencies`, `assessment_topics`, unicidade `(attempt_id, assessment_revision)`, campos de `logical_blocks`).
2. Resolver a contagem de consultas (120 total ou por disciplina) em mapa8/tex/etapa6, recalculando runs e orçamento.
3. Definir gates mensuráveis do modelo; rota/contrato de aceitação de revisão de assessment; schema do `CanonicalSnapshot` e `topic_ids` no GoldRecord.
4. Nomear candidatos/pin para OCR, embeddings e reranker (ou declarar como gate de manifesto); regra de dupla contagem de tokens; orçamento do verificador fora dos 10 s.
5. Pré-registrar no freeze: esforço/orçamento de tuning do SA, margem própria do contraste reduced, regra conjunta operacional no mapa8 §9; reescritas P2 ("inclusive assistido", DTSTAMP, autenticação local, RSS/VRAM).

A rodada não gerou commit; os pareceres originais estão nas sessões `ses_eca39655effe…` (GLM), `ses_eca39655cffe…` (Muse) e `ses_eca39655affe…` (Terra).
