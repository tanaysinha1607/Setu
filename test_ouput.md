$ python test_endpoints.py

==================================================
Testing 1. LOCAL Path
--------------------------------------------------

Status: 200
Response JSON:
{
  "risk_score": 68.4,
  "risk_category": "low",
  "explanation": "Local scoring complete. Daily revenue \u20b94,200 (variance: low, payment consistency: high). Weighted risk score: 68.4/100 \u2192 category: LOW risk. Confidence of extraction: 92%.",
  "route": "local",
  "routing_reason": "Handled locally: confidence 0.92, no anomalies",
  "latency_ms": 0.034
}

==================================================
Testing 2. ESCALATE Path
--------------------------------------------------

Status: 200
Response JSON:
{
  "risk_score": null,
  "risk_category": "pending_review",
  "explanation": "Escalated to Managed Agent (not yet implemented). Routing reason: Escalated: anomaly detected (revenue_spike, narrative_mismatch)",
  "route": "escalate",
  "routing_reason": "Escalated: anomaly detected (revenue_spike, narrative_mismatch)",
  "latency_ms": 0.004
}

==================================================
Testing 3. ERROR Path (Missing required field)
--------------------------------------------------

Status: 422
Response JSON (Error):
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "payment_consistency"
      ],
      "msg": "Field required",
      "input": {
        "source_type": "voice_note",
        "daily_revenue_estimate": 1500,
        "revenue_variance": "medium",
        "confidence_score": 0.75,
        "anomaly_flags": [],
        "raw_extracted_text": "I earn about fifteen hundred rupees per day.",
        "timestamp": "2025-07-11T09:15:00+05:30",
        "borrower_session_id": "sess_error_003",
        "route": "local",
        "routing_reason": "Handled locally: confidence 0.75, no anomalies"
      }
    }
  ]
}
(venv)
