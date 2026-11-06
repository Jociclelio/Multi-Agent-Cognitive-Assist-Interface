/**
 * Núcleo puro e determinístico de estado e invariantes da Interface Gráfica Local
 * do EduAgent-OS v0.1.
 *
 * Todas as funções aqui são puras e testáveis isoladamente via `deno test`.
 */

import type {
  CourseFilterKind,
  CourseSummary,
  ErrorCode,
  FlashcardItem,
  HealthGates,
  HelpLevel,
  LearningItem,
  PlanBlock,
  PomodoroState,
  TypedError,
} from "./contracts.ts";

export const DEFAULT_FOCUS_SECONDS = 25 * 60; // 25 min
export const DEFAULT_BREAK_SECONDS = 5 * 60; // 5 min

/**
 * Ordena disciplinas pelas 4 faixas determinísticas (Decisão D3):
 * 1. Bloco planejado ativo/próximo (`sort_tier = 1`);
 * 2. Demanda crítica/pendente (`sort_tier = 2`);
 * 3. Material recém-indexado sem prática (`sort_tier = 3`);
 * 4. Inatividade / ordem alfabética (`sort_tier = 4`).
 */
export function sortCoursesDeterministically(
  courses: readonly CourseSummary[],
): CourseSummary[] {
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
    return a.title.localeCompare(b.title, "pt-BR");
  });
}

/**
 * Filtra disciplinas na coluna esquerda estilo WhatsApp Web.
 */
export function filterCourses(
  courses: readonly CourseSummary[],
  filter: CourseFilterKind,
  searchQuery = "",
): CourseSummary[] {
  const q = searchQuery.trim().toLowerCase();
  const sorted = sortCoursesDeterministically(courses);
  return sorted.filter((course) => {
    if (filter === "ready" && !course.ready_to_study) {
      return false;
    }
    if (filter === "scheduled" && course.sort_tier !== 1) {
      return false;
    }
    if (
      filter === "pending_approval" &&
      course.pending_demands_count <= 0 &&
      course.sort_tier > 2
    ) {
      return false;
    }
    if (!q) {
      return true;
    }
    const inTitle = course.title.toLowerCase().includes(q);
    const inPreview = (course.last_turn_preview || "").toLowerCase().includes(q);
    const inTopics = (course.topics || []).some((t) =>
      t.title.toLowerCase().includes(q)
    );
    return inTitle || inPreview || inTopics;
  });
}

/**
 * Calcula a duração em segundos de um `PlanBlock` ativo (ou devolve 25 min em estudo livre).
 */
export function resolvePlanBlockDurationSeconds(
  block: PlanBlock | null | undefined,
): number {
  if (!block || !block.planned_start_utc || !block.planned_end_utc) {
    return DEFAULT_FOCUS_SECONDS;
  }
  const startMs = Date.parse(block.planned_start_utc);
  const endMs = Date.parse(block.planned_end_utc);
  if (Number.isNaN(startMs) || Number.isNaN(endMs) || endMs <= startMs) {
    return DEFAULT_FOCUS_SECONDS;
  }
  const diffSeconds = Math.round((endMs - startMs) / 1000);
  // Limita entre 5 min e 180 min para segurança de UI
  return Math.max(5 * 60, Math.min(180 * 60, diffSeconds));
}

/**
 * Inicializa a máquina de estados do Timer Pomodoro sincronizada ao `PlanBlock`
 * da disciplina ativa (Decisão D5).
 */
export function createPomodoroState(
  course?: Pick<CourseSummary, "id" | "active_plan_block"> | null,
): PomodoroState {
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

export function startPomodoro(state: PomodoroState): PomodoroState {
  if (state.phase === "awaiting_confirmation") {
    return state;
  }
  return {
    ...state,
    phase: state.phase === "running_break" ? "running_break" : "running_focus",
    remainingSeconds:
      state.remainingSeconds > 0 ? state.remainingSeconds : state.totalSeconds,
    confirmationModalOpen: false,
  };
}

export function pausePomodoro(state: PomodoroState): PomodoroState {
  if (state.phase !== "running_focus" && state.phase !== "running_break") {
    return state;
  }
  return {
    ...state,
    phase: "paused",
  };
}

export interface PomodoroTickResult {
  state: PomodoroState;
  /**
   * Invariante Fail-Closed (Decisão D5): o tick NUNCA emite `emittedTurnPayload`
   * automaticamente ao zerar o cronômetro; apenas abre o modal de confirmação.
   */
  emittedTurnPayload: null;
}

export function tickPomodoro(
  state: PomodoroState,
  elapsedSeconds = 1,
): PomodoroTickResult {
  if (state.phase !== "running_focus" && state.phase !== "running_break") {
    return { state, emittedTurnPayload: null };
  }
  const nextRemaining = Math.max(0, state.remainingSeconds - Math.max(1, elapsedSeconds));
  if (nextRemaining > 0) {
    return {
      state: {
        ...state,
        remainingSeconds: nextRemaining,
      },
      emittedTurnPayload: null,
    };
  }
  if (state.phase === "running_focus") {
    // Atingiu 00:00 no bloco de foco: entra em `awaiting_confirmation` e abre
    // o `<dialog>` modal nativo. NUNCA marca o bloco como concluído sozinho.
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
  // Fim do intervalo de descanso: volta a idle com foco restaurado
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

export type PomodoroUserDecision = "complete_block" | "extend_10m" | "start_break";

export interface PomodoroDecisionResult {
  state: PomodoroState;
  turnRequest: {
    message: string;
    payload: Record<string, unknown>;
  } | null;
}

/**
 * Processa a decisão explícita do estudante no modal `<dialog>` pós-Pomodoro.
 * Apenas `"complete_block"` gera requisição explícita de atualização de atividade.
 */
export function confirmPomodoroCompletion(
  state: PomodoroState,
  decision: PomodoroUserDecision,
): PomodoroDecisionResult {
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
  // decision === "complete_block" (ação explícita do usuário)
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

export function formatPomodoroClock(seconds: number): string {
  const clamped = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(clamped / 60);
  const secs = clamped % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

/**
 * Invariante Socrático (§7.3): verifica se o gabarito (`expected_answer`) pode
 * ser exibido ao estudante. Jamais exibe em L0, L1 ou L2 se `revealed === false`.
 */
export function canRevealAnswer(
  item: Pick<LearningItem, "help_level" | "revealed">,
): boolean {
  return Boolean(item.revealed || item.help_level === "L3");
}

export function sanitizeLearningItemForDisplay(
  item: LearningItem,
): LearningItem {
  const allowed = canRevealAnswer(item);
  return {
    ...item,
    expected_answer: allowed ? item.expected_answer : null,
  };
}

export function nextHelpLevel(current: HelpLevel): HelpLevel {
  switch (current) {
    case "L0":
      return "L1";
    case "L1":
      return "L2";
    case "L2":
    case "L3":
      return "L3";
  }
}

export function describeHelpLevel(level: HelpLevel): {
  badge: string;
  title: string;
  independentEligible: boolean;
} {
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
      return {
        badge: "L3 · Explicação & Gabarito",
        title: "Resposta revelada (tentativa assistida — exige nova família de item)",
        independentEligible: false,
      };
  }
}

/**
 * Sessão de Flashcards com separação estrita Frente/Verso e zero gamificação.
 */
export interface FlashcardSessionState {
  cards: FlashcardItem[];
  currentIndex: number;
  backVisible: boolean;
  completedIds: string[];
  ratingsById: Record<string, "revisar_em_breve" | "compreendido_com_esforco" | "consolidado">;
}

export function createFlashcardSession(
  cards: readonly FlashcardItem[],
): FlashcardSessionState {
  return {
    cards: [...cards],
    currentIndex: 0,
    backVisible: false,
    completedIds: [],
    ratingsById: {},
  };
}

export function flipFlashcard(
  session: FlashcardSessionState,
): FlashcardSessionState {
  if (session.cards.length === 0) {
    return session;
  }
  return {
    ...session,
    backVisible: !session.backVisible,
  };
}

export function rateFlashcard(
  session: FlashcardSessionState,
  rating: "revisar_em_breve" | "compreendido_com_esforco" | "consolidado",
): FlashcardSessionState {
  const current = session.cards[session.currentIndex];
  if (!current || !session.backVisible) {
    // Fail-closed: exige que o estudante vire o cartão e veja o verso antes de avaliar
    return session;
  }
  const nextCompleted = session.completedIds.includes(current.id)
    ? session.completedIds
    : [...session.completedIds, current.id];
  const nextIndex =
    session.currentIndex + 1 < session.cards.length
      ? session.currentIndex + 1
      : session.currentIndex;
  return {
    ...session,
    currentIndex: nextIndex,
    backVisible: false,
    completedIds: nextCompleted,
    ratingsById: {
      ...session.ratingsById,
      [current.id]: rating,
    },
  };
}

/**
 * Traduz qualquer `TypedError` dos 15 códigos normativos em orientação clara
 * e acionável para o estudante.
 */
export function describeTypedError(error: TypedError): {
  title: string;
  explanation: string;
  actionLabel: string;
  retryable: boolean;
  severity: "warning" | "danger" | "info";
} {
  const map: Record<
    ErrorCode,
    { title: string; explanation: string; actionLabel: string; severity: "warning" | "danger" | "info" }
  > = {
    MODEL_NOT_ADMITTED: {
      title: "Modelo Offline Não Admitido (Bonsai 2)",
      explanation:
        "O gate do modelo local bloqueou a geração porque o servidor GGUF não foi admitido ou não está ativo em 127.0.0.1:8079.",
      actionLabel: "Abrir Diagnóstico (Doctor)",
      severity: "warning",
    },
    NO_EVIDENCE: {
      title: "Sem Evidência Documental Indexada",
      explanation:
        "O Tutor recusa responder sem base nos seus materiais. Ingira e ative pelo menos um documento nesta disciplina.",
      actionLabel: "Ingerir Material na Biblioteca",
      severity: "warning",
    },
    INSUFFICIENT_EVIDENCE: {
      title: "Evidência Insuficiente no Corpus",
      explanation:
        "Os trechos recuperados não cobrem a pergunta com segurança suficiente para evitar alucinação.",
      actionLabel: "Ver Trechos na Gaveta / Ingerir Fonte",
      severity: "warning",
    },
    SOURCE_UNRESOLVED: {
      title: "Fonte ou Recurso Não Resolvido",
      explanation:
        "O artefato, documento ou recurso configurado não pôde ser localizado no diretório confinado do usuário.",
      actionLabel: "Verificar Biblioteca & Diagnóstico",
      severity: "warning",
    },
    AMBIGUOUS_FACT: {
      title: "Fato Ambíguo Aguardando Confirmação",
      explanation:
        "Foram detectadas informações conflitantes (ex.: datas de prova). Confirme qual versão prevalece.",
      actionLabel: "Abrir Fila de Aprovações",
      severity: "info",
    },
    AMBIGUOUS_INPUT: {
      title: "Entrada Ambígua Aguardando Esclarecimento",
      explanation:
        "A solicitação ou fato extraído possui mais de uma interpretação possível. Confirme a opção desejada.",
      actionLabel: "Abrir Fila de Aprovações",
      severity: "info",
    },
    REVISION_CONFLICT: {
      title: "Conflito de Revisão Otimista (OCC)",
      explanation:
        "O estado do domínio mudou desde que esta proposta foi gerada. Recarregue os dados antes de aprovar.",
      actionLabel: "Recarregar Estado",
      severity: "warning",
    },
    VERSION_CONFLICT: {
      title: "Conflito de Versão Otimista (OCC)",
      explanation:
        "A revisão do documento ou plano mudou durante o turno. Atualize os dados da sessão.",
      actionLabel: "Recarregar Estado",
      severity: "warning",
    },
    DEPENDENCY_INVALIDATED: {
      title: "Dependência Invalidada",
      explanation:
        "A versão do documento ou plano base mudou após o preview. Gere uma nova proposta.",
      actionLabel: "Regerar Proposta",
      severity: "warning",
    },
    CONNECTOR_DISABLED: {
      title: "Conector Externo Desabilitado",
      explanation:
        "A busca web ou sincronização externa está desabilitada por padrão (modo offline fail-closed).",
      actionLabel: "Ver Configurações",
      severity: "info",
    },
    RESOURCE_LIMIT: {
      title: "Limite de Recurso Excedido",
      explanation:
        "A operação excedeu o orçamento permitido (ex.: arquivo acima de 50 MiB ou limite de chamadas por turno).",
      actionLabel: "Reduzir Escopo e Tentar Novamente",
      severity: "danger",
    },
    TIMEOUT: {
      title: "Tempo Limite Excedido (Timeout)",
      explanation:
        "A execução local excedeu o orçamento de tempo configurado para o turno.",
      actionLabel: "Tentar Novamente",
      severity: "warning",
    },
    PERMISSION_DENIED: {
      title: "Violação de Confinamento Bloqueada",
      explanation:
        "O caminho ou host solicitado está fora da fronteira segura permitida para o usuário.",
      actionLabel: "Revisar Caminho",
      severity: "danger",
    },
    TOOL_DENIED: {
      title: "Ferramenta ou Caminho Bloqueado pela Política",
      explanation:
        "A política fail-closed bloqueou o acesso fora do diretório do usuário ou conector desabilitado.",
      actionLabel: "Revisar Política",
      severity: "danger",
    },
    INVALID_INPUT: {
      title: "Entrada Inválida",
      explanation: error.message || "Os parâmetros informados não atendem ao contrato da rota.",
      actionLabel: "Corrigir Campos",
      severity: "warning",
    },
    SCHEMA_VALIDATION: {
      title: "Falha de Validação de Schema JSON",
      explanation: "A saída estruturada não passou na validação Draft 2020-12.",
      actionLabel: "Repetir Turno",
      severity: "warning",
    },
    SCHEMA_INVALID: {
      title: "Payload Inválido perante o JSON Schema",
      explanation: "Os dados recebidos ou gerados violam o contrato JSON Schema Draft 2020-12.",
      actionLabel: "Corrigir Dados",
      severity: "warning",
    },
    PARSE_FAILURE: {
      title: "Falha de Extração / Parse",
      explanation: "Não foi possível extrair estrutura válida do documento ou da resposta do modelo.",
      actionLabel: "Inspecionar Diagnóstico",
      severity: "warning",
    },
    UNKNOWN_EFFECT: {
      title: "Efeito Desconhecido na Outbox",
      explanation: "O operação solicitou um efeito colateral fora do catálogo permitido.",
      actionLabel: "Ver Operações",
      severity: "danger",
    },
    INTERNAL_FAILURE: {
      title: "Falha Interna do Sistema",
      explanation: error.message || "Erro inesperado capturado pela barreira fail-closed.",
      actionLabel: "Ver Trace / Doctor",
      severity: "danger",
    },
    CANCELLED: {
      title: "Turno Cancelado pelo Estudante",
      explanation: "A execução do turno foi interrompida com segurança.",
      actionLabel: "Retomar Estudo",
      severity: "info",
    },
  };

  const info = map[error.code] ?? {
    title: `Erro Tipado (${error.code})`,
    explanation: error.message,
    actionLabel: "Ver Detalhes",
    severity: "warning" as const,
  };

  return {
    ...info,
    explanation: error.message ? `${info.explanation} (${error.message})` : info.explanation,
    retryable: Boolean(error.retryable),
  };
}

export interface RuntimeBannerNotice {
  id: string;
  level: "warning" | "info" | "ok";
  badge: string;
  message: string;
}

export function evaluateRuntimeBanner(
  gates: HealthGates | null | undefined,
): RuntimeBannerNotice[] {
  if (!gates) {
    return [
      {
        id: "health-unknown",
        level: "warning",
        badge: "LOOPBACK",
        message: "Verificando conexão com o servidor local 127.0.0.1...",
      },
    ];
  }
  const notices: RuntimeBannerNotice[] = [];
  if (!gates.model_admitted) {
    notices.push({
      id: "model-not-admitted",
      level: "warning",
      badge: "MODEL_NOT_ADMITTED",
      message:
        "Modelo Bonsai 2 não conectado: ingestão, biblioteca, calendário e progresso funcionam normalmente; tutoria gerativa aguarda admissão do modelo local.",
    });
  } else {
    notices.push({
      id: "model-admitted",
      level: "ok",
      badge: "BONSAI 2 ATIVO",
      message: "Modelo local admitido e pronto para tutoria socrática e prática.",
    });
  }
  if (!gates.timezone) {
    notices.push({
      id: "timezone-null",
      level: "info",
      badge: "TIMEZONE: NULL",
      message:
        "Fuso horário explícito ainda não confirmado (ex.: America/Sao_Paulo). Defina nas Configurações antes de aprovar planos de calendário.",
    });
  }
  return notices;
}

