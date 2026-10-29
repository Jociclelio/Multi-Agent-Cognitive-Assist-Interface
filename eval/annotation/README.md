# Anotação, ouro e congelamento — estado registrado (task 003 do plano 06)

Data: 2026-10-29. Esta pasta registra o estado da anotação da seção 2 do
protocolo de avaliação (`fase2/documentos/06_protocolo_de_avaliacao.md`).
**Nada nesta pasta é resultado medido**; contagens e procedimentos são insumo
de preparação, e ausências são declaradas como ausências.

## O que existe (insumo produzido na task 003)

| Insumo | Local | Estado |
|---|---|---|
| 19 famílias documentais derivadas do corpus depositado (uma por material, tipo documento-base), com splits atribuídos por parentesco (6 dev / 3 val / 10 test) e auditoria de duplicatas/parentesco `passed` | `../datasets/familias/registro-familias.json`; atribuição em `../datasets/splits.json` | completo dentro dos mínimos da D4 com a emenda E1 (19 ≥ 18; dev 6 ≥ 6; val 3 ≥ 3; test 10 ≥ 9; ≥5 por disciplina; scans/tabelas 0 são suplementos opcionais — ausência registrada) |
| Rubricas 0–4 para saídas semênticas (O04, O07, O08) e anotação categórica de níveis de ajuda em tentativas | `rubricas-v0.1-rascunho.md` | **rascunho v0.1 — piloto não executado** (ver ausência 1) |

## Ausências registradas (nada simulado, nada fabricado)

1. **Piloto de rubricas no split de desenvolvimento — não executado.** O piloto
   exige anotação real no split de desenvolvimento com dois avaliadores
   independentes cegos à arquitetura e à condição. Avaliadores humanos
   independentes não estavam disponíveis nesta sessão e **anotadores cegos
   inexistentes não são simulados**; por isso nenhuma rubrica foi "testada" e
   nenhum ajuste de rubrica foi registrado. As rubricas permanecem rascunho
   (`v0.1-rascunho`) e não podem ser usadas no teste antes do piloto.
2. **Dois avaliadores independentes, adjudicação e kappa — não produzidos.** A
   anotação com dois julgamentos independentes, o acordo (kappa) e a
   adjudicação de discordâncias dependem dos mesmos avaliadores humanos. Sem
   eles, nenhum kappa, nenhuma adjudicação e nenhum número de acordo existe —
   qualquer valor seria invenção.
3. **Ouro (GoldRecord) — nenhum item produzido.** Por decisão D5 da task 001,
   humanos são ouro de conteúdo: o juiz LLM nunca gera ouro e o ouro nunca
   deriva de saída do sistema avaliado. Sem avaliadores humanos, nenhum
   `GoldRecord` com IDs de fonte/claim, critérios/erros, fatos temporais e
   restrições originais foi criado. A forma do registro a adotar está
   especificada no mapa 08, §3.2 (`gold_id, version, authored_by,
   adjudication_ref, original_refs, critical_facts, entities, relations,
   qrels, required_claims, accepted_answers, criterion_labels,
   misconception_codes, temporal_ledger, constraints_original, ...`; campos
   não aplicáveis ausentes, não arrays vazios).
4. **Congelamento do split de teste — não realizado.** A auditoria de
   duplicatas/parentesco que precede o congelamento (mapa 08, §4) foi
   executada sobre as famílias documentais com resultado `passed`
   (`../datasets/familias/registro-familias.json`,
   `auditoria_parentesco.resultado = "passed"`), mas o split de teste está
   **incompleto**: consultas, tentativas, trajetórias e casos de falha F01–F24
   seguem sem itens (ausências registradas em
   `../datasets/contagens-vs-metas.md`). Congelar agora um conjunto parcial
   forçaria a reabertura do manifesto quando os itens pendentes ingressarem;
   o congelamento ocorrerá com o conjunto de teste completo, **antes de
   qualquer ajuste do sistema sobre ele** (a execução experimental pertence à
   etapa 8), registrando hashes dos arquivos congelados, acessos e data, como
   exige o protocolo (seção 2).

## O que é pendência de avaliadores humanos (para a retomada)

Para executar o que falta, a sessão de retomada precisa de:

1. **Dois avaliadores humanos independentes**, cegos à arquitetura (MA/SA/ablações)
   e à condição, com pseudônimos de avaliador (`evaluator_id_pseudonym`) e
   mapa `blind_artifact_id → run` oculto aos anotadores (mapa 08, §3.4 e §9:
   "Exportar pacotes cegos de artefato, pergunta, fontes e rubrica sem nome de
   condição, trace de identidade ou resposta do Monitor").
2. **Piloto em dev**: aplicar `rubricas-v0.1-rascunho.md` a uma amostra do
   split de desenvolvimento, medir acordo, registrar ajustes de rubrica com
   incremento de versão antes de qualquer uso no teste (protocolo, seção 2).
3. **Adjudicação e kappa** por dimensão/critério após dois julgamentos
   independentes; terceiro/adjudicador nos discordâncias (mapa 08, §4).
4. **Ouro humano** por item, com IDs de fonte/claim, critérios/erros, fatos
   temporais e restrições originais — nunca respostas do sistema avaliado
   (protocolo, seção 2; decisão D5).
5. **Autoria dos itens pendentes** (consultas com/sem suporte, tentativas,
   trajetórias, casos de falha) conforme os procedimentos de coleta em
   `../datasets/*/manifesto.json`, respeitando a regra de parentesco de
   `../datasets/splits.json`.
6. **Congelamento do teste** com hashes dos arquivos congelados, acessos e
   data; pino do juiz LLM (modelo/revisão, prompt, hash, política de
   abstinência) registrado no congelamento da validação, conforme decisão D5
   da task 001 e mapa 08, §9 ("modelo/prompt/hash separados") — sem trocar
   juiz depois de olhar teste.

## Limites de escopo desta pasta

- IDs O01–O18 e F01–F24 são permanentes (origem:
  `fase2/documentos/05_fluxos_resultados_e_falhas.md`); nada é renumerado.
- Os thresholds da seção 3 do protocolo não são alterados por esta pasta; as
  rubricas são instrumentos de anotação, não gates novos.
- Mecanismos de anotação/juíz por célula pertencem à etapa 7 e a
  implementação à etapa 8 (planos 07 e 08); aqui existem apenas o desenho e
  os insumos documentados acima.
