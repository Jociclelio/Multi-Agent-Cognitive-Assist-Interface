# Task 008: Validar opcionais (C05 e sincronização remota de C12) e consolidar cobertura C01–C20

Estado: pendente
Depende de: 007
Origem: nenhuma

## Prompt
Duas partes:

**Parte 1 — Opcionais.** Conferir que a especificação abaixo reproduz **fielmente** o que `fase2/documentos/02_componentes_e_requisitos.md` estabelece para os conectores opcionais (documento-fonte normativo, que permanece intocado):
- **C05 — Curadoria conectada (opcional):** busca/fetch controlados, metadados de texto/vídeo, idioma, acessibilidade e nível; distinguir leitura de metadados de leitura de transcrição; funcionamento offline sem URLs inventadas. *(Conector opcional avaliado separadamente; não é necessário para fechar o núcleo.)*
- **Sincronização remota de C12 (opcional):** apenas o aspecto de integração remota/agenda conectada é opcional; o ICS local de C12 permanece obrigatório no núcleo (especificado na task 004). A especificação do aspecto opcional deve citar C12 pelo ID permanente e não pode reclassificar o ICS local como opcional.

**Parte 2 — Consolidação.** Conferir e registrar em Evidências que: (a) todos os componentes C01–C20 estão representados nas tasks desta família (001–008), cada um com características exigidas e critério verificável extraídos fielmente do documento-fonte; (b) a ordem de implementação futura está registrada conforme a seção de dependências do fonte: núcleo C01 → C02/C03 → C04/C09 → C06/C07/C08 → C11, sustentado desde o início por C13–C17/C20; C18/C19 começam antes da otimização; C05 e sincronização remota de C12 avaliados separadamente; (c) as seis ambiguidades do documento-fonte estão registradas como decisões pendentes, distribuídas pelas tasks onde são relevantes, sem que nenhuma tenha sido resolvida arbitrariamente.

Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências. Se a consolidação revelar lacuna de cobertura (componente sem task), registre o impedimento em Evidências e no campo Notas — não crie task nem edite tasks de outras sessões.

Restrições: não alterar o documento-fonte nem criar documento novo; não resolver ambiguidades; não apresentar especificação como resultado medido; prosa em português; commit de registro separado, sem amend/force-push/commits vazios.

## Contexto
- `fase2/documentos/02_componentes_e_requisitos.md` — documento-fonte: tabela C01–C20, dependências/prioridades e as seis ambiguidades.
- `.agents/tasks/02-componentes-e-requisitos/` — tasks 001–007 desta família, objeto da conferência de cobertura.
- `.agents/plans/02-componentes-e-requisitos/plan.md` — plano aprovado; "Critérios de conclusão" define o que a consolidação deve comprovar.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — Características e critérios de C05 e do aspecto opcional de C12 correspondem item a item ao documento-fonte; ICS local permanece obrigatório no núcleo, sem reclassificação.
- [ ] C2 — Cobertura completa comprovada: cada componente C01–C20 mapeado à task onde está especificado (lista explícita em Evidências); nenhum componente órfão.
- [ ] C3 — Cadeia do núcleo, camada transversal desde o início, C18/C19 antes da otimização e opcionais separados registrados conforme a seção de dependências do fonte.
- [ ] C4 — As seis ambiguidades estão listadas como decisões pendentes e nenhuma foi resolvida nesta etapa.
- [ ] C5 — Documento-fonte intocado (`git diff` vazio para ele em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commit de registro com evidências separado de qualquer commit de entrega; sem commits vazios, amend ou force-push.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
4/10 — A parte 1 é conferência textual simples; a parte 2 exige verificação cruzada de cobertura sobre oito tasks e as seis ambiguidades, com risco moderado de lacuna sutil de mapeamento.

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

Plano: [plan.md](../../plans/02-componentes-e-requisitos/plan.md)
