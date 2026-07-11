import urllib.request, json, sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

payload = {
    "source_type": "sms",
    "daily_revenue_estimate": 21200.0,
    "revenue_variance": "high",
    "payment_consistency": "high",
    "confidence_score": 0.88,
    "anomaly_flags": ["revenue_spike"],
    "raw_extracted_text": (
        "14-07-26 09:00: Received INR 900.00 from Suresh K via UPI Ref 6293080101.\n"
        "14-07-26 11:00: Received INR 18,500.00 from Corporate Corp via UPI Ref 6293080392.\n"
        "14-07-26 15:30: Received INR 1,000.00 from Priya M via UPI Ref 6293080512.\n"
        "14-07-26 19:00: Received INR 800.00 from Ramesh S via UPI Ref 6293080641.\n"
        "Summary: A single massive transaction of INR 18500 occurs, which is ~20x the typical transaction size."
    ),
    "timestamp": "2026-07-14T09:00:00+05:30",
    "borrower_session_id": "sess_sample5_spike",
    "route": "escalate",
    "routing_reason": "Escalated: anomaly detected (revenue_spike)"
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    "http://localhost:8000/assess",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(json.dumps(result, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print(f"HTTP {e.code}: {body}", file=sys.stderr)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
