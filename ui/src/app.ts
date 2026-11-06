/**
 * EduAgent-OS v0.1 — Controlador TypeScript da Interface Gráfica Local (127.0.0.1).
 * Fonte tipada compilada/espelhada em `ui/dist/app.js`.
 */

import type {
  CourseFilterKind,
  CourseSummary,
  FlashcardItem,
  HealthResponse,
  HelpLevel,
  PomodoroState,
  RailView,
  SessionDetailResponse,
} from "./contracts.ts";
import {
  canRevealAnswer,
  confirmPomodoroCompletion,
  createPomodoroState,
  describeHelpLevel,
  describeTypedError,
  evaluateRuntimeBanner,
  filterCourses,
  formatPomodoroClock,
  nextHelpLevel,
  pausePomodoro,
  resolvePlanBlockDurationSeconds,
  sanitizeLearningItemForDisplay,
  sortCoursesDeterministically,
  startPomodoro,
  tickPomodoro,
} from "./state.ts";

export {
  canRevealAnswer,
  confirmPomodoroCompletion,
  createPomodoroState,
  describeHelpLevel,
  describeTypedError,
  evaluateRuntimeBanner,
  filterCourses,
  formatPomodoroClock,
  nextHelpLevel,
  pausePomodoro,
  resolvePlanBlockDurationSeconds,
  sanitizeLearningItemForDisplay,
  sortCoursesDeterministically,
  startPomodoro,
  tickPomodoro,
};

export interface BrowserAppState {
  userId: string;
  activeView: RailView;
  courseFilter: CourseFilterKind;
  courseSearch: string;
  courses: CourseSummary[];
  selectedCourseId: string | null;
  activeSessionId: string;
  helpLevel: HelpLevel;
  turnInFlight: boolean;
  health: HealthResponse | null;
  sessionDetail: SessionDetailResponse | null;
  flashcards: FlashcardItem[];
  flashcardIndex: number;
  flashcardBackVisible: boolean;
  pendingUploadBase64: string | null;
  pomodoro: PomodoroState;
}

export function createInitialBrowserAppState(): BrowserAppState {
  return {
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
  };
}
