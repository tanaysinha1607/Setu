"""
Setu — Adaptive AI Credit Risk Assessment Backend
FastAPI service that receives pre-routed borrower data from the local Gemma
pipeline and either scores it locally or escalates to the Gemini API.

Escalation strategy (in order):
  1. google-adk  (Managed Agents / iAPI)  — preferred if SDK is present
  2. google-genai v2 (google.genai.Client) — automatic fallback

The response always includes 'escalation_method' so you can tell a judge
exactly which path fired.
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Load .env from the project root (one directory above backend/)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass  # python-dotenv not installed; rely on OS env vars

logger = logging.getLogger("setu")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AssessmentRequest(BaseModel):
    # ---- Fields from schema.json ----
    source_type: Literal["sms", "ledger_photo", "voice_note"]
    daily_revenue_estimate: float = Field(..., ge=0)
    revenue_variance: Literal["low", "medium", "high"]
    payment_consistency: Literal["low", "medium", "high"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    anomaly_flags: list[str]
    # Optional: SMS/voice payloads populate this; ledger photo payloads may omit it
    raw_extracted_text: str = ""
    # Optional: ledger photo payloads carry the base64-encoded image here instead
    image_data_base64: str | None = Field(default=None, description="Base64-encoded ledger photo (data URL). Populated by ledger_photo source_type only.")
    timestamp: str
    borrower_session_id: str

    # ---- Extra fields added by the routing layer ----
    route: Literal["local", "escalate"]
    routing_reason: str

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(
                "timestamp must be a valid ISO 8601 date-time string "
                "(e.g. '2025-07-11T10:00:00+05:30')"
            )
        return v


class AssessmentResponse(BaseModel):
    risk_score: float | None       # 0-100; None on total failure
    risk_category: str             # "low" | "medium" | "high" | "error"
    explanation: str
    route: str
    routing_reason: str
    latency_ms: float
    # Tells judges which escalation path fired
    escalation_method: str | None = None


# ---------------------------------------------------------------------------
# Local scoring helpers
# ---------------------------------------------------------------------------

_VARIANCE_MAP    = {"low": 1.0, "medium": 0.5, "high": 0.0}
_CONSISTENCY_MAP = {"high": 1.0, "medium": 0.5, "low": 0.0}
_REVENUE_CAP         = 20_000.0
_WEIGHT_REVENUE      = 0.40
_WEIGHT_VARIANCE     = 0.30
_WEIGHT_CONSISTENCY  = 0.30


def _compute_risk_score(req: AssessmentRequest) -> float:
    """
    Returns a creditworthiness score in [0, 100].
    Higher score = lower risk (more creditworthy).
    """
    revenue_norm     = min(req.daily_revenue_estimate / _REVENUE_CAP, 1.0)
    variance_norm    = _VARIANCE_MAP[req.revenue_variance]
    consistency_norm = _CONSISTENCY_MAP[req.payment_consistency]
    raw = (
        _WEIGHT_REVENUE * revenue_norm
        + _WEIGHT_VARIANCE * variance_norm
        + _WEIGHT_CONSISTENCY * consistency_norm
    )
    return round(raw * 100, 2)


def _categorise(score: float) -> str:
    if score >= 60:
        return "low"
    if score >= 35:
        return "medium"
    return "high"


def _build_local_explanation(req: AssessmentRequest, score: float, category: str) -> str:
    return (
        f"Local scoring complete. "
        f"Daily revenue ₹{req.daily_revenue_estimate:,.0f} "
        f"(variance: {req.revenue_variance}, payment consistency: {req.payment_consistency}). "
        f"Weighted risk score: {score}/100 → category: {category.upper()} risk. "
        f"Confidence of extraction: {req.confidence_score:.0%}."
    )


# ---------------------------------------------------------------------------
# Gemini escalation — shared prompt builders
# ---------------------------------------------------------------------------

_AGENT_SYSTEM_PROMPT = """\
You are a senior credit risk analyst specialising in microfinance for informal-sector \
small businesses in India. You receive structured financial data that a local ML model \
flagged as anomalous or low-confidence and could not safely score on its own.

Your job:
1. Reason carefully over the flagged signals. Consider whether each anomaly flag \
   (e.g. "revenue_spike") is likely a one-off legitimate event (festival bonus, \
   bulk order, salary credit, advance payment from a wholesaler) or a genuine red \
   flag (fabricated data, money laundering, loan stacking). Weigh the raw extracted \
   text as primary evidence.
2. Produce a conservative but fair risk_score between 0 and 100 \
   (higher = MORE creditworthy / LOWER risk).
3. Classify the risk_category as exactly one of: "low", "medium", or "high".
4. Write a clear, concise explanation (2-4 sentences) of your reasoning — \
   your thought process, not just the verdict.

Return ONLY a JSON object with exactly these keys:
{
  "risk_score": <number 0-100>,
  "risk_category": "low" | "medium" | "high",
  "explanation": "<string>"
}
No markdown, no preamble, no extra keys.
"""


def _build_agent_user_message(req: AssessmentRequest) -> str:
    """Construct the user-turn message fed to Gemini."""
    flags_str = ", ".join(req.anomaly_flags) if req.anomaly_flags else "none"
    return (
        f"ESCALATION CASE — BORROWER SESSION: {req.borrower_session_id}\n\n"
        f"Financial data (extracted from {req.source_type.replace('_', ' ')}):\n"
        f"  • Daily revenue estimate : ₹{req.daily_revenue_estimate:,.2f}\n"
        f"  • Revenue variance       : {req.revenue_variance}\n"
        f"  • Payment consistency    : {req.payment_consistency}\n"
        f"  • Extraction confidence  : {req.confidence_score:.0%}\n"
        f"  • Anomaly flags          : {flags_str}\n\n"
        f"Routing reason (why local model could not score this):\n"
        f"  {req.routing_reason}\n\n"
        f"Raw extracted text (primary evidence — treat as ground truth):\n"
        f"\"\"\"\n{req.raw_extracted_text}\n\"\"\"\n\n"
        f"Please analyse and return the JSON risk assessment."
    )


def _parse_gemini_json(text: str) -> dict:
    """
    Extract the first valid JSON object from the model response.
    Uses raw_decode so it stops after the first complete object even if the
    model appends stray trailing characters (e.g. gemini-3.5-flash adds '}').
    Falls back to a regex-extract + loads if raw_decode fails.
    """
    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1)

    text = text.strip()

    # Find the start of the JSON object and parse only that
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in response: {text!r}")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text, idx=start)
        return obj
    except json.JSONDecodeError:
        # Last resort: try loading the whole stripped string
        return json.loads(text)


# ---------------------------------------------------------------------------
# Escalation path 1 — google-adk Managed Agent (iAPI)
# ---------------------------------------------------------------------------

def _call_adk_agent(req: AssessmentRequest) -> tuple[dict, str]:
    """
    Call Gemini via google-adk Managed Agent (iAPI).
    Raises ImportError if ADK is not installed (triggers fallback in caller).
    """
    from google.adk.agents import LlmAgent
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Content, Part

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    
    # Ensure ADK's internal client picks up the API key via the expected env var
    os.environ["GOOGLE_API_KEY"] = api_key

    agent = LlmAgent(
        name="setu_credit_risk_analyst",
        model="gemini-3.5-flash",
        description="Senior credit risk analyst for microfinance escalated cases.",
        instruction=_AGENT_SYSTEM_PROMPT,
    )

    runner = InMemoryRunner(agent=agent, app_name="setu")

    # Use runner's own session service to create session synchronously
    session = runner.session_service.create_session_sync(
        app_name="setu", user_id="backend", session_id=req.borrower_session_id
    )

    user_msg = _build_agent_user_message(req)

    # Run generator synchronously to consume the response
    final_text = ""
    for event in runner.run(
        user_id="backend",
        session_id=session.id,
        new_message=Content(role="user", parts=[Part(text=user_msg)]),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    parsed = _parse_gemini_json(final_text)
    return parsed, "google-adk Managed Agent (iAPI, LlmAgent, gemini-3.5-flash)"



# ---------------------------------------------------------------------------
# Escalation path 2 — google-genai v2 SDK (direct, with agent-style prompt)
# ---------------------------------------------------------------------------

def _call_genai_direct(req: AssessmentRequest) -> tuple[dict, str]:
    """
    Call Gemini via the google-genai v2 SDK (google.genai.Client).
    The system_instruction turns this into an agent-style call — same depth of
    reasoning, just not a formal Managed Agent session.
    """
    import google.genai as genai
    from google.genai import types as genai_types

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)

    user_msg = _build_agent_user_message(req)

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=user_msg,
        config=genai_types.GenerateContentConfig(
            system_instruction=_AGENT_SYSTEM_PROMPT,
            temperature=0.2,           # low temp = consistent, deterministic risk scores
            max_output_tokens=1024,
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text or ""
    parsed = _parse_gemini_json(raw_text)
    return parsed, (
        "google-genai v2 SDK (google.genai.Client, direct GenerativeContent call, "
        "gemini-3.5-flash, agent-style system_instruction)"
    )


# ---------------------------------------------------------------------------
# Escalation orchestrator — tries ADK first, then falls back
# ---------------------------------------------------------------------------

def _escalate_to_gemini(req: AssessmentRequest) -> tuple[float | None, str, str, str]:
    """
    Tries escalation paths in priority order.
    Returns (risk_score, risk_category, explanation, method_label).
    """
    attempts = [
        ("ADK",        _call_adk_agent),
        ("direct-SDK", _call_genai_direct),
    ]

    for label, attempt_fn in attempts:
        try:
            parsed, method = attempt_fn(req)

            risk_score = float(parsed["risk_score"])
            risk_score = max(0.0, min(100.0, round(risk_score, 2)))  # clamp to [0,100]
            risk_category = str(parsed.get("risk_category", "")).lower()
            if risk_category not in ("low", "medium", "high"):
                risk_category = _categorise(risk_score)
            explanation = str(parsed["explanation"])
            return risk_score, risk_category, explanation, method

        except ImportError:
            logger.info(f"[escalate] {label}: SDK not installed — trying next")
            continue
        except Exception as exc:
            logger.warning(f"[escalate] {label}: failed ({exc!r}) — trying next")
            continue

    # All paths failed — safe conservative fallback
    return (
        None,
        "high",
        (
            "Gemini escalation failed (both ADK and direct-SDK paths raised errors). "
            "Defaulting to HIGH risk as a conservative safety measure. "
            f"Routing reason: {req.routing_reason}"
        ),
        "none (all escalation paths failed)",
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Setu Credit Risk API",
    description=(
        "Adaptive AI routing system for credit risk assessment. "
        "Receives pre-routed borrower data from a local Gemma model and either "
        "scores locally or escalates to a Gemini Managed Agent."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root():
    """Redirect bare root to the interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "setu-credit-risk-api",
        "version": "0.2.0",
        "endpoints": {
            "docs":   "/docs",
            "assess": "POST /assess",
            "health": "GET /health",
        },
    }


@app.post("/assess", response_model=AssessmentResponse)
def assess(req: AssessmentRequest) -> AssessmentResponse:
    """
    Main assessment endpoint.

    - route == 'local'    → weighted scoring function returns risk_score + category.
    - route == 'escalate' → calls Gemini API (ADK Managed Agent → direct-SDK fallback).

    Special case: ledger_photo payloads with no extracted text yet return a
    pending_review stub — the real vision/OCR branch is not yet implemented,
    so we must not fabricate a score from placeholder zeros.
    """
    t_start = time.perf_counter()
    escalation_method: str | None = None

    # ── Ledger photo guard ───────────────────────────────────────────────────
    # Until a real vision/OCR branch is built, ledger_photo payloads carry
    # placeholder zeros and an empty raw_extracted_text.  Running the local
    # formula or asking the ADK agent to reason over nothing would produce
    # numbers we cannot explain — return an honest pending_review stub instead.
    if req.source_type == "ledger_photo" and not req.raw_extracted_text.strip():
        latency_ms = round((time.perf_counter() - t_start) * 1000, 3)
        return AssessmentResponse(
            risk_score=None,
            risk_category="pending_review",
            explanation=(
                "Ledger photo received and stored. "
                "Automated vision/OCR extraction is not yet implemented — "
                "a human reviewer must assess this submission before a risk "
                "score can be assigned."
            ),
            route=req.route,
            routing_reason=req.routing_reason,
            latency_ms=latency_ms,
            escalation_method=None,
        )
    # ── End ledger photo guard ───────────────────────────────────────────────

    if req.route == "local":
        risk_score    = _compute_risk_score(req)
        risk_category = _categorise(risk_score)
        explanation   = _build_local_explanation(req, risk_score, risk_category)

    elif req.route == "escalate":
        risk_score, risk_category, explanation, escalation_method = _escalate_to_gemini(req)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown route value: {req.route!r}")

    latency_ms = round((time.perf_counter() - t_start) * 1000, 3)

    return AssessmentResponse(
        risk_score=risk_score,
        risk_category=risk_category,
        explanation=explanation,
        route=req.route,
        routing_reason=req.routing_reason,
        latency_ms=latency_ms,
        escalation_method=escalation_method,
    )
