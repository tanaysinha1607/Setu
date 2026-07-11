"""
E2E automated test for the ledger photo vision path.
Reads the dummy daybook image test_ledger.png, base64 encodes it,
and POSTs it to the FastAPI backend.
"""
import os, json, sys, base64, urllib.request, urllib.error

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure test_ledger.png exists by generating it if missing
test_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ledger.png")
if not os.path.exists(test_image_path):
    print("test_ledger.png not found. Generating it via Pillow...")
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        text = (
            "Ledger - 11/07/26\n"
            "Customer A: Rs 1500 (Paid)\n"
            "Customer B: Rs 3000 (Paid)\n"
            "Customer C: Rs 500  (Paid)\n"
            "Total Sales: Rs 5000"
        )
        d.text((20, 20), text, fill=(0, 0, 0))
        img.save(test_image_path)
        print("Generated successfully.")
    except ImportError:
        print("FAILED: Pillow is not installed. Please run pipeline.py first to create test_ledger.png")
        sys.exit(1)

# Encode image to Base64 data URL
with open(test_image_path, "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
image_data_url = "data:image/png;base64," + encoded_string

# Construct request matching backend schema
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
    "borrower_session_id": "session_vision_demo_999",
    "route": "escalate",
    "routing_reason": "ledger_photo: local vision unsupported"
}

print("POSTing vision request to backend...", flush=True)
url = "http://localhost:8000/assess"
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    url,
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=30) as response:
        res = json.loads(response.read().decode('utf-8'))
        print("\n=== Vision Integration Test Output ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
        # Assertions
        assert res["risk_score"] is not None, "Test Failed: risk_score is None (fallback stub triggered)"
        assert res["risk_category"] in ("low", "medium", "high"), f"Test Failed: unexpected risk_category: {res['risk_category']}"
        assert "iAPI" in res["escalation_method"], "Test Failed: did not run via ADK/iAPI"
        print("\nSUCCESS: Vision integration test passed!")
except urllib.error.URLError as e:
    print(f"\nFAILED: Could not connect to backend: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\nFAILED: Test error: {e}")
    sys.exit(1)
