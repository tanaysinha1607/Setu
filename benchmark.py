import os
import sys
import zipfile
import urllib.request
import json
import time
import subprocess

# Configuration
WORKSPACE_DIR = r"c:\Users\Tanay Sinha\OneDrive\Desktop\Setu"
LLAMA_BIN_DIR = os.path.join(WORKSPACE_DIR, "llama-bin")
ZIP_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b9941/llama-b9941-bin-win-cpu-x64.zip"
ZIP_PATH = os.path.join(WORKSPACE_DIR, "llama-cpu-x64.zip")
MODEL_URL = "https://huggingface.co/bartowski/google_gemma-4-E4B-it-GGUF/resolve/main/google_gemma-4-E4B-it-Q4_K_M.gguf"
MODEL_PATH = os.path.join(WORKSPACE_DIR, "google_gemma-4-E4B-it-Q4_K_M_v2.gguf")

def download_file(url, filepath):
    # Check if the file is fully downloaded.
    # Note: If it exists but is partial, curl -C - will automatically resume it.
    # If it is already complete, curl will exit immediately.
    print(f"Downloading {url} to {filepath} using native curl...")
    
    cmd = [
        "curl.exe",
        "-L",           # Follow redirects
        "-C", "-",      # Auto-resume based on existing file size
        "-o", filepath, # Output path
        url
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: curl download failed with exit code {e.returncode}")
        sys.exit(1)
    
    print("Download completed/verified!")

def unzip_file(zip_path, extract_to):
    if os.path.exists(extract_to) and os.listdir(extract_to):
        print(f"Directory {extract_to} already exists and is not empty. Skipping extraction.")
        return
    
    print(f"Extracting {zip_path} to {extract_to}...")
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction completed!")

def run_benchmark():
    server_exe = os.path.join(LLAMA_BIN_DIR, "llama-server.exe")
    if not os.path.exists(server_exe):
        print(f"Error: llama-server.exe not found at {server_exe}")
        sys.exit(1)
        
    server_cmd = [
        server_exe,
        "--model", MODEL_PATH,
        "--port", "8080",
        "--host", "127.0.0.1",
        "-c", "2048"
    ]
    
    print("\nStarting llama-server.exe...")
    start_time = time.perf_counter()
    server_process = subprocess.Popen(
        server_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    load_time = None
    health_url = "http://127.0.0.1:8080/health"
    print("Polling /health endpoint to measure model load time...")
    
    try:
        while True:
            if server_process.poll() is not None:
                _, stderr = server_process.communicate()
                print("Error: Server process terminated unexpectedly during startup.")
                print(stderr)
                sys.exit(1)
            
            try:
                req = urllib.request.Request(health_url)
                with urllib.request.urlopen(req, timeout=1) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        if data.get("status") == "ok":
                            load_time = (time.perf_counter() - start_time) * 1000
                            break
            except (urllib.error.URLError, ConnectionResetError):
                pass
            
            time.sleep(0.5)
            
        print(f"Model loaded successfully! Load time: {load_time:.2f} ms")
        
        latencies = []
        prompt_url = "http://127.0.0.1:8080/v1/chat/completions"
        prompt = "What is the capital of France?"
        
        for i in range(1, 6):
            print(f"Running iteration {i}/5...")
            payload = json.dumps({
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 50
            }).encode('utf-8')
            
            req = urllib.request.Request(
                prompt_url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            
            iter_start = time.perf_counter()
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                text = res_data['choices'][0]['message']['content']
            iter_time = (time.perf_counter() - iter_start) * 1000
            latencies.append(iter_time)
            print(f"  Latency: {iter_time:.2f} ms | Output snippet: {text.strip()[:100]}...")
            
        min_lat = min(latencies)
        max_lat = max(latencies)
        avg_lat = sum(latencies) / len(latencies)
        
        print("\n=== Latency Results ===")
        print(f"Model Load Time: {load_time:.2f} ms")
        for idx, lat in enumerate(latencies):
            print(f"Iteration {idx+1}: {lat:.2f} ms")
        print(f"Min Inference Latency: {min_lat:.2f} ms")
        print(f"Max Inference Latency: {max_lat:.2f} ms")
        print(f"Avg Inference Latency: {avg_lat:.2f} ms")
        
    finally:
        print("\nTerminating llama-server.exe...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Force killing llama-server.exe...")
            server_process.kill()
        print("Server terminated successfully.")

if __name__ == "__main__":
    # 1. Download/Resume Model using curl
    download_file(MODEL_URL, MODEL_PATH)
    
    # 2. Verify file size matches exactly
    expected_size = 5405168384
    actual_size = os.path.getsize(MODEL_PATH)
    if actual_size != expected_size:
        print(f"Error: Model file size mismatch. Expected {expected_size} bytes, got {actual_size} bytes.")
        sys.exit(1)
        
    print("Model file size verified successfully!")
    
    # 3. Run Benchmark
    run_benchmark()
