/**
 * AG-UI Event Types for TypeScript/React
 * Mirrors the Python AGUIEvent types from core/agui/events.py
 */

export enum EventType {
  // Lifecycle events
  RUN_STARTED = 'RUN_STARTED',
  RUN_FINISHED = 'RUN_FINISHED',
  RUN_ERROR = 'RUN_ERROR',

  // Text message events (streaming)
  TEXT_MESSAGE_START = 'TEXT_MESSAGE_START',
  TEXT_MESSAGE_CONTENT = 'TEXT_MESSAGE_CONTENT',
  TEXT_MESSAGE_END = 'TEXT_MESSAGE_END',

  // Tool call events
  TOOL_CALL_START = 'TOOL_CALL_START',
  TOOL_CALL_ARGS = 'TOOL_CALL_ARGS',
  TOOL_CALL_END = 'TOOL_CALL_END',

  // State synchronization
  STATE_SNAPSHOT = 'STATE_SNAPSHOT',
  STATE_DELTA = 'STATE_DELTA',

  // Human-in-the-loop
  STEP_STARTED = 'STEP_STARTED',
  STEP_FINISHED = 'STEP_FINISHED',

  // EB-1A Custom events
  AGENT_HANDOFF = 'AGENT_HANDOFF',
  VALIDATION_REQUIRED = 'VALIDATION_REQUIRED',
  VALIDATION_RESULT = 'VALIDATION_RESULT',
  DOCUMENT_GENERATED = 'DOCUMENT_GENERATED',
  INTAKE_QUESTION = 'INTAKE_QUESTION',
  INTAKE_ANSWER = 'INTAKE_ANSWER',
}

export interface AGUIEvent {
  type: EventType;
  timestamp: number;
  event_id: string;

  // Content fields
  message_id?: string;
  content?: string;
  delta?: string;
  role?: string;

  // Tool call fields
  tool_call_id?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_result?: unknown;

  // State fields
  state?: Record<string, unknown>;
  state_delta?: Record<string, unknown>;

  // Agent coordination
  agent_name?: string;
  next_agent?: string;

  // Workflow specific
  step_name?: string;
  case_id?: string;

  // Error handling
  error?: string;
  error_code?: string;

  // Metadata
  metadata?: Record<string, unknown>;
}

export interface AGUIRunRequest {
  case_id: string;
  operation: string;
  data?: Record<string, unknown>;
  user_id?: string;
}

export interface AGUIAgentRequest {
  agent_name: string;
  prompt: string;
  case_id?: string;
}

export interface AGUIValidationRequest {
  validation_id: string;
  approved: boolean;
  feedback?: string;
}

export interface IntakeBlock {
  id: string;
  title: string;
  description: string;
  questionsCount: number;
}

export interface IntakeProgressData {
  caseId: string;
  currentBlock: string;
  currentStep: number;
  completedBlocks: string[];
  totalBlocks: number;
  percentage: number;
}

export interface ValidationData {
  validationId: string;
  validationType: string;
  caseId: string;
  data: Record<string, unknown>;
  title?: string;
  description?: string;
}
