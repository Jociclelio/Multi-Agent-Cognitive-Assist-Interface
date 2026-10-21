# Task 017: Ensaio longitudinal offline, congelamento e relatório de testes (mapa §13.8/10, §13.235)

Estado: pendente
Depende de: 016
Origem: nenhuma

## Prompt
Fechar o MVP (mapa §13.8 e §13.10, aceite §13.235): (1) ensaio longitudinal offline da rota completa (ingestão → pergunta/prática com pausas e retomadas → avaliação → replanejamento → exportação ICS → crash/recuperação), em dados de teste locais, dentro de limites de tempo razoáveis — se o ensaio exigir execução inviável no hardware, registrar o impedimento documentado em vez de encurtar silenciosamente o protocolo. (2) Congelar o manifesto: `manifest.json` e `uv.lock` com versões reais de pacotes, modelo, tokenizer, skills (hash) e perfil de sampling selecionado; a configuração é congelada antes do teste final; timezone só fixado após confirmação explícita (sem confirmação, registrar pendência e manter padrão neutro). (3) Verificar o aceite funcional do mapa §13.235 item a item, com evidência executável ou de inspeção: cada rota termina com estado definido; cada artefato cumpre o contrato §4; toda citação resolve; toda escrita tem recibo/versionamento; nenhum plano sem validação do verificador é publicado como aprovado; nenhum ICS sem plano confirmado; sessão retomada preserva item/ajuda/histórico; regra de evidências `insufficient/mixed/favorable` exata; ingestão acima dos limites recusada ou dividida; `MODEL_NOT_ADMITTED` bloqueia tutoria. (4) Emitir o relatório de testes conforme a etapa 8 (`fase2/documentos/08_mapa_completo_da_testagem.md` — referência; critérios quantitativos e dados são do mapa8), sem preencher ausência de resultados experimentais com estimativas inventadas: ausência de resultado é declarada como ausência. Baselines/ablações do mapa §13.10 pertencem à etapa 8: registrar o que fica para o mapa8, sem executar aqui.

## Contexto
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §13.8, §13.10, §13.235.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — referência para o formato do relatório (fora do escopo implementar sua suite quantitativa).
- Sistema completo (001–016).

## Corretude
- [ ] C1 — Ensaio longitudinal offline executado ou impedimento documentado; crash/recuperação e pausa/retomada comprovados no ensaio.
- [ ] C2 — Manifesto congelado com versões/hash reais; config congelada antes do teste final; timezone pendente se não confirmado.
- [ ] C3 — Aceite §13.235 verificado item a item com evidência registrada; nenhuma saída parcial aprovada silenciosamente.
- [ ] C4 — Relatório de testes conforme etapa 8, sem resultados inventados; baselines/ablações registrados como escopo do mapa8; mapa intocado; commits separados.

## Notas

### Dificuldade esperada
6/10 — Consolidação de aceite com execução real; risco de inflar resultados ou encurtar o ensaio.

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

Plano: [plan.md](../../plans/04-mapa-completo-do-sistema/plan.md)
