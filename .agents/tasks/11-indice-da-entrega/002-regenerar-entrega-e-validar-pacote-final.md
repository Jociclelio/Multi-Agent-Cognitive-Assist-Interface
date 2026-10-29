# Task 002: Regenerar a entrega quando necessário e validar o pacote final

Estado: pendente
Depende de: 001
Origem: nenhuma

## Prompt
Fechar a etapa 11: (1) Se as tasks anteriores desta família (ou as etapas 9–10) deixaram alteração documental pendente de publicação — ou a conferência da task 001 revelou entrega dessincronizada — regenerar/publicar com `python3 fase2/scripts/gerar_entrega.py` (valida antes; roda `pdflatex → bibtex → pdflatex → pdflatex`; rejeita citações/referências indefinidas e overfull boxes; valida CRCs de ZIP e SHA-256; sobrescreve ambos os PDFs, `verificacao_documental.json`, `SHA256SUMS.txt` e o ZIP). Pré-requisitos: `/tmp/opencode/`, `pdflatex`, `bibtex`, pacotes TeX de `fase2/README-entrega.md`. (2) Se NADA mudou desde a última entrega íntegra, registrar a decisão de NÃO reconstruir com evidência (git status limpo, hashes comparados) — reconstrução desnecessária é ruído de revisão. (3) Validação final do pacote: `sha256sum -c fase2/SHA256SUMS.txt` sem falhas, CRCs do ZIP válidos, índice coerente com o pacote publicado. (4) Atualizar o índice APENAS se a lista de arquivos ou a estrutura do pacote mudar, em dif mínimo, prosa acadêmica em português. (5) Consolidar na task o estado final da etapa 11 e do pacote de entrega como um todo.

Restrições: sem alteração de conteúdo científico; sem verificação de frescor de PDFs além do que o script faz; sem integração Google Drive; nada apresentado como resultado medido; commits entrega/registro separados; submódulo não tocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/scripts/gerar_entrega.py` — rebuild/publicação da entrega (valida antes de compilar).
- `fase2/README-entrega.md` — requisitos do ambiente de compilação.
- `fase2/documentos/11_indice_da_entrega.md` — índice a manter sincronizado.
- `fase2/SHA256SUMS.txt` e `fase2/eduagent_fase2_entrega.zip` — integridade final do pacote.
- `.agents/tasks/11-indice-da-entrega/001-conferir-indice-e-verificacoes-documentais.md` — estado das verificações (insumo da decisão de reconstruir ou não).

## Corretude
- [ ] C1 — Decisão de reconstrução correta e evidenciada: regeneração via `gerar_entrega.py` concluída sem indefinidas/overfull quando havia mudança pendente, ou dispensa registrada com git status/hashes quando não havia.
- [ ] C2 — Pacote final validado: `sha256sum -c fase2/SHA256SUMS.txt` sem falhas, CRCs do ZIP válidos, `verificacao_documental.json` atualizado quando regenerado.
- [ ] C3 — Índice sincronizado com o pacote publicado (dif mínimo apenas se a estrutura mudou); consolidação final da etapa registrada; commits entrega/registro separados.

## Execução
- Modelo: —
- Base: —
- Entrega: —
- Arquivos da entrega: —
- Evidências: —

## Notas

### Dificuldade esperada
3/10 — Build e validação mecânica com decisão binária de reconstruir; o risco é reconstruir sem necessidade (difiultando a revisão de frescor) ou pular a regeneração com mudança pendente.

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

Plano: [plan.md](../../plans/11-indice-da-entrega/plan.md)
