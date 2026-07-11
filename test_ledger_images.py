"""
Test our ADK vision credit risk agent against the 3 images in the images folder.
"""
import os, json, sys, base64, urllib.request, urllib.error

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
URL = "http://localhost:8000/assess"

images = ["Ledger1.jpeg", "Ledger2.jpeg", "Ledger3.jpeg"]

print("==================================================")
print("TESTING ADK VISION AGENT AGAINST LEDGER SAMPLES")
print("==================================================\n")

for filename in images:
    filepath = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Error: {filename} not found at {filepath}")
        continue

    print(f"Processing {filename}...", flush=True)
    
    # Read and encode image to base64 data URL
    with open(filepath, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    image_data_url = "data:image/jpeg;base64," + encoded_string

    payload = {
        "source_type": "ledger_photo",
        "daily_revenue_estimate": 0.0,
        "revenue_variance": "low",
        "payment_consistency": "low",
        "confidence_score": 0.0,
        "anomaly_flags": [],
        "raw_extracted_text": "",
        "image_data_base64": image_data_url,
        "timestamp": "2026-07-11T12:00:00Z",
        "borrower_session_id": f"sess_vision_test_{filename.split('.')[0]}",
        "route": "escalate",
        "routing_reason": f"ledger_photo: vision verification for {filename}"
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        URL,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            res = json.loads(response.read().decode('utf-8'))
            print(f"\n--- Result for {filename} ---")
            print(f"Risk Score   : {res.get('risk_score')}")
            print(f"Risk Category: {res.get('risk_category')}")
            print(f"Explanation  : {res.get('explanation')}")
            print(f"Escalation   : {res.get('escalation_method')}")
            print(f"Latency (ms) : {res.get('latency_ms')}")
            print("-" * 50 + "\n")
    except urllib.error.URLError as e:
        print(f"FAILED to query backend for {filename}: {e}\n")
    except Exception as e:
        print(f"Error processing {filename}: {e}\n")
