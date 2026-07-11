import urllib.request
import urllib.error
import json
 
BASE_URL = "http://localhost:8000/assess"

payloads = {
    "1. LOCAL Path": {
        "source_type": "sms",
        "daily_revenue_estimate": 4200,
        "revenue_variance": "low",
        "payment_consistency": "high",
        "confidence_score": 0.92,
        "anomaly_flags": [],
        "raw_extracted_text": "Received Rs 4200 from customer. Balance 12500.",
        "timestamp": "2025-07-11T08:30:00+05:30",
        "borrower_session_id": "sess_local_001",
        "route": "local",
        "routing_reason": "Handled locally: confidence 0.92, no anomalies"
    },
    "2. ESCALATE Path": {
        "source_type": "ledger_photo",
        "daily_revenue_estimate": 22000,
        "revenue_variance": "high",
        "payment_consistency": "low",
        "confidence_score": 0.88,
        "anomaly_flags": ["revenue_spike", "narrative_mismatch"],
        "raw_extracted_text": "Ledger shows sudden 5x revenue jump this week with no corresponding expense.",
        "timestamp": "2025-07-11T09:00:00+05:30",
        "borrower_session_id": "sess_escalate_002",
        "route": "escalate",
        "routing_reason": "Escalated: anomaly detected (revenue_spike, narrative_mismatch)"
    },
    "3. ERROR Path (Missing required field)": {
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

for name, payload in payloads.items():
    print(f"\n{'='*50}\nTesting {name}\n{'-'*50}")
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(BASE_URL, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
            print(f"Status: {status}")
            print("Response JSON:")
            print(json.dumps(json.loads(body), indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"Status: {e.code}")
        print("Response JSON (Error):")
        print(json.dumps(json.loads(body), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")
