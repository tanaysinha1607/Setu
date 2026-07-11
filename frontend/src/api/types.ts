// ---------------------------------------------------------------------------
// Setu API — TypeScript types
// ---------------------------------------------------------------------------

/** What the frontend sends to POST /api/process */
export interface ProcessRequest {
  source_type: 'sms' | 'ledger_photo' | 'voice_note';
  /** Raw SMS text — required for source_type === 'sms' */
  raw_text?: string;
  /** Base64-encoded image data URL — required for source_type === 'ledger_photo' */
  image_data_base64?: string;
  /** Base64-encoded audio data URL — required for source_type === 'voice_note' */
  audio_data_base64?: string;
  /** Session identifier for this borrower assessment */
  borrower_session_id: string;
}

/** What the backend returns from POST /api/process */
export interface AssessmentResponse {
  route: 'local' | 'escalate';
  escalation_method: string | null;
  risk_score: number | null;
  risk_category: 'low' | 'medium' | 'high' | 'pending_review';
  explanation: string;
  confidence_score: number | null;
  anomaly_flags: string[];
  latency_ms: number;
  routing_reason?: string;
}

/** Application phase — drives the single-page view transitions */
export type AppPhase = 'hero' | 'input' | 'processing' | 'result';

/** Input modality selected by the user */
export type InputType = 'sms' | 'photo' | 'voice' | null;

/** Shape of the Zustand global state store */
export interface AppState {
  // Navigation
  phase: AppPhase;
  setPhase: (p: AppPhase) => void;

  // Input
  inputType: InputType;
  setInputType: (t: InputType) => void;

  // Processing & results
  isLoading: boolean;
  routeTaken: 'local' | 'escalate' | null;
  result: AssessmentResponse | null;
  error: string | null;
  requestStartTime: number | null;

  // Actions
  startAssessment: (req: ProcessRequest) => Promise<void>;
  reset: () => void;
}
