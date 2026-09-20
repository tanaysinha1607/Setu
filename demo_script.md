# Setu — Demo Video Recording Script

This script is designed for a **1-minute, 5-second (65s)** presentation video. Use the timed cue boxes below to coordinate what you display on screen with what you narrate.

---

### ⏱️ Video Timeline At A Glance
```text
0:00 - 0:10 (10s) | Introduction (Hero Page)
0:10 - 0:15 (05s) | Input Modality Selection (SMS, Photo, Voice)
0:15 - 0:35 (20s) | SMS Processing & Core Hybrid AI Architecture
0:35 - 0:45 (10s) | Explaining the Scorecard & Outcome Metrics
0:45 - 0:55 (10s) | Ledger Photo Multimodal Vision Processing
0:55 - 1:05 (10s) | Voice Note & Outro
```

---

### 🎬 Scene 1: Introduction
* **Duration:** 0:00 - 0:10 (10 seconds)
* **Visual on Screen:**
  - Start on the landing page (`http://localhost:5173`).
  - Show the 3D glowing connection bridge animation in the center.
  - Hover your mouse smoothly over the **"Get Started"** button.

> 🎙️ **What to say:**
> *"This is Setu, an adaptive AI routing system designed for microfinance credit underwriting. It bridges the gap for informal-sector borrowers by turning unstructured data into instant, verified credit assessments."*
> *(Click "Get Started" right at the 0:10 mark)*

---

### 🎬 Scene 2: Modality Selection
* **Duration:** 0:10 - 0:15 (5 seconds)
* **Visual on Screen:**
  - The screen transitions to the input selector.
  - Wave your mouse pointer over the three cards: **SMS Text Logs**, **Ledger Photo**, and **Voice Note**.

> 🎙️ **What to say:**
> *"Our platform accommodates field realities with three distinct entry paths: SMS history, handwritten ledger photos, and spoken voice recordings."*
> *(Click "SMS Text Logs" at 0:15)*

---

### 🎬 Scene 3: SMS Upload & Processing
* **Duration:** 0:15 - 0:35 (20 seconds)
* **Visual on Screen:**
  - Select **"Sample 5 — Anomalous Spike"** from the sample buttons.
  - Click **"Run Gemma Extraction"**.
  - The screen switches to the 3D connection bridge, showing the packet traveling along the routing track (simulating processing).

> 🎙️ **What to say:**
> *"I'll upload SMS transaction history. While it processes, here is how Setu works: a local, lightweight Gemma 4 E4B model runs entirely on the field officer's edge device to extract metrics. If it detects risk anomalies or low confidence, it seamlessly escalates the raw data to cloud-hosted Gemini models."*
> *(Wait for the screen to transition to the result scorecard)*

---

### 🎬 Scene 4: Explaining the Scorecard
* **Duration:** 0:35 - 0:45 (10 seconds)
* **Visual on Screen:**
  - Point to the radial gauge displaying the **Risk Score (e.g., 30)** and the **High Risk** badge.
  - Point to the bottom row showing **Route (CLOUD)**, **Confidence (35%)**, and the lists of **Flags (revenue spike, insufficient data)**.

> 🎙️ **What to say:**
> *"The extraction results display immediately. The system flagged an unexplained ₹18,500 corporate payment, resulting in a conservative credit score of 30, routed through the cloud with full explanations."*
> *(Click "Run Another Case" at 0:45)*

---

### 🎬 Scene 5: Ledger Vision Processing
* **Duration:** 0:45 - 0:55 (10 seconds)
* **Visual on Screen:**
  - Click the **"Ledger Photo"** card.
  - Click the **"Hariom Traders"** sample button.
  - Click **"Escalate to Cloud Vision"**.
  - As the 3D loader pulses, speak the narration.

> 🎙️ **What to say:**
> *"Next, we'll process handwritten daybooks. Because edge models lack vision, Setu routes these images directly to a Gemini Multimodal Vision Agent to digitize, verify entries, and check for layout fabrications."*

---

### 🎬 Scene 6: Voice Note & Outro
* **Duration:** 0:55 - 1:05 (10 seconds)
* **Visual on Screen:**
  - Click **"Run Another Case"**, then click **"Voice Note"** to show the mic/record layout.
  - Point to the **Record** and **Upload** buttons.
  - Hover over your logo or signature line.

> 🎙️ **What to say:**
> *"Similarly, verbal income declarations can be recorded locally using the microphone. Setu transcribes, evaluates risk, and builds a comprehensive credit picture. Empowering microfinance, one connection at a time."*

---

### 💡 Tips for Recording:
1. **Resolution:** Record at `1920x1080` (Full HD).
2. **Backend Console:** Keep the FastAPI terminal running in the background to ensure real-time API responses load instantly during the visual segments.
3. **Sound:** Speak clearly, keeping a steady pace that matches the mouse clicks.
