# Task 002-1: Corrigir o oráculo ambíguo da borda F13 de duração não múltipla

Estado: aguardando revisão
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
- [x] C1 — A instância de borda de duração não múltipla (17 min) tem oráculo inequívoco: a reserva mínima citada está codificada na instância com `esperado` executável que a aplica, ou a menção é removida/justificada no manifesto por não estar definida em regra alguma — sem inventar threshold novo. **Atendida pelo primeiro caminho:** a regra existe em fontes normativas — mapa 04 §9 ("duração ocupa `ceil(duration/15)` slots, sem reduzir minutos"), mapa 04 §15.5 ("Capacidade diária mede minutos efetivamente reservados, inclusive arredondamento") e mapa 08 §12 ("Limite diário conta minutos reservados arredondados+fixos de estudo") — de modo que o `esperado` de `agenda-borda-dev-02` passou a codificar o efeito: `viavel: true`, `reserva_min: 30` (= `ceil(17/30)·30`), `cronograma_referencia` (a1 no slot 600–630 do dia 1, primeiro slot livre da janela 10:00–13:00, fim ≤ prazo 780) e observação que marca como violação o plano que reduza minutos (fim 617) ou contabilize 17 min no limite diário. A citação imprecisa "mapa 08 seção 12: minutos reservados arredondados" foi corrigida para as seções normativas exatas (nenhuma regra nova foi criada; `reserva_min` permanece 30).
- [x] C2 — Regeneração (se houver) permanece determinística e reproduzível: 100 instâncias pequenas inalteradas com split 40/20/40 por família inteira preservado; hashes do manifesto batem com os arquivos regenerados (reexecução 2× com SHA-256 idênticos); alteração restrita à(s) borda(s) afetada(s). **Atendida:** gerador alterado (campo `esperado` da borda e asserto embutido) e regenerado 2× com SHA-256 idênticos entre execuções — `pequenas.jsonl` `ba15a8677a9d63198643954c7ff7264af22907a8c2f40000462edf5e94abda35` (inalterado, confirmado byte a byte por `cmp` contra cópia prévia) e `borda.jsonl` `ebbd9fc4cae0fb3ca32ba6576050b3e4d00b74a6c6eb3ae69d50d39c41e8b8b5`; o dif de `borda.jsonl` fica restrito à linha 2 (`agenda-borda-dev-02`); split 40/20/40 e validações embutidas reconfirmados a cada execução; hashes atualizados no manifesto.
- [x] C3 — Integridade: `fase2/` e `docs/` sem dif entre base e HEAD; submódulo intocado; verificador documental `passed`; árvore limpa; commits de entrega e de registro separados; nada apresentado como resultado medido. **Atendida:** `git diff --name-only -- fase2/ docs/` vazio (documento 04, documento 06 e mapa 08 intocados), `git diff --submodule=log` vazio para `docs/playground-llmagenticsystem`, verificador `passed` após as alterações, `contagens-vs-metas.md` sem alteração (a contagem de bordas, 6 estruturais com 2 por split, e a descrição "especificações estruturais, não resultados de execução" permanecem exatas).

## Execução
- Modelo: GLM-5.3-Flash (provedor `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime.
- Base: e704d5ca0a6817f520b83fc7f14fdcaae7e3d7ad
- Entrega: 4a8b0aebcb86044116af743c1a3b7573eea0d960
- Arquivos da entrega: `eval/datasets/agenda/borda.jsonl`, `eval/datasets/agenda/manifesto.json`, `eval/datasets/scripts/gerar_agenda.py`
- Evidências: ver seção Evidências de verificação abaixo.

## Notas

### Resumo da execução

1. **Localização da regra (passo 1 do prompt):** a reserva mínima citada
   (`reserva_min: 30`) está definida em regra normativa — mapa 04 §9
   (duração ocupa `ceil(duracao/slot)` slots, sem reduzir minutos), mapa 04
   §15.5 (capacidade diária mede minutos efetivamente reservados, inclusive
   arredondamento) e mapa 08 §12 (limite diário conta minutos reservados
   arredondados). A família F13 do documento 05 ("Demanda/slots/zona/solver
   status incorretos; plano formalmente válido viola tempo real") e o
   protocolo, seção 4 (F13: "violações em minutos originais/status; nunca
   plano inválido aprovado") confirmam o que o oráculo deve exigir, sem
   definir parâmetro próprio. Seguiu-se o caminho (2) do prompt: codificar o
   efeito da regra, sem inventar threshold novo — o valor 30 resulta de
   `ceil(17/30)·30` sob a grade de slots de 30 min do dataset (e coincidiria
   com `ceil(17/15)·15` sob a grade de 15 min do mapa 04).
2. **Codificação do oráculo (passo 2):** no gerador, o `esperado` da borda
   `duracao-nao-multipla-de-slot` passou a conter `viavel`, `reserva_min`,
   `cronograma_referencia` (EDF no slot mais cedo) e observação que delimita a
   violação (reduzir minutos ou contabilizar 17 no limite diário); `fundamento`
   e `verificacao` atualizados para as seções normativas exatas. O gerador
   ganhou um asserto embutido que confere, a cada geração, a regra
   (`reserva_min = ceil(duracao/slot)·slot`), a aplicação integral da reserva
   no cronograma, a permanência na janela e o respeito ao prazo.
3. **Regeneração e manifesto (passos 4–5):** regeneração determinística
   (seed mestre 0) executada 2× com SHA-256 idênticos; `pequenas.jsonl`
   inalterado byte a byte; dif de `borda.jsonl` restrito à linha 2; hash novo
   registrado no manifesto, com referência normativa ao mapa 04 e descrição do
   campo `esperado` atualizada. `contagens-vs-metas.md` não exigiu alteração:
   a contagem de bordas (6 estruturais, 2 por split) e sua descrição permanecem
   exatas após o fix.
4. **Escopo preservado:** as demais entregas da 002 (registro por material,
   `splits.json`, demais manifestos, contagens com ausências) intocadas;
   `fase2/` (inclusive documentos 04, 05, 06 e 08) e `docs/` sem dif;
   submódulo intocado; nada apresentado como resultado medido.

### Evidências de verificação

- `python3 eval/datasets/scripts/gerar_agenda.py` (executado duas vezes, pós-
  alteração): `OK: 100 pequenas + 6 borda; split = {'desenvolvimento': 40,
  'validacao': 20, 'teste': 40}` com SHA-256 idênticos entre execuções —
  `pequenas.jsonl` `ba15a8677a9d63198643954c7ff7264af22907a8c2f40000462edf5e94abda35`
  e `borda.jsonl` `ebbd9fc4cae0fb3ca32ba6576050b3e4d00b74a6c6eb3ae69d50d39c41e8b8b5`.
- `cmp` entre `pequenas.jsonl` pré e pós-regeneração: idêntico byte a byte.
- `diff` de `borda.jsonl`: única linha alterada é a 2 (`agenda-borda-dev-02`).
- Checagem independente do oráculo (script pontual em `/tmp/opencode`):
  `reserva_min = ceil(17/30)·30 = 30`; cronograma de referência com
  `fim − inicio = 30`, fim 630 ≤ prazo 780 e dentro da janela 600–780 — OK.
- Asserto embutido no gerador executado a cada geração (regra, reserva
  integral, janela e prazo).
- `python3 -m json.tool` no manifesto: JSON válido.
- `python3 fase2/scripts/verificar_documentos.py` (da raiz, após as
  alterações): `"status": "passed"` — `delivery_pending` vazio.
- `git diff --name-only -- fase2/ docs/`: vazio; `git diff --submodule=log --
  docs/playground-llmagenticsystem`: vazio; árvore limpa após cada commit.

### Pendências de usuário

Nenhuma nova; permanecem as pendências da 002 (depósito do corpus até os
mínimos da D4, precondition da 003).

### Dificuldade esperada
3/10 — Correção pequena e delimitada, mas exige tocar geração determinística com hashes publicados e decidir com justificativa mínima entre aplicar ou descartar a regra de reserva citada, sem inventar regra nova.

### Dificuldade sentida
3/10 — Na escala esperada. O esforço real concentrou-se na verificação normativa: a regra citada pela instância original estava imprecisa ("mapa 08 seção 12: minutos reservados arredondados" descreve o cômputo do limite diário, não uma regra autônoma de arredondamento) e foi necessário cruzar mapa 04 §9/§15.5, mapa 08 §12 e as formulações de F13 nos documentos 05 e 06 antes de decidir entre aplicar e descartar — decisão que, uma vez localizada a regra, foi direta (caminho aplicar, sem threshold novo). A preservação byte a byte das pequenas e a restrição do dif à linha 2 exigiram disciplina de regeneração, mas o gerador determinístico já a garantia.

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
