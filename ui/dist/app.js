/**
 * EduAgent-OS v0.1 — Cliente SPA da Interface Gráfica Local (127.0.0.1)
 * Implementa as 4 zonas coordenadas (Trilho Global, Coluna de Disciplinas,
 * Painel Central de Estudo/Visões Auxiliares e Gaveta de Evidências),
 * Timer Pomodoro Fail-Closed e Gates Explícitos.
 */

const DEFAULT_FOCUS_SECONDS = 25 * 60;
const DEFAULT_BREAK_SECONDS = 5 * 60;
const POMODORO_STORAGE_KEY = "eduagent_pomodoro_v01";

export function sortCoursesDeterministically(courses) {
  return [...courses].sort((a, b) => {
    if (a.sort_tier !== b.sort_tier) {
      return a.sort_tier - b.sort_tier;
    }
    const secCmp = String(a.sort_key_secondary || "").localeCompare(
      String(b.sort_key_secondary || ""),
    );
    if (secCmp !== 0) {
      return secCmp;
    }
    return String(a.title || "").localeCompare(String(b.title || ""), "pt-BR");
  });
}

export function filterCourses(courses, filter, searchQuery = "") {
  const q = String(searchQuery || "").trim().toLowerCase();
  const sorted = sortCoursesDeterministically(courses);
  return sorted.filter((course) => {
    if (filter === "ready" && !course.ready_to_study) return false;
    if (filter === "scheduled" && course.sort_tier !== 1) return false;
    if (
      filter === "pending_approval" &&
      course.pending_demands_count <= 0 &&
      course.sort_tier > 2
    ) {
      return false;
    }
    if (!q) return true;
    const inTitle = String(course.title || "").toLowerCase().includes(q);
    const inPreview = String(course.last_turn_preview || "").toLowerCase().includes(q);
    const inTopics = (course.topics || []).some((t) =>
      String(t.title || "").toLowerCase().includes(q)
    );
    return inTitle || inPreview || inTopics;
  });
}

export function resolvePlanBlockDurationSeconds(block) {
  if (!block || !block.planned_start_utc || !block.planned_end_utc) {
    return DEFAULT_FOCUS_SECONDS;
  }
  const startMs = Date.parse(block.planned_start_utc);
  const endMs = Date.parse(block.planned_end_utc);
  if (Number.isNaN(startMs) || Number.isNaN(endMs) || endMs <= startMs) {
    return DEFAULT_FOCUS_SECONDS;
  }
  const diffSeconds = Math.round((endMs - startMs) / 1000);
  return Math.max(5 * 60, Math.min(180 * 60, diffSeconds));
}

export function createPomodoroState(course) {
  const block = course?.active_plan_block ?? null;
  const duration = resolvePlanBlockDurationSeconds(block);
  return {
    phase: "idle",
    courseId: course?.id ?? null,
    planBlockId: block?.id ?? null,
    totalSeconds: duration,
    remainingSeconds: duration,
    breakSeconds: DEFAULT_BREAK_SECONDS,
    confirmationModalOpen: false,
    autoCompletedForbidden: true,
  };
}

export function tickPomodoro(state, elapsedSeconds = 1) {
  if (state.phase !== "running_focus" && state.phase !== "running_break") {
    return { state, emittedTurnPayload: null };
  }
  const nextRemaining = Math.max(0, state.remainingSeconds - Math.max(1, elapsedSeconds));
  if (nextRemaining > 0) {
    return {
      state: { ...state, remainingSeconds: nextRemaining },
      emittedTurnPayload: null,
    };
  }
  if (state.phase === "running_focus") {
    return {
      state: {
        ...state,
        phase: "awaiting_confirmation",
        remainingSeconds: 0,
        confirmationModalOpen: true,
      },
      emittedTurnPayload: null,
    };
  }
  return {
    state: {
      ...state,
      phase: "idle",
      remainingSeconds: state.totalSeconds,
      confirmationModalOpen: false,
    },
    emittedTurnPayload: null,
  };
}

export function confirmPomodoroCompletion(state, decision) {
  if (decision === "extend_10m") {
    const extra = 10 * 60;
    return {
      state: {
        ...state,
        phase: "running_focus",
        remainingSeconds: extra,
        totalSeconds: state.totalSeconds + extra,
        confirmationModalOpen: false,
      },
      turnRequest: null,
    };
  }
  if (decision === "start_break") {
    return {
      state: {
        ...state,
        phase: "running_break",
        remainingSeconds: state.breakSeconds,
        confirmationModalOpen: false,
      },
      turnRequest: null,
    };
  }
  return {
    state: {
      ...state,
      phase: "running_break",
      remainingSeconds: state.breakSeconds,
      confirmationModalOpen: false,
    },
    turnRequest: {
      message: "/resume concluir bloco de estudo",
      payload: {
        intent: "update_activity",
        course_id: state.courseId,
        block_id: state.planBlockId,
        status: "completed",
        confirmed_by_student: true,
      },
    },
  };
}

export function formatPomodoroClock(seconds) {
  const clamped = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(clamped / 60);
  const secs = clamped % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export function canRevealAnswer(item) {
  return Boolean(item && (item.revealed || item.help_level === "L3"));
}

export function sanitizeLearningItemForDisplay(item) {
  return {
    ...item,
    expected_answer: canRevealAnswer(item) ? item.expected_answer : null,
  };
}

export function nextHelpLevel(current) {
  switch (current) {
    case "L0":
      return "L1";
    case "L1":
      return "L2";
    case "L2":
    case "L3":
    default:
      return "L3";
  }
}

export function describeHelpLevel(level) {
  switch (level) {
    case "L0":
      return {
        badge: "L0 · Sem Dica",
        title: "Tentativa independente (conta para avanço de domínio)",
        independentEligible: true,
      };
    case "L1":
      return {
        badge: "L1 · Pista Conceitual",
        title: "Dica socrática leve (ainda conta como tentativa independente)",
        independentEligible: true,
      };
    case "L2":
      return {
        badge: "L2 · Próximo Passo",
        title: "Andaime guiado (tentativa assistida — exige nova prática independente)",
        independentEligible: false,
      };
    case "L3":
    default:
      return {
        badge: "L3 · Explicação & Gabarito",
        title: "Resposta revelada (tentativa assistida — exige nova família de item)",
        independentEligible: false,
      };
  }
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// ---------------------------------------------------------------------------
// Estado em Memória do Cliente Browser
// ---------------------------------------------------------------------------
const appState = {
  userId: "00000000-0000-0000-0000-000000000001",
  activeView: "courses",
  courseFilter: "all",
  courseSearch: "",
  courses: [],
  selectedCourseId: null,
  activeSessionId: "00000000-0000-0000-0000-000000000099",
  helpLevel: "L0",
  turnInFlight: false,
  health: null,
  sessionDetail: null,
  flashcards: [],
  flashcardIndex: 0,
  flashcardBackVisible: false,
  pendingUploadBase64: null,
  pomodoro: createPomodoroState(null),
  pomodoroTimerId: null,
  // Turnos locais renderizados a partir da resposta do POST /turns (o backend
  // não grava mensagens de chat como eventos de domínio; ver task interface 002).
  localTurns: [],
};

async function apiFetch(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
    "X-EduAgent-User": appState.userId,
  };
  if (options.body && typeof options.body === "object") {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json();
  return { status: response.status, data };
}

function savePomodoroToStorage() {
  try {
    localStorage.setItem(POMODORO_STORAGE_KEY, JSON.stringify(appState.pomodoro));
  } catch (_err) {
    // Ignora se storage estiver indisponível
  }
}

function renderRuntimeGatesBanner() {
  const banner = document.getElementById("runtime-gates-banner");
  if (!banner) return;
  const gates = appState.health?.gates;
  if (!gates) {
    banner.innerHTML = `<span class="banner-pill level-info">Conectando ao LoopbackAPI (127.0.0.1)...</span>`;
    return;
  }
  const pills = [];
  if (!gates.model_admitted) {
    pills.push(
      `<span class="banner-pill level-warning"><strong>MODEL_NOT_ADMITTED</strong> · Tutor gerativo bloqueado até admissão do modelo Bonsai 2 (Ingestão, Acervo e Agenda operacionais)</span>`,
    );
  } else {
    pills.push(
      `<span class="banner-pill level-ok"><strong>Bonsai 2 Admitido</strong> · Tutoria Socrática e Prática ativas</span>`,
    );
  }
  if (!gates.timezone) {
    pills.push(
      `<span class="banner-pill level-info"><strong>timezone: null</strong> · Pendente confirmação explícita (ex.: America/Sao_Paulo)</span>`,
    );
  } else {
    pills.push(
      `<span class="banner-pill level-info"><strong>Fuso: ${escapeHtml(gates.timezone)}</strong> (${escapeHtml(gates.timezone_source || "sistema")})</span>`,
    );
  }
  pills.push(
    `<span class="banner-pill level-info">Web: ${escapeHtml(gates.web_connector)} · Rev #${escapeHtml(gates.domain_revision)}</span>`,
  );
  banner.innerHTML = pills.join("");
}

function renderCoursesList() {
  const container = document.getElementById("courses-list");
  if (!container) return;
  const filtered = filterCourses(
    appState.courses,
    appState.courseFilter,
    appState.courseSearch,
  );
  if (filtered.length === 0) {
    container.innerHTML = `<p class="muted-note">Nenhuma disciplina encontrada para este filtro.</p>`;
    return;
  }
  container.innerHTML = filtered
    .map((course) => {
      const selected = course.id === appState.selectedCourseId ? "is-selected" : "";
      const readyClass = course.ready_to_study ? "is-ready" : "is-pending";
      const readyLabel = course.ready_to_study
        ? "● Pronta p/ estudar"
        : "○ Sem material ativo";
      return `
        <button type="button" class="course-card ${selected}" data-course-id="${escapeHtml(course.id)}" role="option" aria-selected="${course.id === appState.selectedCourseId}">
          <div class="course-card-top">
            <h3 class="course-card-title">${escapeHtml(course.title)}</h3>
            <span class="course-ready-dot ${readyClass}">${readyLabel}</span>
          </div>
          <p class="course-card-preview">${escapeHtml(course.last_turn_preview)}</p>
          <div class="course-card-meta">
            <span class="tier-badge">P${escapeHtml(course.sort_tier)} · ${escapeHtml(course.sort_reason_label)}</span>
            <span>Domínio: ${escapeHtml(course.domain_status)}</span>
          </div>
        </button>
      `;
    })
    .join("");

  container.querySelectorAll("[data-course-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const cid = btn.getAttribute("data-course-id");
      selectCourse(cid);
    });
  });
}

function renderPomodoroWidget() {
  const clockEl = document.getElementById("pomodoro-clock");
  const phaseEl = document.getElementById("pomodoro-phase-label");
  const toggleBtn = document.getElementById("btn-pomodoro-toggle");
  if (clockEl) {
    clockEl.textContent = formatPomodoroClock(appState.pomodoro.remainingSeconds);
  }
  if (phaseEl) {
    const labels = {
      idle: "Foco Pronto",
      running_focus: "Em Foco",
      paused: "Pausado",
      awaiting_confirmation: "Confirmação (00:00)",
      running_break: "Intervalo",
    };
    phaseEl.textContent = labels[appState.pomodoro.phase] || "Foco";
  }
  if (toggleBtn) {
    toggleBtn.textContent =
      appState.pomodoro.phase === "running_focus" ||
      appState.pomodoro.phase === "running_break"
        ? "Pausar"
        : "Iniciar";
  }
  if (appState.pomodoro.confirmationModalOpen) {
    const dialog = document.getElementById("pomodoro-confirm-dialog");
    if (dialog && typeof dialog.showModal === "function" && !dialog.open) {
      dialog.showModal();
    }
  }
}

function renderActiveCourseHeader() {
  const course = appState.courses.find((c) => c.id === appState.selectedCourseId);
  const titleEl = document.getElementById("active-course-title");
  const readyBadge = document.getElementById("active-course-ready-badge");
  const domainBadge = document.getElementById("active-course-domain-badge");
  const subtitleEl = document.getElementById("active-course-subtitle");
  const topicSelect = document.getElementById("topic-select");

  if (!course) {
    if (titleEl) titleEl.textContent = "Selecione ou crie uma disciplina";
    return;
  }
  if (titleEl) titleEl.textContent = course.title;
  if (readyBadge) {
    readyBadge.textContent = course.ready_to_study
      ? "Pronta para estudar"
      : "Aguardando ingestão";
    readyBadge.className = course.ready_to_study
      ? "status-pill status-ready"
      : "status-pill";
  }
  if (domainBadge) {
    domainBadge.textContent = `Domínio: ${course.domain_status}`;
  }
  if (subtitleEl) {
    subtitleEl.textContent = `${course.active_doc_count} versão(ões) ativa(s) · ${course.topics.length} tópico(s) · Sugestão: ${course.recommended_intent}`;
  }
  if (topicSelect) {
    topicSelect.innerHTML =
      `<option value="">Todos os tópicos (${course.topics.length})</option>` +
      course.topics
        .map((t) => `<option value="${escapeHtml(t.id)}">${escapeHtml(t.title)}</option>`)
        .join("");
  }
}

function renderSessionTimelineAndDrawer() {
  const timeline = document.getElementById("chat-timeline");
  const evidenceList = document.getElementById("drawer-evidence-list");
  const rubricList = document.getElementById("drawer-rubric-list");
  const planSummary = document.getElementById("drawer-plan-summary");
  const covBadge = document.getElementById("evidence-coverage-badge");
  if (!timeline) return;

  const detail = appState.sessionDetail;
  if (!detail) {
    timeline.innerHTML = `<p class="muted-note">Carregando histórico da sessão...</p>`;
    return;
  }

  const cardsHtml = [];
  for (const ev of detail.events || []) {
    const p = ev.payload || {};
    const msg = p.message || p.text || p.summary || JSON.stringify(p);
    const isStudent = ev.kind === "reading" || String(msg).startsWith("/");
    cardsHtml.push(`
      <article class="timeline-card ${isStudent ? "role-student" : "role-tutor"}">
        <div class="card-header-meta">
          <strong>${isStudent ? "Estudante" : "Agente (" + escapeHtml(ev.kind) + ")"}</strong>
          <span>${escapeHtml(ev.occurred_at)}</span>
        </div>
        <div>${escapeHtml(msg)}</div>
      </article>
    `);
  }

  // Turnos locais (resposta direta do POST /turns) vêm depois dos eventos
  // persistidos, em ordem de ocorrência.
  for (const lt of appState.localTurns || []) {
    if (lt.message) {
      cardsHtml.push(`
        <article class="timeline-card role-student">
          <div class="card-header-meta">
            <strong>Estudante</strong>
            <span>${escapeHtml(lt.occurredAt)}</span>
          </div>
          <div>${escapeHtml(lt.message)}</div>
        </article>
      `);
    }
    if (lt.errorText) {
      cardsHtml.push(`
        <article class="timeline-card role-tutor">
          <div class="card-header-meta">
            <strong>Falha do turno</strong>
            <span>${escapeHtml(lt.occurredAt)}</span>
          </div>
          <div>${escapeHtml(lt.errorText)}</div>
        </article>
      `);
    } else if (lt.responseText) {
      cardsHtml.push(`
        <article class="timeline-card role-tutor">
          <div class="card-header-meta">
            <strong>Tutor Socrático &amp; Feynman (EduAgent-OS)</strong>
            <span>${escapeHtml(lt.occurredAt)}</span>
          </div>
          <div>${escapeHtml(lt.responseText)}</div>
        </article>
      `);
    }
  }

  for (const rawItem of detail.items || []) {
    const item = sanitizeLearningItemForDisplay(rawItem);
    const refsHtml = (item.source_refs || [])
      .map(
        (ref, idx) =>
          `<button type="button" class="source-ref-btn" data-focus-chunk="${escapeHtml(ref.chunk_id || idx)}">[Fonte #${idx + 1}]</button>`,
      )
      .join("");
    const answerHtml = item.expected_answer
      ? `<div class="info-card"><strong>Gabarito Revelado (L3):</strong> ${escapeHtml(item.expected_answer)}</div>`
      : `<p class="muted-note">🔒 Gabarito oculto na escada socrática (${escapeHtml(item.help_level)}). Tente responder de forma independente ou peça dica gradual.</p>`;
    cardsHtml.push(`
      <article class="timeline-card role-item">
        <div class="card-header-meta">
          <strong>🎯 Exercício Prático · Escada ${escapeHtml(item.help_level)}</strong>
          <span>${item.independent ? "Elegível p/ domínio independente" : "Tentativa assistida"}</span>
        </div>
        <p>${escapeHtml(item.prompt)}</p>
        ${answerHtml}
        <div>${refsHtml}</div>
      </article>
    `);
  }

  if (cardsHtml.length === 0) {
    cardsHtml.push(`
      <article class="timeline-card role-tutor">
        <div class="card-header-meta">
          <strong>Tutor Socrático &amp; Feynman (EduAgent-OS)</strong>
          <span>Pronto</span>
        </div>
        <p>Esta disciplina está selecionada. Você pode anexar materiais na <strong>Biblioteca</strong>, iniciar um exercício com <code>/practice</code> ou fazer uma pergunta ancorada em evidências com <code>/ask</code>.</p>
      </article>
    `);
  }
  timeline.innerHTML = cardsHtml.join("");

  // Atualiza Gaveta de Evidências
  const pack = detail.evidence_pack || { coverage: "insufficient", chunks: [] };
  if (covBadge) {
    covBadge.textContent = `Cobertura: ${pack.coverage}`;
  }
  if (evidenceList) {
    if (!pack.chunks || pack.chunks.length === 0) {
      evidenceList.innerHTML = `<p class="muted-note">Nenhum chunk indexado para esta sessão. Ingira um documento na aba Acervo.</p>`;
    } else {
      evidenceList.innerHTML = pack.chunks
        .map(
          (ch) => `
          <div class="evidence-chunk-card" id="chunk-${escapeHtml(ch.chunk_id)}">
            <div><strong>${escapeHtml(ch.original_ref)}</strong> · <small>${escapeHtml(ch.version_status)}</small></div>
            <p>${escapeHtml(ch.text)}</p>
          </div>
        `,
        )
        .join("");
    }
  }

  if (rubricList) {
    const firstItem = (detail.items || [])[0];
    if (firstItem && Array.isArray(firstItem.rubric) && firstItem.rubric.length > 0) {
      rubricList.innerHTML = firstItem.rubric
        .map(
          (r) => `
          <div class="evidence-chunk-card">
            <strong>Critério ${escapeHtml(r.criterion_id)}</strong> ${r.critical ? "(Crítico)" : ""}
            <p>${escapeHtml(r.description)}</p>
          </div>
        `,
        )
        .join("");
    } else {
      rubricList.innerHTML = `<p class="muted-note">Inicie um turno <code>/practice</code> para visualizar os critérios públicos da rubrica.</p>`;
    }
  }

  const course = appState.courses.find((c) => c.id === appState.selectedCourseId);
  if (planSummary && course) {
    const blk = course.active_plan_block;
    planSummary.innerHTML = `
      <div class="evidence-chunk-card">
        <strong>Bloco Ativo:</strong> ${blk ? escapeHtml(blk.summary || blk.id) : "Estudo livre (25:00)"}<br/>
        <strong>Invariante Avaliativo:</strong> <code>estimate = null</code> (${escapeHtml(course.domain_status)})
      </div>
    `;
  }

  // Citações clicáveis abrem e destacam o chunk correspondente na Gaveta Direita
  timeline.querySelectorAll("[data-focus-chunk]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const chunkId = btn.getAttribute("data-focus-chunk");
      const shell = document.getElementById("app-shell");
      if (shell) {
        shell.setAttribute("data-drawer-open", "true");
      }
      const toggleBtn = document.getElementById("btn-toggle-drawer");
      if (toggleBtn) {
        toggleBtn.setAttribute("aria-expanded", "true");
      }
      const chunkEl = document.getElementById(`chunk-${chunkId}`);
      if (chunkEl && typeof chunkEl.scrollIntoView === "function") {
        chunkEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  });
}

/**
 * Registra um turno enviado pelo compositor a partir da resposta do
 * POST /turns, para exibição imediata na timeline (a resposta do backend
 * carrega `output.turn.text` ou erro tipado; eventos de chat não são
 * gravados no domínio, então `GET /sessions/{id}` não os devolve).
 */
function recordLocalTurnFromResponse(message, data) {
  const occurredAt = new Date().toISOString();
  const turn = { message, occurredAt, responseText: null, errorText: null };
  const out = data && typeof data === "object" ? data.output || {} : {};
  const err =
    (data && (data.error || (Array.isArray(data.errors) && data.errors[0]))) ||
    out.error ||
    null;
  if (err) {
    let described = null;
    if (typeof describeTypedError === "function") {
      try {
        described = describeTypedError(err);
      } catch (_err) {
        described = null;
      }
    }
    const prefix = described && described.title ? `${described.title}: ` : "";
    turn.errorText = `${prefix}${err.message || "falha desconhecida no turno"}`;
  } else if (out && out.turn && out.turn.text) {
    turn.responseText = out.turn.text;
  } else if (data && (data.status === "waiting" || data.status === "waiting_student")) {
    turn.responseText = "Turno registrado — aguardando ação do estudante.";
  }
  appState.localTurns.push(turn);
  if (appState.localTurns.length > 100) appState.localTurns.shift();
}

async function selectCourse(courseId) {
  appState.selectedCourseId = courseId;
  const course = appState.courses.find((c) => c.id === courseId) || null;
  appState.pomodoro = createPomodoroState(course);
  savePomodoroToStorage();
  renderCoursesList();
  renderActiveCourseHeader();
  renderPomodoroWidget();
  const { status, data } = await apiFetch(
    `/sessions/${encodeURIComponent(appState.activeSessionId)}`,
  );
  if (status === 200) {
    appState.sessionDetail = data;
    renderSessionTimelineAndDrawer();
  }
}

async function ensureSystemOrFallbackTimezone() {
  const gates = appState.health?.gates;
  if (!gates || gates.timezone) return;

  let chosenTz = null;
  let source = "browser_auto";
  try {
    const resolved = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (resolved && resolved !== "UTC" && resolved !== "Etc/UTC") {
      chosenTz = resolved;
    }
  } catch (_err) {
    chosenTz = null;
  }

  if (!chosenTz && typeof window !== "undefined" && typeof window.prompt === "function") {
    const manual = window.prompt(
      "Não foi possível detectar automaticamente o fuso horário do sistema.\nInforme o fuso horário IANA a utilizar (ex.: America/Sao_Paulo):",
      "America/Sao_Paulo",
    );
    if (manual && manual.trim()) {
      chosenTz = manual.trim();
      source = "user_prompt";
    }
  }

  if (chosenTz) {
    const res = await apiFetch("/settings/timezone", {
      method: "POST",
      body: { timezone: chosenTz, source },
    });
    if (res.status === 200 && appState.health?.gates) {
      appState.health.gates.timezone = res.data.timezone;
      appState.health.gates.timezone_source = res.data.timezone_source;
      appState.health.gates.timezone_needs_prompt = false;
      renderRuntimeGatesBanner();
    }
  }
}

async function refreshCoreData() {
  try {
    const healthRes = await fetch("/health");
    appState.health = await healthRes.json();
    const registered = appState.health?.gates?.registered_users || [];
    if (registered.length > 0 && !registered.includes(appState.userId)) {
      appState.userId = registered[0];
      const userInput = document.getElementById("active-user-input");
      if (userInput) userInput.value = appState.userId;
    }
    renderRuntimeGatesBanner();
    await ensureSystemOrFallbackTimezone();
  } catch (_err) {
    // servidor offline
  }

  const coursesRes = await apiFetch("/courses");
  if (coursesRes.status === 200 && Array.isArray(coursesRes.data.courses)) {
    appState.courses = coursesRes.data.courses;
    if (!appState.selectedCourseId && appState.courses.length > 0) {
      appState.selectedCourseId = appState.courses[0].id;
      appState.pomodoro = createPomodoroState(appState.courses[0]);
    }
    renderCoursesList();
    renderActiveCourseHeader();
    renderPomodoroWidget();
  }

  const opsRes = await apiFetch("/operations");
  if (opsRes.status === 200) {
    const badge = document.getElementById("rail-ops-badge");
    if (badge) {
      const count = Number(opsRes.data.pending_count || 0);
      badge.textContent = String(count);
      badge.hidden = count <= 0;
    }
  }

  if (appState.selectedCourseId) {
    const sessRes = await apiFetch(
      `/sessions/${encodeURIComponent(appState.activeSessionId)}`,
    );
    if (sessRes.status === 200) {
      appState.sessionDetail = sessRes.data;
      renderSessionTimelineAndDrawer();
    }
  }
}

async function loadAuxiliaryView(viewName) {
  if (viewName === "calendar") {
    const { status, data } = await apiFetch("/calendar");
    const el = document.getElementById("calendar-view-content");
    if (!el || status !== 200) return;
    const demandsHtml = (data.demands || [])
      .map(
        (d) => `
        <div class="info-card">
          <strong>Demanda: ${escapeHtml(d.activity_kind || d.id)}</strong>
          <span>Status: ${escapeHtml(d.status)} · Vencimento: ${escapeHtml(d.due_local_date || "sem data")}</span>
        </div>
      `,
      )
      .join("");
    const blocksHtml = (data.logical_blocks || [])
      .map(
        (b) => `
        <div class="info-card">
          <strong>Bloco Planejado: ${escapeHtml(b.summary || b.id)}</strong>
          <span>${escapeHtml(b.planned_start_utc)} → ${escapeHtml(b.planned_end_utc)} (${escapeHtml(b.status)})</span>
        </div>
      `,
      )
      .join("");
    const exportsHtml = (data.exports || [])
      .map(
        (ex) => `
        <div class="info-card">
          <strong>Arquivo .ics: ${escapeHtml(ex.filename)}</strong>
          <span>${escapeHtml(ex.size_bytes)} bytes</span>
        </div>
      `,
      )
      .join("");
    el.innerHTML =
      demandsHtml + blocksHtml + exportsHtml ||
      `<p class="muted-note">Nenhum bloco ou demanda cadastrada. Clique em "Gerar Proposta (/plan)".</p>`;
  } else if (viewName === "library") {
    const { status, data } = await apiFetch("/library");
    const el = document.getElementById("library-view-content");
    if (!el || status !== 200) return;
    const docsHtml = (data.documents || [])
      .map(
        (d) => `
        <div class="info-card">
          <strong>📄 ${escapeHtml(d.original_ref || d.doc_id)}</strong>
          <span>Disciplina: ${escapeHtml(d.course_title)} · Status: <code>${escapeHtml(d.version_status)}</code> · Chunks: ${escapeHtml(d.chunk_count)}</span>
        </div>
      `,
      )
      .join("");
    el.innerHTML =
      docsHtml ||
      `<p class="muted-note">Nenhum documento ingerido ainda. Use o formulário acima para enviar um PDF ou Markdown.</p>`;
  } else if (viewName === "review") {
    const { status, data } = await apiFetch("/review/flashcards");
    const el = document.getElementById("review-view-content");
    if (!el || status !== 200) return;
    appState.flashcards = data.flashcards || [];
    appState.flashcardIndex = 0;
    appState.flashcardBackVisible = false;
    renderFlashcardStage();
  } else if (viewName === "progress") {
    const { status, data } = await apiFetch("/progress");
    const el = document.getElementById("progress-view-content");
    if (!el || status !== 200) return;
    const itemsHtml = (data.topics || [])
      .map(
        (t) => `
        <div class="info-card">
          <strong>${escapeHtml(t.course_title)} — ${escapeHtml(t.topic_title)}</strong>
          <span>Estado: <code>${escapeHtml(t.status)}</code> · <code>estimate: null</code></span>
          <p class="muted-note">${escapeHtml(t.rationale)}</p>
          <small>Tentativas independentes: ${escapeHtml(t.independent_attempts)} · Assistidas: ${escapeHtml(t.assisted_attempts)}</small>
        </div>
      `,
      )
      .join("");
    el.innerHTML = itemsHtml || `<p class="muted-note">Sem tópicos registrados.</p>`;
  } else if (viewName === "operations") {
    const { status, data } = await apiFetch("/operations");
    const el = document.getElementById("operations-view-content");
    if (!el || status !== 200) return;
    const factsHtml = (data.pending_facts || [])
      .map(
        (f) => `
        <div class="info-card">
          <strong>Fato ${escapeHtml(f.status)}: ${escapeHtml(f.kind)}</strong>
          <pre>${escapeHtml(JSON.stringify(f.value))}</pre>
        </div>
      `,
      )
      .join("");
    const plansHtml = (data.unapproved_plans || [])
      .map(
        (p) => `
        <div class="info-card">
          <strong>Plano Pendente de Aprovação #${escapeHtml(p.id)}</strong>
          <span>Revisão ${escapeHtml(p.revision)}</span>
        </div>
      `,
      )
      .join("");
    el.innerHTML =
      factsHtml + plansHtml ||
      `<p class="muted-note">Nenhuma operação ou aprovação pendente no momento.</p>`;
  } else if (viewName === "settings") {
    const el = document.getElementById("settings-view-content");
    if (!el) return;
    const gates = appState.health?.gates || {};
    el.innerHTML = `
      <div class="info-card">
        <strong>Gate do Modelo Local (Bonsai 2)</strong>
        <span>Status: <code>${escapeHtml(gates.model_status || "desconhecido")}</code></span>
      </div>
      <div class="info-card">
        <strong>Fuso Horário &amp; Conectores</strong>
        <span>Timezone: <code>${escapeHtml(String(gates.timezone))}</code> (${escapeHtml(gates.timezone_source || "unresolved")}) · Web: <code>${escapeHtml(gates.web_connector)}</code></span>
        <div class="modal-actions">
          <input type="text" id="settings-timezone-input" class="input-field" value="${escapeHtml(gates.timezone || "America/Sao_Paulo")}" aria-label="Fuso horário IANA" />
          <button type="button" id="btn-save-timezone" class="btn-secondary btn-compact">Aplicar Fuso Horário</button>
        </div>
      </div>
      <div class="info-card">
        <strong>Armazenamento SQLite/WAL</strong>
        <span>SQLite ${escapeHtml(gates.sqlite_version)} · Revisão de Domínio #${escapeHtml(gates.domain_revision)}</span>
      </div>
    `;
    document.getElementById("btn-save-timezone")?.addEventListener("click", async () => {
      const tzVal = document.getElementById("settings-timezone-input")?.value.trim();
      if (!tzVal) return;
      const res = await apiFetch("/settings/timezone", {
        method: "POST",
        body: { timezone: tzVal, source: "user_manual" },
      });
      if (res.status === 200) {
        await refreshCoreData();
        await loadAuxiliaryView("settings");
      }
    });
  }
}

function renderFlashcardStage() {
  const el = document.getElementById("review-view-content");
  if (!el) return;
  const cards = appState.flashcards;
  if (!cards || cards.length === 0) {
    el.innerHTML = `<p class="muted-note">Nenhum cartão de revisão pendente. Ingira documentos ou pratique exercícios para alimentar a revisão espaçada.</p>`;
    return;
  }
  const card = cards[appState.flashcardIndex] || cards[0];
  el.innerHTML = `
    <div class="flashcard-box">
      <div class="card-header-meta">
        <strong>Cartão ${appState.flashcardIndex + 1} de ${cards.length} (${escapeHtml(card.kind)})</strong>
        <span>Revisão Qualitativa</span>
      </div>
      <div>
        <h4>Frente (Pergunta / Conceito):</h4>
        <p>${escapeHtml(card.front)}</p>
      </div>
      ${
        appState.flashcardBackVisible
          ? `<div class="info-card"><h4>Verso (Critérios / Explicação):</h4><p>${escapeHtml(card.back)}</p></div>`
          : `<p class="muted-note">Formule sua explicação antes de virar o cartão.</p>`
      }
      <div class="modal-actions">
        <button type="button" id="btn-flip-card" class="btn-secondary">
          ${appState.flashcardBackVisible ? "Ocultar Verso" : "Virar Cartão (Mostrar Verso)"}
        </button>
        ${
          appState.flashcardBackVisible
            ? `
          <button type="button" class="btn-ghost" data-rate-card="revisar_em_breve">Revisar em Breve</button>
          <button type="button" class="btn-secondary" data-rate-card="compreendido_com_esforco">Compreendido com Esforço</button>
          <button type="button" class="btn-primary" data-rate-card="consolidado">Explicação Consolidada</button>
        `
            : ""
        }
      </div>
    </div>
  `;
  document.getElementById("btn-flip-card")?.addEventListener("click", () => {
    appState.flashcardBackVisible = !appState.flashcardBackVisible;
    renderFlashcardStage();
  });
  el.querySelectorAll("[data-rate-card]").forEach((btn) => {
    btn.addEventListener("click", () => {
      appState.flashcardBackVisible = false;
      appState.flashcardIndex = (appState.flashcardIndex + 1) % cards.length;
      renderFlashcardStage();
    });
  });
}

function switchView(viewName) {
  appState.activeView = viewName;
  const shell = document.getElementById("app-shell");
  if (shell) shell.setAttribute("data-active-view", viewName);
  document.querySelectorAll("[data-rail-target]").forEach((btn) => {
    btn.classList.toggle(
      "is-active",
      btn.getAttribute("data-rail-target") === viewName,
    );
  });
  document.querySelectorAll(".stage-view").forEach((sec) => {
    const isTarget = sec.id === `view-${viewName}`;
    sec.hidden = !isTarget;
    sec.classList.toggle("is-visible", isTarget);
  });
  if (viewName !== "courses") {
    loadAuxiliaryView(viewName);
  }
}

function bindEvents() {
  // Navegação do Trilho Global Esquerdo
  document.querySelectorAll("[data-rail-target]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-rail-target");
      if (target) switchView(target);
    });
  });

  // Filtros de Disciplinas
  document.querySelectorAll("[data-course-filter]").forEach((chip) => {
    chip.addEventListener("click", () => {
      appState.courseFilter = chip.getAttribute("data-course-filter") || "all";
      document.querySelectorAll("[data-course-filter]").forEach((c) => {
        c.classList.toggle("is-active", c === chip);
      });
      renderCoursesList();
    });
  });

  document.getElementById("course-search-input")?.addEventListener("input", (e) => {
    appState.courseSearch = e.target.value || "";
    renderCoursesList();
  });

  document.getElementById("active-user-input")?.addEventListener("change", (e) => {
    appState.userId = e.target.value.trim();
    refreshCoreData();
  });

  // Gaveta Direita Retrátil
  document.getElementById("btn-toggle-drawer")?.addEventListener("click", (e) => {
    const shell = document.getElementById("app-shell");
    if (!shell) return;
    const isOpen = shell.getAttribute("data-drawer-open") === "true";
    shell.setAttribute("data-drawer-open", isOpen ? "false" : "true");
    e.currentTarget.setAttribute("aria-expanded", isOpen ? "false" : "true");
  });

  // Timer Pomodoro (Fail-Closed)
  document.getElementById("btn-pomodoro-toggle")?.addEventListener("click", () => {
    if (
      appState.pomodoro.phase === "running_focus" ||
      appState.pomodoro.phase === "running_break"
    ) {
      appState.pomodoro = { ...appState.pomodoro, phase: "paused" };
    } else {
      appState.pomodoro = { ...appState.pomodoro, phase: "running_focus" };
    }
    savePomodoroToStorage();
    renderPomodoroWidget();
  });

  document.getElementById("btn-pomodoro-reset")?.addEventListener("click", () => {
    const course = appState.courses.find((c) => c.id === appState.selectedCourseId);
    appState.pomodoro = createPomodoroState(course);
    savePomodoroToStorage();
    renderPomodoroWidget();
  });

  const closePomodoroModal = async (decision) => {
    const res = confirmPomodoroCompletion(appState.pomodoro, decision);
    appState.pomodoro = res.state;
    savePomodoroToStorage();
    const dialog = document.getElementById("pomodoro-confirm-dialog");
    if (dialog && dialog.open) dialog.close();
    renderPomodoroWidget();
    if (res.turnRequest) {
      await apiFetch("/turns", {
        method: "POST",
        body: {
          session_id: appState.activeSessionId,
          message: res.turnRequest.message,
          payload: res.turnRequest.payload,
        },
      });
      await refreshCoreData();
    }
  };

  document
    .getElementById("btn-pomodoro-confirm-complete")
    ?.addEventListener("click", () => closePomodoroModal("complete_block"));
  document
    .getElementById("btn-pomodoro-extend-10m")
    ?.addEventListener("click", () => closePomodoroModal("extend_10m"));
  document
    .getElementById("btn-pomodoro-start-break")
    ?.addEventListener("click", () => closePomodoroModal("start_break"));

  // Composer de Turno
  document.getElementById("turn-composer-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const intent = document.getElementById("intent-select")?.value || "/ask";
    const topicId = document.getElementById("topic-select")?.value || "";
    const textarea = document.getElementById("composer-textarea");
    const text = textarea ? textarea.value.trim() : "";
    const message = text ? `${intent} ${text}` : intent;

    const cancelBtn = document.getElementById("btn-cancel-turn");
    if (cancelBtn) cancelBtn.hidden = false;
    try {
      const res = await apiFetch("/turns", {
        method: "POST",
        body: {
          session_id: appState.activeSessionId,
          message,
          payload: {
            course_id: appState.selectedCourseId || "",
            topic_ids: topicId ? [topicId] : [],
          },
        },
      });
      if (textarea) textarea.value = "";
      recordLocalTurnFromResponse(message, res.data);
      renderSessionTimelineAndDrawer();
      await refreshCoreData();
    } finally {
      if (cancelBtn) cancelBtn.hidden = true;
    }
  });

  document.getElementById("btn-cancel-turn")?.addEventListener("click", async () => {
    await apiFetch(`/turns/${encodeURIComponent(appState.activeSessionId)}/cancel`, {
      method: "POST",
      body: {},
    });
    await refreshCoreData();
  });

  // Botão de progressão na Escada Socrática (L0 -> L1 -> L2 -> L3)
  document.getElementById("btn-request-hint")?.addEventListener("click", async () => {
    appState.helpLevel = nextHelpLevel(appState.helpLevel);
    const indicator = document.getElementById("current-help-level-indicator");
    const info = describeHelpLevel(appState.helpLevel);
    if (indicator) {
      indicator.textContent = info.badge;
      indicator.title = info.title;
    }
    const topicId = document.getElementById("topic-select")?.value || "";
    const lastItem = (appState.sessionDetail?.items || []).slice(-1)[0];
    await apiFetch("/turns", {
      method: "POST",
      body: {
        session_id: appState.activeSessionId,
        message: `/practice Solicitar dica gradual (${appState.helpLevel})`,
        payload: {
          course_id: appState.selectedCourseId || "",
          topic_ids: topicId ? [topicId] : [],
          help_level: appState.helpLevel,
          item_id: lastItem?.id || undefined,
        },
      },
    });
    await refreshCoreData();
  });

  // Atalho de Upload rápido no Composer ("📎 Material")
  document.getElementById("btn-quick-upload")?.addEventListener("click", () => {
    switchView("library");
    const filenameInput = document.getElementById("upload-filename");
    if (filenameInput && typeof filenameInput.focus === "function") {
      filenameInput.focus();
    }
  });

  // Atalhos da visão de Agenda & Calendário (/plan e /export)
  document.getElementById("btn-generate-plan")?.addEventListener("click", async () => {
    await apiFetch("/turns", {
      method: "POST",
      body: {
        session_id: appState.activeSessionId,
        message: "/plan gerar proposta de cronograma semanal",
        payload: {
          course_id: appState.selectedCourseId || "",
        },
      },
    });
    await refreshCoreData();
    await loadAuxiliaryView("calendar");
  });

  document.getElementById("btn-export-ics")?.addEventListener("click", async () => {
    await apiFetch("/turns", {
      method: "POST",
      body: {
        session_id: appState.activeSessionId,
        message: "/export exportar blocos aprovados em iCalendar (.ics)",
        payload: {
          course_id: appState.selectedCourseId || "",
        },
      },
    });
    await refreshCoreData();
    await loadAuxiliaryView("calendar");
  });

  // Atalho de atualização na visão de Operações & Aprovações
  document.getElementById("btn-refresh-operations")?.addEventListener("click", async () => {
    await refreshCoreData();
    await loadAuxiliaryView("operations");
  });

  // Seletor de arquivo local na Biblioteca
  document.getElementById("upload-file-input")?.addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const filenameInput = document.getElementById("upload-filename");
    if (filenameInput && !filenameInput.value.trim()) {
      filenameInput.value = file.name;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const commaIdx = result.indexOf(",");
      appState.pendingUploadBase64 = commaIdx >= 0 ? result.slice(commaIdx + 1) : null;
    };
    reader.readAsDataURL(file);

    if (
      file.name.endsWith(".md") ||
      file.name.endsWith(".txt") ||
      file.name.endsWith(".tex")
    ) {
      const textReader = new FileReader();
      textReader.onload = () => {
        const textArea = document.getElementById("upload-content-text");
        if (textArea && !textArea.value.trim()) {
          textArea.value = String(textReader.result || "");
        }
      };
      textReader.readAsText(file);
    }
  });

  // Upload na Biblioteca
  document.getElementById("library-upload-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const filename = document.getElementById("upload-filename")?.value.trim();
    const contentText = document.getElementById("upload-content-text")?.value || "";
    if (!filename) return;
    await apiFetch("/library/upload", {
      method: "POST",
      body: {
        filename,
        content_base64: appState.pendingUploadBase64 || undefined,
        content_text: contentText || "# Material de estudo\nConteúdo inicial.",
        course_id: appState.selectedCourseId,
        auto_ingest: Boolean(appState.selectedCourseId),
      },
    });
    appState.pendingUploadBase64 = null;
    await refreshCoreData();
    await loadAuxiliaryView("library");
  });

  // Modal Nova Disciplina
  const newCourseDialog = document.getElementById("new-course-dialog");
  document.getElementById("btn-new-course")?.addEventListener("click", () => {
    if (newCourseDialog && typeof newCourseDialog.showModal === "function") {
      newCourseDialog.showModal();
    }
  });
  document.getElementById("btn-close-new-course")?.addEventListener("click", () => {
    if (newCourseDialog && newCourseDialog.open) newCourseDialog.close();
  });
  document.getElementById("new-course-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("new-course-name")?.value.trim();
    const rawTopics = document.getElementById("new-course-topics")?.value || "";
    const topics = rawTopics
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!title) return;
    const res = await apiFetch("/courses", {
      method: "POST",
      body: { title, topics },
    });
    if (res.status === 200 && res.data.course) {
      appState.selectedCourseId = res.data.course.id;
    }
    if (newCourseDialog && newCourseDialog.open) newCourseDialog.close();
    await refreshCoreData();
  });

  // Modal Busca Global (Ctrl+K)
  const searchDialog = document.getElementById("global-search-dialog");
  const openSearch = () => {
    if (searchDialog && typeof searchDialog.showModal === "function" && !searchDialog.open) {
      searchDialog.showModal();
    }
  };
  document.getElementById("btn-open-search")?.addEventListener("click", openSearch);
  document.getElementById("btn-close-search-dialog")?.addEventListener("click", () => {
    if (searchDialog && searchDialog.open) searchDialog.close();
  });
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      openSearch();
    }
  });
  document.getElementById("global-search-input")?.addEventListener("input", async (e) => {
    const q = e.target.value.trim();
    const listEl = document.getElementById("global-search-results");
    if (!listEl) return;
    if (!q) {
      listEl.innerHTML = `<p class="muted-note">Digite um termo para pesquisar no acervo local do estudante.</p>`;
      return;
    }
    const { status, data } = await apiFetch(`/search?q=${encodeURIComponent(q)}`);
    if (status === 200) {
      const results = data.results || [];
      listEl.innerHTML =
        results
          .map(
            (r) => `
          <div class="info-card">
            <strong>[${escapeHtml(r.kind)}] ${escapeHtml(r.title)}</strong>
            <p class="muted-note">${escapeHtml(r.snippet)}</p>
          </div>
        `,
          )
          .join("") || `<p class="muted-note">Nenhum resultado encontrado para "${escapeHtml(q)}".</p>`;
    }
  });

  // Intervalo de 1 segundo para o Timer Pomodoro
  setInterval(() => {
    if (
      appState.pomodoro.phase === "running_focus" ||
      appState.pomodoro.phase === "running_break"
    ) {
      const res = tickPomodoro(appState.pomodoro, 1);
      appState.pomodoro = res.state;
      savePomodoroToStorage();
      renderPomodoroWidget();
    }
  }, 1000);
}

if (typeof document !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    refreshCoreData();
  });
}

