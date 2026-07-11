# Setu: Hackathon Development Update

## Current State of the Backend
We have successfully implemented the **Adaptive AI Routing System** for credit risk assessment. The system acts as the bridge between the local Gemma extraction layer and the cloud-based escalation layer.

### 1. Dual-Path Architecture
The system supports two distinct paths based on the `route` provided by the local pipeline:
*   **Local Path (`route: "local"`):** Uses a weighted deterministic formula to calculate a risk score based on daily revenue, revenue variance, and payment consistency. It returns a fast, local response for high-confidence, non-anomalous data.
*   **Escalation Path (`route: "escalate"`):** Routes complex, anomalous, or low-confidence data to a cloud-based Large Language Model (Gemini) acting as a Senior Credit Risk Analyst.

### 2. The Agentic Escalation Strategy (iAPI / Managed Agent)
We designed and implemented a production-grade escalation flow that runs directly on Google's Agent Development Kit (ADK / iAPI):

#### Tier 1: Google ADK Managed Agents (iAPI) — ACTIVE
We have successfully installed `google-adk` directly from PyPI (no special `.whl` files required) and fully wrapped our credit risk reasoning logic inside an **`adk.agents.LlmAgent`** powered by an **`InMemoryRunner`**.
*   **Agent Configuration:**
    *   **Agent Type:** `LlmAgent`
    *   **Runner:** `InMemoryRunner` with synchronous generation loop.
    *   **Session Management:** `InMemorySessionService.create_session_sync` tracking agent sessions by `borrower_session_id`.
    *   **Model:** `gemini-3.5-flash` with low-temperature deterministic setting (`0.2`).
*   **Live Output Validation (Sample 5 Anomaly):**
    The ADK Managed Agent successfully reasons over the ₹18,500 spike case and returns:
    ```json
    {
      "risk_score": 72.0,
      "risk_category": "medium",
      "explanation": "The borrower exhibits consistent daily transaction patterns of ₹800–₹1,000, but the overall revenue estimate is heavily skewed by a one-off B2B payment of ₹18,500 from Corporate Corp. While this likely represents a legitimate bulk order or invoice clearance, credit limits should be assessed against the baseline daily revenue of ~₹3,000 rather than the skewed ₹21,200 figure to avoid over-leveraging.",
      "route": "escalate",
      "routing_reason": "Escalated: anomaly detected (revenue_spike)",
      "latency_ms": 9085.659,
      "escalation_method": "google-adk Managed Agent (iAPI, LlmAgent, gemini-3.5-flash)"
    }
    ```

#### Tier 2: Resilient Fallback (Direct SDK Agent) — ENABLED
If the system ever encounters an environment issue or missing packages, it automatically falls back to a direct `google-genai` (v2) client call with an identical system instruction.

### 3. Model Versioning & API Key Testing
*   The provided Hackathon API key was successfully authenticated.
*   We queried the API, found that **`gemini-3.5-flash`** is available, and successfully wired it into the application.

## Testing & Validation
*   **FastAPI** is fully configured and handles requests seamlessly.
*   The `JSONDecodeError` caused by preview models appending trailing braces (`}`) has been fixed using a robust `raw_decode` parser.
*   The system successfully processes end-to-end payload routing without errors and correctly attributes the latency and escalation method.

---

## Strategy for the Judges

If you are asked about your use of Managed Agents / iAPI, you can confidently present the following narrative:

> *"We designed Setu to be enterprise-ready and resilient. Our escalation architecture runs directly on Google's formal Managed Agents framework (iAPI / ADK). The system wraps a specialized Credit Analyst persona in a `google.adk.agents.LlmAgent`, driving execution via an `InMemoryRunner` session to track conversation context. Furthermore, we designed a zero-downtime fallback path using the direct `google-genai` SDK to guarantee that local underwriting never stops, even if the runtime environment loses dependencies. We have validated this end-to-end with anomalous transactional spikes, demonstrating detailed, non-templated reasoning."*

