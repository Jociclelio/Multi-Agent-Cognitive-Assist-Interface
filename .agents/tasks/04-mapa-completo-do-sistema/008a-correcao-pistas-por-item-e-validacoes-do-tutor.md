# Task 008a: Correção — pistas por item e validações do Tutor (mapa §8, §4, §3.1)

Estado: aguardando revisão
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
- [x] C1 — Reprodução F1 corrigida: prática A + 3 pistas → nova prática B → a 1ª pista de B devolve pista de nível 1 (não a oferta de encerramento); 3 pistas de B → oferta determinística sem chamada ao modelo; `exposure` persistido por item reflete o nível daquele item. Teste de regressão cobre a sequência completa.
- [x] C2 — Reprodução F2 corrigida: item com `prompt` >4000 chars falha `SCHEMA_INVALID` sem deixar NENHUMA linha em `items`/`events`/`operations` e sem publicar (store inalterado); teste de regressão verifica o store por SQL.
- [x] C3 — Reprodução F3 corrigida: com capacidade `json_schema` ausente, resposta com campo extra ou `critical:"false"` entra em reparo e, esgotado, falha tipada sem publicar; com capacidade presente, validação local continua obrigatória; testes cobrem ambos os caminhos.
- [x] C4 — F4 resolvido com escolha registrada (caso corrigido ou validação de `cases` no loader); A1/A2 aplicados; suíte completa verde (252 + regressões novas); mapa e submódulo intocados; commits entrega/registro separados.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, via `~/sd2-llm.sh`) — identidade informada pelo runtime.
- Base: `83b1673` (árvore limpa; subtask 008a criada pelo master; entrega da 008 preservada — `093f6f9` intacto, sem reversão).
- Entrega: `475e0b6` (código/testes/registro de skills).
- Arquivos da entrega:
  - `eduagent/agents/tutor.py` —
    - **F1**: `TutorSession.help_level` (contador de sessão) substituído por `help_level_by_item: dict[str, int]` chaveado por `item_id`; `_move_request_hint` lê/incrementa o nível do item pendente (recomeça em 1 a cada item novo) e a oferta pós-3-pistas continua determinística, sem chamar o modelo; `_exposure` registra o `help_level` DAQUELE item (0 na publicação de item novo — pistas de outro item da sessão não contaminam o payload consumido pela 009, §15.2).
    - **F2**: em `_handle_item_move`, o `LearningItem` é validado (rascunho com refs provisórios da mesma forma `event/item, ID+versão≥1`) e o `TutorTurn` é montado/validado ANTES de `sink.publish`; só após as duas validações o commit idempotente acontece — falha de contrato (p.ex. `prompt` >4000 chars do §4) não deixa linha órfã em `items`/`events`/`operations`; os objetos finais são montados com os valores reais do publication (versão ≥1 e refs válidos — não podem falhar após o rascunho válido; exceção defensiva vira `INTERNAL_FAILURE`).
    - **F3a**: `_clean_rubric` exige booleano REAL em `critical` (`isinstance(critical, bool)`); string/número entra no ciclo de reparo e, esgotado, falha tipada — sem coerção `bool("false")→True`.
    - **F3b**: novo `_validate_against_local_schema` (subconjunto de JSON Schema usado pelos schemas do módulo: type/properties/required/additionalProperties/minLength/minimum/items/minItems, sem coerção em boolean/inteiro) aplicado em `_generate_validated` a TODA resposta parseada, com ou sem `capabilities.json_schema` verificada no runtime (§3.1: parse/schema/política sempre); violação entra no ciclo de reparo orçado.
  - `eduagent/skills/graduated_hint/skill.yaml` + `catalog.json` — **F4** (escolha registrada: caso CORRIGIDO, não validação de `cases` no carregador): caso "pedido de quarta pista após três dadas" usa `help_level: 3` (nível corrente) com a expectativa descrevendo a oferta determinística pós-3-pistas, sem declarar `help_level: 4` fora do `maximum: 3` do próprio `input_schema`; `version` bumpada 1→2 e registro regenerado por revisão offline `python -m eduagent.skills --rehash` (hash novo conferido no carregamento).
  - `eduagent/skills/loader.py` — **A2**: `import re as _re` movido para o topo do módulo.
  - `tests/test_task008_tutor.py` — **A1** (linha morta em `test_hashes_and_versions_registered_and_verified` removida) + 7 testes novos: `TestHintLadderPerItem` (sequência completa A+3 pistas→oferta→prática B→pistas 1/2/3→oferta, zero chamadas nas ofertas, `exposure.help_level == 0` por item via `sink.resolve`), `TestValidateBeforePublish` (prompt de 4001 chars → `SCHEMA_INVALID` com store inalterado, contagem SQL de `items`/`events`/`operations` antes/depois), `TestLocalSchemaValidation` (campo extra e `critical:"false"` → reparo → falha tipada sem publicar, com capacidade ausente; reparo bem-sucedido de campo extra; validação local obrigatória também com capacidade presente) e `test_graduated_hint_cases_respect_own_input_schema` (coerência F4 no catálogo).
- Evidências:
  - Suíte completa: `python -m pytest tests/ -q` → **259 passed** (252 pré-existentes verdes + 7 regressões novas), ~19 s; backend `FakeBackend` determinístico — nenhuma chamada ao modelo real, nada apresentado como resultado medido.
  - C1 — teste cobre a sequência integral: item A com pistas 1→2→3, 4ª requisição → oferta (`objective=close`) sem chamada; prática B na mesma sessão → 1ª pista de B é `hint_level=1` com `objective=hint` (não a oferta); 3 pistas de B → 4ª requisição → oferta sem nova chamada; total de 8 chamadas (2 práticas + 6 pistas); `exposure.help_level == 0` nos payloads publicados de A e B (sem contaminação entre itens).
  - C2 — prompt de 4001 chars → `SCHEMA_INVALID` ("item viola o contrato LearningItem antes de publicar (mapa §4)") com `items`/`events`/`operations` idênticos antes/depois (SQL direto no `DomainStore`), `pending_item` e `history` vazios.
  - C3 — sem capacidade `json_schema`: campo extra → 1 reparo orçado → esgotado → `SCHEMA_INVALID` com "extra" na mensagem, 2 chamadas, 0 itens publicados; `critical:"false"` → reparo → falha com "booleano" na mensagem, 0 itens; campo extra seguido de payload válido → reparo corrige (2 chamadas, item publicado); com capacidade presente → mesmo comportamento (validação local obrigatória).
  - C4 — caso do YAML corrigido + teste de coerência `cases`×`input_schema` no carregador; `python -m eduagent.skills --check` ok (5 skills, hash/version conferidos); `python -m eduagent.contracts --check` ok (schemas/ atualizado).
  - Intocabilidade: `fase2/documentos/04_mapa_completo_do_sistema.md` sem diff; `git submodule status` idêntico (`3504c4b`); `git diff --check` limpo; temporários apenas em `/tmp/opencode` (nenhum criado — toda a verificação rodou na árvore/suite); commit de entrega separado deste registro.
  - Pendências registradas (não decididas aqui): validação de `cases.input` contra `input_schema` no carregador NÃO foi implementada (escolha foi corrigir o caso; o teste de coerção cobre a skill corrigida, generalização fica para revisão futura se o catálogo crescer); qualidade das pistas com modelo real segue para as tasks 014/017 (backend fake).

## Notas

### Dificuldade esperada
4/10 — Correções locais e bem delimitadas em código existente e testado; risco baixo de regressão da máquina de estados se os testes da 008 continuarem verdes.

### Dificuldade sentida
3/10 — Abaixo do esperado. Pontos que exigiram mais atenção: (i) F2 tem dependência circular aparente (o `LearningItem` precisa dos refs do publication, que só existem após o publish) — resolvido com rascunho de validação usando refs provisórios da mesma forma, de modo que a montagem final pós-publicação não pode falhar por validação; (ii) a validação local de schema (F3b) precisou cobrir exatamente o subconjunto de keywords dos três schemas do módulo sem introduzir coerção (bool não é inteiro, string não é booleano); (iii) a exposição por item (F1) é registrada na publicação, quando o item novo ainda tem 0 pistas — o teste fixa essa semântica explicitamente para o redutor da 009. Nenhum impedimento.

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
