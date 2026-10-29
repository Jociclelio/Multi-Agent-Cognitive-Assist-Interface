# Contagens reais versus metas propostas — task 002 do plano 06

Data do registro: 2026-10-29. As metas abaixo são **propostas** (protocolo de
avaliação, seção 2; mapa da etapa 8, seções 4 e 12.1) — não requisitos
fechados e nunca resultados medidos. As faixas de desvio aceitáveis foram
fixadas por escrito antes de qualquer coleta (task 001 do plano 06, decisão
D4) e nenhum desvio foi decidido após observar escores. Em 2026-10-29 (tarde),
a decisão D4 foi **emendada** (subtask 001-1 do plano 06): scans, tabelas como
material, versões conflitantes, resoluções de exercícios e notas de monitoria
são **suplementos opcionais**, fornecidos pelo aluno quando existirem — o
corpus autorizado é construído com o que os professores de fato disponibilizam
e não depende deles; a ausência de cada suplemento é registrada como ausência
e não bloqueia a avaliação. Onde a contagem real é zero, a ausência é
declarada como ausência, com o procedimento de coleta documentado nos
manifestos; nenhum corpus, item ou caso foi fabricado.

## Tabela consolidada

| Conjunto | Meta proposta | Desvio aceitável (D4) | Contagem real | Desvio e justificativa |
|---|---|---|---|---|
| Famílias documentais | 24 (8 dev / 4 val / 12 test; 12 por disciplina) | ≥18 no total; dev ≥6, val ≥3, test ≥9; ≥5 por disciplina; ≥2 scans e ≥2 tabelas (suplementos opcionais pela emenda E1 da D4) | **19 materiais depositados** (redes: 1 PDD, 6 capítulos de slides v9.0, 2 listas de exercícios; aprendizado não supervisionado: 1 PDD, 9 notas de aula em HTML — `eval/corpus/registro-materiais.json`); **0 famílias derivadas**; scans 0, tabelas 0, versões conflitantes 0 | A derivação de famílias pertence à task 003 e não foi iniciada — 0 famílias é ausência registrada, não resultado. O depósito de 2026-10-29 (tarde) dotou o corpus de materiais de fato disponibilizados pelos professores (PDFs digitais e notas de aula). Pela emenda E1 da D4, os mínimos de scans e tabelas deixam de ser bloqueio: são suplementos opcionais fornecidos pelo aluno quando existirem, e sua ausência é registrada como ausência sem bloquear a anotação nem a avaliação. |
| Consultas | 120 por split (80 com suporte / 40 sem) | ≥96 por split; 60–70% com suporte; ≥40 por split por disciplina | **0 em todos os splits** | Coleta adiada: consultas com suporte exigem claims com IDs de fonte ancorados nas famílias documentais, ainda não derivadas (a derivação pertence à task 003). Redigir sobre o subconjunto atual produziria conjunto não representativo e risco de vazamento na rederivação. Procedimento em `consultas/manifesto.json`. |
| Tentativas | 120 por split (60 por disciplina) | ≥90 por split; ≥40 por disciplina; anotação de ajuda/erros em todas | **0 em todos os splits** | Dependem de itens válidos (O05) e da rubrica testada em piloto (task 003), ambos pendentes da derivação de famílias a partir do corpus depositado. Ausência registrada; nenhum diálogo simulado foi apresentado como tentativa real. Procedimento em `tentativas/manifesto.json`. |
| Trajetórias longitudinais | 30 teste + 6 dev + 4 val, 8 sessões cada | teste ≥24, dev ≥4, val ≥3; 8 sessões mantidas (nunca encurtar roteiro silenciosamente) | **0 trajetórias** | O roteiro de 8 sessões ancora em itens e prazos derivados do corpus, ainda não derivados (task 003). O template de roteiro (elementos fixos do protocolo, seção 2) está documentado em `trajetorias/manifesto.json`; os scripts de aluno simulado são mecanismo (etapa 7) e implementação (etapa 8). |
| Agenda — pequenas | 100 com ótimo/viabilidade conhecidos | ≥60 | **100 sintéticas geradas** (40/20/40 exato por família inteira; seeds fixas) | A meta numérica do subconjunto é atingida com dados **sintéticos**, publicáveis por construção (decisão D2). Viabilidade exata por verificador EDF; ótimo afirmado apenas por força de construção na família `f05-demanda-total`. Não são dados coletados nem execuções do sistema. |
| Agenda — realistas | 100 | ≥60 | **0** | Derivam de restrições reais das disciplinas (cronogramas, grades, disponibilidade), que exigem o corpus completo. Ausência registrada com procedimento em `agenda/manifesto.json`. |
| Agenda — bordas | presentes em todos os splits (sem borda, F13 fica sem casos) | — | **6 estruturais** (2 por split; meio-slot, duração não múltipla, ciclo, UNKNOWN, zona DST, prazo na borda) | Cumpre o requisito de presença mínima em todos os splits; os campos `esperado` são especificações estruturais, não resultados de execução. |
| Casos de falha F01–F24 | ≥10 por falha; 3 seeds com geração; crashpoints determinísticos | ≥6 por falha; nenhuma falha sem caso base — inaplicável vira `N/A` com motivo | **0 casos em cada uma das 24 falhas** | Falhas ancoradas em documento exigem famílias documentais derivadas (task 003); falhas de mecanismo dependem dos controladores do testbed (implementação na etapa 8). Nenhuma falha foi declarada `N/A` nesta task — a decisão, se ocorrer, é caso a caso com motivo registrado. Procedimento em `falhas/manifesto.json`. |

## Consequências registradas

1. **A anotação não inicia** (task 003): a contagem real de famílias derivadas
   é zero — a derivação pertence à task 003 e não foi executada nesta task.
   A precondition material da 003 foi **desbloqueada** pela emenda E1 da D4
   (2026-10-29): os mínimos de scans/tabelas deixam de ser bloqueio, e o
   depósito de 19 materiais (2026-10-29, tarde) comporta a derivação de
   famílias a partir do que os professores de fato disponibilizam.
2. **Nenhum split de teste é congelado** nesta task: o congelamento pertence à
   task 003 e precede-o a auditoria de duplicatas/parentesco (mapa 08,
   seção 4).
3. **Dependência de usuário (atualizada)**: o depósito foi realizado em
   2026-10-29 (tarde) com 17 novos materiais (8 PDFs de Redes do Google
   Classroom G_MC832A_2026S2 e 9 notas de aula em HTML de MC847), todos fora
   do Git e registrados em `../corpus/registro-materiais.json`; o PDD do
   Classroom é byte a byte idêntico ao `mat-redes-001` (sem duplicata).
   Suplementos opcionais (scans, tabelas, versões conflitantes, resoluções de
   exercícios, notas de monitoria) ficam a cargo do aluno quando existirem,
   sem bloquear a coleta; a pendência de autorização de redistribuição
   permanece condicional e registrada (decisão D2).
4. **Nada é apresentado como resultado medido**: este registro trata de
   disponibilidade de dados de entrada, não de desempenho do EduAgent-OS. A
   execução experimental pertence à etapa 8; relatos de métricas, quando
   existirem, virão com denominadores e ICs conforme o protocolo (seções 3, 5
   e 6).

## Verificação dos conjuntos sintéticos existentes

- `python3 eval/datasets/scripts/gerar_agenda.py` recria os arquivos byte a
  byte (seed mestre 0; somente biblioteca padrão).
- SHA-256 na emissão: `pequenas.jsonl`
  `ba15a8677a9d63198643954c7ff7264af22907a8c2f40000462edf5e94abda35`;
  `borda.jsonl`
  `3a59d4a2612d33afdd7046437d71668128cb7dce776b0be71cb4e9d1f396c478`.
- Validações embutidas no gerador: 100 pequenas; split 40/20/40 exato;
  nenhuma família repartida entre splits; IDs e conteúdos únicos; reexecução
  do verificador EDF sobre cada instância serializada confirmando o campo
  `esperado.viavel`; 2 bordas por split.
