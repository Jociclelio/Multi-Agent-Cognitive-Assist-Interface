# Task 002-1: Corrigir o oráculo ambíguo da borda F13 de duração não múltipla

Estado: pendente
Depende de: 002
Origem: 002 (correção — achado médio da revisão; entrega preservada)

## Prompt
Corrigir, na entrega preservada da task 002, o caso de borda estrutural de F13 (duração não múltipla do slot) em `eval/datasets/agenda/borda.jsonl` (linha 2): a instância de 17 min cita uma reserva mínima (`reserva_min: 30`), mas não codifica essa reserva nem define um `esperado` (cronograma/resultado) que a aplique — a borda fica como declaração textual com oráculo ambíguo. Corrigir delimitadamente: (1) verificar onde a regra de reserva mínima está definida (manifesto da agenda, descrição da família F13 em `fase2/documentos/05_fluxos_resultados_e_falhas.md` ou no próprio gerador); (2) se a regra estiver definida, codificar o efeito dela na instância (ex.: duração efetiva arredondada ou slot reservado) e fixar o `esperado` de forma inequívoca e executável; (3) se a regra NÃO estiver definida em nenhum lugar normativo ou do próprio dataset, remover a menção solta de `reserva_min` ou registrar a ambiguidade no manifesto com a decisão mínima justificada — não inventar nem ampliar regras/thresholds novos; (4) regenerar os arquivos de agenda de forma determinística (seed mestre 0) se o gerador for alterado, atualizando os hashes SHA-256 no manifesto e conferindo que as 100 instâncias pequenas e o split 40/20/40 permanecem inalterados (o fix é restrito à(s) borda(s) afetada(s)); (5) atualizar `eval/datasets/contagens-vs-metas.md` e/ou o manifesto da agenda se a contagem ou a descrição das bordas mudar. As demais entregas da 002 (registro por material, splits.json, manifestos, contagens com ausências) permanecem intocadas. Nada é apresentado como resultado medido; ausência continua declarada como ausência.

Restrições: prosa em português acadêmico; IDs F01–F24 e O01–O18 permanentes; `fase2/documentos/04_mapa_completo_do_sistema.md` INTOCADO; dif no documento 06 só o mínimo com justificativa (em princípio nenhum); submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`; originais do corpus fora do Git; commits SEPARADOS — (a) commit de entrega (artefatos em `eval/datasets/`) e (b) commit de registro (esta task + índice do plano), sem amend/force-push/commits vazios; `python3 fase2/scripts/verificar_documentos.py` (da raiz) deve passar após qualquer alteração; registrar dificuldade sentida (_/10 com justificativa) e estado `aguardando revisão`.

## Contexto
- `.agents/tasks/06-protocolo-de-avaliacao/002-montar-corpus-e-conjuntos-por-split.md` — task mãe: seção Revisão registra o achado (Luna A1, médio) e a decisão `corrigir`; leia para entender o que falhou.
- `eval/datasets/agenda/borda.jsonl` — linha 2: instância de 17 min com `reserva_min: 30` não aplicada (alvo da correção).
- `eval/datasets/agenda/manifesto.json` — hashes e descrição das bordas; atualizar hashes se regenerar.
- `eval/datasets/scripts/gerar_agenda.py` — gerador determinístico (seed mestre 0); alterar apenas se a codificação do `esperado` exigir.
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — família F13 (perturbações de agenda); fonte dos IDs, não editar.
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 2 (composição dos conjuntos); normativo, consultar.

## Corretude
- [ ] C1 — A instância de borda de duração não múltipla (17 min) tem oráculo inequívoco: a reserva mínima citada está codificada na instância com `esperado` executável que a aplica, ou a menção é removida/justificada no manifesto por não estar definida em regra alguma — sem inventar threshold novo.
- [ ] C2 — Regeneração (se houver) permanece determinística e reproduzível: 100 instâncias pequenas inalteradas com split 40/20/40 por família inteira preservado; hashes do manifesto batem com os arquivos regenerados (reexecução 2× com SHA-256 idênticos); alteração restrita à(s) borda(s) afetada(s).
- [ ] C3 — Integridade: `fase2/` e `docs/` sem dif entre base e HEAD; submódulo intocado; verificador documental `passed`; árvore limpa; commits de entrega e de registro separados; nada apresentado como resultado medido.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Correção pequena e delimitada, mas exige tocar geração determinística com hashes publicados e decidir com justificativa mínima entre aplicar ou descartar a regra de reserva citada, sem inventar regra nova.

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
