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
import base64
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
    # Optional: voice note payloads carry the base64-encoded audio here
    audio_data_base64: str | None = Field(default=None, description="Base64-encoded voice note audio (data URL). Populated by voice_note source_type only.")
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
    # Pass-through fields expected by the frontend
    confidence_score: float | None = None
    anomaly_flags: list[str] = Field(default_factory=list)


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
small businesses in India. You receive financial data for a borrower case that a local \
model flagged as requiring human-grade cloud analysis.

Your job:
1. Reason carefully over the raw transaction text. It is the ground truth — prioritise \
   it over any structured fields marked 'unknown'.
2. Identify ALL anomalies present. An anomaly is ANYTHING unusual:
   - A transaction that is 3x or more above the borrower's typical amount → "revenue_spike"
   - Inconsistent or unverifiable income sources → "unverified_income_source"
   - Very few transactions (< 3 data points) → "insufficient_data"
   - Round-number entries that look fabricated → "suspected_fabrication"
   - Coached or vague narrative → "narrative_vague"
   - Any other concern → use a descriptive snake_case string
   CRITICAL: if your explanation mentions an anomaly, that anomaly MUST appear in anomaly_flags.
3. Produce a conservative risk_score between 0 and 100 (higher = MORE creditworthy / LOWER risk).
4. Classify risk_category as exactly one of: "low", "medium", or "high".
5. Write a concise explanation (2-4 sentences) of your reasoning.
6. Set confidence_score (0.0-1.0) reflecting how confident you are given data quality and completeness.

Return ONLY a JSON object — no markdown, no preamble:
{
  "risk_score": <number 0-100>,
  "risk_category": "low" | "medium" | "high",
  "explanation": "<string>",
  "confidence_score": <float 0.0-1.0>,
  "anomaly_flags": ["<snake_case_flag>", ...]
}
If no anomalies exist, anomaly_flags must be [].
"""

_VISION_AGENT_SYSTEM_PROMPT = """\
You are a senior credit risk analyst specialising in microfinance for informal-sector \
small businesses in India. You receive an image of a handwritten or printed ledger or daybook from a borrower's business.

Your job:
1. Parse the image carefully. Read all visible daybook or ledger entries, transaction dates, descriptions, and amounts.
2. Formulate a credit risk assessment grounded ONLY on what you can read from the ledger image:
   - Calculate or estimate the typical daily/weekly revenue shown.
   - Gauge payment consistency (daily? highly irregular? clustered?).
   - Evaluate revenue variance (volatile vs. stable transaction sizes).
3. Identify ALL anomalies visible in the ledger:
   - Inconsistent handwriting/ink across entries (post-facto fabrication) → "inconsistent_handwriting"
   - Identical, round-number entries that look too clean → "suspected_fabrication"
   - Very high outstanding balance relative to revenue → "high_debt_load"
   - Any other concern → descriptive snake_case string
   CRITICAL: if you mention an anomaly in your explanation, it MUST appear in anomaly_flags.
4. Assign a conservative but fair risk_score between 0 and 100 (higher = MORE creditworthy / LOWER risk).
5. Classify risk_category as exactly one of: "low", "medium", or "high".
6. Write a clear explanation (2-4 sentences) summarizing what transactions you read and your reasoning.
7. Set confidence_score (0.0-1.0) based on image legibility and data completeness.

Return ONLY a valid JSON object — no markdown, no preamble:
{
  "risk_score": <number 0-100>,
  "risk_category": "low" | "medium" | "high",
  "explanation": "<string>",
  "confidence_score": <float 0.0-1.0>,
  "anomaly_flags": ["<snake_case_flag>", ...]
}
Your ENTIRE response must be this JSON object and nothing else.
"""


def _build_agent_user_message(req: AssessmentRequest) -> str:
    """Construct the user-turn message fed to Gemini."""
    flags_str = ", ".join(req.anomaly_flags) if req.anomaly_flags else "none pre-detected (infer from raw text below)"

    # When pipeline couldn't run, confidence is the sentinel 0.5 — show as "unknown"
    # so Gemini doesn't anchor on it and forms its own confidence judgement.
    pipeline_ran = req.confidence_score != 0.5 or bool(req.anomaly_flags)
    conf_str = f"{req.confidence_score:.0%}" if pipeline_ran else "unknown (pipeline unavailable — use raw text as sole input)"

    # Likewise, revenue/variance/consistency are 0/low/low when pipeline fallback fires
    if not pipeline_ran and req.daily_revenue_estimate == 0.0:
        revenue_str = "unknown (parse from raw text)"
        variance_str = "unknown"
        consistency_str = "unknown"
    else:
        revenue_str = f"₹{req.daily_revenue_estimate:,.2f}"
        variance_str = req.revenue_variance
        consistency_str = req.payment_consistency

    return (
        f"ESCALATION CASE — BORROWER SESSION: {req.borrower_session_id}\n\n"
        f"Financial data (extracted from {req.source_type.replace('_', ' ')}):\n"
        f"  • Daily revenue estimate : {revenue_str}\n"
        f"  • Revenue variance       : {variance_str}\n"
        f"  • Payment consistency    : {consistency_str}\n"
        f"  • Extraction confidence  : {conf_str}\n"
        f"  • Anomaly flags          : {flags_str}\n\n"
        f"Routing reason (why local model could not score this):\n"
        f"  {req.routing_reason}\n\n"
        f"Raw extracted text (primary evidence — treat as ground truth over structured fields above):\n"
        f"\"\"\"\n{req.raw_extracted_text}\n\"\"\"\n\n"
        f"Please analyse and return the JSON risk assessment."
    )


def _extract_flags_from_explanation(explanation: str, existing_flags: list[str]) -> list[str]:
    """
    Post-processing safety net: keyword-scans Gemini's explanation and injects
    standard anomaly flags if they're described in text but not in the JSON array.
    Prevents the common failure mode where Gemini describes an anomaly in prose
    but returns anomaly_flags: [].
    """
    flags = list(existing_flags)  # copy
    text = explanation.lower()

    checks = [
        ("revenue_spike",           ["spike", "20x", "10x", "unusual", "unexplained", "large payment", "corporate", "one-off", "outsized"]),
        ("suspected_fabrication",   ["fabricat", "identical", "round-number", "uniform amount", "written in one"]),
        ("narrative_vague",         ["vague", "coached", "generic", "scripted", "unnatural"]),
        ("insufficient_data",       ["insufficient", "limited data", "only one day", "single day", "few transactions"]),
        ("unverified_income_source", ["unexplained", "unverified", "unknown source", "cannot corroborate"]),
        ("inconsistent_handwriting", ["inconsistent handwriting", "ink", "written in one sitting"]),
    ]

    for flag_name, keywords in checks:
        if flag_name not in flags and any(kw in text for kw in keywords):
            flags.append(flag_name)

    return flags


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
    from google.genai.types import Content, Part, GenerateContentConfig

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
        generate_content_config=GenerateContentConfig(
            temperature=0.2,               # low temp = consistent, fact-grounded scores
            max_output_tokens=4096,        # 1024 caused unterminated-string truncation on explanation
            # NOTE: response_mime_type="application/json" intentionally omitted.
            # Causes JSON truncation on developer API keys. Prompt + _parse_gemini_json handles it.
        ),
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


def _parse_base64_image(data_url: str) -> tuple[bytes, str]:
    """
    Parses a base64 data URL (e.g. 'data:image/png;base64,...')
    and returns (raw_bytes, mime_type).
    """
    if not data_url.startswith("data:image/"):
        try:
            return base64.b64decode(data_url), "image/png"
        except Exception as e:
            raise ValueError(f"Invalid base64 payload: {e}")
    
    header, encoded = data_url.split(",", 1)
    mime_type = header.split(";")[0].split(":")[1]
    raw_bytes = base64.b64decode(encoded)
    return raw_bytes, mime_type


def _call_adk_vision_agent(req: AssessmentRequest) -> tuple[dict, str]:
    """
    Decodes the image_data_base64 and calls Gemini via google-adk
    Managed Agent (iAPI) supporting multimodal vision inputs.
    """
    from google.adk.agents import LlmAgent
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Content, Part, GenerateContentConfig

    if not req.image_data_base64:
        raise ValueError("Missing image_data_base64 in request for vision assessment")

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    os.environ["GOOGLE_API_KEY"] = api_key

    # Decode base64 image data
    img_bytes, mime_type = _parse_base64_image(req.image_data_base64)

    agent = LlmAgent(
        name="setu_ledger_vision_analyst",
        model="gemini-3.5-flash",
        description="Senior credit risk analyst specializing in handwritten ledger vision OCR and underwriting.",
        instruction=_VISION_AGENT_SYSTEM_PROMPT,
        generate_content_config=GenerateContentConfig(
            temperature=0.2,               # low temp = grounded in image facts, not heuristic defaults
            max_output_tokens=4096,        # 2048 could still truncate long vision explanations
            # NOTE: response_mime_type="application/json" is intentionally omitted here.
            # JSON output mode is incompatible with multimodal (image) inputs on this API
            # configuration — it causes truncated output. The vision prompt + _parse_gemini_json
            # handles extraction robustly without it.
        ),
    )

    runner = InMemoryRunner(agent=agent, app_name="setu_vision")

    # Start runner session
    session = runner.session_service.create_session_sync(
        app_name="setu_vision", user_id="backend_vision", session_id=req.borrower_session_id
    )

    # Wrap the image bytes and request as multimodal parts
    parts = [
        Part.from_bytes(data=img_bytes, mime_type=mime_type),
        Part(text=(
            f"Please analyze this ledger photo for borrower session {req.borrower_session_id}.\n"
            f"Routing reason: {req.routing_reason}"
        ))
    ]

    final_text = ""
    for event in runner.run(
        user_id="backend_vision",
        session_id=session.id,
        new_message=Content(role="user", parts=parts),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    parsed = _parse_gemini_json(final_text)
    return parsed, "google-adk Managed Agent (iAPI, Vision LlmAgent, gemini-3.5-flash)"


_AUDIO_AGENT_SYSTEM_PROMPT = """\
You are a senior credit risk analyst specialising in microfinance for informal-sector \
small businesses in India. You receive an audio voice note recorded by a borrower or a \
field officer describing the borrower's income and business.

Your job:
1. Transcribe the audio carefully. Extract all financial figures mentioned: \
   daily/weekly income, typical revenue range, payment amounts, and any anomalies \
   stated (missed payments, sudden windfalls, illness, slow season, etc.).
2. Formulate a credit risk assessment grounded ONLY on what you can hear in the audio:
   - Estimate daily revenue in Indian Rupees.
   - Gauge payment consistency from the narrative (regular? seasonal? sporadic?).
   - Evaluate revenue variance from the spread of figures mentioned.
3. Check for red flags in the narrative:
   - Conflicting figures (claims ₹500/day then mentions ₹15,000 sale).
   - Coached or scripted sounding responses that don't match natural speech patterns.
   - Unexplained large transactions or vague income sources.
4. Assign a conservative but fair risk_score between 0 and 100 \
   (higher = MORE creditworthy / LOWER risk).
5. Classify the risk_category as exactly one of: "low", "medium", or "high".
6. Write a clear, concise explanation (2-4 sentences) summarising what you heard \
   (key figures and narrative) and your credit risk reasoning.

Return ONLY a valid JSON object — no markdown, no preamble, no chain-of-thought — with exactly these keys:
{
  "risk_score": <number 0-100>,
  "risk_category": "low" | "medium" | "high",
  "explanation": "<string>"
}
Your ENTIRE response must be this JSON object and nothing else.
"""


def _parse_base64_audio(data_url: str) -> tuple[bytes, str]:
    """
    Parses a base64 data URL (e.g. 'data:audio/wav;base64,...')
    and returns (raw_bytes, mime_type).
    """
    if not data_url.startswith("data:audio/"):
        try:
            return base64.b64decode(data_url), "audio/wav"
        except Exception as e:
            raise ValueError(f"Invalid audio base64 payload: {e}")

    header, encoded = data_url.split(",", 1)
    mime_type = header.split(";")[0].split(":")[1]
    raw_bytes = base64.b64decode(encoded)
    return raw_bytes, mime_type


def _call_adk_audio_agent(req: AssessmentRequest) -> tuple[dict, str]:
    """
    Decodes the audio_data_base64 and calls Gemini via google-adk
    Managed Agent (iAPI) supporting multimodal audio inputs.
    Mirrors _call_adk_vision_agent() exactly — same structure, audio modality.
    """
    from google.adk.agents import LlmAgent
    from google.adk.runners import InMemoryRunner
    from google.genai.types import Content, Part, GenerateContentConfig

    if not req.audio_data_base64:
        raise ValueError("Missing audio_data_base64 in request for audio assessment")

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    os.environ["GOOGLE_API_KEY"] = api_key

    # Decode base64 audio data
    audio_bytes, mime_type = _parse_base64_audio(req.audio_data_base64)

    agent = LlmAgent(
        name="setu_audio_voice_analyst",
        model="gemini-3.5-flash",
        description="Senior credit risk analyst specializing in voice note transcription and microfinance underwriting.",
        instruction=_AUDIO_AGENT_SYSTEM_PROMPT,
        generate_content_config=GenerateContentConfig(
            temperature=0.2,               # low temp = grounded in audio facts, not heuristic defaults
            max_output_tokens=2048,
            # NOTE: response_mime_type="application/json" is intentionally omitted here.
            # JSON output mode is incompatible with multimodal (audio) inputs on this API
            # configuration — it causes truncated output. Same fix as vision agent.
        ),
    )

    runner = InMemoryRunner(agent=agent, app_name="setu_audio")

    session = runner.session_service.create_session_sync(
        app_name="setu_audio", user_id="backend_audio", session_id=req.borrower_session_id
    )

    # Wrap the audio bytes and request as multimodal parts
    parts = [
        Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        Part(text=(
            f"Please analyze this voice note for borrower session {req.borrower_session_id}.\n"
            f"Routing reason: {req.routing_reason}"
        ))
    ]

    final_text = ""
    for event in runner.run(
        user_id="backend_audio",
        session_id=session.id,
        new_message=Content(role="user", parts=parts),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    parsed = _parse_gemini_json(final_text)
    return parsed, "google-adk Managed Agent (iAPI, Audio LlmAgent, gemini-3.5-flash)"



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
            max_output_tokens=4096,    # 1024 caused unterminated-string truncation
            # NOTE: response_mime_type="application/json" is intentionally omitted.
            # It causes JSONDecodeError/truncation on the developer API tier.
            # The _AGENT_SYSTEM_PROMPT instructs JSON-only output; _parse_gemini_json handles extraction.
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

def _escalate_to_gemini(
    req: AssessmentRequest,
) -> tuple[float | None, str, str, str, float | None, list[str]]:
    """
    Tries escalation paths in priority order.
    Returns (risk_score, risk_category, explanation, method_label, confidence_score, anomaly_flags).
    confidence_score and anomaly_flags come from Gemini's JSON when available.
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

            # confidence_score: prefer Gemini's own value, fall back to pipeline extraction value
            raw_conf = parsed.get("confidence_score")
            if raw_conf is not None:
                confidence_score = min(1.0, max(0.0, float(raw_conf)))
            else:
                confidence_score = req.confidence_score  # from pipeline (real value)

            # anomaly_flags: merge Gemini's detections with pipeline's pre-flagged ones,
            # then enrich from explanation text as a safety net
            gemini_flags = parsed.get("anomaly_flags", [])
            if isinstance(gemini_flags, list) and gemini_flags:
                anomaly_flags = [str(f) for f in gemini_flags]
            else:
                anomaly_flags = req.anomaly_flags or []  # from pipeline (real value)

            # Post-process: extract any flags described in explanation but missing from JSON
            anomaly_flags = _extract_flags_from_explanation(explanation, anomaly_flags)

            return risk_score, risk_category, explanation, method, confidence_score, anomaly_flags

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
        None,
        [],
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

    # ── Voice note guard / Audio path ────────────────────────────────────────
    # If a voice note is sent with base64 audio data, run our ADK audio analyst.
    # If the audio call fails or no audio data was supplied, fall back to the
    # honest pending_review stub.
    if req.source_type == "voice_note":
        if req.audio_data_base64 and req.audio_data_base64.strip():
            try:
                parsed, method = _call_adk_audio_agent(req)
                risk_score = float(parsed["risk_score"])
                risk_score = max(0.0, min(100.0, round(risk_score, 2)))
                risk_category = str(parsed.get("risk_category", "")).lower()
                if risk_category not in ("low", "medium", "high"):
                    risk_category = _categorise(risk_score)
                explanation = str(parsed["explanation"])
                latency_ms = round((time.perf_counter() - t_start) * 1000, 3)

                return AssessmentResponse(
                    risk_score=risk_score,
                    risk_category=risk_category,
                    explanation=explanation,
                    route="escalate",
                    routing_reason=req.routing_reason,
                    latency_ms=latency_ms,
                    escalation_method=method,
                )
            except Exception as e:
                logger.warning(f"[assess] Audio escalation failed: {e!r}. Falling back to pending review stub.")

        # Fallback pending review stub
        latency_ms = round((time.perf_counter() - t_start) * 1000, 3)
        return AssessmentResponse(
            risk_score=None,
            risk_category="pending_review",
            explanation=(
                "Voice note received. Audio processing failed or was skipped. "
                "A human reviewer must listen to and assess this voice note before a "
                "risk score can be assigned."
            ),
            route=req.route,
            routing_reason=req.routing_reason,
            latency_ms=latency_ms,
            escalation_method="fallback-stub",
        )
    # ── End voice note guard ─────────────────────────────────────────────────

    # ── Ledger photo guard / Vision path ─────────────────────────────────────
    # If a ledger photo is sent with base64 image data, run our ADK vision analyst.
    # If the vision call fails or if no image data was supplied, fall back to the
    # honest pending_review stub.
    if req.source_type == "ledger_photo":
        if req.image_data_base64 and req.image_data_base64.strip():
            try:
                parsed, method = _call_adk_vision_agent(req)
                risk_score = float(parsed["risk_score"])
                risk_score = max(0.0, min(100.0, round(risk_score, 2)))
                risk_category = str(parsed.get("risk_category", "")).lower()
                if risk_category not in ("low", "medium", "high"):
                    risk_category = _categorise(risk_score)
                explanation = str(parsed["explanation"])

                # Extract confidence and flags from vision JSON, post-process explanation
                raw_conf = parsed.get("confidence_score")
                vis_confidence = min(1.0, max(0.0, float(raw_conf))) if raw_conf is not None else None

                vis_flags_raw = parsed.get("anomaly_flags", [])
                vis_flags = [str(f) for f in vis_flags_raw] if isinstance(vis_flags_raw, list) else []
                vis_flags = _extract_flags_from_explanation(explanation, vis_flags)

                latency_ms = round((time.perf_counter() - t_start) * 1000, 3)

                return AssessmentResponse(
                    risk_score=risk_score,
                    risk_category=risk_category,
                    explanation=explanation,
                    route="escalate",
                    routing_reason=req.routing_reason,
                    latency_ms=latency_ms,
                    escalation_method=method,
                    confidence_score=vis_confidence,
                    anomaly_flags=vis_flags,
                )
            except Exception as e:
                logger.warning(f"[assess] Vision escalation failed: {e!r}. Falling back to pending review stub.")
        
        # Fallback pending review stub
        latency_ms = round((time.perf_counter() - t_start) * 1000, 3)
        return AssessmentResponse(
            risk_score=None,
            risk_category="pending_review",
            explanation=(
                "Ledger photo received. Vision processing failed or was skipped. "
                "A human reviewer must assess this daybook image before a risk score "
                "can be assigned."
            ),
            route=req.route,
            routing_reason=req.routing_reason,
            latency_ms=latency_ms,
            escalation_method="fallback-stub",
        )
    # ── End ledger photo guard ───────────────────────────────────────────────

    if req.route == "local":
        risk_score    = _compute_risk_score(req)
        risk_category = _categorise(risk_score)
        explanation   = _build_local_explanation(req, risk_score, risk_category)
        # Use pipeline-extracted values for local path
        confidence_score  = req.confidence_score
        anomaly_flags_out = req.anomaly_flags

    elif req.route == "escalate":
        risk_score, risk_category, explanation, escalation_method, confidence_score, anomaly_flags_out = _escalate_to_gemini(req)

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
        confidence_score=confidence_score,
        anomaly_flags=anomaly_flags_out or [],
    )


# ---------------------------------------------------------------------------
# Frontend-facing /api/process endpoint
# ---------------------------------------------------------------------------
# The frontend sends a simple {source_type, raw_text|image_data_base64|audio_data_base64}
# payload. This endpoint handles pipeline-level extraction/routing internally
# and returns the full AssessmentResponse the frontend expects.

class FrontendProcessRequest(BaseModel):
    """Simple request shape sent by the React frontend."""
    source_type: Literal["sms", "ledger_photo", "voice_note"]
    raw_text: str | None = None
    image_data_base64: str | None = None
    audio_data_base64: str | None = None
    borrower_session_id: str


def _check_api_key() -> None:
    """Raise a 503 with a clear message if the Gemini API key is missing."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY is not configured on this server. "
                "Add it to the .env file in the project root and restart the backend."
            ),
        )


@app.post("/api/process", response_model=AssessmentResponse)
def api_process(req: FrontendProcessRequest) -> AssessmentResponse:
    """
    Frontend-facing unified endpoint.

    Accepts the simple payload sent by the React UI and internally:
      - SMS       → runs local pipeline extraction (Gemma), then local/escalate score
      - Photo     → base64 image, runs cloud Vision ADK agent
      - Voice     → base64 audio, runs cloud Audio ADK agent

    Always requires GEMINI_API_KEY for escalation paths.
    Returns 503 with a descriptive error if the key is absent.
    """
    import datetime as dt

    # ── SMS path ──────────────────────────────────────────────────────────────
    if req.source_type == "sms":
        if not req.raw_text or not req.raw_text.strip():
            raise HTTPException(status_code=400, detail="raw_text is required for source_type=sms")

        # Try local Gemma pipeline extraction
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from pipeline import process_sms_input
            extracted = process_sms_input(req.raw_text, req.borrower_session_id)
        except Exception as pipeline_err:
            logger.warning(
                f"[api/process] Local SMS pipeline failed: {pipeline_err!r} "
                f"— falling back to Gemini text extraction"
            )
            _check_api_key()
            # Fallback: low-confidence escalation with raw text
            extracted = {
                "source_type": "sms",
                "daily_revenue_estimate": 0.0,
                "revenue_variance": "medium",
                "payment_consistency": "medium",
                "confidence_score": 0.5,
                "anomaly_flags": [],
                "raw_extracted_text": req.raw_text,
                "route": "escalate",
                "routing_reason": "pipeline unavailable; raw text escalated to Gemini",
                "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "borrower_session_id": req.borrower_session_id,
            }

        internal_req = AssessmentRequest(
            source_type=extracted["source_type"],
            daily_revenue_estimate=float(extracted.get("daily_revenue_estimate", 0)),
            revenue_variance=extracted.get("revenue_variance", "medium"),
            payment_consistency=extracted.get("payment_consistency", "medium"),
            confidence_score=float(extracted.get("confidence_score", 0.5)),
            anomaly_flags=extracted.get("anomaly_flags", []),
            raw_extracted_text=extracted.get("raw_extracted_text", req.raw_text or ""),
            timestamp=extracted.get("timestamp", dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
            borrower_session_id=req.borrower_session_id,
            route=extracted.get("route", "local"),
            routing_reason=extracted.get("routing_reason", ""),
        )

        resp = assess(internal_req)
        # NOTE: do NOT overwrite resp.confidence_score or resp.anomaly_flags here.
        # assess() already computes them correctly via _escalate_to_gemini() which
        # calls Gemini, runs the post-processor, and falls back to pipeline values.
        return resp

    # ── Ledger photo path ─────────────────────────────────────────────────────
    if req.source_type == "ledger_photo":
        if not req.image_data_base64 or not req.image_data_base64.strip():
            raise HTTPException(status_code=400, detail="image_data_base64 is required for source_type=ledger_photo")
        _check_api_key()

        internal_req = AssessmentRequest(
            source_type="ledger_photo",
            daily_revenue_estimate=0.0,
            revenue_variance="low",
            payment_consistency="low",
            confidence_score=0.0,
            anomaly_flags=[],
            raw_extracted_text="",
            image_data_base64=req.image_data_base64,
            timestamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            borrower_session_id=req.borrower_session_id,
            route="escalate",
            routing_reason="ledger_photo: local vision unsupported",
        )
        return assess(internal_req)

    # ── Voice note path ───────────────────────────────────────────────────────
    if req.source_type == "voice_note":
        if not req.audio_data_base64 or not req.audio_data_base64.strip():
            raise HTTPException(status_code=400, detail="audio_data_base64 is required for source_type=voice_note")
        _check_api_key()

        internal_req = AssessmentRequest(
            source_type="voice_note",
            daily_revenue_estimate=0.0,
            revenue_variance="low",
            payment_consistency="low",
            confidence_score=0.0,
            anomaly_flags=[],
            raw_extracted_text="",
            audio_data_base64=req.audio_data_base64,
            timestamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            borrower_session_id=req.borrower_session_id,
            route="escalate",
            routing_reason="voice_note: local audio transcription unsupported",
        )
        return assess(internal_req)

    raise HTTPException(status_code=400, detail=f"Unknown source_type: {req.source_type!r}")
