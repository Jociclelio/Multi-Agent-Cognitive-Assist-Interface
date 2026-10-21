# Task 008a: Correção — pistas por item e validações do Tutor (mapa §8, §4, §3.1)

Estado: pendente
Depende de: 008
Origem: 008 — correção

## Prompt
Corrigir na entrega da 008 (preservada, sem reversão) os achados confirmados na revisão, sobre `eduagent/agents/tutor.py`, `eduagent/skills/graduated_hint/skill.yaml` e `tests/test_task008_tutor.py`:

- **F1 (alto) — escada de pistas por item, não por sessão.** Hoje `help_level` é campo da `TutorSession` (tutor.py ~:475), incrementado a cada pista (~:943/:980) e lido na exposição (~:1585), sem reset na troca de item. Consequência reproduzida: prática A + 3 pistas → nova prática B → a 1ª pista de B devolve `objective=close` com a oferta "Você já recebeu três pistas…" e zero pistas no item B, e `exposure.help_level=3` gravado no evento do item B. Corrigir: o nível de ajuda deve recomeçar em 1 para cada item pendente novo (por `item_id`/`pending_item`), mantendo a oferta determinística pós-3-pistas SEM chamar o modelo; a exposição registrada no item deve refletir o nível realmente oferecido naquele item (§15.2 é por tentativa — o redutor da 009 consumirá esse payload). Decisão de implementação (por exemplo, mover o contador para o item pendente da sessão) fica a cargo do executor, desde que a semântica por item fique provada por teste.
- **F2 (médio) — validar antes de publicar.** Hoje o item é commitado no sink (~:868, `item.publish` + evento + projeção) ANTES de o `LearningItem` ser validado (~:881-898) e de o `TutorTurn` ser montado; um `prompt` >4000 chars (limite `_MAX_TEXT` do §4, `contracts.py`) gera `SCHEMA_INVALID` DEPOIS do commit, deixando linha órfã em `items`/`events`/`operations` com 0 turnos — efeito parcial sem reparo possível. Corrigir: validar o `LearningItem` (incluindo limites do §4) e montar o `TutorTurn` ANTES do `sink.publish` (ou tornar publicação e montagem atômicas na ordem certa); nenhum efeito parcial pode persistir quando a validação falha (§12).
- **F3 (médio) — validação estrita da saída.** (a) Em ~:1179, `bool(entry.get("critical"))` coage `"false"`→`True`: aceitar apenas booleanos reais na rubrica; valor não booleano entra no ciclo de reparo e, esgotado, erro tipado. (b) Quando o runtime NÃO tem `capabilities.json_schema` verificada, a resposta do modelo só passa por parse + validador de política (~:1216-1271, schema `None` em ~:1301-1304), e campos extras/rubrica inválida passam sem reparo; §3.1 exige parse/schema/política SEMPRE. Corrigir: validar a resposta contra o schema declarado localmente (contrato Pydantic estrito ou validador equivalente) dentro do loop de reparo também quando o schema não é enviado ao runtime.
- **F4 (baixo) — coerência do YAML.** `graduated_hint/skill.yaml` (~:59-64) declara caso "quatro pistas seguidas" com `help_level: 4`, acima do `maximum: 3` do próprio `input_schema` (~:13-22). Corrigir o caso (descrever a oferta pós-3 sem campo inválido) ou validar `cases.input` contra `input_schema` no carregador; registrar a escolha.
- **A1/A2 (cosméticos, aproveitar na mesma passagem):** remover linha morta em `tests/test_task008_tutor.py:478` e mover `import re as _re` de `loader.py:266` para o topo do módulo.

Restrições: não alterar `fase2/documentos/04_mapa_completo_do_sistema.md`; não tocar o submódulo `docs/playground-llmagenticsystem`; sem autoedição de skills em runtime; sem citação fictícia; nenhuma saída parcial aprovada silenciosamente; backend de testes continua fake determinístico (nada é resultado medido); commits de entrega e registro SEPARADOS, sem amend/force-push.

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/008-skills-yaml-e-tutor.md` — task mãe: contrato, evidências, seção Revisão com os achados F1–F4/A1/A2 e referências de linha.
- `eduagent/agents/tutor.py` — máquina de estados, orçamento de chamadas, publicação via sink (commit idempotente da 005), exposição.
- `eduagent/skills/loader.py` e `eduagent/skills/graduated_hint/skill.yaml` — catálogo estrito e caso a corrigir.
- `eduagent/contracts.py` — limites do §4 (`_MAX_TEXT` 4000) e `LearningItem`.
- `tests/test_task008_tutor.py` — 40 testes existentes; adicionar regressões para F1/F2/F3.

## Corretude
- [ ] C1 — Reprodução F1 corrigida: prática A + 3 pistas → nova prática B → a 1ª pista de B devolve pista de nível 1 (não a oferta de encerramento); 3 pistas de B → oferta determinística sem chamada ao modelo; `exposure` persistido por item reflete o nível daquele item. Teste de regressão cobre a sequência completa.
- [ ] C2 — Reprodução F2 corrigida: item com `prompt` >4000 chars falha `SCHEMA_INVALID` sem deixar NENHUMA linha em `items`/`events`/`operations` e sem publicar (store inalterado); teste de regressão verifica o store por SQL.
- [ ] C3 — Reprodução F3 corrigida: com capacidade `json_schema` ausente, resposta com campo extra ou `critical:"false"` entra em reparo e, esgotado, falha tipada sem publicar; com capacidade presente, validação local continua obrigatória; testes cobrem ambos os caminhos.
- [ ] C4 — F4 resolvido com escolha registrada (caso corrigido ou validação de `cases` no loader); A1/A2 aplicados; suíte completa verde (252 + regressões novas); mapa e submódulo intocados; commits entrega/registro separados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — Correções locais e bem delimitadas em código existente e testado; risco baixo de regressão da máquina de estados se os testes da 008 continuarem verdes.

### Dificuldade sentida
_/10 — —

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

<!-- task-cycle: {"decision":"corrigir","next_task":".agents/tasks/04-mapa-completo-do-sistema/008a-correcao-pistas-por-item-e-validacoes-do-tutor.md","family":".agents/tasks/04-mapa-completo-do-sistema/001-scaffold-e-configuracao.md","plan":".agents/plans/04-mapa-completo-do-sistema/plan.md"} -->

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
