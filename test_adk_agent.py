"""
Smoke test: ADK LlmAgent with InMemoryRunner on Sample 5 (revenue spike).
Run this BEFORE modifying main.py.
"""
import os, json, sys
from dotenv import load_dotenv
load_dotenv(".env")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

api_key = os.environ.get("GEMINI_API_KEY", "").strip()
os.environ["GOOGLE_API_KEY"] = api_key   # ADK reads GOOGLE_API_KEY

SYSTEM_PROMPT = """\
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
4. Write a clear, concise explanation (2-4 sentences) of your reasoning.

Return ONLY a JSON object with exactly these keys:
{"risk_score": <number 0-100>, "risk_category": "low"|"medium"|"high", "explanation": "<string>"}
No markdown, no preamble, no extra keys.
"""

USER_MSG = (
    "ESCALATION CASE - BORROWER SESSION: sess_sample5_spike\n\n"
    "Financial data (extracted from sms):\n"
    "  * Daily revenue estimate : INR 21200.00\n"
    "  * Revenue variance       : high\n"
    "  * Payment consistency    : high\n"
    "  * Extraction confidence  : 88%\n"
    "  * Anomaly flags          : revenue_spike\n\n"
    "Routing reason:\n"
    "  Escalated: anomaly detected (revenue_spike)\n\n"
    "Raw extracted text (primary evidence):\n"
    '"""\n'
    "14-07-26 09:00: Received INR 900.00 from Suresh K via UPI Ref 6293080101.\n"
    "14-07-26 11:00: Received INR 18,500.00 from Corporate Corp via UPI Ref 6293080392.\n"
    "14-07-26 15:30: Received INR 1,000.00 from Priya M via UPI Ref 6293080512.\n"
    "14-07-26 19:00: Received INR 800.00 from Ramesh S via UPI Ref 6293080641.\n"
    "Summary: A single massive transaction of INR 18500 occurs, which is ~20x the typical transaction size.\n"
    '"""\n\n'
    "Please analyse and return the JSON risk assessment."
)

print("Creating LlmAgent...", flush=True)
agent = LlmAgent(
    name="setu_credit_risk_analyst",
    model="gemini-3.5-flash",
    instruction=SYSTEM_PROMPT,
    description="Senior credit risk analyst for microfinance escalated cases.",
)

print("Creating InMemoryRunner...", flush=True)
runner = InMemoryRunner(agent=agent, app_name="setu")

# Use the runner's own session_service (sync variant)
print("Creating session (sync)...", flush=True)
session = runner.session_service.create_session_sync(
    app_name="setu", user_id="test_user", session_id="sess_test_001"
)
print(f"Session created: {session.id}", flush=True)

print("Running agent (sync generator)...", flush=True)
final_text = ""
for event in runner.run(
    user_id="test_user",
    session_id=session.id,
    new_message=Content(role="user", parts=[Part(text=USER_MSG)]),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                final_text += part.text

print(f"\n--- Raw ADK agent response ---\n{repr(final_text[:300])}\n", flush=True)

# Parse
import re
text = final_text.strip()
start = text.find("{")
obj, _ = json.JSONDecoder().raw_decode(text, idx=start)
print(f"Parsed JSON:\n{json.dumps(obj, indent=2, ensure_ascii=False)}", flush=True)
print("\nSMOKE TEST PASSED", flush=True)
