# Project Setu: Directory & File Overview

This document provides a comprehensive overview of the files, folders, and architecture of **Project Setu**—an adaptive AI routing system designed for microfinance credit risk assessment.

---

## 1. System Architecture Context
Project Setu operates in three logical layers:
1. **Local Layer:** A local instance of the **Gemma 4 E4B** model running via `llama.cpp` extracts structured financial metrics from messy inputs (SMS logs, ledger photos, voice notes).
2. **Escalation Routing:** The local system analyzes confidence scores and anomaly flags. If confidence is low or a risk anomaly is detected, the case is routed to a cloud-hosted Gemini model for deeper validation.
3. **Voice/Interactivity:** Field officers can perform interactive spoken Q&A using the Gemini Live API.

---

## 2. Directory Tree
```text
Setu/
├── .agents/
│   └── AGENTS.md
├── .cache/
│   └── huggingface/
│       └── download/ (clean / empty leftover download cache)
├── llama-bin/ (contains 51 DLLs and EXEs for llama.cpp execution)
│   ├── llama-server.exe
│   ├── llama.exe
│   └── ...
├── benchmark.py
├── extract_sms.py
├── schema.json
├── schema_documentation.md
├── google_gemma-4-E4B-it-Q4_K_M_v2.gguf
├── llama-cpu-x64.zip
├── llama_server.log
├── routing_engine.py
├── pipeline.py
└── project_overview.md (this file)
```

---

## 3. Detailed File-by-File Breakdown

### 📂 Configuration & Guidelines

#### 📄 [.agents/AGENTS.md](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/.agents/AGENTS.md)
* **Purpose:** Outlines workspace rules and constraints.
* **Key Details:**
  * Defines **Hackathon Mode** guidelines (13-hour build window for Google DeepMind Bangalore Hackathon on July 11, 2026).
  * Outlines system architecture components (Local layer, Escalation, Voice layer).

---

### 📂 Schema & Rules

#### 📄 [schema.json](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/schema.json)
* **Purpose:** JSON Schema Draft-07 file defining the target extraction object (`BorrowerFinancialData`).
* **Core Output Fields:**
  * `source_type`: enum (`"sms"`, `"ledger_photo"`, `"voice_note"`).
  * `daily_revenue_estimate`: number (INR credit estimate).
  * `revenue_variance`: enum (`"low"`, `"medium"`, `"high"`).
  * `payment_consistency`: enum (`"low"`, `"medium"`, `"high"`).
  * `confidence_score`: float (`0.0` to `1.0`).
  * `anomaly_flags`: list of strings (e.g. `["revenue_spike"]`).
  * `raw_extracted_text`: raw string representation of the source material.
  * `timestamp`: ISO 8601 extraction timestamp.
  * `borrower_session_id`: unique string mapping related data collections.

#### 📄 [schema_documentation.md](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/schema_documentation.md)
* **Purpose:** Plain-English documentation describing each field of `schema.json`, its data type, and logical constraints to help developers align model prompts.

---

### 📂 Executables & Binary Files

#### 📄 [google_gemma-4-E4B-it-Q4_K_M_v2.gguf](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/google_gemma-4-E4B-it-Q4_K_M_v2.gguf)
* **Purpose:** A quantized 4-bit (medium size) binary of Google's Edge-optimized **Gemma 4 E4B** instruction-tuned model (~5.36 GB).

#### 📁 [llama-bin/](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/llama-bin/)
* **Purpose:** Extracted folder containing 51 core compiled files for `llama.cpp` CPU execution on Windows.
* **Key Binaries:**
  * `llama-server.exe`: Launches the HTTP server exposing the model via OpenAI-compatible endpoints.
  * `llama.exe`: CLI execution tool.
  * `.dll` Files: Compiled CPU instruction-set variants (AVX, Alder Lake, Haswell, Zen4, etc.) to optimize execution on host CPU.

#### 📄 [llama-cpu-x64.zip](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/llama-cpu-x64.zip)
* **Purpose:** Original zipped bundle of `llama.cpp` binaries used to extract `llama-bin`.

---

### 📂 Scripts & Execution Logs

#### 📄 [benchmark.py](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/benchmark.py)
* **Purpose:** Measures startup time and sequential inference latencies of `llama-server.exe` to evaluate the host machine's hardware capabilities.

#### 📄 [extract_sms.py](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/extract_sms.py)
* **Purpose:** Core Python script managing local structured data extraction.
* **Key Processes:**
  1. Starts `llama-server.exe` using full CPU threads (`--threads 12`), single slot allocation (`--parallel 1`), and disabled reasoning content (`--reasoning off --reasoning-budget 0`).
  2. Sends UPI SMS logs to `/v1/chat/completions` with JSON response constraints.
  3. Formats response, auto-generates timestamps, and validates content against `schema.json`.
  4. Implements fallback retry logic to correct formatting or parsing failures.
  5. Includes 5 distinct test scenarios representing small vendors (consistent, varying, and anomalous payments).

#### 📄 [llama_server.log](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/llama_server.log)
* **Purpose:** Captured stdout/stderr logs of the running `llama-server.exe` subprocess. Used to analyze prompt token counts, prompt processing speeds, decoding speeds, slots allocation, and error stack traces.

#### 📄 [routing_engine.py](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/routing_engine.py)
* **Purpose:** Implements the credit risk routing engine. Evaluates structured financial extractions using anomaly-first logic: escalates to cloud if anomalies exist or if confidence < 0.7; otherwise processes locally. Includes 3 unit tests.

#### 📄 [pipeline.py](file:///c:/Users/Tanay%20Sinha/OneDrive/Desktop/Setu/pipeline.py)
* **Purpose:** Chained pipeline script that integrates both `extract_sms.py` and `routing_engine.py`. Executes the full extraction-and-routing flow on the 5 vendor scenarios in a single pass.
