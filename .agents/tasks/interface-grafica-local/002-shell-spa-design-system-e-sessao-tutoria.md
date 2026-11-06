# Task 002: Shell SPA em 3 Colunas, Design System, Contratos e Sessão de Tutoria

Estado: concluída
Plano: `.agents/plans/interface-grafica-local/plan.md`

## Objetivo

Implementar os contratos TypeScript (`ui/src/contracts.ts`), o núcleo de estado puro e determinístico (`ui/src/state.ts`) e o shell visual em CSS Grid de 3 colunas com gaveta lateral retrátil de evidências (`ui/dist/index.html`, `ui/dist/styles.css`, `ui/src/app.ts` / `ui/dist/app.js`), cobrindo a lista de disciplinas estilo WhatsApp Web, a timeline conversacional do Tutor com escada `L0 -> L1 -> L2 -> L3`, cartões de `LearningItem`, `Assessment` e `EvidencePack` (`SourceRef`).

## Arquivos tocados

- `ui/src/contracts.ts`
- `ui/src/state.ts`
- `ui/src/app.ts`
- `ui/dist/index.html`
- `ui/dist/styles.css`
- `ui/dist/app.js`

## Critérios de corretude

- [x] Layout em CSS Grid com 3 colunas principais (`64px` trilho, `320px` lista de disciplinas, `1fr` painel central) e 4ª coluna retrátil (`340px` gaveta de evidências) usando `100dvh` e `overscroll-behavior: contain`.
- [x] `LearningItem` oculta gabarito (`expected_answer`) até `L3` ou `revealed=true`.
- [x] Clique em badge `[Fonte]` abre a gaveta de evidências com `SourceRef`, documento, página, cobertura e trecho recuperado.

