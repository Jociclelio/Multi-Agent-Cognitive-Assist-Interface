# Task 009: Consolidar orçamentos da etapa 4, limites bibliográficos e cobertura C01–C20

Estado: pendente
Depende de: 008
Origem: nenhuma

## Prompt
Duas partes:

**Parte 1 — Orçamentos de parâmetros da etapa 4 e limites bibliográficos.** Conferir que os registros abaixo reproduzem **fielmente** as seções "Conflitos de parâmetros resolvidos para a etapa 4" (linhas 30–38) e "Limites da base bibliográfica" (linhas 40–42) de `fase2/documentos/03_metodologias_de_implementacao.md` (documento-fonte normativo, que permanece intocado). Registrar em Evidências a conferência item a item. Se encontrar desvio de fidelidade, corrija **apenas o texto desta task** em dif mínimo, preservando o sentido do fonte, e registre a correção em Evidências.

Orçamentos a validar (extraídos do documento-fonte; todos são escolhas iniciais configuráveis, não resultados medidos):
- **Janela operacional:** inicial de 32.768 tokens, não a janela máxima anunciada. Reservas únicas: saída 16.384, ferramentas 2.048 e margem 1.024; entrada máxima 13.312. A reserva cobre geração de raciocínio e resposta quando aplicável. Se o hardware não comportar, o perfil deve ser revalidado; não combinar simultaneamente a regra percentual da frente pedagógica com essas reservas.
- **Evidências e memória:** evidências documentais até 4.096 tokens; memória até oito unidades, com limite de 2.048 tokens. O limite de entrada total prevalece sobre limites locais.
- **Solver:** sete dias, slots conservadores de quinze minutos e dez segundos **totais** entre etapas lexicográficas. `FEASIBLE` não é prova de ótimo; `UNKNOWN` não é inviável.
- **Aprendizagem:** estimativa numérica `null` no MVP; três respostas independentes de famílias distintas permitem apenas rótulo provisório de evidência favorável. Intervalos 1/3/7 dias são política de ensaio, não uma lei de retenção.
- **Grafo:** seis chamadas LLM, oito ferramentas, dezesseis transições, dois reparos globais e um por artefato; 120 s de computação ativa por turno. Jobs de ingestão são separados.
- **Regras gerais:** todos esses números são escolhas iniciais configuráveis; o teste de desenvolvimento determina viabilidade; a configuração é congelada antes do teste final; a extensão de agenda remota permanece atrás de feature flag até a documentação específica e os ensaios de concorrência serem concluídos.

Limites bibliográficos a validar (extraídos do documento-fonte): metadados foram acessados, mas não o texto integral de Wood, Corbett e RRF; Chi foi acessado pelo resumo editorial; a formulação operacional de RRF é sustentada também pela documentação oficial; BKT é descrito a partir do texto acessível de pyBKT; MetaGPT é referenciado pela versão arXiv consultada, sem afirmar uma verificação editorial que falhou; a bibliografia preliminar da fase 1 não foi reaproveitada (contém entradas não verificadas).

**Parte 2 — Consolidação da cobertura e dos documentos integrantes.** Com as decisões registradas nas tasks 001–008 e os orçamentos nesta task, registrar em Evidências: (a) a lista explícita completa componente(s) → task da família (20/20), na partição desta família: C01/C20 → task 001; C02/C03 → task 002; C04 e C05 → task 003; C06 e C07/C08 → task 004; C09/C10 e C11 → task 005; C12 e C13/C14 → task 006; C15/C16 e C17 → task 007; C18/C19 → task 008; (b) os documentos integrantes da etapa 3 e a regra de distribuição — os relatórios integrais `fase2/pesquisa/03a_arquitetura_rag.md` (C01–C05, C13–C17, C20; 18 núcleos bibliográficos) e `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` (C06–C12; 18 itens com alcance de leitura discriminado), com bibliografias em `fase2/pesquisa/references_arquitetura.bib` e `fase2/pesquisa/references_pedagogia.bib`; a síntese não deve ser distribuída sem os relatórios integrantes (o pacote final inclui todos); C18–C19 são completados pela pesquisa específica das etapas 6–7; (c) a conferência dos critérios de conclusão do plano: método selecionado e limites por componente (C01–C20), orçamentos reproduzidos como escolhas iniciais configuráveis com as regras de prevalência ("o limite de entrada total prevalece sobre limites locais") e de não combinação explícitas, dependentes externos identificados (C18–C19 nas etapas 6–7, feature flag da agenda remota, congelamento de configuração antes do teste final).

Desvio de fidelidade: corrija apenas o texto desta task em dif mínimo e registre em Evidências.

Restrições: não alterar o documento-fonte nem criar documento novo; não derivar novos números dos orçamentos (ex.: não recalcular entrada máxima a partir das reservas) nem apresentá-los como resultado medido; não resolver pendências (validação de C04 em português, posicionamento de C10, ambiguidades da etapa 2, pesquisa das etapas 6–7); IDs C01–C20 permanentes; prosa em português; commit de entrega (correção de fidelidade, se houver) e commit de registro separados, sem amend/force-push/commits vazios; submódulo `docs/playground-llmagenticsystem` não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/03_metodologias_de_implementacao.md` — documento-fonte: seções "Conflitos de parâmetros resolvidos para a etapa 4" (linhas 30–38), "Limites da base bibliográfica" (linhas 40–42) e "Método e documentos integrantes" (linhas 3–10).
- `.agents/tasks/03-metodologias-de-implementacao/` — tasks 001–008 desta família, objeto da consolidação de cobertura.
- `fase2/pesquisa/03a_arquitetura_rag.md` e `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` — relatórios integrantes; verificação de existência e da contagem declarada (18 núcleos/18 itens), sem reabrir conteúdo.
- `.agents/plans/03-metodologias-de-implementacao/plan.md` — plano aprovado; "Critérios de conclusão" define o que a Parte 2 confere.
- `AGENTS.md` (raiz) — convenções do repositório.

## Corretude
- [ ] C1 — Os orçamentos de parâmetros e os limites bibliográficos nesta task correspondem item a item às seções do fonte (linhas 30–42); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task; nenhum número derivado ou recalculado além do fonte.
- [ ] C2 — Cobertura C01–C20 completa comprovada: lista explícita em Evidências com a partição 20/20 mapeada às tasks 001–009 (conforme a Parte 2 do prompt); documentos integrantes e regra de distribuição registrados; critérios de conclusão do plano conferidos com evidência.
- [ ] C3 — Todos os números são apresentados como escolhas iniciais configuráveis, nunca como resultados medidos; as regras de prevalência (limite de entrada total) e de não combinação (regra percentual da frente pedagógica × reservas) estão explícitas; pendências permanecem abertas, nenhuma resolvida.
- [ ] C4 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — A Parte 1 é conferência textual de duas seções com vários números (risco de transcrição dígito a dígito); a Parte 2 exige consolidação cruzada sobre nove tasks sem derivar nem recalcular valores.

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
