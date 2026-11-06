# Task 003: Visões Auxiliares, Timer Pomodoro Fail-Closed e Gates de Confirmação

Estado: concluída
Plano: `.agents/plans/interface-grafica-local/plan.md`

## Objetivo

Implementar na Interface Gráfica Local o Timer Pomodoro *fail-closed* sincronizado ao `PlanBlock` ativo com modal `<dialog>` nativo de confirmação, o modal de busca global (`Ctrl+K`) e as 6 visões auxiliares do trilho esquerdo: `Operações / Aprovações`, `Calendário & Demandas` (com `.ics`), `Biblioteca & Ingestão` (com upload confinado), `Revisão & Flashcards` (frente/verso sem gamificação), `Progresso & Domínio` (`TopicState` qualitativo com `estimate=null`) e `Configurações / Diagnóstico` (`doctor`, backup, restore, delete).

## Arquivos tocados

- `ui/src/state.ts`
- `ui/src/app.ts`
- `ui/dist/index.html`
- `ui/dist/styles.css`
- `ui/dist/app.js`

## Critérios de corretude

- [x] Ao atingir `00:00`, o Timer Pomodoro transita para `awaiting_confirmation`, abre `<dialog id="pomodoro-confirm-dialog">` via `showModal()` e nunca dispara `update_activity` (`completed`) sem clique explícito do usuário.
- [x] Modais `<dialog>` seguem boas práticas HTML5 (sem `role="dialog"` ou `aria-modal` redundantes, com `aria-labelledby`, `autofocus` e `overscroll-behavior: contain`).
- [x] Visão de Flashcards separa frente e verso e não exibe streaks, pontos ou rankings.
- [x] Visão de Progresso exibe exclusivamente estados qualitativos (`insufficient`, `mixed`, `favorable`) e preserva `estimate = null`.

