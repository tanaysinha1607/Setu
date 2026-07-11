// ---------------------------------------------------------------------------
// Setu API — Configuration
// ---------------------------------------------------------------------------
// Single place to change the backend URL and endpoint path.
// Atharv's /api/process wraps pipeline.py extraction + routing internally.

export const API_BASE_URL = 'http://localhost:8000';
export const PROCESS_ENDPOINT = '/api/process';

// Mock mode: reads VITE_MOCK_MODE env var.  Defaults to true so the frontend
// can be developed and demoed even when the backend isn't reachable.
export const MOCK_MODE =
  import.meta.env.VITE_MOCK_MODE !== undefined
    ? import.meta.env.VITE_MOCK_MODE === 'true'
    : true;

// Timeouts (ms) — generous but finite
export const TIMEOUT_SMS_MS = 30_000;    // Local Gemma extraction can take ~14-35s
export const TIMEOUT_ESCALATE_MS = 60_000; // Cloud ADK can take ~9s but leave headroom
