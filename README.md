# Setu: Adaptive ML Routing for Credit Risk Assessment

An adaptive routing layer between Gemma and Gemini — reasons on-device by default, escalates to the cloud only when the model isn't confident. Demoed on rural credit decisioning for India's credit-invisible borrowers (SMS + handwritten ledgers), built for the Google DeepMind Bangalore Hackathon.

---

## 🌟 Key Features
- **On-Device First (Gemma 4 E4B):** Runs light ML extraction and credit assessment locally.
- **Dynamic Cloud Escalation (Gemini):** Automatically routes to cloud-hosted Gemini model if confidence falls below threshold (< 0.70) or anomalies are detected.
- **Multimodal Support:** Decodes SMS text, handles handwritten ledger daybook images, and processes field voice notes.
- **Premium Live Dashboard:** Visualizes routing path animations (Teal/Gemma vs. Gold/Gemini) with real-time millisecond latency counters.

---

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python), Google ADK (Agent Development Kit), Gemini API
- **Frontend:** React 18, Vite, TailwindCSS v4, Framer Motion, React Three Fiber (Three.js)

---

## 🚀 Getting Started

### 1. Run the Backend API
```bash
python -m uvicorn backend.main:app --port 8000
```
API docs will be available at `http://localhost:8000/docs`.

### 2. Run the Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173/` in your browser.
