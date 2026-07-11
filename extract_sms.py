import os
import sys
import json
import time
import datetime
import subprocess
import urllib.request
from jsonschema import validate, ValidationError

# Reconfigure stdout to support UTF-8 encoding in windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Configuration
WORKSPACE_DIR = r"c:\Users\Tanay Sinha\OneDrive\Desktop\Setu"
LLAMA_BIN_DIR = os.path.join(WORKSPACE_DIR, "llama-bin")
MODEL_PATH = os.path.join(WORKSPACE_DIR, "google_gemma-4-E4B-it-Q4_K_M_v2.gguf")
SCHEMA_PATH = os.path.join(WORKSPACE_DIR, "schema.json")
SERVER_LOG_PATH = os.path.join(WORKSPACE_DIR, "llama_server.log")

# Load Schema
with open(SCHEMA_PATH, "r") as f:
    SCHEMA = json.load(f)

def extract_financial_data(sms_text: str, borrower_session_id: str, is_retry: bool = False) -> dict:
    url = "http://127.0.0.1:8080/v1/chat/completions"
    
    # Generate timestamp
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Clean system prompt (reasoning is disabled server-side, so no length constraint is needed)
    system_prompt = (
        "You are a credit risk AI. Extract structured financial data from raw UPI SMS logs.\n"
        "Return ONLY a JSON object with these keys:\n"
        "- daily_revenue_estimate (number: total daily credit in INR)\n"
        "- revenue_variance (\"low\"|\"medium\"|\"high\")\n"
        "- payment_consistency (\"low\"|\"medium\"|\"high\")\n"
        "- confidence_score (number between 0.0 and 1.0)\n"
        "- anomaly_flags (list of strings: e.g. [\"revenue_spike\"] if a credit is 4-5x normal average, else [])\n\n"
        "Example Input:\n"
        "10-07-26 10:00: Received INR 600.00 from Customer A.\n"
        "10-07-26 15:00: Received INR 400.00 from Customer B.\n\n"
        "Example Output:\n"
        "{\n"
        "  \"daily_revenue_estimate\": 1000.0,\n"
        "  \"revenue_variance\": \"low\",\n"
        "  \"payment_consistency\": \"high\",\n"
        "  \"confidence_score\": 0.95,\n"
        "  \"anomaly_flags\": []\n"
        "}\n\n"
        "No conversational text, no markdown. Return raw JSON only."
    )
    
    user_prompt = f"Analyze these logs:\n{sms_text}"
    
    if is_retry:
        system_prompt += "\n\nWARNING: Your previous response was invalid. You MUST output ONLY valid JSON matching the schema, with no markdown code blocks or extra text."

    payload = json.dumps({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 200, # 200 is plenty since reasoning tokens are disabled
        "response_format": {"type": "json_object"}
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    
    # 90s socket timeout is now safe since latency is significantly reduced
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            raw_content = res_data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error calling local llama-server: {e}")
        raise e
        
    cleaned_content = raw_content
    if cleaned_content.startswith("```"):
        lines = cleaned_content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned_content = "\n".join(lines).strip()
        
    try:
        extracted_data = json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        if not is_retry:
            print("JSON decoding failed. Retrying with stricter prompt...")
            return extract_financial_data(sms_text, borrower_session_id, is_retry=True)
        else:
            print(f"JSON decoding failed on retry. Raw output was:\n{raw_content}")
            raise e

    # Inject/ensure fields match schema exactly
    extracted_data["source_type"] = "sms"
    extracted_data["raw_extracted_text"] = sms_text
    extracted_data["timestamp"] = timestamp_str
    extracted_data["borrower_session_id"] = borrower_session_id

    # Schema Validation
    try:
        validate(instance=extracted_data, schema=SCHEMA)
    except ValidationError as e:
        if not is_retry:
            print(f"Validation failed: {e.message}. Retrying with stricter prompt...")
            return extract_financial_data(sms_text, borrower_session_id, is_retry=True)
        else:
            print(f"Validation failed on retry: {e.message}")
            raise e

    return extracted_data

def start_server():
    server_exe = os.path.join(LLAMA_BIN_DIR, "llama-server.exe")
    if not os.path.exists(server_exe):
        print(f"Error: llama-server.exe not found at {server_exe}")
        sys.exit(1)
        
    server_cmd = [
        server_exe,
        "--model", MODEL_PATH,
        "--port", "8080",
        "--host", "127.0.0.1",
        "-c", "2048",
        "--parallel", "1",
        "--threads", "12",
        "--reasoning", "off",       # Disable reasoning mode in llama-server
        "--reasoning-budget", "0"   # Set reasoning token budget to 0
    ]
    
    print("Starting llama-server.exe with --parallel 1, --threads 12 and reasoning disabled...")
    log_file = open(SERVER_LOG_PATH, "w", encoding="utf-8")
    process = subprocess.Popen(
        server_cmd,
        stdout=log_file,
        stderr=log_file,
        text=True
    )
    
    health_url = "http://127.0.0.1:8080/health"
    print("Waiting for model to load...")
    while True:
        if process.poll() is not None:
            print("Error: Server process terminated unexpectedly. Check llama_server.log for details.")
            sys.exit(1)
        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get("status") == "ok":
                        print("Model loaded successfully!")
                        break
        except (urllib.error.URLError, ConnectionResetError):
            pass
        time.sleep(0.5)
    return process, log_file

def stop_server(process, log_file):
    print("\nTerminating llama-server.exe...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("Force killing llama-server.exe...")
        process.kill()
    log_file.close()
    print("Server terminated successfully.")

SAMPLES = [
    # 1. Clean/Consistent Example A
    (
        "10-07-26 09:30: Received INR 800.00 from Suresh K via UPI Ref 6293049102.\n"
        "10-07-26 12:15: Received INR 1,100.00 from Priya M via UPI Ref 6293049221.\n"
        "10-07-26 16:45: Received INR 950.00 from Ramesh S via UPI Ref 6293049381.\n"
        "10-07-26 20:00: Received INR 1,050.00 from Amit B via UPI Ref 6293049442.\n"
        "Summary: Payments are stable and recurring at similar times."
    ),
    # 2. Clean/Consistent Example B
    (
        "11-07-26 09:45: Received INR 900.00 from Vikram L via UPI Ref 6293050110.\n"
        "11-07-26 11:30: Received INR 1,000.00 from Priya M via UPI Ref 6293050201.\n"
        "11-07-26 17:00: Received INR 850.00 from Suresh K via UPI Ref 6293050392.\n"
        "11-07-26 19:30: Received INR 1,200.00 from Nitin P via UPI Ref 6293050410.\n"
        "Summary: Stable transactions, consistent daily revenue."
    ),
    # 3. Natural Variance but Normal Example A
    (
        "12-07-26 10:00: Received INR 500.00 from Joy D via UPI Ref 6293060123.\n"
        "12-07-26 13:00: Received INR 2,500.00 from Rohit G via UPI Ref 6293060341.\n"
        "12-07-26 18:30: Received INR 700.00 from Sneha V via UPI Ref 6293060592.\n"
        "Summary: Fluctuation in transaction sizes, typical for weekend sales."
    ),
    # 4. Natural Variance but Normal Example B
    (
        "13-07-26 08:30: Received INR 3,000.00 from Anand R via UPI Ref 6293070001.\n"
        "13-07-26 14:15: Received INR 600.00 from Divya K via UPI Ref 6293070192.\n"
        "13-07-26 21:00: Received INR 500.00 from Rahul P via UPI Ref 6293070441.\n"
        "Summary: Moderate daily fluctuations, transaction amounts vary from INR 500 to INR 3000."
    ),
    # 5. Deliberately Anomalous (spiked)
    (
        "14-07-26 09:00: Received INR 900.00 from Suresh K via UPI Ref 6293080101.\n"
        "14-07-26 11:00: Received INR 18,500.00 from Corporate Corp via UPI Ref 6293080392.\n"
        "14-07-26 15:30: Received INR 1,000.00 from Priya M via UPI Ref 6293080512.\n"
        "14-07-26 19:00: Received INR 800.00 from Ramesh S via UPI Ref 6293080641.\n"
        "Summary: A single massive transaction of INR 18500 occurs, which is ~20x the typical transaction size."
    )
]

if __name__ == "__main__":
    server_process, server_log = start_server()
    try:
        session_id = "borrower_session_xyz_777"
        for idx, sample in enumerate(SAMPLES, 1):
            print(f"\n==========================================")
            print(f"PROCESSING SAMPLE {idx}/{len(SAMPLES)}")
            print(f"==========================================")
            print(f"Input SMS:\n{sample.strip()}\n")
            try:
                result = extract_financial_data(sample, borrower_session_id=session_id)
                print("Extracted Structured JSON:")
                print(json.dumps(result, indent=2))
            except Exception as e:
                print(f"Error processing sample {idx}: {e}")
    finally:
        stop_server(server_process, server_log)
