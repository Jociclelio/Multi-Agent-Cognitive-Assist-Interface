# Task 009: Consolidar orçamentos da etapa 4, limites bibliográficos e cobertura C01–C20

Estado: aguardando revisão
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
- [x] C1 — Os orçamentos de parâmetros e os limites bibliográficos nesta task correspondem item a item às seções do fonte (linhas 30–42); desvios apenas tipográficos corrigidos em dif mínimo no arquivo desta task; nenhum número derivado ou recalculado além do fonte. (Conferência item a item em Evidências: nenhum desvio de fidelidade encontrado, nenhuma correção necessária.)
- [x] C2 — Cobertura C01–C20 completa comprovada: lista explícita em Evidências com a partição 20/20 mapeada às tasks 001–009 (conforme a Parte 2 do prompt); documentos integrantes e regra de distribuição registrados; critérios de conclusão do plano conferidos com evidência.
- [x] C3 — Todos os números são apresentados como escolhas iniciais configuráveis, nunca como resultados medidos; as regras de prevalência (limite de entrada total) e de não combinação (regra percentual da frente pedagógica × reservas) estão explícitas; pendências permanecem abertas, nenhuma resolvida.
- [x] C4 — O documento-fonte permanece intocado (`git diff` vazio em relação à base); correções limitadas ao arquivo desta task em dif mínimo; commits de entrega e de registro separados; sem commits vazios, amend ou force-push; submódulo não tocado. (Sem correção de fidelidade, não houve commit de entrega; apenas o commit de registro.)

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, model `GLM-5.3-Flash`, via `~/sd2-llm.sh`)
- Base: `0923d8d` (task 008 fechada; árvore de trabalho limpa no início)
- Entrega: sem alteração de artefatos — a conferência da Parte 1 não encontrou desvio de fidelidade, portanto não houve correção nem commit de entrega; a entrega desta task é o registro documental abaixo.
- Arquivos da entrega: nenhum (registro: este `task.md`, commit de registro separado).
- Evidências:
  - **Parte 1 — conferência item a item** contra `fase2/documentos/03_metodologias_de_implementacao.md` (leitura direta das linhas 30–42):
    - Janela operacional (task l. 13 ↔ fonte l. 32): reprodução literal — 32.768 tokens inicial (não a janela máxima anunciada); reservas únicas saída 16.384, ferramentas 2.048, margem 1.024; entrada máxima 13.312; reserva cobre geração de raciocínio e resposta quando aplicável; revalidação do perfil se o hardware não comportar; proibição de combinar a regra percentual da frente pedagógica com as reservas. ✓
    - Evidências e memória (l. 14 ↔ l. 33): reprodução literal — evidências documentais até 4.096 tokens; memória até oito unidades com limite de 2.048 tokens; "O limite de entrada total prevalece sobre limites locais" (regra de prevalência explícita). ✓
    - Solver (l. 15 ↔ l. 34): reprodução literal — sete dias; slots conservadores de quinze minutos; dez segundos **totais** entre etapas lexicográficas; `FEASIBLE` não é prova de ótimo; `UNKNOWN` não é inviável. ✓
    - Aprendizagem (l. 16 ↔ l. 35): reprodução literal — estimativa numérica `null` no MVP; três respostas independentes de famílias distintas permitem apenas rótulo provisório de evidência favorável; intervalos 1/3/7 dias como política de ensaio, não lei de retenção. ✓
    - Grafo (l. 17 ↔ l. 36): reprodução literal — seis chamadas LLM, oito ferramentas, dezesseis transições, dois reparos globais e um por artefato; 120 s de computação ativa por turno; jobs de ingestão separados. ✓
    - Regras gerais (l. 18 ↔ l. 38): mesmo teor com pontuação adaptada ao formato de item de lista (pontos finais → ponto e vírgula); números como escolhas iniciais configuráveis; teste de desenvolvimento determina viabilidade; configuração congelada antes do teste final; agenda remota atrás de feature flag até documentação específica e ensaios de concorrência. ✓
    - Limites bibliográficos (l. 20 ↔ l. 42): paráfrase fiel — metadados sem texto integral de Wood, Corbett e RRF; Chi pelo resumo editorial; formulação operacional de RRF sustentada também pela documentação oficial; BKT a partir do texto acessível de pyBKT; MetaGPT pela versão arXiv consultada, sem afirmar verificação editorial que falhou; bibliografia preliminar da fase 1 não reaproveitada (entradas não verificadas). A frase meta do fonte "Os relatórios distinguem precisamente esses casos." é omitida no resumo da task, sem alterar sentido. ✓
    - **Resultado:** nenhum desvio de fidelidade numérica ou conceitual; nenhuma correção necessária; nenhum número derivado ou recalculado (a entrada máxima 13.312 foi apenas transcrita, não recalculada a partir das reservas).
  - **Parte 2 — consolidação da cobertura:**
    - (a) Partição 20/20 conferida contra os cabeçalhos de `001`–`008` (leitura dos títulos/estados) e a tabela de tasks do plano: C01/C20 → 001 (fechada); C02/C03 → 002 (fechada); C04 e C05 → 003 (aguardando revisão); C06 e C07/C08 → 004 (aguardando revisão); C09/C10 e C11 → 005 (fechada); C12 e C13/C14 → 006 (aguardando revisão); C15/C16 e C17 → 007 (fechada); C18/C19 → 008 (fechada); orçamentos + limites bibliográficos + consolidação → 009 (esta). União = C01–C20, 20/20, sem omissão nem duplicação.
    - (b) Documentos integrantes conferidos por existência e contagem declarada, sem reabrir conteúdo: `fase2/pesquisa/03a_arquitetura_rag.md` (C01–C05, C13–C17 e C20; declara "18 núcleos bibliográficos"), `fase2/pesquisa/03b_pedagogia_memoria_planejamento.md` (C06–C12; declara "18 itens bibliográficos" com alcance de leitura discriminado — 15 com conteúdo substantivo, Chi por resumo do editor, Wood e Corbett só metadados); bibliografias `fase2/pesquisa/references_arquitetura.bib` e `fase2/pesquisa/references_pedagogia.bib` presentes. Regra de distribuição (fonte l. 10): a síntese não deve ser distribuída sem os relatórios integrantes; o pacote final inclui todos; C18–C19 são completados pela pesquisa específica das etapas 6–7.
    - (c) Critérios de conclusão do plano (`plan.md` "Critérios de conclusão"): método selecionado e limites por componente registrados nas tasks 001–008 (C01–C20); orçamentos da etapa 4 reproduzidos como escolhas iniciais configuráveis com regras de prevalência (limite de entrada total) e de não combinação (regra percentual × reservas) explícitas na Parte 1; dependentes externos identificados: C18–C19 nas etapas 6–7, feature flag da agenda remota, congelamento de configuração antes do teste final. Nenhum número apresentado como resultado medido; nenhum texto afirma verificação bibliográfica que não ocorreu.
  - **Integridade:** `git status` limpo na base `0923d8d`; `git diff 0923d8d` vazio — documento-fonte e demais arquivos intocados; submódulo `docs/playground-llmagenticsystem` não acessado para escrita. `python3 fase2/scripts/verificar_documentos.py` → `status: passed` (39 links locais verificados, 0 citações faltantes; o campo `failures: 24` é constante do script, não falha da execução).
  - **Pendências registradas como abertas (não resolvidas nesta task):** posicionamento de C10 na cadeia do núcleo; validação de C04 em português; ambiguidades 1–6 da etapa 2; pesquisa específica das etapas 6–7 (C18–C19); feature flag da agenda remota.

## Notas

### Dificuldade esperada
3/10 — A Parte 1 é conferência textual de duas seções com vários números (risco de transcrição dígito a dígito); a Parte 2 exige consolidação cruzada sobre nove tasks sem derivar nem recalcular valores.

### Dificuldade sentida
2/10 — Conferência textual direta com o fonte disponível; o risco principal (transcrição dígito a dígito dos orçamentos) não se concretizou — todos os números bateram na primeira passada. A Parte 2 foi cruzamento de cabeçalhos de tasks e do plano, sem derivação de valores; única atenção foi não recalcular a entrada máxima a partir das reservas e tratar as paráfrases dos limites bibliográficos como fiéis sem "melhorá-las".

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
