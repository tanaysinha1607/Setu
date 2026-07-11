import json
import urllib.request
import urllib.error
from extract_sms import extract_financial_data, start_server, stop_server, SAMPLES
from routing_engine import route_credit_assessment

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

if __name__ == "__main__":
    # Start inference server with configured optimizations
    server_process, server_log = start_server()
    try:
        session_id = "borrower_session_xyz_777"
        for idx, sample in enumerate(SAMPLES, 1):
            print(f"\n==========================================")
            print(f"PIPELINE: PROCESSING SAMPLE {idx}/{len(SAMPLES)}")
            print(f"==========================================")
            print(f"Input SMS:\n{sample.strip()}\n")
            try:
                # 1. Local Extraction + Pre-routing
                pipeline_out = process_sms_input(sample, borrower_session_id=session_id)
                print("1. Pipeline Extraction & Routing Output:")
                print(json.dumps(pipeline_out, indent=2))
                print("-" * 40)
                
                # 2. POST to FastAPI Backend for Credit Scoring
                backend_out = call_backend(pipeline_out)
                print("2. Backend Credit Risk Assessment Output:")
                print(json.dumps(backend_out, indent=2))
            except ConnectionError:
                # Handled gracefully, exit early
                break
            except Exception as e:
                print(f"Error processing sample {idx} in pipeline: {e}")
    finally:
        # Shutdown server gracefully
        stop_server(server_process, server_log)
