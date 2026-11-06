/**
 * Suíte Automatizada de Testes do Frontend (Deno Test) — EduAgent-OS v0.1
 * Cobre UI-FE-01 a UI-FE-06 conforme especificado em `Relatorio da interface.md` (§2.1)
 * e `.agents/tasks/interface-grafica-local/004-testes-automatizados-ui-api-e2e.md`.
 *
 * Execução offline (zero dependências remotas):
 *   deno test --allow-read ui/tests/ui_automated_test.ts
 */

import type {
  CourseSummary,
  ErrorCode,
  FlashcardItem,
  LearningItem,
  TypedError,
} from "../src/contracts.ts";
import {
  canRevealAnswer,
  confirmPomodoroCompletion,
  createFlashcardSession,
  createPomodoroState,
  DEFAULT_BREAK_SECONDS,
  DEFAULT_FOCUS_SECONDS,
  describeHelpLevel,
  describeTypedError,
  evaluateRuntimeBanner,
  filterCourses,
  flipFlashcard,
  formatPomodoroClock,
  nextHelpLevel,
  pausePomodoro,
  rateFlashcard,
  resolvePlanBlockDurationSeconds,
  sanitizeLearningItemForDisplay,
  sortCoursesDeterministically,
  startPomodoro,
  tickPomodoro,
} from "../src/state.ts";

function assert(condition: unknown, message = "Asserção falhou"): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertEquals<T>(actual: T, expected: T, message?: string): void {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(
      `${message ? message + ": " : ""}esperado ${expectedJson}, obtido ${actualJson}`,
    );
  }
}

function makeCourse(overrides: Partial<CourseSummary> & { id: string; title: string }): CourseSummary {
  return {
    id: overrides.id,
    user_id: overrides.user_id ?? "00000000-0000-0000-0000-000000000001",
    title: overrides.title,
    aliases: overrides.aliases ?? [],
    revision: overrides.revision ?? 1,
    topics: overrides.topics ?? [],
    active_doc_count: overrides.active_doc_count ?? 0,
    indexed_doc_count: overrides.indexed_doc_count ?? 0,
    ready_to_study: overrides.ready_to_study ?? false,
    sort_tier: overrides.sort_tier ?? 4,
    sort_key_secondary: overrides.sort_key_secondary ?? overrides.title.toLowerCase(),
    sort_reason_label: overrides.sort_reason_label ?? "Sem atividade recente",
    recommended_intent: overrides.recommended_intent ?? "/ingest",
    pending_demands_count: overrides.pending_demands_count ?? 0,
    active_plan_block: overrides.active_plan_block ?? null,
    last_turn_preview: overrides.last_turn_preview ?? "",
    last_activity_at: overrides.last_activity_at ?? null,
    domain_status: overrides.domain_status ?? "insufficient",
    topic_states_summary: overrides.topic_states_summary ?? {
      insufficient: 1,
      mixed: 0,
      favorable: 0,
    },
    attempts_count: overrides.attempts_count ?? 0,
  };
}

// ============================================================================
// UI-FE-01: Ordenação Determinística e Filtros da Coluna de Disciplinas (D3)
// ============================================================================
Deno.test("UI-FE-01: ordena disciplinas pelas 4 faixas determinísticas (D3) e desempata por sort_key_secondary e título pt-BR", () => {
  const cTier4B = makeCourse({
    id: "c-4b",
    title: "Zootecnia Geral",
    sort_tier: 4,
    sort_key_secondary: "zootecnia",
  });
  const cTier4A = makeCourse({
    id: "c-4a",
    title: "Algoritmos e Grafos",
    sort_tier: 4,
    sort_key_secondary: "algoritmos",
  });
  const cTier3 = makeCourse({
    id: "c-3",
    title: "Física Quântica",
    sort_tier: 3,
    ready_to_study: true,
    active_doc_count: 1,
    sort_key_secondary: "0001_fisica",
  });
  const cTier2Late = makeCourse({
    id: "c-2-late",
    title: "Cálculo Numérico",
    sort_tier: 2,
    pending_demands_count: 1,
    sort_key_secondary: "2026-06-20",
  });
  const cTier2Early = makeCourse({
    id: "c-2-early",
    title: "Álgebra Linear",
    sort_tier: 2,
    pending_demands_count: 2,
    sort_key_secondary: "2026-06-10",
  });
  const cTier1 = makeCourse({
    id: "c-1",
    title: "Sistemas Multiagente",
    sort_tier: 1,
    ready_to_study: true,
    active_doc_count: 2,
    sort_key_secondary: "2026-06-05T14:00:00Z",
    active_plan_block: {
      id: "blk-1",
      status: "planned",
      planned_start_utc: "2026-06-05T14:00:00Z",
      planned_end_utc: "2026-06-05T14:45:00Z",
    },
  });

  const sorted = sortCoursesDeterministically([
    cTier4B,
    cTier2Late,
    cTier3,
    cTier1,
    cTier4A,
    cTier2Early,
  ]);

  assertEquals(
    sorted.map((c) => c.id),
    ["c-1", "c-2-early", "c-2-late", "c-3", "c-4a", "c-4b"],
    "A ordem deve respeitar estritamente sort_tier 1 < 2 < 3 < 4 e sort_key_secondary",
  );

  // Filtro "ready": apenas ready_to_study === true
  const readyOnly = filterCourses(sorted, "ready");
  assertEquals(
    readyOnly.map((c) => c.id),
    ["c-1", "c-3"],
  );

  // Filtro "scheduled": apenas sort_tier === 1
  const scheduledOnly = filterCourses(sorted, "scheduled");
  assertEquals(
    scheduledOnly.map((c) => c.id),
    ["c-1"],
  );

  // Filtro "pending_approval": demandas pendentes > 0 ou sort_tier <= 2
  const pendingApproval = filterCourses(sorted, "pending_approval");
  assertEquals(
    pendingApproval.map((c) => c.id),
    ["c-1", "c-2-early", "c-2-late"],
  );

  // Filtro textual por título, preview ou tópico
  const withTopic = makeCourse({
    id: "c-topic",
    title: "Biologia Celular",
    sort_tier: 4,
    last_turn_preview: "Revisão sobre mitocôndrias",
    topics: [{ id: "t-1", course_id: "c-topic", title: "Ciclo de Krebs", aliases: [], revision: 1 }],
  });
  const byTopicQuery = filterCourses([...sorted, withTopic], "all", "krebs");
  assertEquals(byTopicQuery.map((c) => c.id), ["c-topic"]);
});

// ============================================================================
// UI-FE-02: Máquina de Estados do Timer Pomodoro Fail-Closed (D5)
// ============================================================================
Deno.test("UI-FE-02: máquina de estados do Timer Pomodoro é fail-closed e nunca emite auto-conclusão ao zerar", () => {
  // Estudo livre sem PlanBlock -> 25 min (1500s)
  const freePomodoro = createPomodoroState(null);
  assertEquals(freePomodoro.phase, "idle");
  assertEquals(freePomodoro.totalSeconds, DEFAULT_FOCUS_SECONDS);
  assertEquals(freePomodoro.remainingSeconds, 1500);
  assertEquals(freePomodoro.autoCompletedForbidden, true);
  assertEquals(formatPomodoroClock(freePomodoro.remainingSeconds), "25:00");

  // Com PlanBlock de 45 minutos -> 2700s
  const courseWith45mBlock = {
    id: "course-1",
    active_plan_block: {
      id: "block-45m",
      status: "planned",
      planned_start_utc: "2026-06-05T14:00:00Z",
      planned_end_utc: "2026-06-05T14:45:00Z",
    },
  };
  assertEquals(resolvePlanBlockDurationSeconds(courseWith45mBlock.active_plan_block), 45 * 60);

  let state = createPomodoroState(courseWith45mBlock);
  assertEquals(state.totalSeconds, 2700);
  assertEquals(state.planBlockId, "block-45m");

  // Inicia foco e pausa
  state = startPomodoro(state);
  assertEquals(state.phase, "running_focus");
  state = pausePomodoro(state);
  assertEquals(state.phase, "paused");

  // Tick enquanto pausado não altera o relógio
  const pausedTick = tickPomodoro(state, 60);
  assertEquals(pausedTick.state.remainingSeconds, 2700);
  assertEquals(pausedTick.emittedTurnPayload, null);

  // Retoma foco e avança até zerar (00:00)
  state = startPomodoro(state);
  const partialTick = tickPomodoro(state, 2000);
  assertEquals(partialTick.state.phase, "running_focus");
  assertEquals(partialTick.state.remainingSeconds, 700);
  assertEquals(partialTick.emittedTurnPayload, null);

  const zeroTick = tickPomodoro(partialTick.state, 700);
  assertEquals(zeroTick.state.phase, "awaiting_confirmation");
  assertEquals(zeroTick.state.remainingSeconds, 0);
  assertEquals(zeroTick.state.confirmationModalOpen, true);
  assertEquals(
    zeroTick.emittedTurnPayload,
    null,
    "Invariante D5: zerar o cronômetro NUNCA emite requisição automática de conclusão",
  );
  assertEquals(formatPomodoroClock(zeroTick.state.remainingSeconds), "00:00");

  // Decisão 1: Estender +10 min -> não emite turnRequest
  const extended = confirmPomodoroCompletion(zeroTick.state, "extend_10m");
  assertEquals(extended.state.phase, "running_focus");
  assertEquals(extended.state.remainingSeconds, 600);
  assertEquals(extended.state.confirmationModalOpen, false);
  assertEquals(extended.turnRequest, null);

  // Decisão 2: Iniciar pausa de 5 min sem concluir bloco -> não emite turnRequest
  const breakOnly = confirmPomodoroCompletion(zeroTick.state, "start_break");
  assertEquals(breakOnly.state.phase, "running_break");
  assertEquals(breakOnly.state.remainingSeconds, DEFAULT_BREAK_SECONDS);
  assertEquals(breakOnly.state.confirmationModalOpen, false);
  assertEquals(breakOnly.turnRequest, null);

  // Decisão 3: Confirmar conclusão explícita pelo estudante -> emite turnRequest com confirmed_by_student: true
  const completed = confirmPomodoroCompletion(zeroTick.state, "complete_block");
  assertEquals(completed.state.phase, "running_break");
  assertEquals(completed.state.confirmationModalOpen, false);
  assert(completed.turnRequest !== null, "A confirmação explícita deve construir turnRequest");
  assertEquals(completed.turnRequest.payload.intent, "update_activity");
  assertEquals(completed.turnRequest.payload.block_id, "block-45m");
  assertEquals(completed.turnRequest.payload.status, "completed");
  assertEquals(completed.turnRequest.payload.confirmed_by_student, true);
});

// ============================================================================
// UI-FE-03: Escada Socrática L0-L3 e Sanitização de Vazamento de Gabarito (§7.3)
// ============================================================================
Deno.test("UI-FE-03: escada socrática L0->L1->L2->L3 oculta expected_answer antes de L3/revealed=true", () => {
  const baseItem: LearningItem = {
    id: "item-1",
    family_id: "fam-1",
    version: 1,
    prompt: "Explique por que o protocolo de 2 fases evita inconsistência na Outbox.",
    help_level: "L0",
    revealed: false,
    expected_answer: "Porque persiste a intenção antes do efeito colateral e reconcilia recibos.",
    rubric: [
      { criterion_id: "c1", description: "Menciona persistência prévia na tabela operations", critical: true },
    ],
    source_refs: [{ chunk_id: "chunk-1", original_ref: "aula04.pdf" }],
    independent: true,
  };

  // Em L0, L1 e L2 com revealed=false, canRevealAnswer deve ser false e expected_answer deve ser null
  for (const level of ["L0", "L1", "L2"] as const) {
    const candidate: LearningItem = { ...baseItem, help_level: level, revealed: false };
    assertEquals(canRevealAnswer(candidate), false, `Gabarito não pode vazar em ${level}`);
    const sanitized = sanitizeLearningItemForDisplay(candidate);
    assertEquals(
      sanitized.expected_answer,
      null,
      `sanitizeLearningItemForDisplay deve mascarar expected_answer como null em ${level}`,
    );
  }

  // Em L3 (ou quando revealed=true), expected_answer é liberado
  const atL3: LearningItem = { ...baseItem, help_level: "L3", revealed: false, independent: false };
  assertEquals(canRevealAnswer(atL3), true);
  assertEquals(
    sanitizeLearningItemForDisplay(atL3).expected_answer,
    baseItem.expected_answer,
  );

  const explicitlyRevealed: LearningItem = { ...baseItem, help_level: "L1", revealed: true };
  assertEquals(canRevealAnswer(explicitlyRevealed), true);
  assertEquals(
    sanitizeLearningItemForDisplay(explicitlyRevealed).expected_answer,
    baseItem.expected_answer,
  );

  // Transições monotônicas L0 -> L1 -> L2 -> L3 -> L3
  assertEquals(nextHelpLevel("L0"), "L1");
  assertEquals(nextHelpLevel("L1"), "L2");
  assertEquals(nextHelpLevel("L2"), "L3");
  assertEquals(nextHelpLevel("L3"), "L3");

  // Elegibilidade para tentativa independente: L0 e L1 são independentes; L2 e L3 são assistidas
  assertEquals(describeHelpLevel("L0").independentEligible, true);
  assertEquals(describeHelpLevel("L1").independentEligible, true);
  assertEquals(describeHelpLevel("L2").independentEligible, false);
  assertEquals(describeHelpLevel("L3").independentEligible, false);
});

// ============================================================================
// UI-FE-04: Sessão de Flashcards (Frente/Verso e Autoavaliação Qualitativa)
// ============================================================================
Deno.test("UI-FE-04: sessão de flashcards exige virar o cartão antes de registrar autoavaliação qualitativa", () => {
  const sampleCards: FlashcardItem[] = [
    {
      id: "fc-1",
      kind: "item_review",
      front: "Qual o papel do Bibliotecário no EduAgent-OS?",
      back: "Ingerir documentos, extrair fatos com proveniência e indexar chunks BGE-M3.",
      revealed: false,
      source_refs: [],
      course_id: "c-1",
    },
    {
      id: "fc-2",
      kind: "concept_recall",
      front: "O que significa estimate = null em TopicState?",
      back: "Ausência deliberada de nota numérica ou porcentagem na v0.1 (§8.1).",
      revealed: false,
      source_refs: [],
      course_id: "c-1",
    },
  ];

  let session = createFlashcardSession(sampleCards);
  assertEquals(session.currentIndex, 0);
  assertEquals(session.backVisible, false);
  assertEquals(session.completedIds.length, 0);

  // Tentar avaliar sem virar o cartão é bloqueado (fail-closed)
  const blockedAttempt = rateFlashcard(session, "consolidado");
  assertEquals(blockedAttempt.currentIndex, 0);
  assertEquals(blockedAttempt.completedIds.length, 0);
  assertEquals(blockedAttempt.ratingsById["fc-1"], undefined);

  // Virar o cartão exibe o verso e habilita a autoavaliação
  session = flipFlashcard(session);
  assertEquals(session.backVisible, true);

  session = rateFlashcard(session, "compreendido_com_esforco");
  assertEquals(session.completedIds, ["fc-1"]);
  assertEquals(session.ratingsById["fc-1"], "compreendido_com_esforco");
  assertEquals(session.currentIndex, 1);
  assertEquals(session.backVisible, false, "Ao avançar para o próximo cartão, o verso inicia oculto");

  // Segundo cartão
  session = flipFlashcard(session);
  session = rateFlashcard(session, "consolidado");
  assertEquals(session.completedIds, ["fc-1", "fc-2"]);
  assertEquals(session.ratingsById["fc-2"], "consolidado");

  // Invariante de zero gamificação: nenhuma chave de streak/points/xp/leaderboard no estado ou nos cartões
  for (const forbidden of ["streak", "points", "xp", "leaderboard"]) {
    assert(
      !(forbidden in session),
      `Estado da sessão de flashcards não pode conter chave de gamificação: ${forbidden}`,
    );
    for (const card of session.cards) {
      assert(
        !(forbidden in card),
        `FlashcardItem não pode conter chave de gamificação: ${forbidden}`,
      );
    }
  }
});

// ============================================================================
// UI-FE-05: Tradução de Erros Tipados e Banners de Gates de Runtime
// ============================================================================
Deno.test("UI-FE-05: traduz todos os códigos de erro tipados e avalia banners de gates (MODEL_NOT_ADMITTED, timezone: null)", () => {
  const allCodes: ErrorCode[] = [
    "INVALID_INPUT",
    "SCHEMA_VALIDATION",
    "SCHEMA_INVALID",
    "PARSE_FAILURE",
    "PERMISSION_DENIED",
    "TOOL_DENIED",
    "REVISION_CONFLICT",
    "VERSION_CONFLICT",
    "DEPENDENCY_INVALIDATED",
    "AMBIGUOUS_FACT",
    "AMBIGUOUS_INPUT",
    "INSUFFICIENT_EVIDENCE",
    "NO_EVIDENCE",
    "SOURCE_UNRESOLVED",
    "RESOURCE_LIMIT",
    "TIMEOUT",
    "CONNECTOR_DISABLED",
    "MODEL_NOT_ADMITTED",
    "UNKNOWN_EFFECT",
    "INTERNAL_FAILURE",
    "CANCELLED",
  ];

  for (const code of allCodes) {
    const err: TypedError = {
      code,
      message: `Detalhe simulado para ${code}`,
      retryable: code === "TIMEOUT" || code === "REVISION_CONFLICT",
    };
    const desc = describeTypedError(err);
    assert(desc.title.length > 0, `Título ausente para ${code}`);
    assert(desc.explanation.includes(code), `Explicação deve preservar detalhe de ${code}`);
    assert(desc.actionLabel.length > 0, `ActionLabel ausente para ${code}`);
    assert(
      ["warning", "danger", "info"].includes(desc.severity),
      `Severidade inválida para ${code}`,
    );
  }

  // Banners quando gates ausentes (conectando)
  const connectingNotices = evaluateRuntimeBanner(null);
  assertEquals(connectingNotices.length, 1);
  assertEquals(connectingNotices[0].id, "health-unknown");

  // Banners com modelo não admitido e timezone null
  const blockedNotices = evaluateRuntimeBanner({
    model_admitted: false,
    model_status: "MODEL_NOT_ADMITTED",
    timezone: null,
    network_enabled: false,
    web_connector: "CONNECTOR_DISABLED",
    calendar_sync_enabled: false,
    reranker_enabled: false,
    sqlite_version: "3.45.0",
    domain_revision: 3,
    ui_available: true,
    registered_users: [],
  });
  assertEquals(blockedNotices.map((n) => n.id), ["model-not-admitted", "timezone-null"]);
  assertEquals(blockedNotices[0].badge, "MODEL_NOT_ADMITTED");
  assertEquals(blockedNotices[1].badge, "TIMEZONE: NULL");

  // Banners com modelo admitido e timezone configurado
  const admittedNotices = evaluateRuntimeBanner({
    model_admitted: true,
    model_status: "admitted",
    timezone: "America/Sao_Paulo",
    network_enabled: false,
    web_connector: "CONNECTOR_DISABLED",
    calendar_sync_enabled: false,
    reranker_enabled: false,
    sqlite_version: "3.45.0",
    domain_revision: 4,
    ui_available: true,
    registered_users: [],
  });
  assertEquals(admittedNotices.map((n) => n.id), ["model-admitted"]);
  assertEquals(admittedNotices[0].level, "ok");
});

// ============================================================================
// UI-FE-06: Auditoria Estática de Soberania Offline, Acessibilidade e Invariantes
// ============================================================================
Deno.test("UI-FE-06: HTML, CSS e JS em ui/dist/ são 100% offline (zero CDNs), possuem modais <dialog> e respeitam invariantes", async () => {
  const htmlUrl = new URL("../dist/index.html", import.meta.url);
  const cssUrl = new URL("../dist/styles.css", import.meta.url);
  const jsUrl = new URL("../dist/app.js", import.meta.url);

  const html = await Deno.readTextFile(htmlUrl);
  const css = await Deno.readTextFile(cssUrl);
  const js = await Deno.readTextFile(jsUrl);

  // 1. Zero CDNs externas ou links http(s):// nos ativos estáticos HTML/CSS
  const externalUrlRegex = /https?:\/\/(?!127\.0\.0\.1|localhost)/i;
  assert(
    !externalUrlRegex.test(html),
    "ui/dist/index.html não pode conter URLs externas (violação de soberania offline)",
  );
  assert(
    !externalUrlRegex.test(css),
    "ui/dist/styles.css não pode conter URLs externas (@import/fontes remotas)",
  );

  // 2. Presença das 4 zonas arquiteturais e 7 destinos do trilho global
  assert(html.includes('id="app-shell"'), "Deve conter #app-shell");
  assert(html.includes('class="global-rail"'), "Deve conter Zona 1 (.global-rail)");
  assert(html.includes('class="courses-column"'), "Deve conter Zona 2 (.courses-column)");
  assert(html.includes('id="main-stage"'), "Deve conter Zona 3 (#main-stage)");
  assert(html.includes('id="evidence-drawer"'), "Deve conter Zona 4 (#evidence-drawer)");

  for (const railView of [
    "courses",
    "calendar",
    "library",
    "review",
    "progress",
    "operations",
    "settings",
  ]) {
    assert(
      html.includes(`data-rail-target="${railView}"`),
      `Botão do trilho global ausente para a visão ${railView}`,
    );
    assert(
      html.includes(`id="view-${railView}"`),
      `Container de visão ausente para #view-${railView}`,
    );
  }

  // 3. Presença dos 3 modais <dialog> nativos (Pomodoro, Busca Global Ctrl+K, Nova Disciplina) sem role="dialog" ou aria-modal redundantes
  assert(html.includes('id="pomodoro-confirm-dialog"'), "Modal <dialog> do Pomodoro ausente");
  assert(html.includes('id="global-search-dialog"'), "Modal <dialog> de Busca Global ausente");
  assert(html.includes('id="new-course-dialog"'), "Modal <dialog> de Nova Disciplina ausente");
  assert(!html.includes('role="dialog"'), "<dialog> nativo não deve usar role=\"dialog\" redundante");
  assert(!html.includes("aria-modal="), "<dialog> nativo não deve usar aria-modal redundante");

  // 4. Tokens de Design Acadêmico Calmo, CSS Grid 4 colunas, 100dvh, overscroll-behavior: contain e suporte a prefers-reduced-motion e tema escuro
  const cssLower = css.toLowerCase();
  assert(cssLower.includes("--bg-canvas: #f7f5f0"), "Token de paleta --bg-canvas (#F7F5F0) ausente");
  assert(cssLower.includes("--accent-primary: #1f5f5b"), "Token --accent-primary (#1F5F5B) ausente");
  assert(cssLower.includes("grid-template-columns: 64px 320px minmax(0, 1fr)"), "Layout CSS Grid de 4 colunas ausente");
  assert(cssLower.includes("100dvh"), "Unidade 100dvh ausente");
  assert(cssLower.includes("overscroll-behavior: contain"), "Regra overscroll-behavior: contain ausente");
  assert(cssLower.includes("scrollbar-gutter: stable"), "Regra scrollbar-gutter: stable ausente");
  assert(cssLower.includes("prefers-color-scheme: dark"), "Media query de modo escuro ausente");
  assert(cssLower.includes("prefers-reduced-motion: reduce"), "Media query de movimento reduzido ausente");

  // 5. Todos os 5 botões de atalho secundários conectados em ui/dist/app.js
  for (const btnId of [
    "btn-request-hint",
    "btn-quick-upload",
    "btn-generate-plan",
    "btn-export-ics",
    "btn-refresh-operations",
  ]) {
    assert(
      js.includes(`getElementById("${btnId}")`),
      `Handler para #${btnId} deve estar conectado em ui/dist/app.js`,
    );
  }
});
