/**
 * Contratos TypeScript da Interface Gráfica Local do EduAgent-OS v0.1.
 * Espelha 1:1 os 15 JSON Schemas (Draft 2020-12) em `schemas/` e os
 * payloads da `LoopbackAPI` (`eduagent/api.py`).
 */

export type ErrorCode =
  | "INVALID_INPUT"
  | "SCHEMA_VALIDATION"
  | "SCHEMA_INVALID"
  | "PARSE_FAILURE"
  | "PERMISSION_DENIED"
  | "TOOL_DENIED"
  | "REVISION_CONFLICT"
  | "VERSION_CONFLICT"
  | "DEPENDENCY_INVALIDATED"
  | "AMBIGUOUS_FACT"
  | "AMBIGUOUS_INPUT"
  | "INSUFFICIENT_EVIDENCE"
  | "NO_EVIDENCE"
  | "SOURCE_UNRESOLVED"
  | "RESOURCE_LIMIT"
  | "TIMEOUT"
  | "CONNECTOR_DISABLED"
  | "MODEL_NOT_ADMITTED"
  | "UNKNOWN_EFFECT"
  | "INTERNAL_FAILURE"
  | "CANCELLED";

export interface TypedError {
  code: ErrorCode;
  message: string;
  retryable: boolean;
  details?: Record<string, unknown>;
}

export type HelpLevel = "L0" | "L1" | "L2" | "L3";

export type TopicStateStatus = "insufficient" | "mixed" | "favorable";

export type IntentKind =
  | "/ask"
  | "/practice"
  | "/submit"
  | "/ingest"
  | "/plan"
  | "/approve"
  | "/export"
  | "/resume"
  | "/delete";

export type RailView =
  | "courses"
  | "calendar"
  | "library"
  | "review"
  | "progress"
  | "operations"
  | "settings";

export type CourseFilterKind =
  | "all"
  | "ready"
  | "scheduled"
  | "pending_approval";

export interface SourceRef {
  doc_id?: string;
  version_id?: string;
  chunk_id?: string;
  block_id?: string;
  page?: number;
  original_ref?: string;
}

export interface EvidenceChunk {
  chunk_id: string;
  doc_id: string;
  version_id: string;
  original_ref: string;
  version_status: string;
  block_refs: string[];
  text: string;
}

export interface EvidencePack {
  coverage: "sufficient" | "partial" | "insufficient";
  chunks: EvidenceChunk[];
}

export interface RubricCriterion {
  criterion_id: string;
  description: string;
  critical?: boolean;
  passed?: boolean;
}

export interface LearningItem {
  id: string;
  family_id: string;
  version: number;
  prompt: string;
  help_level: HelpLevel;
  revealed: boolean;
  expected_answer: string | null;
  rubric: RubricCriterion[];
  source_refs: SourceRef[];
  attempt_id?: string | null;
  attempt_ordinal?: number | null;
  independent: boolean;
}

export interface TopicSummaryItem {
  id: string;
  course_id: string;
  title: string;
  aliases: string[];
  revision: number;
}

export interface PlanBlock {
  id: string;
  uid?: string;
  revision?: number;
  status: string;
  planned_start_utc: string;
  planned_end_utc: string;
  actual_start_utc?: string | null;
  actual_end_utc?: string | null;
  source_demand_id?: string | null;
  end_conflict?: number | boolean;
  summary?: string | null;
}

export interface CourseSummary {
  id: string;
  user_id: string;
  title: string;
  aliases: string[];
  revision: number;
  topics: TopicSummaryItem[];
  active_doc_count: number;
  indexed_doc_count: number;
  ready_to_study: boolean;
  sort_tier: 1 | 2 | 3 | 4;
  sort_key_secondary: string;
  sort_reason_label: string;
  recommended_intent: IntentKind;
  pending_demands_count: number;
  active_plan_block: PlanBlock | null;
  last_turn_preview: string;
  last_activity_at: string | null;
  domain_status: TopicStateStatus;
  topic_states_summary: Record<TopicStateStatus, number>;
  attempts_count: number;
}

export interface SessionEvent {
  id: string;
  session_id: string;
  kind: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface AssessmentRecord {
  id: string;
  attempt_id: string;
  assessor_version: string;
  revision: number;
  payload: Record<string, unknown>;
}

export interface SessionDetailResponse {
  status: "ok";
  session_id: string;
  events: SessionEvent[];
  items: LearningItem[];
  assessments: AssessmentRecord[];
  evidence_pack: EvidencePack;
  checkpoint: {
    step?: string | null;
    status?: string | null;
    interrupted?: Record<string, unknown> | null;
  } | null;
}

export interface StudyDemand {
  id: string;
  topic_id: string | null;
  activity_kind: string | null;
  due_local_date: string | null;
  status: string;
  revision: number;
  payload: Record<string, unknown>;
}

export interface PlanRecord {
  id: string;
  revision: number;
  snapshot_version: number;
  payload: Record<string, unknown>;
  approval_ref: string | null;
}

export interface CalendarResponse {
  status: "ok";
  demands: StudyDemand[];
  plans: PlanRecord[];
  active_plan: PlanRecord | null;
  logical_blocks: PlanBlock[];
  exports: Array<{
    id: string;
    filename: string;
    size_bytes: number;
  }>;
}

export interface TopicProgress {
  topic_id: string;
  topic_title: string;
  course_id: string;
  course_title: string;
  revision: number;
  status: TopicStateStatus;
  /** Invariante §8.1: estimate permanece SEMPRE null na v0.1 */
  estimate: null;
  rationale: string;
  critical_errors: string[];
  independent_attempts: number;
  assisted_attempts: number;
}

export interface ProgressResponse {
  status: "ok";
  summary: {
    counts_by_status: Record<TopicStateStatus, number>;
    total_topics: number;
    total_attempts: number;
    independent_attempts: number;
    assisted_attempts: number;
    estimate: null;
  };
  topics: TopicProgress[];
}

export interface LibraryDocument {
  doc_id: string;
  course_id: string;
  course_title: string;
  active_version: string | null;
  version_id: string | null;
  sha256: string | null;
  mime: string | null;
  original_ref: string | null;
  version_status: "pending" | "indexed" | "active" | "failed";
  chunk_count: number;
  extractor_manifest: Record<string, unknown>;
}

export interface LibraryFact {
  id: string;
  kind: string;
  value: Record<string, unknown>;
  authority: string;
  recorded_at: string;
  source_refs: SourceRef[];
  status: "candidate" | "ambiguous" | "confirmed" | "rejected";
  revision: number;
}

export interface LibraryResponse {
  status: "ok";
  documents: LibraryDocument[];
  facts: LibraryFact[];
}

export interface OperationsResponse {
  status: "ok";
  pending_count: number;
  operations: Array<{
    id: string;
    digest: string;
    state: string;
    expected_version: number | null;
    receipt: Record<string, unknown>;
  }>;
  pending_facts: LibraryFact[];
  unapproved_plans: PlanRecord[];
  confirmations: Array<Record<string, unknown>>;
}

export interface FlashcardItem {
  id: string;
  kind: "item_review" | "concept_recall";
  front: string;
  back: string;
  revealed: boolean;
  source_refs: SourceRef[];
  course_id: string | null;
}

export interface SearchResultItem {
  kind: "course" | "topic" | "chunk";
  id: string;
  course_id?: string;
  doc_id?: string;
  title: string;
  snippet: string;
}

export interface HealthGates {
  model_admitted: boolean;
  model_status: "admitted" | "MODEL_NOT_ADMITTED";
  timezone: string | null;
  network_enabled: boolean;
  web_connector: "enabled" | "CONNECTOR_DISABLED";
  calendar_sync_enabled: boolean;
  reranker_enabled: boolean;
  sqlite_version: string;
  domain_revision: number;
  ui_available: boolean;
  registered_users: string[];
}

export interface HealthResponse {
  status: "ok";
  service: string;
  mode: string;
  gates?: HealthGates;
}

export interface TurnResponse {
  status: string;
  session_id: string;
  intent: string | null;
  route: string[];
  output: Record<string, unknown> | null;
  errors: TypedError[];
  interrupted: Record<string, unknown> | null;
  trace_id: string | null;
}

export type PomodoroPhase =
  | "idle"
  | "running_focus"
  | "paused"
  | "awaiting_confirmation"
  | "running_break";

export interface PomodoroState {
  phase: PomodoroPhase;
  courseId: string | null;
  planBlockId: string | null;
  totalSeconds: number;
  remainingSeconds: number;
  breakSeconds: number;
  confirmationModalOpen: boolean;
  autoCompletedForbidden: true;
}

