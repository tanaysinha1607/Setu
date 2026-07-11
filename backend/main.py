"""
Setu — Adaptive AI Credit Risk Assessment Backend
FastAPI service that receives pre-routed borrower data from the local Gemma
pipeline and either scores it locally or stubs an escalation to the Gemini
Managed Agent.
"""

import time
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AssessmentRequest(BaseModel):
    # ---- Fields from schema.json (all required) ----
    source_type: Literal["sms", "ledger_photo", "voice_note"]
    daily_revenue_estimate: float = Field(..., ge=0)
    revenue_variance: Literal["low", "medium", "high"]
    payment_consistency: Literal["low", "medium", "high"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    anomaly_flags: list[str]
    raw_extracted_text: str
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
    risk_score: float | None       # 0-100; None when pending review
    risk_category: str             # "low" | "medium" | "high" | "pending_review"
    explanation: str
    route: str
    routing_reason: str
    latency_ms: float


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

# Ordinal mappings for categorical fields
_VARIANCE_MAP = {"low": 1.0, "medium": 0.5, "high": 0.0}
_CONSISTENCY_MAP = {"high": 1.0, "medium": 0.5, "low": 0.0}

# Revenue normalisation ceiling (₹20,000 daily → score 1.0; anything above caps)
_REVENUE_CAP = 20_000.0

# Weights (must sum to 1.0)
_WEIGHT_REVENUE = 0.40
_WEIGHT_VARIANCE = 0.30
_WEIGHT_CONSISTENCY = 0.30


def _compute_risk_score(req: AssessmentRequest) -> float:
    """
    Returns a creditworthiness score in [0, 100].
    Higher score = lower risk (more creditworthy).

    Formula (weighted sum of normalised components):
      revenue_component    : clamped daily_revenue / cap        (40 %)
      variance_component   : inverted variance level            (30 %)
      consistency_component: payment_consistency level          (30 %)
    """
    revenue_norm = min(req.daily_revenue_estimate / _REVENUE_CAP, 1.0)
    variance_norm = _VARIANCE_MAP[req.revenue_variance]
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
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Setu Credit Risk API",
    description=(
        "Adaptive AI routing system for credit risk assessment. "
        "Receives pre-routed borrower data from a local Gemma model and either "
        "scores locally or escalates to a Gemini Managed Agent."
    ),
    version="0.1.0",
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
        "version": "0.1.0",
        "endpoints": {
            "docs": "/docs",
            "assess": "POST /assess",
            "health": "GET /health",
        },
    }


@app.post("/assess", response_model=AssessmentResponse)
def assess(req: AssessmentRequest) -> AssessmentResponse:
    """
    Main assessment endpoint.

    - route == 'local'    → weighted scoring function returns risk_score + category.
    - route == 'escalate' → stubbed response; Gemini Managed Agent not yet wired.
    """
    t_start = time.perf_counter()

    if req.route == "local":
        risk_score = _compute_risk_score(req)
        risk_category = _categorise(risk_score)
        explanation = _build_local_explanation(req, risk_score, risk_category)

    elif req.route == "escalate":
        # TODO: Replace stub with real Gemini Managed Agent call
        risk_score = None
        risk_category = "pending_review"
        explanation = (
            "Escalated to Managed Agent (not yet implemented). "
            f"Routing reason: {req.routing_reason}"
        )

    else:
        # Pydantic's Literal already guards this, but be defensive
        raise HTTPException(status_code=400, detail=f"Unknown route value: {req.route!r}")

    latency_ms = round((time.perf_counter() - t_start) * 1000, 3)

    return AssessmentResponse(
        risk_score=risk_score,
        risk_category=risk_category,
        explanation=explanation,
        route=req.route,
        routing_reason=req.routing_reason,
        latency_ms=latency_ms,
    )
