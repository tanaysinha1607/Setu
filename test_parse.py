"""Test that _parse_gemini_json works with the trailing brace."""
import re, json

def _parse_gemini_json(text: str) -> dict:
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1)
    brace_match = re.search(r"\{[\s\S]+\}", text)
    if brace_match:
        text = brace_match.group(0)
    return json.loads(text.strip())

# Simulate the raw response.text we saw
raw = '{\n  "risk_score": 65,\n  "risk_category": "medium",\n  "explanation": "test explanation"\n}\n}'

try:
    result = _parse_gemini_json(raw)
    print(f"SUCCESS: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"FAILED: {e}")
    
# Also test what response.text returns for a truncated case
raw2 = '{\n  "risk_'
try:
    result2 = _parse_gemini_json(raw2)
    print(f"Truncated result: {result2}")
except Exception as e:
    print(f"Truncated parse failed (expected): {e}")
