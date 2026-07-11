#!/usr/bin/env python3
"""
voice_qa.py — Standalone Python Prototype for Voice-Based Credit Risk Q&A
Demonstrates real-time voice exchange with Gemini Live API using google-genai SDK.
Grounded strictly in the assessment facts of Ramesh (Sample 1).
"""

import os
import sys
import time
import asyncio
import warnings
from dotenv import load_dotenv

# Filter warning messages from clean terminal output
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Setup colors for rich terminal output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Grounding System Instructions for Ramesh (Sample 1)
RAMESH_FACTS = """\
You are a credit assessment assistant speaking to a microfinance field officer.
You are helping the officer understand the automated credit risk assessment results for the borrower named Ramesh.

Ramesh's credit assessment details:
- Borrower Name: Ramesh
- Occupation: Vegetable cart vendor (Sample 1)
- Risk Score: 68 out of 100 (Higher score means more creditworthy / lower risk)
- Risk Category: low
- Daily Revenue Estimate: Rs. 3,900
- Revenue Variance: low (stable income)
- Payment Consistency: high (pays regularly)
- Extraction Confidence: 98% (0.98)
- Anomaly Flags: None
- Routing: Routed to the LOCAL scoring model (not escalated to cloud agents because it was high-confidence and low-variance)

Your instructions:
1. Speak in a clear, professional, and friendly tone as a senior credit assistant.
2. Rely ONLY on the borrower facts provided above. Do not invent any numbers, transactions, dates, names, or other details.
3. If asked something that is not in the data (e.g. Ramesh's age, number of children, specific location, or what vegetables he sells), say honestly: "I don't have that information in my records."
4. Keep your responses relatively short and direct (1-3 sentences), as they will be spoken aloud to the officer.
"""

def print_header():
    print("=" * 65)
    print(f"{BOLD}{GREEN}            SETU - VOICE CREDIT ASSISTANT PROTOTYPE{RESET}")
    print("=" * 65)
    print("Grounding context: Ramesh (Vegetable Vendor, Sample 1)")
    print("Facts loaded: Risk Score 68 (Low), Revenue Rs. 3,900/day, Local Route")
    print("-" * 65)


async def main():
    print_header()

    # Load and verify API Key
    api_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", "")).strip()
    if not api_key:
        print(f"{RED}Error: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment.{RESET}")
        print("Please configure it in your .env file or environment.")
        sys.exit(1)

    # Force google-genai to use the detected key
    os.environ["GEMINI_API_KEY"] = api_key

    # Import google-genai inside main to handle missing package cleanly
    try:
        from google.genai import Client
        from google.genai.types import LiveConnectConfig, Modality, AudioTranscriptionConfig
        from google.genai.errors import APIError
    except ImportError as e:
        print(f"{RED}Error: google-genai SDK not found.{RESET}")
        print("Please install it in your virtualenv: pip install google-genai")
        sys.exit(1)

    # Detect and check audio devices
    audio_available = False
    try:
        import sounddevice as sd
        import numpy as np
        # Quick query to check default devices
        sd.query_devices(kind='input')
        sd.query_devices(kind='output')
        audio_available = True
        print(f"{GREEN}✓ Audio Hardware detected (Microphone and Speakers available).{RESET}")
    except Exception as e:
        print(f"{YELLOW}⚠ Audio Hardware initialization failed: {e}{RESET}")
        print("Available audio devices:")
        try:
            import sounddevice as sd
            print(sd.query_devices())
        except Exception:
            print("  (sounddevice query failed)")
        print(f"\n{BOLD}{YELLOW}Defaulting to text-only Q&A fallback.{RESET}\n")

    # Connect to the Live API with fallback
    client = Client()
    config = LiveConnectConfig(
        response_modalities=[Modality.AUDIO] if audio_available else [Modality.TEXT],
        system_instruction=RAMESH_FACTS,
    )

    models = ["gemini-live-2.5-flash-native-audio", "gemini-3.1-flash-live-preview"]
    session = None
    connected_model = None

    for model in models:
        try:
            # client.aio.live.connect returns an async context manager
            ctx = client.aio.live.connect(model=model, config=config)
            session = await ctx.__aenter__()
            connected_model = model
            print(f"{GREEN}✓ Connected to Gemini Live API via: {model}{RESET}\n")
            break
        except Exception as e:
            # Clean single-line print as requested
            print(f"{YELLOW}Voice layer unavailable on {model}: {str(e).splitlines()[0]}{RESET}")

    if not session:
        print(f"\n{RED}Voice layer unavailable: All Live models failed to connect.{RESET}")
        print(f"{BOLD}Falling back to text Q&A demo.{RESET}\n")
        # Run text fallback loop
        await run_text_fallback_loop(client)
        return

    try:
        if audio_available:
            await run_voice_loop(session, sd, np)
        else:
            await run_text_loop_with_live_session(session)
    finally:
        # Exit context manager cleanly
        await ctx.__aexit__(None, None, None)


async def run_voice_loop(session, sd, np):
    print("=" * 65)
    print(f"{BOLD}VOICE SESSION ACTIVE{RESET}")
    print("Instructions:")
    print("  1. Press Enter (without typing) to speak a question (records for 5s).")
    print("  2. OR type your question directly and press Enter (text mode).")
    print("  3. Type 'quit' and press Enter to exit cleanly.")
    print("=" * 65 + "\n")

    sample_rate = 16000  # 16kHz mono
    duration = 5.0       # 5 seconds recording limit

    while True:
        try:
            # Hybrid text/voice prompt
            prompt_str = f"{BOLD}Type question OR press Enter to record (or 'quit'): {RESET}"
            cmd = await asyncio.to_thread(input, prompt_str)
            cmd = cmd.strip()
            
            if not cmd:
                # User pressed Enter without typing -> Record Audio
                print(f"{YELLOW}Recording... Speak now ({duration}s limit)...{RESET}")
                recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
                
                # Show a simple countdown in console
                for sec in range(int(duration), 0, -1):
                    sys.stdout.write(f"\r  [{sec}s left] Recording...")
                    sys.stdout.flush()
                    await asyncio.sleep(1)
                sd.wait()
                sys.stdout.write("\r  Recording complete! Processing...\n")
                sys.stdout.flush()

                # Convert numpy recording to raw PCM bytes
                pcm_bytes = recording.tobytes()

                # Send audio payload to Gemini Live Session
                await session.send(input={"data": pcm_bytes, "mime_type": "audio/pcm;rate=16000"}, end_of_turn=True)
            
            elif cmd.lower() == "quit":
                print("Exiting voice session...")
                break
                
            else:
                # User typed a question -> Send Text
                print(f"{BLUE}Sending question as text...{RESET}")
                await session.send(input=cmd, end_of_turn=True)

            print(f"\n{BOLD}{BLUE}[Gemini Live Response]{RESET}")
            audio_chunks = []
            
            # Receive and play response stream
            async for response in session.receive():
                if response.server_content:
                    content = response.server_content
                    
                    # Print text transcription in real time
                    if content.output_transcription and content.output_transcription.text:
                        sys.stdout.write(f"{GREEN}{content.output_transcription.text}{RESET}")
                        sys.stdout.flush()
                    
                    # Collect audio parts
                    if content.model_turn:
                        for part in content.model_turn.parts:
                            if part.inline_data:
                                # Convert inline PCM data to numpy array
                                chunk_arr = np.frombuffer(part.inline_data.data, dtype=np.int16)
                                audio_chunks.append(chunk_arr)
                    
                    # Play back aggregated audio once the turn finishes to avoid stuttering
                    if content.turn_complete:
                        sys.stdout.write("\n\n")
                        sys.stdout.flush()
                        
                        if audio_chunks:
                            full_audio = np.concatenate(audio_chunks)
                            # Gemini Live outputs 24kHz mono PCM audio
                            sd.play(full_audio, samplerate=24000)
                            sd.wait()  # Wait for playback to complete before next input
                        
                        break  # Break out of receive loop for this turn
        except Exception as e:
            print(f"\n{RED}Error during exchange: {e}{RESET}")
            print("Let's try again...\n")


async def run_text_loop_with_live_session(session):
    print("=" * 65)
    print(f"{BOLD}TEXT-ONLY MODE (LIVE SESSION){RESET}")
    print("Type your questions below. Type 'quit' to exit.")
    print("=" * 65 + "\n")

    while True:
        try:
            question = await asyncio.to_thread(input, f"\n{BOLD}Ask Ramesh's Credit Assistant: {RESET}")
            question = question.strip()
            if not question:
                continue
            if question.lower() == "quit":
                break

            await session.send(input=question, end_of_turn=True)
            print(f"\n{BOLD}{BLUE}[Assistant Response]{RESET}")

            async for response in session.receive():
                if response.server_content:
                    content = response.server_content
                    if content.output_transcription and content.output_transcription.text:
                        sys.stdout.write(f"{GREEN}{content.output_transcription.text}{RESET}")
                        sys.stdout.flush()
                    
                    if content.turn_complete:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        break
        except Exception as e:
            print(f"\n{RED}Error: {e}{RESET}")


async def run_text_fallback_loop(client):
    """Fallback text loop using simple generate_content in case Live API connection fails entirely"""
    print("=" * 65)
    print(f"{BOLD}TEXT FALLBACK DEMO ACTIVE{RESET}")
    print("Type your questions below. Type 'quit' to exit.")
    print("=" * 65 + "\n")

    while True:
        question = await asyncio.to_thread(input, f"\n{BOLD}Ask Ramesh's Credit Assistant: {RESET}")
        question = question.strip()
        if not question:
            continue
        if question.lower() == "quit":
            break

        try:
            # Simple content generation using gemini-2.5-flash or gemini-1.5-flash
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=question,
                config={"system_instruction": RAMESH_FACTS}
            )
            print(f"\n{BOLD}{BLUE}[Assistant Response]{RESET}")
            print(f"{GREEN}{response.text}{RESET}")
        except Exception as e:
            print(f"{RED}Fallback failed: {e}{RESET}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting cleanly...")
        sys.exit(0)
