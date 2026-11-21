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

function renderTutorResponse(text) {
  // SourceLocator emitido pelo Tutor: [doc:<uuid>@<versão>:p<página>:b<bloco>].
  // Converte a referência técnica num link para o arquivo original/página.
  const locator =
    /\[?(doc:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})@\d+:p(\d+):b[^\]\s]*)\]?/gi;
  let html = "";
  let previous = 0;
  const sourceText = String(text || "");
  for (const match of sourceText.matchAll(locator)) {
    html += escapeHtml(sourceText.slice(previous, match.index));
    const [, , docId, page] = match;
    const href = `/documents/${encodeURIComponent(docId)}/original#page=${page}`;
    html += `<a class="tutor-citation" href="${href}" target="_blank" rel="noopener" title="Abrir documento original na página ${page}">📄 Fonte · p. ${page}</a>`;
    previous = match.index + match[0].length;
  }
  html += escapeHtml(sourceText.slice(previous));
  return html.replace(/\n/g, "<br>");
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
  // Uploads enviados cuja resposta ainda não chegou: aparecem no topo da
  // lista do Acervo com barra de progresso (otimista, §12).
  optimisticUploads: [],
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
  calendarWeekOffset: 0,
  // Rascunhos de matérias sugeridas (fluxo +Nova): pendentes de aprovação.
  suggestions: [],
  // Arquivos escolhidos no popup +Nova (ainda não analisados).
  ncFiles: [],
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

// Polling do Acervo: revalida a lista a cada 3 s enquanto houver ingestão
// em andamento (documento com versão pending/indexed). Guarda contra pilhas
// de timers duplicados.
let libraryPollTimer = null;
function scheduleLibraryPoll() {
  if (libraryPollTimer) return;
  libraryPollTimer = setTimeout(async () => {
    libraryPollTimer = null;
    const view = document.getElementById("view-library");
    if (view && !view.hidden) {
      await loadAuxiliaryView("library");
    }
  }, 3000);
}

function sanitizeFilename(name) {
  // Sanitização para o confinamento da API (^[A-Za-z0-9._ -]{1,180}$):
  // NFKC dobra caracteres de compatibilidade (ex.: "º" → "o", acentos → base)
  // e sequências inválidas (com espaços adjacentes) viram um único "_".
  // Nunca altera o arquivo — só o nome.
  let base = String(name || "").normalize("NFKC");
  base = base.replace(/[\s_]*[^A-Za-z0-9._ -]+[\s_]*/g, "_");
  base = base.replace(/_{2,}/g, "_").replace(/^[_ ]+|[_ ]+$/g, "").trim();
  if (!base) base = "documento.pdf";
  // "_" residual encostando na extensão: "relat_rio_final_.pdf" → "relat_rio_final.pdf"
  base = base.replace(/_+(\.\w+)$/, "$1");
  return base.slice(0, 180);
}

function readUploadFileIntoForm(file) {
  document.cookie = `eduagent_user=${appState.userId}; path=/; SameSite=Lax`;
  const filenameInput = document.getElementById("upload-filename");  if (filenameInput) filenameInput.value = sanitizeFilename(file.name);
  const safeName = sanitizeFilename(file.name);
  const reader = new FileReader();
  reader.onload = () => {
    const result = String(reader.result || "");
    const commaIdx = result.indexOf(",");
    appState.pendingUploadBase64 = commaIdx >= 0 ? result.slice(commaIdx + 1) : null;
  };
  reader.readAsDataURL(file);
  if (safeName.endsWith(".md") || safeName.endsWith(".txt") || safeName.endsWith(".tex")) {
    const textReader = new FileReader();
    textReader.onload = () => {
      const textArea = document.getElementById("upload-content-text");
      if (textArea && !textArea.value.trim()) {
        textArea.value = String(textReader.result || "");
      }
    };
    textReader.readAsText(file);
  }
}

// Fila de uploads múltiplos: cada arquivo é enviado em sequência (um
// subprocesso de extração por vez — evita N doclings competindo por CPU),
// com cartão otimista na lista desde o enfileiramento.
async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const commaIdx = result.indexOf(",");
      resolve(commaIdx >= 0 ? result.slice(commaIdx + 1) : "");
    };
    reader.onerror = () => reject(new Error(`Falha ao ler ${file.name}`));
    reader.readAsDataURL(file);
  });
}

function queueUploads(files) {
  const statusEl = document.getElementById("upload-status");
  if (!appState.selectedCourseId) {
    if (statusEl) {
      statusEl.hidden = false;
      statusEl.innerHTML = `<small class="upload-err">✖ Selecione uma disciplina ativa antes de enviar (a ingestão é por disciplina).</small>`;
    }
    return;
  }
  appState.uploadQueue = appState.uploadQueue || [];
  appState.optimisticUploads = appState.optimisticUploads || [];
  for (const file of files) {
    const name = sanitizeFilename(file.name);
    appState.uploadQueue.push({ file, name });
    appState.optimisticUploads.push(name);
  }
  if (statusEl) {
    statusEl.hidden = false;
    statusEl.innerHTML = `<small class="upload-ok">📄 ${files.length} arquivo(s) na fila de ingestão — acompanhe na lista abaixo.</small>`;
  }
  loadAuxiliaryView("library");
  processUploadQueue();
}

async function processUploadQueue() {
  if (appState.uploadQueueRunning) return;
  appState.uploadQueueRunning = true;
  const statusEl = document.getElementById("upload-status");
  const total = appState.uploadQueue.length;
  let done = 0;
  while ((appState.uploadQueue || []).length > 0) {
    const item = appState.uploadQueue.shift();
    try {
      const base64 = await fileToBase64(item.file);
      const { status, data } = await apiFetch("/library/upload", {
        method: "POST",
        body: {
          filename: item.name,
          content_base64: base64 || undefined,
          content_text: "# Material de estudo\nConteúdo inicial.",
          course_id: appState.selectedCourseId,
          auto_ingest: true,
        },
      });
      if (status !== 200) {
        if (statusEl) {
          statusEl.innerHTML = `<small class="upload-err">✖ Falha ao ingerir ${escapeHtml(item.name)}: ${escapeHtml(data?.error?.message || `HTTP ${status}`)}</small>`;
        }
      }
    } catch (err) {
      if (statusEl) {
        statusEl.innerHTML = `<small class="upload-err">✖ Falha ao ingerir ${escapeHtml(item.name)}: ${escapeHtml(String(err))}</small>`;
      }
    }
    done += 1;
    appState.optimisticUploads = (appState.optimisticUploads || []).filter(
      (n) => n !== item.name,
    );
    if (statusEl && total > 1) {
      statusEl.innerHTML = `<small class="upload-ok">Fila: ${done} de ${total} arquivo(s) processado(s)…</small>`;
    }
    await loadAuxiliaryView("library");
    await refreshCoreData();
  }
  appState.uploadQueueRunning = false;
  if (statusEl && total > 0) {
    statusEl.innerHTML = `<small class="upload-ok">✔ Fila concluída: ${total} arquivo(s) enviado(s) para ingestão.</small>`;
  }
  await loadAuxiliaryView("library");
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
      `<span class="banner-pill level-ok"><strong>${escapeHtml(appState.health?.gates?.model_label || "Modelo admitido")}</strong> · Tutoria Socrática e Prática ativas</span>`,
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

// Rascunho em revisão no popup (escopo de módulo: o rail e os handlers do
// popup compartilham a mesma referência).
let reviewedSuggestion = null;

function openSuggestionReview(suggestion) {
  reviewedSuggestion = suggestion;
  const suggestionDialog = document.getElementById("suggestion-review-dialog");
  const titleInput = document.getElementById("suggestion-title-input");
  const topicsInput = document.getElementById("suggestion-topics-input");
  const filesEl = document.getElementById("suggestion-files-list");
  const metaEl = document.getElementById("suggestion-meta");
  if (titleInput) titleInput.value = suggestion.title || "";
  if (topicsInput) topicsInput.value = (suggestion.topics || []).join(", ");
  if (filesEl) {
    filesEl.innerHTML = (suggestion.files || [])
      .map(
        (f) => `
          <li class="nc-file-item">
            <a class="nc-file-name" href="/courses/suggestions/${encodeURIComponent(suggestion.id)}/files/${encodeURIComponent(f.filename)}" target="_blank" rel="noopener" title="Abrir conteúdo do arquivo">📄 ${escapeHtml(f.filename)}</a>
            <span class="nc-class-chip">${escapeHtml(f.class_label || "📄 Outro")}</span>
            <span class="nc-file-size">${((f.size_bytes || 0) / 1024 / 1024).toFixed(2)} MB</span>
          </li>
        `,
      )
      .join("");
  }
  if (metaEl) {
    metaEl.textContent = `Proposta em ${new Date(suggestion.created_at).toLocaleString("pt-BR")} — expira em ${new Date(suggestion.expires_at).toLocaleString("pt-BR")}`;
  }
  if (suggestionDialog && typeof suggestionDialog.showModal === "function") {
    suggestionDialog.showModal();
  }
}

function renderCoursesList() {
  const container = document.getElementById("courses-list");
  if (!container) return;
  const filtered = filterCourses(
    appState.courses,
    appState.courseFilter,
    appState.courseSearch,
  );
  const suggestions = appState.suggestions || [];
  if (filtered.length === 0 && suggestions.length === 0) {
    container.innerHTML = `<p class="muted-note">Nenhuma disciplina encontrada para este filtro.</p>`;
    return;
  }
  const suggestionCards = suggestions
    .map(
      (s) => `
        <div class="course-card is-suggestion" data-suggestion-id="${escapeHtml(s.id)}" role="option" aria-selected="false" tabindex="0">
          <div class="course-card-top">
            <h3 class="course-card-title">${escapeHtml(s.title)}</h3>
            <span class="suggestion-badge">⏳ esperando aprovação</span>
          </div>
          <p class="course-card-preview">${escapeHtml((s.files || []).map((f) => f.filename).join(", "))}</p>
          <div class="course-card-meta">
            <span>${(s.topics || []).length} tópico(s) sugerido(s) · ${(s.files || []).length} arquivo(s)</span>
          </div>
        </div>
      `,
    )
    .join("");
  const courseCards = filtered
    .map((course) => {
      const selected = course.id === appState.selectedCourseId ? "is-selected" : "";
      const readyClass = course.ready_to_study ? "is-ready" : "is-pending";
      const readyLabel = course.ready_to_study
        ? "● Pronta p/ estudar"
        : "○ Sem material ativo";
      return `
        <div class="course-card ${selected}" data-course-id="${escapeHtml(course.id)}" role="option" aria-selected="${course.id === appState.selectedCourseId}" tabindex="0">
          <div class="course-card-top">
            <h3 class="course-card-title">${escapeHtml(course.title)}</h3>
            <span class="course-ready-dot ${readyClass}">${readyLabel}</span>
            <details class="doc-action-menu course-menu">
              <summary aria-label="Ações da disciplina" title="Ações da disciplina">…</summary>
              <div class="doc-action-popover">
                <button type="button" data-archive-course="${escapeHtml(course.id)}" data-course-title="${escapeHtml(course.title)}" data-archive-to="true">Arquivar</button>
                <button type="button" class="danger" data-delete-course="${escapeHtml(course.id)}" data-course-title="${escapeHtml(course.title)}">Apagar disciplina</button>
              </div>
            </details>
          </div>
          <p class="course-card-preview">${escapeHtml(course.last_turn_preview)}</p>
          <div class="course-card-meta">
            <span class="tier-badge">P${escapeHtml(course.sort_tier)} · ${escapeHtml(course.sort_reason_label)}</span>
            <span>Domínio: ${escapeHtml(course.domain_status)}</span>
          </div>
        </div>
      `;
    })
    .join("");

  container.innerHTML = suggestionCards + courseCards;

  container.querySelectorAll("[data-course-id]").forEach((card) => {
    card.addEventListener("click", () => {
      const cid = card.getAttribute("data-course-id");
      selectCourse(cid);
    });
  });
  container.querySelectorAll("[data-suggestion-id]").forEach((card) => {
    card.addEventListener("click", () => {
      const sid = card.getAttribute("data-suggestion-id");
      const suggestion = (appState.suggestions || []).find((s) => s.id === sid);
      if (suggestion) openSuggestionReview(suggestion);
    });
  });
  // O "…" não deve selecionar a disciplina: cliques no menu ficam no menu.
  container.querySelectorAll(".course-menu").forEach((menu) => {
    menu.addEventListener("click", (e) => e.stopPropagation());
  });
  // Ações da disciplina no rail: arquivar / apagar (mesmos endpoints do Acervo)
  container.querySelectorAll("[data-archive-course]").forEach((button) => {
    button.addEventListener("click", async () => {
      const cid = button.getAttribute("data-archive-course");
      const title = button.getAttribute("data-course-title") || "esta disciplina";
      if (!window.confirm(`Arquivar “${title}”? Ela sai deste rail — dá para desarquivar no Acervo.`)) return;
      button.disabled = true;
      try {
        const result = await apiFetch(`/courses/${encodeURIComponent(cid)}/archive`, {
          method: "POST",
          body: { archived: true },
        });
        if (result.status !== 200) throw new Error(result.data?.error?.message || "Falha ao arquivar.");
        if (appState.selectedCourseId === cid) {
          appState.selectedCourseId = (appState.courses || []).find((c) => c.id !== cid)?.id || null;
        }
        await refreshCoreData();
      } catch (error) {
        window.alert(String(error));
        button.disabled = false;
      }
    });
  });
  container.querySelectorAll("[data-delete-course]").forEach((button) => {
    button.addEventListener("click", async () => {
      const cid = button.getAttribute("data-delete-course");
      const title = button.getAttribute("data-course-title") || "esta disciplina";
      if (!window.confirm(`Apagar “${title}” e TODO o material ingerido dela (documentos, tópicos e índice)? Esta ação não pode ser desfeita.`)) return;
      button.disabled = true;
      try {
        const result = await apiFetch(`/courses/${encodeURIComponent(cid)}`, { method: "DELETE" });
        if (result.status !== 200) throw new Error(result.data?.error?.message || "Não foi possível apagar.");
        if (appState.selectedCourseId === cid) {
          appState.selectedCourseId = (appState.courses || []).find((c) => c.id !== cid)?.id || null;
        }
        await refreshCoreData();
      } catch (error) {
        window.alert(String(error));
        button.disabled = false;
      }
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
    syncPracticeTopicGate();
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
  syncPracticeTopicGate();
}

function hasPendingPracticeItem() {
  const checkpoint = appState.sessionDetail?.checkpoint;
  if (checkpoint && Object.hasOwn(checkpoint, "pending_item_ref")) {
    return Boolean(checkpoint.pending_item_ref);
  }
  return (appState.sessionDetail?.items || []).some(
    (item) => !item.attempt_id && !item.cancelled,
  );
}

function pendingPracticeItemId() {
  const ref = appState.sessionDetail?.checkpoint?.pending_item_ref;
  if (typeof ref === "string" && ref.startsWith("item:")) {
    return ref.slice("item:".length).split("@", 1)[0];
  }
  return null;
}

function syncPracticeTopicGate() {
  const topicSelect = document.getElementById("topic-select");
  const intentSelect = document.getElementById("intent-select");
  const sendButton = document.getElementById("btn-send-turn");
  const hintButton = document.getElementById("btn-request-hint");
  const note = document.getElementById("topic-practice-note");
  const hasTopic = Boolean(topicSelect?.value);
  const hasPending = hasPendingPracticeItem();
  const practiceNeedsTopic =
    intentSelect?.value === "/practice" && !hasTopic && !hasPending;
  const submitNeedsPending =
    intentSelect?.value === "/submit" && !hasPending;

  if (sendButton) {
    sendButton.disabled = practiceNeedsTopic || submitNeedsPending;
    const sendHint = submitNeedsPending
      ? "Não há exercício pendente para responder."
      : practiceNeedsTopic
        ? "Selecione um tópico antes de criar um exercício."
        : "";
    sendButton.title = sendHint;
    const sendGroup = sendButton.parentElement;
    if (sendGroup) {
      if (sendHint) sendGroup.dataset.hoverHint = sendHint;
      else delete sendGroup.dataset.hoverHint;
    }
  }
  if (hintButton) {
    hintButton.disabled = !hasPending;
    hintButton.title = hasPending
      ? "Pedir a próxima dica do exercício pendente."
      : "Inicie ou selecione uma atividade pendente para pedir dica.";
  }
  if (note) {
    note.hidden = !(practiceNeedsTopic || submitNeedsPending);
    note.textContent = submitNeedsPending
      ? "Não há exercício pendente para responder."
      : "Selecione um tópico para criar um exercício.";
  }
  document.querySelectorAll("[data-new-practice]").forEach((button) => {
    button.disabled = !hasTopic;
    const hint = hasTopic
      ? "Preparar um novo exercício no campo de mensagem."
      : "Selecione um tópico para criar um exercício.";
    button.title = hint;
    const actions = button.parentElement;
    if (actions) {
      if (!hasTopic) actions.dataset.hoverHint = hint;
      else delete actions.dataset.hoverHint;
    }
  });
}

function renderSessionTimelineAndDrawer() {
  const timeline = document.getElementById("chat-timeline");
  const evidenceList = document.getElementById("drawer-evidence-list");
  const rubricList = document.getElementById("drawer-rubric-list");
  const planSummary = document.getElementById("drawer-plan-summary");
  const covBadge = document.getElementById("evidence-coverage-badge");
  if (!timeline) return;

  const detail = appState.sessionDetail || {};

  // events são o log de auditoria interno (§15), não mensagens de chat.
  // Os payloads JSON e eventos de execução não devem aparecer ao estudante.
  const cardsHtml = [];

  // Turnos locais (resposta direta do POST /turns) vêm depois dos eventos
  // persistidos, em ordem de ocorrência.
  for (const lt of appState.localTurns || []) {
    if (lt.message) {
      cardsHtml.push(`
        <article class="timeline-card role-student">
          <div class="card-header-meta">
            <strong>${lt.pending ? "Estudante · Enviando…" : "Estudante"}</strong>
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
          <div class="tutor-response">${renderTutorResponse(lt.responseText)}</div>
        </article>
      `);
    }
  }

  const sessionItems = detail.items || [];
  const pendingItemId = pendingPracticeItemId();
  const currentPendingItem = pendingItemId
    ? sessionItems.find((candidate) => candidate.id === pendingItemId)
    : detail.checkpoint &&
        Object.hasOwn(detail.checkpoint, "pending_item_ref")
      ? null
      : sessionItems.find(
          (candidate) => !candidate.attempt_id && !candidate.cancelled,
        );
  const currentActivity = currentPendingItem || null;
  const previousActivities = currentActivity
    ? sessionItems.filter((candidate) => candidate.id !== currentActivity.id)
    : sessionItems;
  for (const rawItem of currentActivity ? [currentActivity] : []) {
    const item = sanitizeLearningItemForDisplay(rawItem);
    const isPendingItem =
      !item.attempt_id && item.id === currentPendingItem?.id;
    const assessment = (detail.assessments || []).find(
      (candidate) => candidate.attempt_id && candidate.attempt_id === item.attempt_id,
    );
    const assessed = assessment?.payload?.assessment || assessment?.payload || {};
    const correctness = assessed.correctness;
    const assessmentReason =
      assessed.criterion_results?.find((result) => result.reason)?.reason ||
      assessed.reason ||
      "";
    const activityStatus = item.cancelled
      ? "Exercício cancelado"
      : item.attempt_id
      ? correctness === "correct"
        ? "✅ Resposta correta"
        : correctness === "incorrect"
          ? "↻ Resposta incorreta"
          : "✓ Resposta registrada"
      : isPendingItem
        ? "⏳ Aguardando sua resposta"
        : "Atividade anterior";
    const refsHtml = (item.source_refs || [])
      .map((ref, idx) => {
        const href = ref.doc_id
          ? `/documents/${encodeURIComponent(ref.doc_id)}/original${
              ref.physical_page ? `#page=${ref.physical_page}` : ""
            }`
          : null;
        return href
          ? `<a class="source-ref-btn" href="${href}" target="_blank" rel="noopener" title="Abrir o documento original na página citada">[Fonte #${idx + 1}]</a>`
          : `<button type="button" class="source-ref-btn" data-focus-chunk="${escapeHtml(ref.chunk_id || idx)}">[Fonte #${idx + 1}]</button>`;
      })
      .join("");
    const answerHtml = item.expected_answer
      ? `<div class="info-card"><strong>Gabarito Revelado (L3):</strong> ${escapeHtml(item.expected_answer)}</div>`
      : `<p class="muted-note">🔒 Gabarito oculto na escada socrática (${escapeHtml(item.help_level)}). Tente responder de forma independente ou peça dica gradual.</p>`;
    cardsHtml.push(`
      <article class="timeline-card role-item">
        <div class="card-header-meta">
          <strong>🎯 Atividade atual · Dica ${escapeHtml(item.help_level)}</strong>
          <span>${escapeHtml(activityStatus)}</span>
        </div>
        <p>${escapeHtml(item.prompt)}</p>
        ${
          item.attempt_id && assessmentReason
            ? `<p class="activity-feedback">${correctness === "correct" ? "✅" : "ℹ️"} ${escapeHtml(assessmentReason)}</p>`
            : ""
        }
        ${answerHtml}
        <div>${refsHtml}</div>
        ${
          isPendingItem
            ? `<div class="activity-actions">
                <button type="button" class="btn-primary btn-compact" data-activity-intent="/submit">Responder</button>
                <button type="button" class="btn-ghost btn-compact" data-activity-intent="/practice">💡 Pedir dica</button>
                <button type="button" class="btn-ghost btn-compact" data-activity-intent="/ask">Fazer pergunta</button>
                <button type="button" class="btn-ghost btn-compact activity-cancel-button" data-cancel-activity="${escapeHtml(item.id)}">Cancelar exercício</button>
              </div>`
            : ""
        }
        ${
          (item.attempt_id || item.cancelled) &&
          !currentPendingItem &&
          item.id === currentActivity?.id
            ? `<div class="activity-actions"><button type="button" class="btn-ghost btn-compact" data-new-practice="${escapeHtml(item.id)}">🎯 Novo exercício</button></div>`
            : ""
        }
      </article>
    `);
  }
  if (previousActivities.length > 0) {
    cardsHtml.unshift(`
      <details class="activity-history">
        <summary>Atividades anteriores (${previousActivities.length})</summary>
        <div class="activity-history-list">
          ${previousActivities
            .map((oldItem) => {
              const oldAssessment = (detail.assessments || []).find(
                (candidate) => candidate.attempt_id && candidate.attempt_id === oldItem.attempt_id,
              );
              const oldResult =
                oldAssessment?.payload?.assessment?.correctness ||
                oldAssessment?.payload?.correctness;
              const oldStatus = oldItem.cancelled
                ? "Exercício cancelado"
                : !oldItem.attempt_id
                ? "Aguardando resposta"
                : oldResult === "correct"
                  ? "Resposta correta"
                  : oldResult === "incorrect"
                    ? "Resposta incorreta"
                    : "Resposta registrada";
              return `<article class="activity-history-item">
                <span>${escapeHtml(oldStatus)} · Dica ${escapeHtml(oldItem.help_level)}</span>
                <p>${escapeHtml(oldItem.prompt)}</p>
              </article>`;
            })
            .join("")}
        </div>
      </details>
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
  syncPracticeTopicGate();

  timeline.querySelectorAll("[data-activity-intent]").forEach((button) => {
    button.addEventListener("click", async () => {
      const intent = button.getAttribute("data-activity-intent");
      const intentSelect = document.getElementById("intent-select");
      if (intentSelect && intent) intentSelect.value = intent;
      const composer = document.getElementById("composer-textarea");
      composer?.scrollIntoView({ behavior: "smooth", block: "center" });
      composer?.focus({ preventScroll: true });
    });
  });
  timeline.querySelectorAll("[data-cancel-activity]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("Cancelar somente este exercício? A conversa da disciplina continuará aberta.")) return;
      button.disabled = true;
      try {
        const result = await apiFetch(
          `/turns/${encodeURIComponent(appState.activeSessionId)}/cancel`,
          { method: "POST", body: { cancel_activity: true } },
        );
        if (result.status !== 200) {
          throw new Error(result.data?.error?.message || "Não foi possível cancelar o exercício.");
        }
        await refreshCoreData();
        const sessionRes = await apiFetch(
          `/sessions/${encodeURIComponent(appState.activeSessionId)}?course_id=${encodeURIComponent(appState.selectedCourseId || "")}`,
        );
        if (sessionRes.status === 200) appState.sessionDetail = sessionRes.data;
        renderSessionTimelineAndDrawer();
      } catch (error) {
        window.alert(String(error));
        button.disabled = false;
      }
    });
  });
  timeline.querySelectorAll("[data-new-practice]").forEach((button) => {
    button.addEventListener("click", async () => {
      const intentSelect = document.getElementById("intent-select");
      if (intentSelect) intentSelect.value = "/practice";
      const composer = document.getElementById("composer-textarea");
      composer?.scrollIntoView({ behavior: "smooth", block: "center" });
      composer?.focus({ preventScroll: true });
    });
  });

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
            <div><strong>📄 ${escapeHtml(ch.display_name || ch.original_ref)}</strong> · <small>${escapeHtml(ch.version_status)}</small></div>
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
      const chunkEl =
        document.getElementById(`chunk-${chunkId}`) ||
        (Number.isInteger(Number(chunkId))
          ? document.querySelectorAll(".evidence-chunk-card")[Number(chunkId)]
          : null);
      if (chunkEl && typeof chunkEl.scrollIntoView === "function") {
        chunkEl.classList.add("is-focused");
        chunkEl.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => chunkEl.classList.remove("is-focused"), 2400);
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
function recordLocalTurnFromResponse(message, data, existingTurn = null) {
  const turn = existingTurn || {
    message,
    occurredAt: new Date().toISOString(),
    responseText: null,
    errorText: null,
    pending: false,
  };
  turn.pending = false;
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
  } else if (out && out.feedback) {
    const fb = out.feedback;
    const parts = [`Avaliação da submissão: ${fb.correctness || "—"}.`];
    const review = Array.isArray(out.review_requests) ? out.review_requests : [];
    if (review.length > 0) {
      parts.push("Revisão espaçada agendada para este tópico.");
    }
    turn.responseText = parts.join(" ");
  } else if (data && (data.status === "waiting" || data.status === "waiting_student")) {
    turn.responseText = "Turno registrado — aguardando ação do estudante.";
  }
  if (!existingTurn) {
    appState.localTurns.push(turn);
    if (appState.localTurns.length > 100) appState.localTurns.shift();
  }
}

/**
 * POST /turns com registro e renderização imediata do resultado na timeline
 * (contrato compartilhado por todos os disparadores de turno da UI: composer,
 * dica gradual, Pomodoro, plano e exportação).
 */
let livePollTimer = null;
let lastLiveState = { phase: "reading", text: "", reasoning: "" };

// Cartão de gate (§9/§6.3): turno waiting_student com interrupt — o usuário
// aprova/recusa direto na timeline; a retomada é POST /turns/{id}/resume.
function renderApprovalGate(sessionId, question) {
  removeApprovalGate();
  const timeline = document.getElementById("chat-timeline");
  if (!timeline) return;
  const card = document.createElement("article");
  card.id = "approval-gate-card";
  card.className = "timeline-card role-tutor approval-gate";
  const qText =
    (question && (question.question || question.message)) ||
    JSON.stringify(question);
  const preview = question && question.preview ? question.preview : null;
  card.innerHTML = `
    <div class="card-header-meta"><strong>⏸ Aguardando sua confirmação</strong></div>
    <div class="approval-question">${escapeHtml(String(qText))}</div>
    ${
      preview
        ? `<pre class="approval-preview">${escapeHtml(JSON.stringify(preview, null, 2))}</pre>`
        : ""
    }
    <div class="approval-actions">
      <button type="button" class="btn-primary btn-compact" data-answer="yes">✅ Aprovar</button>
      <button type="button" class="btn-ghost btn-compact" data-answer="no">✖ Recusar</button>
    </div>`;
  card.querySelectorAll("[data-answer]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const approved = btn.getAttribute("data-answer") === "yes";
      card.querySelectorAll("button").forEach((b) => (b.disabled = true));
      try {
        const res = await apiFetch(
          `/turns/${encodeURIComponent(sessionId)}/resume`,
          {
            method: "POST",
            body: { approved, confirmed: approved },
          },
        );
        removeApprovalGate();
        if (res.data) recordLocalTurnFromResponse("", res.data);
        renderSessionTimelineAndDrawer();
        await refreshCoreData();
      } catch (_err) {
        card.querySelectorAll("button").forEach((b) => (b.disabled = false));
      }
    });
  });
  timeline.appendChild(card);
  timeline.scrollTop = timeline.scrollHeight;
}

function removeApprovalGate() {
  document.getElementById("approval-gate-card")?.remove();
}
const LIVE_PHASE_LABEL = {
  reading: "📖 Lendo o contexto da sessão",
  thinking: "💭 Pensando",
  answering: "✍️ Gerando a resposta",
};
const LIVE_PREFS_KEY = "eduagent_live_prefs_v1";

function getLivePrefs() {
  try {
    return JSON.parse(localStorage.getItem(LIVE_PREFS_KEY)) || {};
  } catch (_err) {
    return {};
  }
}

function setLivePref(key, value) {
  try {
    const prefs = getLivePrefs();
    prefs[key] = value;
    localStorage.setItem(LIVE_PREFS_KEY, JSON.stringify(prefs));
  } catch (_err) {
    // storage indisponível: preferências ficam só na sessão
  }
}

function renderLiveBubble(state) {
  const timeline = document.getElementById("chat-timeline");
  if (!timeline) return;
  let bubble = document.getElementById("live-turn-bubble");
  if (!bubble) {
    bubble = document.createElement("article");
    bubble.id = "live-turn-bubble";
    bubble.className = "timeline-card role-tutor live-bubble";
    bubble.addEventListener("click", () => {
      // Clique no balão revela/oculta o stream bruto quando escondido
      if (bubble.dataset.isjson === "1") {
        bubble.dataset.revealed = bubble.dataset.revealed === "1" ? "0" : "1";
        renderLiveBubble(lastLiveState);
      }
    });
    timeline.appendChild(bubble);
  }
  const prefs = getLivePrefs();
  const phase = state.phase || "reading";
  const label = LIVE_PHASE_LABEL[phase] || "⏳ Trabalhando";
  const raw = String(state.text || "");
  const reasoning = String(state.reasoning || "");
  const isJson = raw.trimStart().startsWith("{");
  const revealed = bubble.dataset.revealed === "1";
  const showRawLive = prefs.showLiveText === true;
  const dots = `<span class="live-dots"><span></span><span></span><span></span></span>`;
  let body = "";
  if (phase === "thinking" && reasoning) {
    if (prefs.showThinking === true) {
      body = `<div class="live-text live-reasoning">${escapeHtml(reasoning.slice(-600))}</div>`;
    }
  } else if (phase === "answering" && raw) {
    if (isJson) {
      // Saída estruturada (json_schema): oculta por padrão — clique revela
      body = `<div class="live-structured-note">estruturando a resposta… ${raw.length} caracteres${
        showRawLive || revealed
          ? `</div><div class="live-text live-reasoning">${escapeHtml(raw)}</div>`
          : ` — <em>clique no balão para ver o texto bruto</em></div>`
      }`;
    } else {
      body = `<div class="live-text">${escapeHtml(raw)}<span class="live-caret"></span></div>`;
    }
  }
  bubble.dataset.isjson = isJson ? "1" : "0";
  bubble.innerHTML = `
    <div class="card-header-meta">
      <strong>Agente (gerando)</strong>${dots}
    </div>
    <div class="live-phase">${label}</div>
    ${body}`;
  timeline.scrollTop = timeline.scrollHeight;
}

function removeLiveBubble() {
  document.getElementById("live-turn-bubble")?.remove();
}

function startLivePoll() {
  stopLivePoll();
  lastLiveState = { phase: "reading", text: "", reasoning: "" };
  livePollTimer = setInterval(async () => {
    try {
      const { status, data } = await apiFetch("/generation/live");
      if (status === 200) {
        lastLiveState = data;
        renderLiveBubble(data);
      }
    } catch (_err) {
      // silencioso: o POST /turns entrega o resultado final
    }
  }, 400);
}

function stopLivePoll() {
  if (livePollTimer) {
    clearInterval(livePollTimer);
    livePollTimer = null;
  }
  removeLiveBubble();
}

async function postTurnAndRecord(message, payload) {
  const turn = {
    message,
    occurredAt: new Date().toISOString(),
    responseText: null,
    errorText: null,
    pending: true,
  };
  appState.localTurns.push(turn);
  if (appState.localTurns.length > 100) appState.localTurns.shift();
  renderSessionTimelineAndDrawer();
  const timeline = document.getElementById("chat-timeline");
  if (timeline) timeline.scrollTop = timeline.scrollHeight;
  startLivePoll();
  try {
    const res = await apiFetch("/turns", {
      method: "POST",
      body: {
        session_id: appState.activeSessionId,
        message,
        payload,
      },
    });
    recordLocalTurnFromResponse(message, res.data, turn);
    renderSessionTimelineAndDrawer();
    await refreshCoreData();
    const sessionRes = await apiFetch(
      `/sessions/${encodeURIComponent(appState.activeSessionId)}?course_id=${encodeURIComponent(appState.selectedCourseId || "")}`,
    );
    if (sessionRes.status === 200) {
      appState.sessionDetail = sessionRes.data;
      renderSessionTimelineAndDrawer();
    }
    // Gate de confirmação (§9/§6.3): turno pausado esperando o estudante
    if (res.data?.question || res.data?.interrupted) {
      renderApprovalGate(appState.activeSessionId, res.data.question);
    }
    return res.data;
  } catch (error) {
    turn.pending = false;
    turn.errorText = `Não foi possível concluir o envio: ${error?.message || error}`;
    renderSessionTimelineAndDrawer();
    throw error;
  } finally {
    stopLivePoll();
  }
}

async function selectCourse(courseId) {
  appState.selectedCourseId = courseId;
  const course = appState.courses.find((c) => c.id === courseId) || null;
  appState.selectedCourseTitle = course?.title || null;
  // Cada disciplina tem a sua própria conversa: a sessão do turno é
  // derivada do id da disciplina (UUID estável — mesma disciplina sempre
  // reabre a mesma linha do tempo; disciplinas nunca se misturam).
  appState.activeSessionId = courseId || "00000000-0000-0000-0000-000000000099";
  appState.pomodoro = createPomodoroState(course);
  savePomodoroToStorage();
  renderCoursesList();
  renderActiveCourseHeader();
  renderPomodoroWidget();
  if (appState.activeView === "library") {
    await loadAuxiliaryView("library");
  }
  const { status, data } = await apiFetch(
    `/sessions/${encodeURIComponent(appState.activeSessionId)}?course_id=${encodeURIComponent(courseId || "")}`,
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

  // Rascunhos de matérias sugeridas (fluxo +Nova): falha silenciosa — o rail
  // mostra só as matérias reais se a rota não responder.
  const suggestionsRes = await apiFetch("/courses/suggestions");
  if (suggestionsRes.status === 200 && Array.isArray(suggestionsRes.data.suggestions)) {
    appState.suggestions = suggestionsRes.data.suggestions;
    renderCoursesList();
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

function datePartsInTimezone(date, timezone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return {
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
    hour: Number(values.hour),
    minute: Number(values.minute),
  };
}

function dateKeyInTimezone(date, timezone) {
  const parts = datePartsInTimezone(date, timezone);
  return `${parts.year}-${String(parts.month).padStart(2, "0")}-${String(parts.day).padStart(2, "0")}`;
}

function getVisibleWeekStart() {
  const timezone = appState.health?.gates?.timezone || undefined;
  const localToday = datePartsInTimezone(new Date(), timezone);
  const start = new Date(Date.UTC(localToday.year, localToday.month - 1, localToday.day));
  start.setUTCDate(
    start.getUTCDate() - start.getUTCDay() + appState.calendarWeekOffset * 7,
  );
  return start;
}

async function loadAuxiliaryView(viewName) {
  if (viewName === "calendar") {
    const { status, data } = await apiFetch("/calendar");
    const el = document.getElementById("calendar-view-content");
    if (!el || status !== 200) return;
    const weekStart = getVisibleWeekStart();
    const weekDates = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(weekStart);
      date.setUTCDate(date.getUTCDate() + index);
      return date;
    });
    const weekKeys = weekDates.map((date) => date.toISOString().slice(0, 10));
    const timezone = appState.health?.gates?.timezone || undefined;
    const demandsByDate = new Map();
    for (const demand of data.demands || []) {
      if (!demand.due_local_date) continue;
      const dayDemands = demandsByDate.get(demand.due_local_date) || [];
      dayDemands.push(demand);
      demandsByDate.set(demand.due_local_date, dayDemands);
    }
    const blocksByDate = new Map();
    for (const block of data.logical_blocks || []) {
      const start = new Date(block.planned_start_utc);
      const end = new Date(block.planned_end_utc);
      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) continue;
      const dateKey = dateKeyInTimezone(start, timezone);
      if (!weekKeys.includes(dateKey)) continue;
      const startParts = datePartsInTimezone(start, timezone);
      const endParts = datePartsInTimezone(end, timezone);
      const startMinute = startParts.hour * 60 + startParts.minute;
      let endMinute = endParts.hour * 60 + endParts.minute;
      if (dateKeyInTimezone(end, timezone) !== dateKey) endMinute = 23 * 60;
      const visibleStart = Math.max(startMinute, 6 * 60);
      const visibleEnd = Math.min(endMinute, 23 * 60);
      if (visibleEnd <= visibleStart) continue;
      const dayBlocks = blocksByDate.get(dateKey) || [];
      dayBlocks.push({
        ...block,
        top: ((visibleStart - 6 * 60) / 60) * 64,
        height: Math.max(((visibleEnd - visibleStart) / 60) * 64, 36),
        localStart: startParts,
        localEnd: endParts,
      });
      blocksByDate.set(dateKey, dayBlocks);
    }
    const dateLabel = new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "short",
      timeZone: "UTC",
    });
    const dayLabel = new Intl.DateTimeFormat("pt-BR", {
      weekday: "short",
      timeZone: "UTC",
    });
    const startLabel = dateLabel.format(weekDates[0]);
    const endLabel = new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(weekDates[6]);
    const todayKey = dateKeyInTimezone(new Date(), timezone);
    const dayHeaders = weekDates
      .map((date, index) => {
        const key = weekKeys[index];
        const dayDemands = demandsByDate.get(key) || [];
        return `<div class="calendar-day-heading${key === todayKey ? " is-today" : ""}">
          <strong>${escapeHtml(dayLabel.format(date).replace(".", ""))}</strong>
          <span>${escapeHtml(dateLabel.format(date))}</span>
          ${dayDemands
            .map(
              (demand) =>
                `<small title="${escapeHtml(demand.activity_kind || "Demanda")}">📌 ${escapeHtml(demand.activity_kind || "Demanda")}</small>`,
            )
            .join("")}
        </div>`;
      })
      .join("");
    const timeLabels = Array.from({ length: 17 }, (_, index) => {
      const hour = index + 6;
      return `<div class="calendar-time-label">${String(hour).padStart(2, "0")}:00</div>`;
    }).join("");
    const dayColumns = weekKeys
      .map((key) => {
        const blocks = blocksByDate.get(key) || [];
        return `<div class="calendar-day-column" data-date="${key}">
          ${blocks
            .map((block) => {
              const startText = `${String(block.localStart.hour).padStart(2, "0")}:${String(block.localStart.minute).padStart(2, "0")}`;
              const endText = `${String(block.localEnd.hour).padStart(2, "0")}:${String(block.localEnd.minute).padStart(2, "0")}`;
              return `<article class="calendar-event" style="top:${block.top}px;height:${block.height}px" title="${escapeHtml(`${block.summary || "Bloco de estudo"} · ${startText}–${endText}`)}">
                <strong>${escapeHtml(block.summary || "Bloco de estudo")}</strong>
                <span>${startText}–${endText}</span>
              </article>`;
            })
            .join("")}
        </div>`;
      })
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
    el.className = "calendar-content";
    el.innerHTML = `
      <div class="calendar-week-toolbar">
        <button type="button" class="btn-ghost btn-compact" data-calendar-week="-1" aria-label="Semana anterior">‹</button>
        <strong>${escapeHtml(startLabel)} – ${escapeHtml(endLabel)}</strong>
        <button type="button" class="btn-ghost btn-compact" data-calendar-week="1" aria-label="Próxima semana">›</button>
        <button type="button" class="btn-secondary btn-compact" data-calendar-week="today">Hoje</button>
      </div>
      <div class="calendar-scroll">
        <div class="calendar-week-grid">
          <div class="calendar-week-head">
            <div class="calendar-time-corner">${escapeHtml(timezone || "Horário local")}</div>
            ${dayHeaders}
          </div>
          <div class="calendar-week-body">
            <div class="calendar-time-axis">${timeLabels}</div>
            ${dayColumns}
          </div>
        </div>
      </div>
      ${(data.demands || []).length === 0 && (data.logical_blocks || []).length === 0 ? `<p class="muted-note">Ainda não há demandas ou blocos nesta agenda. Gere uma proposta para visualizar os horários sugeridos.</p>` : ""}
      ${exportsHtml ? `<div class="calendar-exports"><h4>Exportações</h4>${exportsHtml}</div>` : ""}
    `;
    el.querySelectorAll("[data-calendar-week]").forEach((button) => {
      button.addEventListener("click", async () => {
        const value = button.getAttribute("data-calendar-week");
        appState.calendarWeekOffset =
          value === "today"
            ? 0
            : appState.calendarWeekOffset + Number(value || 0);
        await loadAuxiliaryView("calendar");
      });
    });
  } else if (viewName === "library") {
    const courseQuery = appState.selectedCourseId
      ? `?course_id=${encodeURIComponent(appState.selectedCourseId)}`
      : "";
    const { status, data } = await apiFetch(`/library${courseQuery}`);
    const el = document.getElementById("library-view-content");
    if (!el || status !== 200) return;
    const docs = data.documents || [];
    // Cartões otimistas que o servidor já persistiu saem do espelho (a linha
    // real assume, com o progresso por página) para não duplicar.
    const serverNames = new Set(docs.map((d) => d.display_name));
    const pendingOptimistic = (appState.optimisticUploads || []).filter(
      (n) => !serverNames.has(n),
    );
    const optimisticHtml = pendingOptimistic
      .map(
        (name) => `
        <div class="info-card doc-card">
          <div class="doc-card-head"><strong>📄 ${escapeHtml(name)}</strong><span class="status-chip status-ingesting">⏳ Enviando</span></div>
          <span>Disciplina: ${escapeHtml(appState.selectedCourseTitle || "disciplina ativa")}</span>
          <div class="ingest-progress" role="progressbar" aria-label="Enviando documento"><div class="ingest-progress-fill"></div></div>
          <small class="muted-note">Upload em andamento — o progresso da ingestão aparece aqui assim que o servidor responder.</small>
        </div>
      `,
      )
      .join("");
    const docsHtml = docs
      .map((d) => {
        const active = d.version_status === "active";
        const failed = d.version_status === "failed";
        const prog = d.progress || null;
        const hasPages = prog && Number(prog.total_pages) > 0;
        const pct = hasPages
          ? Math.min(100, Math.round((100 * Number(prog.pages_done)) / Number(prog.total_pages)))
          : null;
        const chip = active
          ? `<span class="status-chip status-active">✔ Ativo</span>`
          : failed
            ? `<span class="status-chip status-failed">✖ Falhou</span>`
            : `<span class="status-chip status-ingesting">⏳ Ingerindo</span>`;
        let bar = "";
        if (!active) {
          const fillStyle = pct !== null ? ` style="width: ${pct}%; animation: none;"` : "";
          const label = failed
            ? `<small class="muted-note">A extração falhou — reenvie o arquivo para tentar de novo.</small>`
            : pct !== null
              ? `<small class="muted-note">Página ${escapeHtml(String(prog.pages_done))} de ${escapeHtml(String(prog.total_pages))} (${pct}%)${pct >= 100 ? " — indexando embeddings…" : ""}</small>`
              : `<small class="muted-note">Preparando extração (Curador + Bibliotecário) — a lista atualiza automaticamente.</small>`;
          bar = `<div class="ingest-progress${pct !== null ? " determinate" : ""}${failed ? " failed" : ""}" role="progressbar" aria-label="Progresso da ingestão"${pct !== null ? ` aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"` : ""}><div class="ingest-progress-fill"${fillStyle}></div></div>${label}`;
        }
        return `
        <div class="info-card doc-card">
          <div class="doc-card-head">
            <strong>📄 ${escapeHtml(d.display_name || d.original_ref || d.doc_id)}</strong>
            <div class="doc-card-actions">
              ${chip}
              <details class="doc-action-menu">
                <summary aria-label="Ações do documento" title="Ações">…</summary>
                <div class="doc-action-popover">
                  <a href="/documents/${encodeURIComponent(d.doc_id)}/original" target="_blank" rel="noopener">Abrir (PDF/texto)</a>
                  <button type="button" data-delete-document="${escapeHtml(d.doc_id)}" data-document-name="${escapeHtml(d.display_name || d.doc_id)}">Excluir do acervo</button>
                </div>
              </details>
            </div>
          </div>
          <span>Disciplina: ${escapeHtml(d.course_title)} · Chunks: ${escapeHtml(String(d.chunk_count))}</span>
          ${bar}
        </div>
      `;
      })
      .join("");

    // Ações de disciplina vivem no rail (… à direita do nome). No Acervo só
    // aparece o grupo "Arquivadas" (quando existir) — de lá se desarquiva.
    let coursesHtml = "";
    const allRes = await apiFetch("/courses?include_archived=1");
    if (allRes.status === 200 && Array.isArray(allRes.data.courses)) {
      const activeIds = new Set((appState.courses || []).map((c) => c.id));
      const all = allRes.data.courses;
      const archivedCourses = all.filter((c) => !activeIds.has(c.id));
      if (archivedCourses.length) {
        const archivedChip = (c) => `
          <div class="lib-course-chip is-archived${c.id === appState.selectedCourseId ? " is-selected" : ""}">
            <button type="button" class="lib-course-name" data-lib-select-course="${escapeHtml(c.id)}" title="Disciplina arquivada">${escapeHtml(c.title)} · arquivada</button>
            <details class="doc-action-menu">
              <summary aria-label="Ações da disciplina" title="Ações da disciplina">…</summary>
              <div class="doc-action-popover">
                <button type="button" data-archive-course="${escapeHtml(c.id)}" data-course-title="${escapeHtml(c.title)}" data-archive-to="false">Desarquivar</button>
                <button type="button" class="danger" data-delete-course="${escapeHtml(c.id)}" data-course-title="${escapeHtml(c.title)}">Apagar disciplina</button>
              </div>
            </details>
          </div>
        `;
        coursesHtml = `
          <div class="lib-courses-block">
            <h4 class="lib-courses-heading">Arquivadas</h4>
            <div class="lib-course-chips">
              ${archivedCourses.map(archivedChip).join("")}
            </div>
          </div>
        `;
      }
    }

    el.innerHTML =
      coursesHtml + optimisticHtml + docsHtml ||
      coursesHtml + `<p class="muted-note">Nenhum documento ingerido ainda. Use o formulário acima (ou arraste e solta um arquivo) para enviar um PDF ou Markdown.</p>` ||
      `<p class="muted-note">Nenhum documento ingerido ainda. Use o formulário acima (ou arraste e solta um arquivo) para enviar um PDF ou Markdown.</p>`;

    // Ações de disciplina: selecionar, arquivar/desarquivar, apagar
    el.querySelectorAll("[data-lib-select-course]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectCourse(btn.getAttribute("data-lib-select-course"));
      });
    });
    el.querySelectorAll("[data-archive-course]").forEach((button) => {
      button.addEventListener("click", async () => {
        const cid = button.getAttribute("data-archive-course");
        const title = button.getAttribute("data-course-title") || "esta disciplina";
        const to = button.getAttribute("data-archive-to") === "true";
        const msg = to
          ? `Arquivar “${title}”? Ela sai do rail de disciplinas — dá para desarquivar aqui no Acervo.`
          : `Desarquivar “${title}”? Ela volta ao rail de disciplinas.`;
        if (!window.confirm(msg)) return;
        button.disabled = true;
        try {
          const result = await apiFetch(`/courses/${encodeURIComponent(cid)}/archive`, {
            method: "POST",
            body: { archived: to },
          });
          if (result.status !== 200) throw new Error(result.data?.error?.message || "Falha ao arquivar.");
          await refreshCoreData();
          await loadAuxiliaryView("library");
        } catch (error) {
          window.alert(String(error));
          button.disabled = false;
        }
      });
    });
    el.querySelectorAll("[data-delete-course]").forEach((button) => {
      button.addEventListener("click", async () => {
        const cid = button.getAttribute("data-delete-course");
        const title = button.getAttribute("data-course-title") || "esta disciplina";
        if (!window.confirm(`Apagar “${title}” e TODO o material ingerido dela (documentos, tópicos e índice)? Esta ação não pode ser desfeita.`)) return;
        button.disabled = true;
        try {
          const result = await apiFetch(`/courses/${encodeURIComponent(cid)}`, { method: "DELETE" });
          if (result.status !== 200) throw new Error(result.data?.error?.message || "Não foi possível apagar.");
          if (appState.selectedCourseId === cid) {
            appState.selectedCourseId = (appState.courses || []).find((c) => c.id !== cid)?.id || null;
          }
          await refreshCoreData();
          await loadAuxiliaryView("library");
        } catch (error) {
          window.alert(String(error));
          button.disabled = false;
        }
      });
    });

    el.querySelectorAll("[data-delete-document]").forEach((button) => {
      button.addEventListener("click", async () => {
        const docId = button.getAttribute("data-delete-document");
        const name = button.getAttribute("data-document-name") || "este documento";
        if (!docId || !window.confirm(`Excluir “${name}” do acervo? Esta ação não pode ser desfeita.`)) return;
        button.disabled = true;
        try {
          const result = await apiFetch(`/documents/${encodeURIComponent(docId)}`, { method: "DELETE" });
          if (result.status !== 200) throw new Error(result.data?.error?.message || "Não foi possível excluir.");
          await loadAuxiliaryView("library");
          await refreshCoreData();
        } catch (error) {
          window.alert(String(error));
          button.disabled = false;
        }
      });
    });
  // Atualiza automaticamente enquanto houver upload/ingestão em andamento
  // (cartões otimistas que o servidor já persistiu saem do espelho para não
  // duplicar — a linha real assume com o progresso por página).
  if (
    docs.some((d) => d.version_status !== "active" && d.version_status !== "failed") ||
    pendingOptimistic.length > 0
  ) {
    scheduleLibraryPoll();
  }
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
      .map((f) => {
        const v = f.value || {};
        const original = v.original_expression ?? "—";
        const normalized = v.normalized_value ?? "—";
        const source = (f.source_refs || [])[0] || {};
        const page = source.physical_page ? ` · p. ${source.physical_page}` : "";
        const docName = source.doc_id ? (source.display_name || "documento") : "";        return `
        <div class="info-card fact-card">
          <div class="doc-card-head">
            <strong>${escapeHtml(String(f.kind))}: “${escapeHtml(String(original))}”</strong>
            <span class="status-chip status-ingesting">${escapeHtml(String(f.status))}</span>
          </div>
          <span>Valor normalizado: <code>${escapeHtml(String(normalized))}</code> · Precisão: ${escapeHtml(String(v.precision ?? "—"))}</span>
          <small class="muted-note">Fonte: ${escapeHtml(docName)}${escapeHtml(page)} · autoridade: ${escapeHtml(String(f.authority))} · registrado em ${escapeHtml(String(f.recorded_at).slice(0, 16))}</small>
        </div>
      `;
      })
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
        <strong>Preferências de Geração ao Vivo</strong>
        <span>Como exibir a geração do modelo durante o turno (barrinha "Agente (gerando)").</span>
        <div class="modal-actions">
          <label class="live-pref-row">
            <input type="checkbox" id="pref-show-live-text" ${getLivePrefs().showLiveText === true ? "checked" : ""} />
            Mostrar o texto sendo gerado ao vivo (sem precisar clicar no balão)
          </label>
          <label class="live-pref-row">
            <input type="checkbox" id="pref-show-thinking" ${getLivePrefs().showThinking === true ? "checked" : ""} />
            Mostrar o <em>thinking</em> (raciocínio) sendo gerado, quando existir
          </label>
        </div>
        <small class="muted-note">Com as opções desligadas, a saída estruturada fica oculta durante a geração — clique no balão para espiar. As preferências ficam salvas neste navegador.</small>
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
    document.getElementById("pref-show-live-text")?.addEventListener("change", (ev) => {
      setLivePref("showLiveText", ev.target.checked);
    });
    document.getElementById("pref-show-thinking")?.addEventListener("change", (ev) => {
      setLivePref("showThinking", ev.target.checked);
    });
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

function setPlanGenerationStatus(message, state = "info") {
  const status = document.getElementById("plan-generation-status");
  if (!status) return;
  status.hidden = !message;
  status.textContent = message;
  status.className = `plan-generation-status${state === "loading" ? " is-loading" : ""}${state === "error" ? " is-error" : ""}`;
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
      await postTurnAndRecord(res.turnRequest.message, res.turnRequest.payload);
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
  document
    .getElementById("topic-select")
    ?.addEventListener("change", syncPracticeTopicGate);
  document
    .getElementById("intent-select")
    ?.addEventListener("change", syncPracticeTopicGate);
  syncPracticeTopicGate();
  document.getElementById("turn-composer-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const intent = document.getElementById("intent-select")?.value || "/ask";
    const topicId = document.getElementById("topic-select")?.value || "";
    if (intent === "/practice" && !topicId && !hasPendingPracticeItem()) {
      syncPracticeTopicGate();
      document.getElementById("topic-select")?.focus();
      return;
    }
    if (intent === "/submit" && !hasPendingPracticeItem()) {
      syncPracticeTopicGate();
      return;
    }
    const textarea = document.getElementById("composer-textarea");
    const text = textarea ? textarea.value.trim() : "";
    const message = text ? `${intent} ${text}` : intent;

    const cancelBtn = document.getElementById("btn-cancel-turn");
    if (cancelBtn) cancelBtn.hidden = false;
    try {
      if (textarea) textarea.value = "";
      await postTurnAndRecord(message, {
        course_id: appState.selectedCourseId || "",
        topic_ids: topicId ? [topicId] : [],
      });
    } finally {
      if (cancelBtn) cancelBtn.hidden = true;
    }
  });

  document.getElementById("btn-cancel-turn")?.addEventListener("click", async () => {
    const res = await apiFetch(
      `/turns/${encodeURIComponent(appState.activeSessionId)}/cancel`,
      {
        method: "POST",
        body: {},
      },
    );
    recordLocalTurnFromResponse("/cancel", res.data);
    renderSessionTimelineAndDrawer();
    await refreshCoreData();
  });

  // Escada Socrática: slider horizontal L0..L3 (volume-style) + botão de envio
  const hintSlider = document.getElementById("hint-slider");
  function updateHintSliderUI() {
    const levels = ["L0", "L1", "L2", "L3"];
    const level = appState.helpLevel;
    const idx = Math.max(0, levels.indexOf(level));
    if (hintSlider && hintSlider.value !== String(idx)) {
      hintSlider.value = String(idx);
    }
    const info = describeHelpLevel(level);
    const indicator = document.getElementById("current-help-level-indicator");
    if (indicator) {
      indicator.textContent = info.badge;
      indicator.title = info.title;
    }
    const desc = document.getElementById("hint-level-description");
    if (desc) {
      desc.innerHTML = `<strong>${escapeHtml(info.badge)}</strong> — ${escapeHtml(info.title)}`;
    }
    if (hintSlider) {
      const pct = (idx / 3) * 100;
      hintSlider.style.background = `linear-gradient(to right, var(--accent, #4a90d9) ${pct}%, rgba(128,128,128,0.25) ${pct}%)`;
    }
  }
  hintSlider?.addEventListener("input", () => {
    const idx = Number(hintSlider.value) || 0;
    appState.helpLevel = ["L0", "L1", "L2", "L3"][idx] || "L0";
    updateHintSliderUI();
  });
  updateHintSliderUI();

  // Botão de dica: envia o turno no nível selecionado pelo slider
  document.getElementById("btn-request-hint")?.addEventListener("click", async () => {
    const topicId = document.getElementById("topic-select")?.value || "";
    const lastItem = (appState.sessionDetail?.items || []).slice(-1)[0];
    await postTurnAndRecord(
      `/practice Solicitar dica gradual (${appState.helpLevel})`,
      {
        course_id: appState.selectedCourseId || "",
        topic_ids: topicId ? [topicId] : [],
        help_level: appState.helpLevel,
        item_id: lastItem?.id || undefined,
      },
    );
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
    const button = document.getElementById("btn-generate-plan");
    if (button?.disabled) return;
    const originalLabel = button?.textContent || "Gerar Proposta (/plan)";
    if (button) {
      button.disabled = true;
      button.textContent = "Gerando proposta…";
    }
    setPlanGenerationStatus(
      "O Planejador está analisando as demandas e montando a proposta. Isso pode levar alguns instantes.",
      "loading",
    );
    try {
      const result = await postTurnAndRecord("/plan gerar proposta de cronograma semanal", {
        course_id: appState.selectedCourseId || "",
      });
      const turnError =
        Array.isArray(result?.errors) && result.errors.length
          ? result.errors[0]?.message || "O Planejador não conseguiu concluir a proposta."
          : null;
      if (turnError || result?.status === "failed" || result?.status === "cancelled") {
        throw new Error(turnError || "O Planejador não conseguiu concluir a proposta.");
      }
      setPlanGenerationStatus("Proposta recebida. Atualizando a agenda…", "loading");
      await loadAuxiliaryView("calendar");
      setPlanGenerationStatus("Proposta atualizada na agenda.", "success");
    } catch (error) {
      setPlanGenerationStatus(
        `Não foi possível gerar a proposta: ${error?.message || error}`,
        "error",
      );
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    }
  });

  document.getElementById("btn-export-ics")?.addEventListener("click", async () => {
    await postTurnAndRecord("/export exportar blocos aprovados em iCalendar (.ics)", {
      course_id: appState.selectedCourseId || "",
    });
    await loadAuxiliaryView("calendar");
  });

  // Atalho de atualização na visão de Operações & Aprovações
  document.getElementById("btn-refresh-operations")?.addEventListener("click", async () => {
    await refreshCoreData();
    await loadAuxiliaryView("operations");
  });

  // Seletor de arquivo local na Biblioteca (múltiplo: fila; único: formulário)
  document.getElementById("upload-file-input")?.addEventListener("change", (e) => {
    const files = [...(e.target.files || [])];
    if (!files.length) return;
    if (files.length > 1) {
      queueUploads(files);
    } else {
      readUploadFileIntoForm(files[0]);
    }
    e.target.value = "";
  });

  // Upload na Biblioteca (otimista: feedback imediato; a lista pola sozinha)
  document.getElementById("library-upload-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rawName = document.getElementById("upload-filename")?.value.trim();
    const contentText = document.getElementById("upload-content-text")?.value || "";
    if (!rawName) return;
    const filename = sanitizeFilename(rawName);
    const filenameInput = document.getElementById("upload-filename");
    if (filenameInput && filename !== rawName) {
      filenameInput.value = filename; // reflete o nome sanitizado ao usuário
    }
    const statusEl = document.getElementById("upload-status");
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (!appState.selectedCourseId && statusEl) {
      statusEl.hidden = false;
      statusEl.innerHTML = `<small class="upload-err">✖ Selecione uma disciplina ativa antes de enviar (a ingestão é por disciplina).</small>`;
      return;
    }
    if (submitBtn) submitBtn.disabled = true;
    if (statusEl) {
      statusEl.hidden = false;
      statusEl.innerHTML = `
        <div class="ingest-progress"><div class="ingest-progress-fill"></div></div>
        <small>Enviando e ingerindo <strong>${escapeHtml(filename)}</strong> — a extração de PDFs grandes pode levar alguns minutos…</small>`;
    }
    // Cartão otimista no topo da lista (§12: feedback imediato, sem fingir
    // progresso que ainda não existe — a barra fica "Enviando" até o
    // servidor confirmar e o progresso real assumir).
    appState.optimisticUploads = appState.optimisticUploads || [];
    appState.optimisticUploads.push(filename);
    await loadAuxiliaryView("library");
    let ok = false;
    let errMsg = "";
    try {
      const { status, data } = await apiFetch("/library/upload", {
        method: "POST",
        body: {
          filename,
          content_base64: appState.pendingUploadBase64 || undefined,
          content_text: contentText || "# Material de estudo\nConteúdo inicial.",
          course_id: appState.selectedCourseId,
          auto_ingest: Boolean(appState.selectedCourseId),
        },
      });
      ok = status === 200;
      if (!ok) {
        errMsg = data?.error?.message || `HTTP ${status}`;
      }
    } catch (err) {
      errMsg = String(err);
    }
    if (statusEl) {
      statusEl.innerHTML = ok
        ? `<small class="upload-ok">✔ Upload concluído para <strong>${escapeHtml(filename)}</strong> — acompanhe a ingestão na lista abaixo.</small>`
        : `<small class="upload-err">✖ Falha no upload de ${escapeHtml(filename)}: ${escapeHtml(errMsg)}</small>`;
    }
    if (submitBtn) submitBtn.disabled = false;
    appState.pendingUploadBase64 = null;
    appState.optimisticUploads = (appState.optimisticUploads || []).filter(
      (n) => n !== filename,
    );
    await refreshCoreData();
    await loadAuxiliaryView("library");
  });

  // Arrastar e soltar arquivos no cartão do Acervo
  const uploadCard = document.getElementById("library-upload-form");
  if (uploadCard) {
    ["dragenter", "dragover"].forEach((evName) =>
      uploadCard.addEventListener(evName, (e) => {
        e.preventDefault();
        uploadCard.classList.add("dragover");
      }),
    );
    uploadCard.addEventListener("dragleave", (e) => {
      if (e.target === uploadCard) uploadCard.classList.remove("dragover");
    });
    uploadCard.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadCard.classList.remove("dragover");
      const files = [...(e.dataTransfer?.files || [])];
      if (!files.length) return;
      const statusEl = document.getElementById("upload-status");
      if (!appState.selectedCourseId && statusEl) {
        statusEl.hidden = false;
        statusEl.innerHTML = `<small class="upload-err">✖ Selecione uma disciplina ativa antes de soltar o arquivo (a ingestão é por disciplina).</small>`;
        return;
      }
      if (files.length > 1) {
        queueUploads(files);
        return;
      }
      readUploadFileIntoForm(files[0]);
      const readyEl = document.getElementById("upload-status");
      if (readyEl) {
        readyEl.hidden = false;
        readyEl.innerHTML = `<small class="upload-ok">📄 <strong>${escapeHtml(sanitizeFilename(files[0].name))}</strong> pronto — clique em <strong>Fazer Upload &amp; Ingerir</strong> para enviar.</small>`;
      }
    });
  }
  // ==========================================================================
  // Modal Nova Disciplina (fluxo +Nova): aba "Enviar arquivos" (padrão, com
  // análise pelo modelo local) e aba "Manual" (formulário direto).
  // ==========================================================================
  const newCourseDialog = document.getElementById("new-course-dialog");
  document.getElementById("btn-new-course")?.addEventListener("click", () => {
    appState.ncFiles = [];
    renderNcFileList();
    setNcTab("files");
    const statusEl = document.getElementById("nc-analyze-status");
    if (statusEl) {
      statusEl.hidden = true;
      statusEl.innerHTML = "";
    }
    if (newCourseDialog && typeof newCourseDialog.showModal === "function") {
      newCourseDialog.showModal();
    }
  });
  document.getElementById("btn-close-new-course")?.addEventListener("click", () => {
    if (newCourseDialog && newCourseDialog.open) newCourseDialog.close();
  });

  // Abas do popup (Arquivos | Manual)
  function setNcTab(tabName) {
    document.querySelectorAll("[data-nc-tab]").forEach((tab) => {
      tab.classList.toggle("is-active", tab.getAttribute("data-nc-tab") === tabName);
    });
    const filesPane = document.getElementById("nc-pane-files");
    const manualPane = document.getElementById("nc-pane-manual");
    if (filesPane) filesPane.classList.toggle("is-active", tabName === "files");
    if (manualPane) manualPane.classList.toggle("is-active", tabName === "manual");
  }
  document.querySelectorAll("[data-nc-tab]").forEach((tab) => {
    tab.addEventListener("click", () => setNcTab(tab.getAttribute("data-nc-tab")));
  });

  // Zona de arrastar/soltar + seletor de arquivos
  const dropzone = document.getElementById("nc-dropzone");
  const fileInput = document.getElementById("nc-file-input");
  document.getElementById("nc-browse")?.addEventListener("click", () => {
    fileInput?.click();
  });
  dropzone?.addEventListener("click", (e) => {
    if (e.target === dropzone) fileInput?.click();
  });
  fileInput?.addEventListener("change", (e) => {
    const files = [...(e.target.files || [])];
    if (files.length) {
      appState.ncFiles = files;
      renderNcFileList();
    }
    e.target.value = "";
  });
  ["dragenter", "dragover"].forEach((evName) =>
    dropzone?.addEventListener(evName, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    }),
  );
  dropzone?.addEventListener("dragleave", (e) => {
    if (e.target === dropzone) dropzone.classList.remove("dragover");
  });
  dropzone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const files = [...(e.dataTransfer?.files || [])];
    if (files.length) {
      appState.ncFiles = files;
      renderNcFileList();
    }
  });

  function renderNcFileList() {
    const listEl = document.getElementById("nc-file-list");
    const actionsEl = document.getElementById("nc-files-actions");
    if (!listEl) return;
    const files = appState.ncFiles || [];
    listEl.innerHTML = files
      .map(
        (f, idx) => `
          <li class="nc-file-item">
            <span class="nc-file-name">📄 ${escapeHtml(f.name)}</span>
            <span class="nc-file-size">${(f.size / 1024 / 1024).toFixed(2)} MB</span>
            <button type="button" class="btn-ghost btn-compact" data-nc-remove="${idx}" title="Remover">✕</button>
          </li>
        `,
      )
      .join("");
    listEl.querySelectorAll("[data-nc-remove]").forEach((btn) => {
      btn.addEventListener("click", () => {
        appState.ncFiles.splice(Number(btn.getAttribute("data-nc-remove")), 1);
        renderNcFileList();
      });
    });
    if (actionsEl) actionsEl.hidden = files.length === 0;
  }

  function readAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result || "");
        const comma = result.indexOf(",");
        resolve(comma >= 0 ? result.slice(comma + 1) : result);
      };
      reader.onerror = () => reject(reader.error || new Error("falha ao ler arquivo"));
      reader.readAsDataURL(file);
    });
  }

  document.getElementById("nc-analyze-btn")?.addEventListener("click", async () => {
    const files = appState.ncFiles || [];
    if (!files.length) return;
    const statusEl = document.getElementById("nc-analyze-status");
    const analyzeBtn = document.getElementById("nc-analyze-btn");
    if (analyzeBtn) analyzeBtn.disabled = true;
    try {
      // Fase 1: um arquivo por chamada — progresso arquivo a arquivo; o
      // servidor faz staging + classificação rápida (cacheada por sha256).
      let batchId = null;
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.size > 50 * 1024 * 1024) {
          throw new Error(`${file.name} excede o limite de 50 MB`);
        }
        if (statusEl) {
          statusEl.hidden = false;
          statusEl.innerHTML = `
            <div class="ingest-progress determinate"><div class="ingest-progress-fill" style="width: ${Math.round((100 * i) / files.length)}%; animation: none;"></div></div>
            <small>Classificando ${i + 1}/${files.length}: <strong>${escapeHtml(file.name)}</strong>…</small>`;
        }
        const b64 = await readAsBase64(file);
        const { status, data } = await apiFetch("/courses/suggestions/classify", {
          method: "POST",
          body: {
            filename: sanitizeFilename(file.name),
            content_base64: b64,
            batch_id: batchId,
          },
        });
        if (status !== 200) {
          throw new Error(data?.error?.message || `HTTP ${status}`);
        }
        batchId = data.batch_id;
      }
      // Fase 2: agregação — decide matérias, título e tópicos.
      if (statusEl) {
        statusEl.hidden = false;
        statusEl.innerHTML = `
          <div class="ingest-progress"><div class="ingest-progress-fill"></div></div>
          <small>Agrupando matérias e montando título/tópicos…</small>`;
      }
      const agg = await apiFetch("/courses/suggestions", {
        method: "POST",
        body: { batch_id: batchId },
      });
      if (agg.status !== 200) {
        throw new Error(agg.data?.error?.message || `HTTP ${agg.status}`);
      }
      const count = (agg.data.suggestions || []).length;
      appState.ncFiles = [];
      renderNcFileList();
      if (newCourseDialog && newCourseDialog.open) newCourseDialog.close();
      await refreshCoreData();
      if (statusEl) {
        statusEl.hidden = false;
        statusEl.innerHTML = `<small class="upload-ok">✔ ${count} matéria(s) sugerida(s) — revise no rail, marcadas como <strong>esperando aprovação</strong>.</small>`;
      }
    } catch (err) {
      if (statusEl) {
        statusEl.hidden = false;
        statusEl.innerHTML = `<small class="upload-err">✖ ${escapeHtml(String(err))} — use a aba <strong>Manual</strong> se quiser criar sem análise.</small>`;
      }
    } finally {
      if (analyzeBtn) analyzeBtn.disabled = false;
    }
  });

  // Aba Manual: formulário direto (fluxo anterior, inalterado)
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

  // ==========================================================================
  // Popup de revisão da matéria sugerida (rail: "esperando aprovação")
  // ==========================================================================
  const suggestionDialog = document.getElementById("suggestion-review-dialog");

  document.getElementById("btn-close-suggestion-review")?.addEventListener("click", () => {
    if (suggestionDialog && suggestionDialog.open) suggestionDialog.close();
  });

  document.getElementById("btn-suggestion-discard")?.addEventListener("click", async () => {
    if (!reviewedSuggestion) return;
    const discardBtn = document.getElementById("btn-suggestion-discard");
    if (discardBtn) discardBtn.disabled = true;
    await apiFetch(
      `/courses/suggestions/${encodeURIComponent(reviewedSuggestion.id)}`,
      { method: "DELETE" },
    );
    if (discardBtn) discardBtn.disabled = false;
    if (suggestionDialog && suggestionDialog.open) suggestionDialog.close();
    await refreshCoreData();
  });

  document.getElementById("btn-suggestion-approve")?.addEventListener("click", async () => {
    if (!reviewedSuggestion) return;
    const approveBtn = document.getElementById("btn-suggestion-approve");
    const discardBtn = document.getElementById("btn-suggestion-discard");
    const title = document.getElementById("suggestion-title-input")?.value.trim();
    const topics = (document.getElementById("suggestion-topics-input")?.value || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!title) return;
    if (approveBtn) {
      approveBtn.disabled = true;
      approveBtn.textContent = "Criando e ingerindo…";
    }
    if (discardBtn) discardBtn.disabled = true;
    try {
      const { status, data } = await apiFetch(
        `/courses/suggestions/${encodeURIComponent(reviewedSuggestion.id)}/confirm`,
        { method: "POST", body: { title, topics } },
      );
      if (status === 200 && data.course) {
        appState.selectedCourseId = data.course.id;
      }
      if (suggestionDialog && suggestionDialog.open) suggestionDialog.close();
      await refreshCoreData();
    } finally {
      if (approveBtn) {
        approveBtn.disabled = false;
        approveBtn.textContent = "Aprovar e ingerir";
      }
      if (discardBtn) discardBtn.disabled = false;
    }
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
    // Cookie do usuário ativo: navegações diretas (abrir PDF da fonte em
    // nova aba) carregam o contexto sem precisar de headers de fetch.
    document.cookie = `eduagent_user=${appState.userId}; path=/; SameSite=Lax`;
    bindEvents();
    refreshCoreData();
  });
}
