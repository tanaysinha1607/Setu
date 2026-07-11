"""
Diagnostic script to inspect the raw JSON output of the ADK vision agent
for all 3 real ledger images.
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

from backend.main import _VISION_AGENT_SYSTEM_PROMPT, _parse_base64_image

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
images = ["Ledger1.jpeg", "Ledger2.jpeg", "Ledger3.jpeg"]

for filename in images:
    filepath = os.path.join(IMAGES_DIR, filename)
    print(f"\n==================================================")
    print(f"RAW ADK CALL FOR {filename}")
    print(f"==================================================")
    
    with open(filepath, "rb") as f:
        img_bytes = f.read()
    
    agent = LlmAgent(
        name="diagnostic_vision",
        model="gemini-3.5-flash",
        instruction=_VISION_AGENT_SYSTEM_PROMPT,
    )
    runner = InMemoryRunner(agent=agent, app_name="setu_diag")
    session = runner.session_service.create_session_sync(
        app_name="setu_diag", user_id="diag", session_id=f"sess_{filename.split('.')[0]}"
    )
    
    parts = [
        Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
        Part(text="Assess the ledger and return the credit risk JSON.")
    ]
    
    final_text = ""
    for event in runner.run(
        user_id="diag",
        session_id=session.id,
        new_message=Content(role="user", parts=parts),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text
                    
    print("Raw Model Response:")
    print(final_text)
    print("-" * 50)
