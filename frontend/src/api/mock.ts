// ---------------------------------------------------------------------------
// Setu API — Mock responses
// ---------------------------------------------------------------------------
// Realistic fake data used when MOCK_MODE is enabled or as a graceful
// fallback when a real API call fails.  Delays simulate actual latencies.

import type { AssessmentResponse, ProcessRequest } from './types';

// ── Pre-baked mock responses ────────────────────────────────────────────────

const LOCAL_LOW_RISK: AssessmentResponse = {
  route: 'local',
  escalation_method: null,
  risk_score: 67.8,
  risk_category: 'low',
  explanation:
    'Local scoring complete. Daily revenue ₹3,900 (variance: low, payment consistency: high). ' +
    'Weighted risk score: 67.8/100 → category: LOW risk. Confidence of extraction: 92%.',
  confidence_score: 0.92,
  anomaly_flags: [],
  latency_ms: 14200,
  routing_reason: 'Handled locally: confidence 0.92, no anomalies',
};

const LOCAL_MEDIUM_RISK: AssessmentResponse = {
  route: 'local',
  escalation_method: null,
  risk_score: 48.5,
  risk_category: 'medium',
  explanation:
    'Local scoring complete. Daily revenue ₹3,700 (variance: medium, payment consistency: medium). ' +
    'Weighted risk score: 48.5/100 → category: MEDIUM risk. Confidence of extraction: 78%.',
  confidence_score: 0.78,
  anomaly_flags: [],
  latency_ms: 13800,
  routing_reason: 'Handled locally: confidence 0.78, no anomalies',
};

const ESCALATED_ANOMALY: AssessmentResponse = {
  route: 'escalate',
  escalation_method: 'google-adk Managed Agent — gemini-2.5-flash',
  risk_score: 38.0,
  risk_category: 'medium',
  explanation:
    'The ₹18,500 transaction from "Corporate Corp" is approximately 20x the typical transaction size ' +
    'for this borrower profile.  While it could represent a legitimate bulk order or wholesaler advance, ' +
    'the single outsized amount warrants caution.  Remaining transactions are consistent at ₹800-₹1,000. ' +
    'Assigning MEDIUM risk pending verification of the large transfer source.',
  confidence_score: 0.91,
  anomaly_flags: ['revenue_spike'],
  latency_ms: 9100,
  routing_reason: 'Escalated: anomaly detected (revenue_spike)',
};

const ESCALATED_LOW_CONFIDENCE: AssessmentResponse = {
  route: 'escalate',
  escalation_method: 'google-adk Managed Agent — gemini-2.5-flash',
  risk_score: 52.0,
  risk_category: 'medium',
  explanation:
    'Extraction confidence was below threshold (0.65).  Cloud analysis of the raw text shows moderate ' +
    'daily revenue with some inconsistencies in transaction formatting.  Revenue appears legitimate but ' +
    'the data quality is uncertain.  Recommend follow-up verification.',
  confidence_score: 0.65,
  anomaly_flags: [],
  latency_ms: 8700,
  routing_reason: 'Escalated: confidence 0.65 below threshold',
};

const LEDGER_VISION: AssessmentResponse = {
  route: 'escalate',
  escalation_method: 'google-adk Managed Agent — Vision LlmAgent, gemini-2.5-flash',
  risk_score: 61.0,
  risk_category: 'low',
  explanation:
    'Ledger image shows daily transactions ranging from ₹500 to ₹3,000 over a 7-day period. ' +
    'Handwriting is consistent, entries are dated sequentially, and totals appear internally consistent. ' +
    'Moderate daily revenue of approximately ₹4,200 with low variance. LOW risk assessment.',
  confidence_score: null,
  anomaly_flags: [],
  latency_ms: 11400,
  routing_reason: 'ledger_photo: local vision unsupported',
};

const LEDGER_VISION_MEDIUM: AssessmentResponse = {
  route: 'escalate',
  escalation_method: 'google-adk Managed Agent — Vision LlmAgent, gemini-2.5-flash',
  risk_score: 45.0,
  risk_category: 'medium',
  explanation:
    'Ledger image shows irregular entries with varying handwriting styles across dates. ' +
    'Some round-number entries (₹5,000, ₹10,000) lack customer names or descriptions. ' +
    'Daily revenue estimates around ₹6,500 but consistency is questionable. MEDIUM risk.',
  confidence_score: null,
  anomaly_flags: ['inconsistent_handwriting'],
  latency_ms: 12800,
  routing_reason: 'ledger_photo: local vision unsupported',
};

const LEDGER_VISION_HIGH: AssessmentResponse = {
  route: 'escalate',
  escalation_method: 'google-adk Managed Agent — Vision LlmAgent, gemini-2.5-flash',
  risk_score: 28.0,
  risk_category: 'high',
  explanation:
    'Ledger entries appear fabricated — identical round amounts (₹2,000) repeated across 5 consecutive ' +
    'days with no variation. Transaction descriptions are generic ("sale"). Ink colour and pressure ' +
    'appear uniform, suggesting entries were written in one sitting rather than daily. HIGH risk.',
  confidence_score: null,
  anomaly_flags: ['suspected_fabrication', 'uniform_amounts'],
  latency_ms: 10200,
  routing_reason: 'ledger_photo: local vision unsupported',
};

// ── SMS sample-index to mock response mapping ──────────────────────────────

const SMS_MOCK_RESPONSES: AssessmentResponse[] = [
  LOCAL_LOW_RISK,         // Sample 1 — Clean/Consistent A
  LOCAL_LOW_RISK,         // Sample 2 — Clean/Consistent B
  LOCAL_MEDIUM_RISK,      // Sample 3 — Natural variance A
  ESCALATED_LOW_CONFIDENCE, // Sample 4 — Natural variance B
  ESCALATED_ANOMALY,      // Sample 5 — Anomalous spike
];

// Map ledger filenames to specific mock responses
const LEDGER_MOCK_MAP: Record<string, AssessmentResponse> = {
  hariom: LEDGER_VISION,
  shiva: LEDGER_VISION_MEDIUM,
  shree: LEDGER_VISION_HIGH,
};

// ── Public API ──────────────────────────────────────────────────────────────

/**
 * Returns a realistic mock response with artificial delay.
 * Used in MOCK_MODE and as graceful fallback when the real API fails.
 */
export async function getMockResponse(
  req: ProcessRequest,
  isFallback = false,
): Promise<AssessmentResponse> {
  let response: AssessmentResponse;
  let delayMs: number;

  if (req.source_type === 'ledger_photo') {
    // Try to match a specific ledger sample
    const key = Object.keys(LEDGER_MOCK_MAP).find((k) =>
      req.borrower_session_id?.toLowerCase().includes(k),
    );
    response = key ? { ...LEDGER_MOCK_MAP[key] } : { ...LEDGER_VISION };
    delayMs = isFallback ? 500 : 3000 + Math.random() * 2000; // 3-5s simulated
  } else {
    // SMS — try to match by sample index embedded in session id
    const idxMatch = req.borrower_session_id?.match(/sample[_-]?(\d)/i);
    const idx = idxMatch ? parseInt(idxMatch[1], 10) - 1 : 0;
    const safeIdx = Math.max(0, Math.min(idx, SMS_MOCK_RESPONSES.length - 1));
    response = { ...SMS_MOCK_RESPONSES[safeIdx] };
    delayMs = isFallback
      ? 500
      : response.route === 'local'
        ? 2000 + Math.random() * 1000
        : 6000 + Math.random() * 3000;
  }

  // Add some jitter to latency_ms to look realistic
  if (!isFallback) {
    response.latency_ms = Math.round(delayMs + Math.random() * 500);
  }

  await new Promise((resolve) => setTimeout(resolve, delayMs));
  return response;
}
