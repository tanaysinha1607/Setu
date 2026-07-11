# Project Setu: Summary & Overview

## The Idea
**Project Setu** is an adaptive AI routing system designed for microfinance credit risk assessment. It aims to extract structured financial metrics from messy informal inputs such as SMS logs, ledger photos, and voice notes. It evaluates the credit risk of microfinance borrowers based on these inputs.

The system is built on a hybrid architecture:
1. **Local Layer:** A local instance of the **Gemma 4 E4B** model runs via `llama.cpp` to parse SMS inputs and extract structured financial metrics. This helps in low-latency, privacy-preserving, and offline-capable initial processing.
2. **Escalation Routing:** The local system calculates confidence scores and identifies anomaly flags. If the confidence is low or there is a significant anomaly, the data is escalated to a cloud-hosted Gemini model for deeper validation. Ledger photos and voice notes are automatically escalated because local models lack vision and audio capabilities.
3. **Voice/Interactivity:** A voice layer is integrated, enabling field officers to perform interactive spoken Q&A using the Gemini Live API.

---

## File Breakdown

Here is a comprehensive overview of the files in the repository:

### Core Pipeline & Routing
* **`pipeline.py`**: Chains the local SMS extraction layer, ledger photo pipelines, and voice note pipelines with the backend scoring service. It prepares base64 payloads for images and audio files and sets routing fields (`route`, `routing_reason`).
* **`routing_engine.py`**: Handles the logical criteria for credit assessment routing. It checks confidence scores, transaction frequencies, and anomaly flags to determine if the local score is sufficient or if the case must route to the cloud.
* **`extract_sms.py`**: Coordinates starting and stopping the local `llama-server.exe` subprocess and performs local structured data extraction via prompt templates sent to the Gemma model.

### Modality & Interactivity Scripts
* **`voice_qa.py`**: Standalone real-time interactive audio prototype using the Gemini Live API (`google-genai`). It implements push-to-talk recording, handles a real-time conversational session, and grounds responses on a mock borrower's credit profile (Ramesh).
* **`test_voice_note.py`**: E2E validation script for the voice note input pipeline. It scans `./audio/` for audio files, encodes them to base64 Data URLs, calls the backend, and presents the assessment results.

### Backend Application
* **`backend/main.py`**: FastAPI application containing the assessment endpoints. It performs local weighted scoring for SMS data (`route="local"`) or runs cloud-based Gemini Managed Agents via `google-adk` to process escalated text, handwritten ledger photos (Vision), and voice notes (Audio).
* **`backend/main_no_adk.py`**: Fallback server implementation using direct `google-genai` SDK calls, bypassing `google-adk` if necessary.

### Schema & Metadata
* **`schema.json`**: Defines the target extraction object structure (`BorrowerFinancialData`), enforcing data types for modalities (including `image_data_base64` and `audio_data_base64`).
* **`schema_documentation.md`**: Provides plain-English documentation detailing each field within `schema.json` and logical constraints.

### Test & Utility Scripts
* **`benchmark.py`**: Utility script to measure local `llama-server.exe` startup times and sequential inference latencies.
* **`test_ledger_images.py`**: Evaluates the vision analysis capabilities of the backend against sample handwritten ledger images in the `images/` directory.
* **`test_endpoints.py`**: Runs health check and payload parsing tests against the FastAPI backend.
* **`test_schema_fix.py` / `test_adk_agent.py` / `test_adk_multimodal.py`**: Various integration tests verifying ADK agent setup, JSON parsing robustness, and temperature controls.

### Documentation
* **`project_overview.md`**: Original comprehensive documentation detailing the project's folder structure, API details, and routing design.
* **`voice_capabilities_summary.md`**: Dedicated user guide detailing the architecture, implementation, and testing steps for the Voice QA and Voice Note layers.
* **`hackathon_update.md`**: Tracking sheet detailing changes, fixes, and implemented modules for submission.
