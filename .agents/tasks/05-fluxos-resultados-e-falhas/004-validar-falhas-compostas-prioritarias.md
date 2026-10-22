# Task 004: Validar as seis falhas compostas prioritárias e suas exigências

Estado: pendente
Depende de: 003
Origem: nenhuma

## Prompt
Conferir a seção 4 ("Falhas compostas prioritárias") de `fase2/documentos/05_fluxos_resultados_e_falhas.md` — os 6 cenários compostos — quanto a: (a) fidelidade — cada cenário encadeia falhas do catálogo F01–F24 de forma coerente (OCR→prazo errado envolve F01/F02; erro correlacionado Tutor/Monitor envolve F06/F09; retry pós-timeout sobrescrevendo mudança externa envolve F14/F15; invalidação transitiva de resumo envolve F21; reexecução sem `operation_id` envolve F15 e o contrato §11; falhas fora do denominador de p95 envolve F22/F23); (b) exigências — cada cenário registra a exigência de mitigação correspondente (validação independente de fontes/julgamento; snapshot/ETag e reconciliação; invalidação transitiva; idempotência por `operation_id`; falhas permanentes no denominador) sem contradizer §11 (commit idempotente), §15.1 (snapshot/`domain_revision`) e §15.5 (verificador independente) do mapa; (c) honestidade — a ressalva de que o solver/verificador não elimina as falhas de montante (cenário 1) e que checkpoint sozinho não garante idempotência (cenário 5) permanece no texto. Se encontrar desvio, corrija **apenas o documento 05** em dif mínimo, preservando o sentido normativo, e registre em Evidências.

Restrições: `fase2/documentos/04_mapa_completo_do_sistema.md` é INTOCADO ("deve" é contrato; §15 prevalece); correções no documento 05 somente em dif mínimo com justificativa; cenários compostos são riscos potenciais — nada apresentado como ocorrência observada; IDs F permanentes; prosa em português; `python3 fase2/scripts/verificar_documentos.py` deve passar; commit de entrega e registro separados, sem amend/force-push/commits vazios; submódulo intocado; temporários em `/tmp/opencode`.

## Contexto
- `fase2/documentos/05_fluxos_resultados_e_falhas.md` — documento a materializar (entregável): seção 4, cenários 1–6 (linhas 76–83).
- `fase2/documentos/04_mapa_completo_do_sistema.md` — §11 idempotência, §12 checkpoint/limites, §15.1 snapshot, §15.5 verificador (fonte normativo, intocado).
- Registros das tasks 005/010a/013a/015b/016/016a do plano 04 — implementação real de idempotência, reconciliação com ETag, invalidação e fail-closed para coerência.
- `fase2/scripts/verificar_documentos.py` — verificação documental.

## Corretude
- [ ] C1 — Os 6 cenários conferidos item a item: encadeamento de falhas coerente com o catálogo e exigências de mitigação registradas, sem contradição com §11/§15.1/§15.5 do mapa; desvios corrigidos em dif mínimo ou justificados.
- [ ] C2 — Ressalvas de honestidade preservadas (solver não elimina falha de montante; checkpoint não garante idempotência; falhas no denominador); nada como ocorrência medida.
- [ ] C3 — `python3 fase2/scripts/verificar_documentos.py` passa; mapa intocado; commits entrega/registro separados.

## Execução
- Modelo: <identificador real do executor>
- Base: <SHA completo antes da implementação>
- Entrega: <SHA(s) completos, sem commits de registro, ou sem alteração de artefatos>
- Arquivos da entrega: <paths ou referência ao diff dos commits>
- Evidências: <comandos/procedimentos, resultados e limitações>

## Notas

### Dificuldade esperada
4/10 — Seis cenários de encadeamento exigem rastrear cadeias entre falhas e exigências de mitigação até §11/§15; risco de reinterpretar exigência como solução implementada.

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
