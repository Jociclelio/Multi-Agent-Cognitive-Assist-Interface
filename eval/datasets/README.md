# Datasets da etapa 6 — estrutura, regra de split e estado atual

Este diretório materializa a seção 2 do protocolo de avaliação
(`fase2/documentos/06_protocolo_de_avaliacao.md`): os conjuntos do desenho
experimental (famílias documentais, consultas, tentativas, trajetórias
longitudinais, agenda e casos de falha F01–F24). O corpus restrito que
alimenta os conjuntos fica em `../corpus/` (originais fora do Git; registro
por material em `../corpus/registro-materiais.json`).

## Estado atual (task 002 do plano 06, 2026-10-29)

| Conjunto | Real | Meta proposta | Estado |
|---|---|---|---|
| Famílias documentais | 2 materiais (PDF digital; 0 famílias derivadas) | 24 famílias (8/4/12) | aguardando coleta |
| Consultas | 0 por split | 120 por split | aguardando coleta |
| Tentativas | 0 por split | 120 por split | aguardando coleta |
| Trajetórias (8 sessões) | 0 | 30 teste + 6 dev + 4 val | aguardando coleta |
| Agenda pequenas | 100 sintéticas (40/20/40) | 100 | completo (sintético) |
| Agenda realistas | 0 | 100 | aguardando coleta |
| Agenda bordas | 6 estruturais (2 por split) | presentes em todos os splits | completo (estrutural) |
| Casos de falha F01–F24 | 0 por falha | ≥10 por falha | aguardando coleta |

As metas são propostas, não requisitos fechados nem resultados medidos. As
contagens reais, os desvios e suas justificativas estão consolidados em
`contagens-vs-metas.md` e nos manifestos de cada conjunto. As faixas de desvio
aceitáveis foram fixadas antes de qualquer coleta (task 001 do plano 06,
decisão D4) e nenhuma foi decidida após observar escores.

## Árvore de diretórios

```
eval/datasets/
  README.md               este arquivo (estrutura, regra de split, estado)
  contagens-vs-metas.md   contagens reais versus metas, desvios e consequências
  splits.json             regra de split e atribuição atual por família
  familias/manifesto.json
  consultas/manifesto.json
  tentativas/manifesto.json
  trajetorias/manifesto.json
  agenda/manifesto.json
  agenda/pequenas.jsonl   100 instâncias sintéticas (seed mestre 0)
  agenda/borda.jsonl      6 casos de borda estruturais (2 por split)
  falhas/manifesto.json
  scripts/gerar_agenda.py gerador determinístico + verificador EDF
```

## Regra de split (resumo)

Splits por família documental, por família de parâmetros e por trajetória;
parentes nunca são repartidos entre desenvolvimento/validação/teste. Itens são
distintos por split (sem variações vazadas do mesmo enunciado); o par
limpo/perturbado de caso de falha fica no mesmo split. A auditoria de
duplicatas/parentesco e de referências de ouro (mapa 08, seção 4) precede o
congelamento do teste, que ocorre na task 003. Detalhes e atribuição atual em
`splits.json`.

## Reprodução dos conjuntos sintéticos

```
python3 eval/datasets/scripts/gerar_agenda.py
```

Somente biblioteca padrão; recria `agenda/pequenas.jsonl` e
`agenda/borda.jsonl` byte a byte a partir da seed mestre 0. As instâncias são
sintéticas: não derivam do corpus restrito, não representam dados coletados e
são publicáveis conforme a decisão D2 da task 001 (hashes, IDs, manifestos e
exemplos sintéticos). A viabilidade de cada pequena é verificada de forma
exata por EDF para tarefas unitárias implementado no próprio gerador; o valor
de ótimo é afirmado apenas por força de construção na família
`f05-demanda-total`.

## Limites de escopo registrados

- Nada neste diretório é resultado medido do EduAgent-OS; são dados de entrada,
  especificações e procedimentos. A execução experimental pertence à etapa 8
  (plano 08); os mecanismos por célula, à etapa 7 (plano 07).
- Os IDs F01–F24 e O01–O18 são permanentes (origem:
  `fase2/documentos/05_fluxos_resultados_e_falhas.md`) e não são renumerados.
- Os thresholds da seção 3 do protocolo são gates de engenharia do corpus
  escolhido; nenhum threshold foi criado ou ampliado nesta task.
- Casos de falha marcados como inaplicáveis à v0.1 viram `N/A` com motivo
  registrado, nunca omissão (decisão D4); nenhuma foi declarada nesta task.
- O fuso horário da v0.1 permanece pendente de confirmação (plano 04); as
  instâncias de agenda usam horário local de parede com o campo `zona: null`.
