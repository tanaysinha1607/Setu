import os
import json
import base64
import datetime
import urllib.request
import urllib.error
from extract_sms import extract_financial_data, start_server, stop_server, SAMPLES
from routing_engine import route_credit_assessment

# Try importing Pillow for generating the dummy ledger image
try:
    from PIL import Image, ImageDraw
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

def process_sms_input(sms_text: str, borrower_session_id: str) -> dict:
    """
    Chains the extraction layer (Gemma 4 E4B) and the routing layer together.
    
    Returns:
        dict: The full extracted schema fields plus "route" and "routing_reason".
    """
    # 1. Extract structured financial data from raw SMS text
    extracted_data = extract_financial_data(sms_text, borrower_session_id)
    
    # 2. Determine routing (local vs escalate) based on anomalies & confidence score
    route, reason = route_credit_assessment(extracted_data)
    
    # 3. Combine extraction fields and routing fields into a single object
    combined_result = dict(extracted_data)
    combined_result["route"] = route
    combined_result["routing_reason"] = reason
    
    return combined_result

def encode_image_to_base64(image_path: str) -> str:
    """Reads a local image file and returns a base64 Data URL string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    mime_prefix = "data:image/png;base64,"
    if image_path.lower().endswith(".jpg") or image_path.lower().endswith(".jpeg"):
        mime_prefix = "data:image/jpeg;base64,"
    
    return mime_prefix + encoded_string

def process_ledger_photo_input(image_path: str, borrower_session_id: str) -> dict:
    """
    Handles ledger photo inputs. Since local Gemma lacks vision support,
    it skips local extraction entirely, hardcodes escalation routing,
    and base64-encodes the image.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Ledger photo not found at: {image_path}")
    
    # 1. Base64-encode the image
    base64_image = encode_image_to_base64(image_path)
    
    # 2. Construct timestamp
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 3. Package payload matching schema.json
    payload = {
        "source_type": "ledger_photo",
        "daily_revenue_estimate": 0.0,            # Placeholder — will be read by Gemini vision
        "revenue_variance": "low",                # Placeholder
        "payment_consistency": "low",             # Placeholder
        "confidence_score": 0.0,                  # Placeholder
        "anomaly_flags": [],                      # Placeholder
        "raw_extracted_text": "",                 # Empty — text not available for photos
        "image_data_base64": base64_image,        # Base64 data URL for Gemini vision
        "timestamp": timestamp_str,
        "borrower_session_id": borrower_session_id,
        "route": "escalate",                      # Hardcoded cloud escalation
        "routing_reason": "ledger_photo: local vision unsupported"
    }
    
    return payload

def call_backend(payload: dict) -> dict:
    """
    POSTs the pipeline payload to the FastAPI credit risk backend.
    """
    url = "http://localhost:8000/assess"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print("\n[CONNECTION ERROR] Could not connect to the FastAPI backend service.")
        print("Please ensure that you have started the backend API server first by running:")
        print("    python -m uvicorn backend.main:app --port 8000")
        print(f"Details: {e.reason}\n")
        raise ConnectionError("Backend connection failed") from e
    except Exception as e:
        print(f"\n[ERROR] Unexpected error calling backend: {e}\n")
        raise e

def ensure_test_image(image_path: str):
    """Generates a dummy handwritten ledger photo using Pillow if not present."""
    if os.path.exists(image_path):
        return
    
    if not PILLOW_AVAILABLE:
        print("Warning: Pillow not available. Cannot generate dummy image.")
        return
        
    print(f"Generating dummy ledger image at: {image_path}")
    # Create white canvas
    img = Image.new('RGB', (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Text to simulate manual transaction lines
    text = (
        "Ledger - 11/07/26\n"
        "Customer A: Rs 1500 (Paid)\n"
        "Customer B: Rs 3000 (Paid)\n"
        "Customer C: Rs 500  (Paid)\n"
        "Total Sales: Rs 5000"
    )
    d.text((20, 20), text, fill=(0, 0, 0))
    img.save(image_path)

if __name__ == "__main__":
    # Define test workspace paths
    test_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ledger.png")
    session_id = "borrower_session_xyz_777"
    
    # 1. Run the Ledger Photo pipeline verification
    print("==========================================")
    print("RUNNING LEDGER PHOTO PIPELINE TEST")
    print("==========================================")
    
    # Generate dummy photo
    ensure_test_image(test_image_path)
    
    try:
        # Pre-route and encode image
        ledger_payload = process_ledger_photo_input(test_image_path, session_id)
        
        # Display the payload shape (truncate base64 data for readability)
        print("1. Ledger Pipeline Routing & Payload Output:")
        payload_copy = dict(ledger_payload)
        payload_copy["raw_extracted_text"] = payload_copy["raw_extracted_text"][:80] + "... [TRUNCATED IMAGE BASE64] ..."
        print(json.dumps(payload_copy, indent=2))
        print("-" * 40)
        
        # Post payload to FastAPI backend
        backend_out = call_backend(ledger_payload)
        print("2. Backend Assessment Response (Stubs Escalation):")
        print(json.dumps(backend_out, indent=2))
        
    except ConnectionError:
        print("Pipeline run aborted: Backend is offline.")
        os._exit(1)
    except Exception as e:
        print(f"Ledger pipeline verification failed: {e}")
        
    print("\n")
    
    # 2. Run the original SMS samples (requires local llama-server.exe)
    print("==========================================")
    print("RUNNING SMS SAMPLES PIPELINE TEST")
    print("==========================================")
    server_process, server_log = start_server()
    try:
        for idx, sample in enumerate(SAMPLES, 1):
            print(f"\n------------------------------------------")
            print(f"PROCESSING SMS SAMPLE {idx}/{len(SAMPLES)}")
            print(f"------------------------------------------")
            print(f"Input SMS:\n{sample.strip()}\n")
            try:
                pipeline_out = process_sms_input(sample, borrower_session_id=session_id)
                print("1. Pipeline Extraction & Routing Output:")
                print(json.dumps(pipeline_out, indent=2))
                print("-" * 40)
                
                backend_out = call_backend(pipeline_out)
                print("2. Backend Credit Risk Assessment Output:")
                print(json.dumps(backend_out, indent=2))
            except ConnectionError:
                break
            except Exception as e:
                print(f"Error processing SMS sample {idx} in pipeline: {e}")
    finally:
        stop_server(server_process, server_log)
