# Task 002: Validar a qualidade por saída O01–O18

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Conferir a seção 2 ("O que constitui qualidade de cada saída") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — a tabela O01–O18 — quanto a: (a) cobertura — as 18 saídas cobrem artefatos internos (O01–O02, O12–O13, O16–O18), saídas ao estudante (O03–O11) e operacionais, sem lacuna de artefato previsto no contrato §4 da etapa 4; (b) fidelidade — "conteúdo necessário" e "perda de qualidade típica" de cada saída são coerentes com o contrato Pydantic/tabela §4 do mapa e com os artefatos reais do sistema implementado (ex.: O14 exige ICS RFC5545 com UID/versão/recibo — ver `eduagent/services/`; O17 traces com falhas incluídas; O18 manifesto com hashes e `uv.lock`); (c) consistência interna — cada saída citada na matriz W01–W12 existe na tabela e vice-versa (todas as O são alcançáveis por algum fluxo). Se encontrar desvio, corrija **apenas o documento 05** em dif mínimo, preservando o sentido normativo, e registre em Evidências.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece); correções no documento 05 somente em dif mínimo com justificativa; nada apresentado como resultado medido (perdas típicas são riscos potenciais, não ocorrências observadas); IDs O01–O18 permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar; commit de entrega e registro separados, sem amend/force-push/commits vazios; submódulo intocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento a materializar (entregável): seção 2, tabela O01–O18 (linhas 22–43).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — contrato de artefatos da tabela §4 e saídas por rota (fonte normativo, intocado).
- `eduagent/`, `manifest.json`, `eval/relatorio-testes-mvp.md` — artefatos reais da v0.1 para coerência (planos 04, tasks 001–017).
- `fase2/scripts/verificar_documentos.py` — verificação documental.

## Corretude
- [ ] C1 — As 18 saídas conferidas item a item contra o contrato §4 e os artefatos reais (conteúdo necessário e perdas típicas), com registro em Evidências; desvios corrigidos em dif mínimo ou justificados.
- [ ] C2 — Consistência interna matriz×tabela confirmada: todo O citado em W01–W12 existe; toda O é alcançável por algum fluxo; nenhuma perda típica descrita como ocorrência medida.
- [ ] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
3/10 — Conferência de tabela de qualidade contra contratos e artefatos reais; exige cruzar 18 linhas com o mapa §4 e o código entregue.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: <SHAs da entrega e versão do registro revisado>
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: <síntese dos achados, evidências, divergências e Corretude pendente>
- Decisão: <fechar | corrigir | reiniciar | repartir; pendente se bloqueada>
- Reversão: <SHA ou não se aplica>
- Próximo passo: <subtasks em ordem ou próxima task liberada>

Plano: [plan.md](../../plans/05-fluxos-resultados-e-falhas/plan.md)
