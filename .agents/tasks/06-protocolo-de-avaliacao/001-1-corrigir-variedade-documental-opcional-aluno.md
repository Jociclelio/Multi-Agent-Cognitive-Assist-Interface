# Task 001-1: Emendar a D4 — materiais suplementares opcionais e registro do novo depósito

Estado: pendente
Depende de: 001
Origem: 001 (correção — decisão do usuário de 2026-10-29: professores não costumam fornecer scans, resoluções de exercícios nem notas de monitoria; o sistema não pode depender desses materiais)

## Prompt
Emendar a decisão D4 da task 001 e alinhar o protocolo e os registros ao princípio decidido pelo usuário: **scans, tabelas como material, versões conflitantes, resoluções de exercícios e notas de monitoria são materiais suplementares OPCIONAIS, fornecidos pelo aluno quando existirem — o corpus autorizado é construído com o que os professores de fato disponibilizam (PDFs digitais, notas de aula, listas, PDDs) e não depende dos suplementos.** Delimitadamente: (1) registrar na task 001, como emenda datada e justificativa do usuário, a alteração da D4 — os mínimos "≥2 scans e ≥2 tabelas" deixam de ser bloqueio e passam a ser condicionais à disponibilidade/autorização real, com ausência registrada como ausência; preservar o texto original da D4 intacto (a emenda é acréscimo, nunca reescrita que simule que sempre foi assim); registrar também que a falha F01 (rotação/scan ruidoso) permanece testável por perturbação sintética na etapa 8, sem exigir scans reais no corpus (a implementação do mecanismo é da etapa 8 e fica fora deste escopo — apenas a nota normativa da emenda); (2) ajustar em dif mínimo com justificativa no commit a linha 11 de `fase2/documentos/06_protocolo_de_avaliacao.md` ("Incluir PDFs digitais, scans, tabelas e versões conflitantes.") para refletir que scans, tabelas e versões conflitantes são suplementos opcionais, incluídos quando disponíveis e autorizados, e que sua ausência é registrada como ausência e não bloqueia a avaliação — sem tocar nenhuma outra seção nem os documentos 04, 05, 07 e 08; (3) estender `eval/corpus/registro-materiais.json` com o registro por material dos depósitos de 2026-10-29 (tarde), todos fora do Git: 8 PDFs de Redes baixados do Google Classroom da turma G_MC832A_2026S2 (Chapter_1 a Chapter_6 v9.0 e ListaExercicio1/2, fonte: Classroom, aba Atividades/Material, conta j231722@dac.unicamp.br, modelo de uso privado sem redistribuição da D2) e 9 notas de aula em HTML de MC847 (aula01–aula09, fonte pública `https://www.ic.unicamp.br/mraimundo/teaching/unsupervised-learning/aulaNN/notas.html`), cada um com fonte, tipo, SHA-256 conferido contra o arquivo depositado, vínculo de versão e autorização; registrar que o PDD do Classroom é byte a byte idêntico ao `mat-redes-001` já registrado (hash `d9c2355f…`) e por isso não constitui versão conflitante nem novo material; (4) atualizar `eval/datasets/contagens-vs-metas.md`: contagens reais dos materiais depositados (19 no total), a nova regra da D4 emendada para scans/tabelas/versões conflitantes (condicionais, ausência como ausência) e a consequência de que a precondition de famílias deriváveis da task 003 deixa de depender dos suplementos; nada apresentado como resultado medido.

Restrições: a emenda é decisão do usuário registrada antes de qualquer coleta experimental sobre o corpus (nada medido nesta etapa); prosa em português acadêmico; IDs O01–O18 e F01–F24 permanentes; `fase2/documentos/04_mapa_completo_do_sistema.md`, `05_fluxos_resultados_e_falhas.md`, `07_metodologias_de_testagem.md` e `08_mapa_completo_da_testagem.md` INTOCADOS; dif no documento 06 restrito à linha 11 com justificativa no commit; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`; originais do corpus fora do Git (nunca `git add` neles); `python3 fase2/scripts/verificar_documentos.py` (da raiz) deve passar após qualquer alteração; commits SEPARADOS — (a) commit de entrega (documento 06, registro-materiais.json, contagens-vs-metas.md) e (b) commit de registro (esta task, task 001 com a emenda e índice do plano), sem amend/force-push/commits vazios; registrar dificuldade sentida (_/10 com justificativa) e estado `aguardando revisão`.

## Contexto
- `.agents/tasks/06-protocolo-de-avaliacao/001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md` — decisão D4 original (tabela de desvios aceitáveis; linha das famílias com mínimos de scans/tabelas) e decisões D1–D3/D7; a emenda entra aqui.
- `fase2/documentos/06_protocolo_de_avaliacao.md` — linha 11 (composição do corpus, seção 2); normativo, dif mínimo com justificativa.
- `eval/corpus/registro-materiais.json` — registro por material existente (mat-redes-001, mat-ans-001); estender com os novos depósitos.
- `eval/corpus/README.md` — regras de depósito e registro.
- `eval/datasets/contagens-vs-metas.md` — contagens reais versus metas; atualizar com a nova regra.
- `eval/corpus/originais/redes-de-computadores/` e `eval/corpus/originais/aprendizado-nao-supervisionado/` — arquivos depositados (fora do Git; calcular SHA-256 dos arquivos, não dos registros).
- `.agents/tasks/06-protocolo-de-avaliacao/003-anotacao-ouro-e-congelamento.md` — task bloqueada cuja precondition (mínimos da D4) é afetada pela emenda; não alterar seu contrato nesta task.

## Corretude
- [ ] C1 — A emenda da D4 está registrada na task 001 como acréscimo datado com a justificativa do usuário (suplementos opcionais fornecidos pelo aluno; corpus não depende deles; professores não os fornecem usualmente), preservando integralmente o texto original da D4; a nota de que F01 permanece testável por perturbação sintética na etapa 8 consta na emenda; nenhuma quantidade é apresentada como resultado medido.
- [ ] C2 — O documento 06 tem dif restrito à linha 11, com o novo texto declarando os suplementos (scans, tabelas, versões conflitantes) como opcionais/condicionais e a ausência como não bloqueante, com justificativa no commit; documentos 04, 05, 07 e 08, submódulo e demais seções do 06 sem dif; `verificar_documentos.py` com `passed` reproduzido após a alteração.
- [ ] C3 — O registro por material cobre os 17 novos materiais (8 PDFs de Redes do Classroom + 9 notas HTML de MC847), cada um com fonte, tipo, SHA-256 conferido contra o arquivo em `eval/corpus/originais/`, vínculo de versão e autorização (modelo D2); a identidade byte a byte do PDD do Classroom com `mat-redes-001` está registrada (sem duplicata no depósito); `contagens-vs-metas.md` atualizada com contagens reais e a regra emendada; originais fora do Git confirmados por `git check-ignore`; commits de entrega e de registro separados e árvore limpa.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Edições documentais delimitadas e bookkeeping de hashes; os cuidados são a disciplina de dif mínimo no texto normativo (apenas a linha 11), a preservação do texto original da D4 na emenda e a conferência dos SHA-256 contra os arquivos depositados.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: —
- Decisão: —
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/06-protocolo-de-avaliacao/plan.md)
