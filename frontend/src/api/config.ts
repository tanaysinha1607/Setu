// ---------------------------------------------------------------------------
// Setu API — Configuration
// ---------------------------------------------------------------------------
// Single place to change the backend URL and endpoint path.

export const API_BASE_URL = 'http://localhost:8000';
export const PROCESS_ENDPOINT = '/api/process';

// Mock mode: reads VITE_MOCK_MODE env var.
// Defaults to FALSE so the frontend always tries the real backend first.
// Set VITE_MOCK_MODE=true in a .env.local to force mock data for UI-only dev.
export const MOCK_MODE =
  import.meta.env.VITE_MOCK_MODE === 'true';

// Timeouts (ms) — generous but finite
export const TIMEOUT_SMS_MS = 60_000;       // Local Gemma extraction can take ~14-35s
export const TIMEOUT_ESCALATE_MS = 90_000;  // Cloud ADK can take ~9s but leave headroom
