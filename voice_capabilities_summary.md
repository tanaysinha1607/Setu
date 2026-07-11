# Setu: Voice QA and Voice Note Extraction Documentation

This document provides a detailed summary of the two voice-oriented capabilities implemented in Setu:
1. **Voice QA Layer** (`voice_qa.py`): The standalone real-time audio interaction prototype using the Gemini Live API.
2. **Voice Note Extraction Layer** (`voice_note_input.py` / `pipeline.py` / `backend` integration): The asynchronous audio risk assessment pipeline.

---

## 1. Voice QA Layer (`voice_qa.py`)

The **Voice QA Layer** is a standalone conversational prototype that allows a field officer to ask spoken questions about a borrower and receive immediate, low-latency spoken responses. 

### Architecture & Grounding
- **Engine**: Powered by the **Gemini Live API** (`gemini-2.0-flash-exp` or similar Live API-supported models via the `google-genai` SDK).
- **Grounding Context**: Hardcoded with verified data for **Ramesh** (Sample 1: vegetable cart vendor, risk score 68, daily revenue estimate ₹3,900, low variance, high consistency, routed LOCAL).
- **System Instruction**: Explicitly instructs the model to act as a supportive, professional credit coach for field officers. It strictly bounds the model's knowledge to the provided borrower details to prevent hallucinating financials.

### Key Features
- **Bi-directional Live Session**: Supports real-time text-to-speech, speech-to-text, and speech-to-speech.
- **Push-to-Talk Recording**: Uses `pyaudio` and `wave` to record audio input locally, saving it to `input.wav` before passing it to the session.
- **Output Transcription**: Automatically prints the spoken response transcription in the terminal.

---

## 2. Voice Note Extraction Layer

The **Voice Note Extraction Layer** is a structured assessment modality. When a borrower describes their income in a voice note, the app transcribes and parses the audio to extract financial metrics, aligning with the core credit assessment schema.

### Architecture Flow
1. **Pipeline Stage** (`pipeline.py`):
   - Reads the local audio file (supports `.wav`, `.mp3`, `.ogg`, `.m4a`, etc.).
   - Converts the audio to a base64 Data URL matching the MIME type (`data:audio/wav;base64,...`).
   - Packages the metadata with placeholders for financial metrics and sets `route="escalate"` (since local Gemma has no audio capability).
2. **Backend Assessment Stage** (`backend/main.py`):
   - Accepts the request with the `audio_data_base64` field.
   - Invokes the `google-adk` **Audio LlmAgent** (`setu_audio_voice_analyst`).
   - Grounded by `_AUDIO_AGENT_SYSTEM_PROMPT` to extract daily/weekly income, evaluate variance, determine consistency, and check for coached or conflicting verbal cues.
   - Temperature is pinned at `0.2` and explicit JSON instructions are parsed robustly to prevent truncation/parsing errors.
   - **Fallback Guard**: If no audio base64 is present or the API call fails, it gracefully falls back to a `pending_review` category with a clean explanation.

---

## 3. How to Test

### Setup Prerequisites
Ensure your `.env` contains your Gemini credentials:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### A. Testing the Voice QA Layer
Run the interactive console session:
```powershell
python voice_qa.py
```
*Follow the on-screen prompts to type questions (e.g., "Why is this borrower low risk?") or record voice inputs using the push-to-talk loop.*

### B. Testing the Voice Note Extraction Layer
1. Start the FastAPI backend:
   ```powershell
   python -m uvicorn backend.main:app --port 8000
   ```
2. Create an `audio` directory in your project root and add a sample voice note (e.g. `sample.wav`).
3. Run the E2E verification script:
   ```powershell
   python test_voice_note.py
   ```
   Or run it against a specific file:
   ```powershell
   python test_voice_note.py audio/my_voice_recording.mp3
   ```
