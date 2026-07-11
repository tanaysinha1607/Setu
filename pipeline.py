import json
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
                result = process_sms_input(sample, borrower_session_id=session_id)
                print("Combined Output (Data + Routing Decision):")
                print(json.dumps(result, indent=2))
            except Exception as e:
                print(f"Error processing sample {idx} in pipeline: {e}")
    finally:
        # Shutdown server gracefully
        stop_server(server_process, server_log)
