"""
Multimodal smoke test for ADK LlmAgent.
Creates a small dummy image, encodes it, and sends it to ADK agent to see if it responds.
"""
import os, json, sys, base64
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
os.environ["GOOGLE_API_KEY"] = api_key

# 1. Create a tiny 1x1 black PNG bytes
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
img_bytes = base64.b64decode(TINY_PNG_B64)

SYSTEM_PROMPT = "You are a helpful assistant. Describe what you see in the provided image."

agent = LlmAgent(
    name="test_multimodal",
    model="gemini-3.5-flash",
    instruction=SYSTEM_PROMPT,
)

runner = InMemoryRunner(agent=agent, app_name="setu_test")
session = runner.session_service.create_session_sync(
    app_name="setu_test", user_id="test", session_id="test_sess"
)

parts = [
    Part.from_bytes(data=img_bytes, mime_type="image/png"),
    Part(text="Is this image a solid black pixel?")
]

print("Running multimodal agent call...", flush=True)
final_text = ""
try:
    for event in runner.run(
        user_id="test",
        session_id=session.id,
        new_message=Content(role="user", parts=parts),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text
    print(f"SUCCESS: {final_text}")
except Exception as e:
    print(f"FAILED: {e}")
