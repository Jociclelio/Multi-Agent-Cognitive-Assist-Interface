# Task 015b: Correção da 015a — fail-closed do confronto com tombstones do domínio corrente no restore

Estado: aguardando revisão
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
- [x] C1 — Teste de regressão novo: banco corrente **presente** porém ilegível (arquivo corrompido/inválido na raiz de dados do restore) + restore de conjunto com payload → recusa tipada (código coerente com o mapa §4, ex. `INTERNAL_FAILURE`) com diretório alvo descartado, sem payload restaurado; a sonda (adaptada de `/tmp/opencode/reviewer-015/probe_a_tombstone.py` ou equivalente nova em `/tmp/opencode`) manifesta a recusa DEPOIS da correção e o comportamento fail-open é documentado como conduta ANTES (leitura de código `backup.py:544-551`, confirmada pelos três revisores).
- [x] C2 — Restore legítimo preservado: TOM-1, TOM-2 e os testes de restore da 015/015a continuam passando; restore sem `domain.sqlite` corrente (raiz isolada) continua funcionando com confronto trivialmente satisfeito; suíte integral verde (533 anteriores + regressões novas, sem quebrar 521).
- [x] C3 — Diferenciação por existência do arquivo implementada (presente+ilegível → recusa tipada; ausente → lista vazia documentada); docstring e limitação registrada na task 015a alinhados ao novo comportamento; mapa, `config/`, `docs/`, submódulo e `uv.lock` intocados; commits de entrega e registro separados.

## Execução
- Modelo: GLM-5.3-Flash (provider `sd2`, model id `GLM-5.3-Flash`, via `~/sd2-llm.sh`) — identidade informada pelo runtime da sessão.
- Base: `23eb88fe61471c25503ef3e044caa749d647ed62` (árvore limpa, pós-criação da subtask; entrega da 015a `e17cbf0` preservada sem reversão).
- Entrega: `a9fb8aa349063cefce656555adf0c1b8ce71af6c` (commit de código; commit de registro é este, encontrado por `git log -- <task.md>`).
- Arquivos da entrega: `eduagent/services/backup.py` (`_current_domain_tombstones` fail-closed: existência do arquivo verificada ANTES de abrir a conexão — ausente → lista vazia documentada (raiz isolada, §15.1); presente + qualquer `sqlite3.Error` (conexão ou leitura, incl. arquivo corrompido/sem tabela) → `EduAgentError` `INTERNAL_FAILURE` com a causa preservada via `from exc`, atravessando o fluxo de restore que já descarta o diretório alvo em falha; docstring alinhada), `tests/test_task015b_correcoes.py` (novo; 2 regressões TOM-3/TOM-4). Módulo de erros não precisou de alteração (`INTERNAL_FAILURE` já existe no conjunto fechado do §4).

### Evidências (Corretude)

- **Sonda antes/depois** (`/tmp/opencode/015b/probe_failclosed.py`; saídas em `/tmp/opencode/015b/probe_ANTES.txt` e `probe_DEPOIS.txt`; cenário: evento com payload marcado → backup pré-deleção → deleção com tombstone → banco corrente `domain.sqlite` sobrescrito com bytes não-SQLite (presente, ilegível) → restore do backup pré-deleção):
  - ANTES (`backup.py:544-551`, `except sqlite3.Error: return []` — reproduzido na base antes da edição): `RESTORE: restored`; `payload excluído vivo no conjunto restaurado? True`; `diretório alvo existe? True` — fail-open: restore liberado SEM confrontar tombstones do domínio corrente, payload excluído ressuscitado (violação §15.1; achado alto luna-A1 confirmado).
  - DEPOIS: `RECUSA TIPADA: ErrorCode.INTERNAL_FAILURE: banco de domínio corrente presente porém ilegível — tombstones do §15.1 não podem ser confrontados no restore: file is not a database`; `diretório alvo descartado? True`.
- **C1**: TOM-3 em `tests/test_task015b_correcoes.py` fixa a recusa tipada `INTERNAL_FAILURE` com mensagem "ilegível" e diretório alvo descartado (`assert not target.exists()`).
- **C2**: TOM-4 fixa a diferenciação — sem `domain.sqlite` corrente, `_current_domain_tombstones()` retorna `[]` e o restore legítimo completa com `current_domain_tombstones_checked == 0` (confronto trivialmente satisfeito, raiz isolada); TOM-1, TOM-2 e as 12 regressões da 015a continuam passando (14 passed em `tests/test_task015b_correcoes.py + tests/test_task015a_correcoes.py`); suíte integral DEPOIS: **535 passed** em 28,8 s (baseline ANTES reproduzida: **533 passed** em 29,4 s — 521 anteriores + 12 da 015a; 2 warnings pré-existentes), sem regressões.
- **C3**: diferenciação por `domain_path.exists()` antes de abrir a conexão (arquivo presente → qualquer `sqlite3.Error` em conexão ou leitura recusa por código; arquivo ausente → lista vazia documentada no docstring); "Limitação registrada" da task 015a alinhada (parágrafo atualizado apontando o comportamento fail-closed da 015b); `git status`/`git diff --stat` confirmando alteração somente em `eduagent/services/backup.py`, `tests/test_task015b_correcoes.py` e `.agents/` (registro); `fase2/` (mapa), `config/`, `docs/` e `uv.lock` sem diff; submódulo `docs/playground-llmagenticsystem` intocado; commit de entrega `a9fb8aa` separado deste registro.
- Verificação adicional: `py_compile` OK em `eduagent/services/backup.py`.

### Limitações e pendências registradas

- A recusa tipada cobre `sqlite3.Error` na conexão e na leitura do banco corrente; falhas de leitura FORA dessa classe no mesmo arquivo (ex.: permissão de SO negada também elevada como `sqlite3.OperationalError` — coberta) continuam resguardadas pelo fluxo de restore, que descarta o diretório em qualquer exceção; nenhum caminho conhecido retorna `[]` com o arquivo presente.
- Nada apresentado como resultado medido: contagens da suíte são contagens de testes; defaults e garantias permanecem os do mapa §5/§15.1.

### Dificuldade sentida
2/10 — Correção local e unificada conforme a estimativa: a diferenciação por existência do arquivo e o ponto de recusa foram diretos, o fluxo de restore já descartava o diretório alvo em qualquer exceção (nenhuma mudança de fluxo adicional necessária), e a sonda reproduziu o fail-open ANTES e a recusa DEPOIS de primeira. Único atrito: ajustar a sonda (conversão `bytes` na verificação do payload no conjunto restaurado).

## Notas

### Dificuldade esperada
2/10 — Correção local e unificada num único ponto de falha, com o comportamento ANTES inequívoco (leitura de código convergente entre os três revisores) e o caminho legítimo já coberto por testes existentes.

### Dificuldade sentida
2/10 — Correção local e unificada num único ponto de falha, com o comportamento ANTES inequívoco (leitura de código convergente entre os três revisores) e o caminho legítimo já coberto por testes existentes. Registrada pelo executor na seção Execução.

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
