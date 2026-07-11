# Setu Project Rules & Guidelines

## Hackathon Mode
- **Time Pressure**: Real-time 13-hour build window for the Google DeepMind Bangalore Hackathon on July 11, 2026.
- **Decision Priority**: Default to whichever technical option is fastest to implement and most reliable. Avoid over-engineering.
- **Fail Fast & Communicate**: If an approach fails or takes too long, stop immediately and present the issue/options to the user rather than iterating silently on alternative approaches.

## System Architecture
- **Setu**: Adaptive AI routing system for microfinance credit risk assessment.
- **Local Layer**: Local Gemma 4 E4B model for structured extraction from messy inputs (SMS, ledger, voice).
- **Escalation**: local confidence/anomaly scoring -> if low confidence or anomaly found, escalate case to cloud-hosted Managed Agent (Gemini).
- **Voice / Interactivity**: Gemini Live API for spoken Q&A by field officers.
