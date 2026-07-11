"""
Regression test for the two Pydantic schema changes:
  1. raw_extracted_text is now optional (default "")
  2. image_data_base64 is a new optional field

Tests:
  A. Ledger photo payload — omits raw_extracted_text, sends image_data_base64
     → must NOT 422, must return a valid AssessmentResponse
  B. SMS local payload — sends raw_extracted_text, no image_data_base64
     → must work exactly as before (backward compat)
  C. Minimal payload — omits BOTH optional text fields entirely
     → must NOT 422
"""
import json, sys, urllib.request, urllib.error, base64

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/assess"
PASS = "\u2705"
FAIL = "\u274c"

def post(payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, {"error": body}

results = []

# ──────────────────────────────────────────────
# Test A: Ledger photo — must return pending_review stub,
#         NOT a computed score (guard fires before any formula/ADK)
# ──────────────────────────────────────────────
dummy_b64 = "data:image/png;base64," + base64.b64encode(b"FAKEPNG").decode()

ledger_payload = {
    "source_type": "ledger_photo",
    "daily_revenue_estimate": 0.0,
    "revenue_variance": "low",
    "payment_consistency": "low",
    "confidence_score": 0.0,
    "anomaly_flags": [],
    # raw_extracted_text intentionally OMITTED (triggers the guard)
    "image_data_base64": dummy_b64,
    "timestamp": "2026-07-11T07:00:00+05:30",
    "borrower_session_id": "ledger_test_001",
    "route": "escalate",          # real ledger route — guard fires before this matters
    "routing_reason": "ledger_photo: local vision unsupported"
}
status_a, body_a = post(ledger_payload)
# Guard must return 200 with pending_review stub — NOT a computed score
ok_a = (
    status_a == 200
    and body_a.get("risk_score") is None
    and body_a.get("risk_category") == "pending_review"
)
results.append(("A — Ledger photo stub (pending_review, risk_score=null)", ok_a, status_a, body_a))

# ──────────────────────────────────────────────
# Test B: SMS backward compat — raw_extracted_text only
# ──────────────────────────────────────────────
sms_payload = {
    "source_type": "sms",
    "daily_revenue_estimate": 4500.0,
    "revenue_variance": "low",
    "payment_consistency": "high",
    "confidence_score": 0.95,
    "anomaly_flags": [],
    "raw_extracted_text": "Received INR 4500 from Ramesh via UPI Ref 123.",
    "timestamp": "2026-07-11T07:00:00+05:30",
    "borrower_session_id": "sms_test_001",
    "route": "local",
    "routing_reason": "Handled locally: high confidence, no anomalies"
}
status_b, body_b = post(sms_payload)
ok_b = status_b == 200
results.append(("B — SMS local path (raw_extracted_text, no image field)", ok_b, status_b, body_b))

# ──────────────────────────────────────────────
# Test C: Both text fields omitted entirely (minimal)
# ──────────────────────────────────────────────
minimal_payload = {
    "source_type": "sms",
    "daily_revenue_estimate": 3000.0,
    "revenue_variance": "medium",
    "payment_consistency": "medium",
    "confidence_score": 0.80,
    "anomaly_flags": [],
    "timestamp": "2026-07-11T07:00:00+05:30",
    "borrower_session_id": "minimal_test_001",
    "route": "local",
    "routing_reason": "Handled locally"
}
status_c, body_c = post(minimal_payload)
ok_c = status_c == 200
results.append(("C — Minimal payload (both text fields absent)", ok_c, status_c, body_c))

# ──────────────────────────────────────────────
# Print results
# ──────────────────────────────────────────────
print("\n=== Schema Fix Regression Tests ===\n")
all_passed = True
for name, passed, status, body in results:
    icon = PASS if passed else FAIL
    print(f"{icon}  {name}")
    print(f"     HTTP {status}")
    if passed:
        print(f"     risk_score={body.get('risk_score')}  category={body.get('risk_category')}")
    else:
        print(f"     BODY: {json.dumps(body)[:300]}")
    print()
    if not passed:
        all_passed = False

print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
sys.exit(0 if all_passed else 1)
