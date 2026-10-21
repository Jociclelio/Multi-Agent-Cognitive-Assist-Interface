# Task 003: Validar decisões de método — recuperação e curadoria (C04 e C05)

Estado: pendente
Depende de: 002
Origem: nenhuma

## Prompt
Conferir que as duas decisões abaixo reproduzem **fielmente** as linhas C04 e C05 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linhas 18 e 19). Registrar em Evidências a conferência item a item de cada linha (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisões a validar (extraídas da tabela do documento-fonte):
- **C04 — Recuperação:** BM25 + BGE-M3 denso, RRF explícito e reranker opcional *(referências/chaves: `m3`, `rrf09`, `qdranthyb`, `bgerank`)* *(por quê e limite: recupera literais e paráfrases; parâmetros e benefício precisam de validação em português)*
- **C05 — Curadoria (opcional):** curadoria com estados de conteúdo realmente acessado *(referências/chaves: `ytcaptions`, `mcpsec`)* *(por quê e limite: metadados de vídeo não autorizam resumo da transcrição; provedor conectado é configurável)*

Além da fidelidade, conferir que: os IDs C04 e C05 são tratados como permanentes; nada acrescenta requisito, número ou métrica não presente no fonte; a pendência de validação dos parâmetros de recuperação em português (C04) permanece registrada como limite, não resolvida (questão aberta da etapa 3 do plano); C05 permanece conector opcional, sem reclassificação; a fronteira da etapa 2 (metadados de vídeo ≠ leitura de transcrição) permanece coerente.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver a validação em português nem reclassificar opcionais; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linhas C04 (linha 18) e C05 (linha 19).
- `fase2/pesquisa/03a_arquitetura_rag.md` — relatório integral da frente de arquitetura, referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/002-validar-rag-e-memoria-persistente.md` e `008-validar-opcionais-e-consolidar-cobertura-c01-c20.md` — etapa 2: características de C04/C09 e o caráter opcional de C05.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado; "Questões abertas" registra a validação de C04 em português.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — As decisões de método para C04 e C05 nesta task correspondem item a item às linhas 18 e 19 do fonte (método selecionado, referências/chaves e limite de cada linha); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [ ] C2 — Nada acrescido além do fonte; a pendência de validação em português (C04) e o caráter opcional de C05 permanecem registrados, sem resolução ou reclassificação; reranker permanece opcional; IDs permanentes; nada apresentado como resultado medido.
- [ ] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de duas linhas de tabela; cuidado em preservar o caráter opcional do reranker e de C05 e a pendência de validação em português.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: —
- Nota final: —
- Parecer: —
- Decisão: pendente
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/03-metodologias-de-implementacao/plan.md)
