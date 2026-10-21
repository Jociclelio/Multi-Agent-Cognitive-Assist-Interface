# Task 002: Validar decisão de método — ingestão e ontologia (C02/C03)

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Conferir que a decisão abaixo reproduz **fielmente** a linha C02/C03 da tabela "Decisões reconciliadas" de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado; linha 17). Registrar em Evidências a conferência item a item (método selecionado, referências/chaves, por quê e limite). Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Decisão a validar (extraída da tabela do documento-fonte):
- **C02/C03 — Ingestão e ontologia:** Docling, OCR seletivo, blocos com página/origem, ontologia relacional e fatos candidatos *(referências/chaves: `docling`, `ocrpdf`, `pydstrict`)* *(por quê e limite: permite conferir números, datas e citações; confirmação prevalece sobre confiança verbal)*

Além da fidelidade, conferir que: os IDs C02 e C03 são tratados como permanentes; nada acrescenta requisito, número ou métrica não presente no fonte; a regra "confirmação prevalece sobre confiança verbal" aparece como limite do método (reconciliada na etapa 3), sem reabrir a ambiguidade 4 da etapa 2 (documento externo mais recente não substitui prazo confirmado; reconciliação) — que permanece pendente; a posição de C02/C03 na cadeia do núcleo (segundo passo, após C01) permanece a da etapa 2.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades nem a política de reconciliação de prazos; nada apresentado como resultado medido; IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: tabela "Decisões reconciliadas", linha C02/C03 (linha 17).
- `fase2/pesquisa/03a_arquitetura_rag.md` — relatório integral da frente de arquitetura, referência de embasamento, sem reabrir alternativas.
- `.agents/tasks/02-componentes-e-requisitos/001-validar-fundacao-inferencia-ingestao-ontologia.md` — etapa 2: características exigidas de C02 e C03, incluindo a ambiguidade 4 como pendente.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — A decisão de método para C02/C03 nesta task corresponde item a item à linha 17 do fonte (método selecionado, referências/chaves e limite); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task.
- [ ] C2 — Nada acrescido além do fonte; a regra de confirmação sobre confiança verbal é registrada como limite reconciliado, sem resolver a ambiguidade 4 (pendência preservada); IDs permanentes; nada apresentado como resultado medido.
- [ ] C3 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Conferência textual de uma linha de tabela; cuidado único em não transformar o limite reconciliado em resolução da ambiguidade 4.

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
