# Task 002: Montar o corpus autorizado e os conjuntos por split

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Montar o corpus autorizado das duas disciplinas definidas na task 001 e construir os conjuntos do desenho (seção 2 do protocolo), respeitando os desvios aceitáveis definidos na 001: (1) famílias documentais cobrindo a variedade do protocolo (PDFs digitais, scans, tabelas, versões conflitantes), divididas em desenvolvimento/validação/teste (meta: 8/4/12); (2) consultas e tentativas por conjunto (meta: 120 consultas e 120 tentativas por split, itens distintos por split, sem vazamento); (3) trajetórias longitudinais com 8 sessões cada, roteirizadas com scripts fixos de aluno simulado (meta: 30); (4) instâncias de agenda pequenas com ótimo/viabilidade conhecidos e instâncias realistas, mais casos de borda (split meta 40/20/40%); (5) no mínimo 10 casos base por falha F01–F24, com 3 seeds quando houver geração e crashpoints determinísticos. Splits por família/trajetória (nunca repartir parentes entre splits); registrar estrutura, contagens reais versus metas e os desvios com justificativa; nada redistribuído sem permissão.

Restrições: as metas de quantidade são propostas — registrar contagens reais e desvios, nunca apresentar metas como resultados medidos; IDs F01–F24 e O01–O18 permanentes; prosa em português; commit de entrega (datasets/estrutura) e commit de registro separados; submódulo `docs/playground-llmagenticsystem` não tocado; materiais autorizados não vão para o Git sem permissão explícita (registrar referências de acesso quando o material não puder ser commitado); temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/06_protocolo_de_avaliacao.md` — seção 2: composição dos conjuntos, variedade documental e regras de split.
- `.agents/tasks/06-protocolo-de-avaliacao/001-definir-corpus-autorizacoes-e-desvios-aceitaveis.md` — disciplinas escolhidas, autorizações e desvios aceitáveis (insumo desta task).
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — catálogo F01–F24 (casos base por falha) e O01–O18.
- `fase2/documentos/08_mapa_completo_da_testagem.md` — §4 e §12.1: metas e targets de captura do dataset que os conjuntos devem atender (consultar, não implementar aqui).

## Corretude
- [ ] C1 — Corpus montado com as duas disciplinas e variedade documental do protocolo; fonte e autorização de cada material registradas (ou referência de acesso quando o material não puder ser versionado).
- [ ] C2 — Conjuntos construídos por split (famílias, consultas/tentativas, trajetórias, agenda, ≥10 casos por F01–F24) sem vazamento entre splits e sem repartir parentes; contagens reais versus metas registradas com os desvios justificados pelos limites definidos na 001.
- [ ] C3 — Estrutura dos conjuntos documentada de forma reproduzível (localização, formato, procedimento de geração com seeds quando aplicável); nada apresentado como resultado medido.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
6/10 — Coleta real de materiais autorizados com controle de vazamento e cobertura das 24 famílias de falha; volume alto de trabalho manual e dependência de autorizações.

### Dificuldade sentida
_/10 — <Justificativa do executor, na mesma escala.>

### Revisão
- Orquestrador: —
- Alvo: —
- Avaliações: <modelo A: _/10; modelo B: _/10; modelo C: _/10>
- Nota final: _/10
- Parecer: —
- Decisão: —
- Reversão: —
- Próximo passo: —

Plano: [plan.md](../../plans/06-protocolo-de-avaliacao/plan.md)
