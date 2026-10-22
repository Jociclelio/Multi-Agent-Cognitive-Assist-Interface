# Task 015b: Correção da 015a — fail-closed do confronto com tombstones do domínio corrente no restore

Estado: pendente
Depende de: 015a
Origem: task mãe 015a — correção (decisão `corrigir`, revisão com quórum GLM 9/10, qwen3-27b 9/10, gpt-6-luna 8/10)

## Prompt
Corrigir pontualmente a entrega da task 015a (commit `e17cbf0`, preservado sem reversão; design aprovado). Único item obrigatório, com a divergência da revisão como prova:

1. **Fail-closed no confronto com tombstones do domínio corrente (achado alto, luna-A1 da revisão da 015a; mesma conduta classificada baixa por GLM e qwen, ambos recomendando recusa)** — `eduagent/services/backup.py` (`_current_domain_tombstones`, ~linhas 544-551): `except sqlite3.Error: return []` faz o restore **prosseguir sem confrontar tombstones** quando o `domain.sqlite` corrente existe mas está corrompido, ilegível ou sem a tabela esperada — podendo restaurar payload excluído, violando a garantia do §15.1 e o critério C2 da 015a ("nenhum ref tombstonado resolva vivo no conjunto liberado"). Corrigir para fail-closed: quando o banco corrente **existe** mas não pode ser consultado, recusar o restore com erro tipado (sem aplicar o restore) e descartar o diretório alvo; reservar lista vazia (confronto trivialmente satisfeito) **apenas** para a ausência documentada do banco (raiz isolada, sem `domain.sqlite`), que é o caso já coberto pelos testes legítimos da 015/015a. Distinguir as duas situações por existência do arquivo (`os.path.exists`/`Path.exists`) antes de abrir a conexão; qualquer `sqlite3.Error` (ou falha equivalente de leitura) com o arquivo presente é recusa tipada, nunca `[]` mudo. Alinhar docstring e a "Limitação registrada" na task 015a ao novo comportamento.

Restrições: preservar o design e a entrega da 015/015a; tocar apenas `eduagent/services/backup.py` (e, se estritamente necessário para o erro tipado, o módulo de erros correspondente) e `tests/`; mapa, `config/`, `docs/` e submódulo intocados; sem dependência nova (`uv.lock` inalterado); nada apresentado como resultado medido; temporários em `/tmp/opencode`. Commits SEPARADOS: entrega (código) e registro (task.md com SHAs/evidências). Suíte integral deve permanecer verde (533 passed no momento, mais regressões novas) sem quebrar os 521 testes anteriores.

## Contexto
- `.agents/tasks/04-mapa-completo-do-sistema/015a-correcao-ownership-restore-e-api-json.md` — task mãe com a Revisão completa (achados A1 luna, F1 qwen, residual A1 GLM), a entrega e as escolhas documentadas.
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §15.1 (tombstones antes de liberar restore; §15 prevalece quando mais preciso). INTOCADO.
- `eduagent/services/backup.py` — alvo da correção (`_current_domain_tombstones`, chamada no fluxo de restore; ver também o verificador e a cópia que consomem o resultado).
- `tests/test_task015a_correcoes.py` — regressões TOM-1/TOM-2 existentes, que não devem quebrar (restore sem banco corrente e recusa por tombstone do manifesto permanecem válidos).
- Precedente de estilo: `.agents/tasks/04-mapa-completo-do-sistema/014a-correcao-seguranca-paths-fetch-e-limites.md` — correção delimitada de fail-open de segurança.

## Corretude
- [ ] C1 — Teste de regressão novo: banco corrente **presente** porém ilegível (arquivo corrompido/inválido na raiz de dados do restore) + restore de conjunto com payload → recusa tipada (código coerente com o mapa §4, ex. `INTERNAL_FAILURE`) com diretório alvo descartado, sem payload restaurado; a sonda (adaptada de `/tmp/opencode/reviewer-015/probe_a_tombstone.py` ou equivalente nova em `/tmp/opencode`) manifesta a recusa DEPOIS da correção e o comportamento fail-open é documentado como conduta ANTES (leitura de código `backup.py:544-551`, confirmada pelos três revisores).
- [ ] C2 — Restore legítimo preservado: TOM-1, TOM-2 e os testes de restore da 015/015a continuam passando; restore sem `domain.sqlite` corrente (raiz isolada) continua funcionando com confronto trivialmente satisfeito; suíte integral verde (533 anteriores + regressões novas, sem quebrar 521).
- [ ] C3 — Diferenciação por existência do arquivo implementada (presente+ilegível → recusa tipada; ausente → lista vazia documentada); docstring e limitação registrada na task 015a alinhados ao novo comportamento; mapa, `config/`, `docs/`, submódulo e `uv.lock` intocados; commits de entrega e registro separados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
2/10 — Correção local e unificada num único ponto de falha, com o comportamento ANTES inequívoco (leitura de código convergente entre os três revisores) e o caminho legítimo já coberto por testes existentes.

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
