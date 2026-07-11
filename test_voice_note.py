"""
test_voice_note.py  —  E2E voice note pipeline test for Setu
-------------------------------------------------------------
Usage:
    python test_voice_note.py                          # uses audio files in ./audio/ folder
    python test_voice_note.py path/to/sample.wav       # single file override

Requires:
    - Backend running: python -m uvicorn backend.main:app --port 8000
    - GEMINI_API_KEY set in .env
"""
import sys
import os
import json
import glob
from pipeline import process_voice_note_input, call_backend

def run_voice_test(audio_path: str, session_id: str):
    print(f"\n{'='*55}")
    print(f"  VOICE NOTE: {os.path.basename(audio_path)}")
    print(f"{'='*55}")

    # Step 1 — pipeline encodes audio, sets route=escalate
    payload = process_voice_note_input(audio_path, session_id)

    # Show payload shape (truncate base64 for readability)
    display = dict(payload)
    if "audio_data_base64" in display and display["audio_data_base64"]:
        b64_len = len(display["audio_data_base64"])
        display["audio_data_base64"] = f"<{b64_len} chars — truncated>"
    print("\n1. Pipeline Payload:")
    print(json.dumps(display, indent=2))

    # Step 2 — post to backend
    print("\n2. Backend Assessment Response:")
    result = call_backend(payload)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Collect audio files to test
    if len(sys.argv) > 1:
        audio_files = [sys.argv[1]]
    else:
        # Look in ./audio/ folder for any common audio formats
        audio_dir = os.path.join(os.path.dirname(__file__), "audio")
        patterns = ["*.wav", "*.mp3", "*.ogg", "*.m4a", "*.flac", "*.webm"]
        audio_files = []
        for pat in patterns:
            audio_files.extend(glob.glob(os.path.join(audio_dir, pat)))
        audio_files.sort()

    if not audio_files:
        print("[ERROR] No audio files found.")
        print("  Place .wav/.mp3/.ogg/.m4a files in ./audio/ folder, or pass a path as argument.")
        sys.exit(1)

    print(f"\nFound {len(audio_files)} audio file(s) to test.")

    results = []
    for idx, af in enumerate(audio_files, 1):
        session_id = f"voice_test_session_{idx:03d}"
        try:
            r = run_voice_test(af, session_id)
            results.append({"file": os.path.basename(af), "result": r})
        except ConnectionError:
            print("\n[FATAL] Backend is offline — start it with:")
            print("    python -m uvicorn backend.main:app --port 8000")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            results.append({"file": os.path.basename(af), "error": str(e)})

    print(f"\n{'='*55}")
    print(f"  SUMMARY  ({len(results)} files tested)")
    print(f"{'='*55}")
    for r in results:
        if "error" in r:
            print(f"  {r['file']:<30}  ERROR: {r['error']}")
        else:
            res = r["result"]
            score_str = f"{res.get('risk_score', 'N/A')}"
            cat_str   = res.get("risk_category", "?").upper()
            print(f"  {r['file']:<30}  score={score_str:>6}  category={cat_str}")
