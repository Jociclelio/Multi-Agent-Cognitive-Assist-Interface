# Task 004: Suíte de Testes Automatizados (Backend, Frontend e E2E) e Documentação

Estado: concluída
Plano: `.agents/plans/interface-grafica-local/plan.md`

## Objetivo

Implementar e executar a suíte de testes automatizados de frontend (`ui/tests/ui_automated_test.ts` via `deno test`) e de backend/E2E (`tests/test_interface_grafica_local.py`), validar que a verificação documental (`fase2/scripts/verificar_documentos.py`) permanece íntegra e atualizar `RELATORIO_ESTADO_E_PROXIMOS_PASSOS.md` com o plano de testes automatizados e o registro da entrega concluída.

## Arquivos tocados

- `ui/tests/ui_automated_test.ts`
- `tests/test_interface_grafica_local.py`
- `RELATORIO_ESTADO_E_PROXIMOS_PASSOS.md`

## Critérios de corretude

- [x] `deno test ui/tests/ui_automated_test.ts` executa e aprova 100% dos testes (`UI-FE-01` a `UI-FE-06`).
- [x] `tests/test_interface_grafica_local.py` executa e aprova 100% dos testes de API loopback e fluxos E2E (`UI-API-01` a `UI-API-07` + E2E 1–3).
- [x] `python3 fase2/scripts/verificar_documentos.py` retorna `{"status": "passed"}`.

