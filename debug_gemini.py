"""Debug what the server actually sees from response.text"""
import os, json, sys
from dotenv import load_dotenv
load_dotenv('.env')

import google.genai as genai
from google.genai import types as genai_types

key = os.environ.get('GEMINI_API_KEY', '').strip()
client = genai.Client(api_key=key)

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
{
  "risk_score": <number 0-100>,
  "risk_category": "low" | "medium" | "high",
  "explanation": "<string>"
}
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
    "Routing reason (why local model could not score this):\n"
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

print("Making API call...", flush=True)
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=USER_MSG,
    config=genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
        max_output_tokens=1024,
        response_mime_type="application/json",
    ),
)

print(f"type(response.text) = {type(response.text)}", flush=True)
print(f"len(response.text) = {len(response.text) if response.text else 'None'}", flush=True)
print(f"response.text bytes = {response.text.encode('utf-8')[:100] if response.text else 'None'}", flush=True)
print(f"response.text repr = {repr(response.text[:200]) if response.text else 'None'}", flush=True)

# Now try _parse_gemini_json logic
import re
text = response.text or ""
text = text.strip()
start = text.find("{")
print(f"\nstart idx = {start}", flush=True)
if start >= 0:
    print(f"char at start = {repr(text[start:start+5])}", flush=True)
    try:
        obj, end = json.JSONDecoder().raw_decode(text, idx=start)
        print(f"SUCCESS: parsed={json.dumps(obj, indent=2)}", flush=True)
    except json.JSONDecodeError as e:
        print(f"raw_decode failed: {e}", flush=True)
        print(f"Context around error: {repr(text[max(0, e.pos-5):e.pos+20])}", flush=True)
