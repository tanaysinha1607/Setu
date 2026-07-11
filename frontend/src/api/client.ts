// ---------------------------------------------------------------------------
// Setu API — HTTP Client
// ---------------------------------------------------------------------------
// Single function: submitAssessment().  Posts to /api/process for both SMS
// and ledger photo inputs.  Falls back to mock on failure rather than
// surfacing raw errors to the UI.

import { API_BASE_URL, PROCESS_ENDPOINT, MOCK_MODE, TIMEOUT_SMS_MS, TIMEOUT_ESCALATE_MS } from './config';
import { getMockResponse } from './mock';
import type { ProcessRequest, AssessmentResponse } from './types';

/**
 * Submit a credit-risk assessment request.
 *
 * - In MOCK_MODE → returns a realistic fake response with artificial delay.
 * - Otherwise → POSTs to /api/process.  On failure, falls back to a mock
 *   response for that single request (logged to console, hidden from UI).
 */
export async function submitAssessment(
  req: ProcessRequest,
): Promise<AssessmentResponse> {
  if (MOCK_MODE) {
    console.info('[Setu] Mock mode active — returning simulated response');
    return getMockResponse(req);
  }

  const timeoutMs =
    req.source_type === 'ledger_photo' ? TIMEOUT_ESCALATE_MS : TIMEOUT_SMS_MS;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const res = await fetch(`${API_BASE_URL}${PROCESS_ENDPOINT}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Unknown error');
      throw new Error(`Backend returned ${res.status}: ${errorText}`);
    }

    return (await res.json()) as AssessmentResponse;
  } catch (err) {
    // ── Graceful fallback: log the real error, return mock data ──────────
    const message =
      err instanceof DOMException && err.name === 'AbortError'
        ? `Request timed out after ${timeoutMs}ms`
        : err instanceof TypeError
          ? 'Backend not reachable (is /api/process running?)'
          : String(err);

    console.warn(`[Setu] Real API call failed — falling back to mock response.\n  Reason: ${message}`);
    return getMockResponse(req, /* isFallback */ true);
  }
}
