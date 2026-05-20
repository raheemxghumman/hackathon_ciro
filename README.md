<div align="center">

# ITLA — Crisis Intelligence & Response Orchestrator

### Real-time AI-powered crisis detection, reasoning, and response planning

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Firebase-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)](https://hackathon-496621.web.app)
[![Backend API](https://img.shields.io/badge/Backend%20API-Cloud%20Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://ciro-backend-421829186296.us-central1.run.app)
[![Built with Google ADK](https://img.shields.io/badge/Built%20with-Google%20ADK-34A853?style=for-the-badge&logo=google&logoColor=white)](https://google.github.io/adk-docs/)

</div>

---

## 📚 Table of Contents
- [Project Overview](#-project-overview)
- [Architecture](#-architecture)
- [API Endpoints](#-api-endpoints)
- [External APIs Integrated](#-external-apis-integrated)
- [Program Flow](#-program-flow)
- [Directory Structure](#-directory-structure)
- [Local Development Setup](#-local-development-setup)
- [Deployment](#-deployment)

---

## 🌍 Project Overview
**ITLA (Crisis Intelligence & Response Orchestrator)** is a real-time crisis analysis platform that combines a Flutter client with a FastAPI backend, orchestrated through Google ADK + Gemini 2.5 Flash, with Groq fallback support.

- Repository: [GitHub](https://github.com/AbdulRaheem/ciro_project)
- Live Web App: [https://hackathon-496621.web.app](https://hackathon-496621.web.app)
- Backend API: [https://ciro-backend-421829186296.us-central1.run.app](https://ciro-backend-421829186296.us-central1.run.app)
- Stack: Flutter (mobile + web), FastAPI, Google ADK, Gemini 2.5 Flash, Groq fallback

---

## 🏗️ Architecture
The system has two top-level components:

1. `ciro_backend/` — FastAPI server deployed on Google Cloud Run
2. `ciro_app/` — Flutter app (mobile + web) deployed on Firebase Hosting

### Backend Agents (Google ADK pipeline, 4 stages in sequence)
- **Stage 1 — Ingest Agent**: Receives raw crisis signal text, extracts structured fields (location, crisis_type, severity, timestamp)
- **Stage 2 — Detect Agent**: Classifies severity (low/medium/high/critical), identifies affected population, detects crisis category
- **Stage 3 — Plan Agent**: Generates multi-step response plan with resource allocation, agency coordination, priorities
- **Stage 4 — Execute Agent**: Validates plan feasibility, produces final actionable report with confidence score

### Fallback Behavior
If ADK/Gemini times out (180s), the system falls back to the Groq pipeline (LLaMA 3.3 70B via Groq API) and labels the response accordingly.

---

## 🔌 API Endpoints
- `POST /analyze-adk` — Main crisis analysis, runs 4-agent ADK pipeline
- `GET /incidents` — Latest 5 global incidents from ReliefWeb + GDACS + USGS (merged, deduplicated)
- `GET /signals` — Live signals: weather anomalies, traffic disruptions, seismic activity
- `GET /health` — Health check
- `GET /docs` — Auto-generated Swagger UI

---

## 🌐 External APIs Integrated
- Google ADK (Antigravity) + Gemini 2.5 Flash — orchestrator LLM
- Groq API (LLaMA 3.3 70B) — fallback pipeline, 4 rotating API keys
- WeatherAPI — live weather signal monitoring
- Google Maps API — location enrichment and routing
- ReliefWeb API — global humanitarian crisis feed
- GDACS (Global Disaster Alert and Coordination System) — disaster RSS feed
- USGS Earthquake Hazards API — real-time seismic data

---

## 🔄 Program Flow
```text
User types incident text OR clicks a live incident card
  -> Flutter app POST /analyze-adk
    -> Ingest Agent: parse + structure raw signal
    -> Detect Agent: classify severity + crisis type
    -> Plan Agent: generate multi-step response plan
    -> Execute Agent: validate + produce final report
  -> Response JSON returned with: severity, crisis_type, response_plan,
     confidence, framework (ADK or Groq), adk_trace
  -> Results screen shows: severity badge, framework badge, response plan,
     social signal stats, map location

Live Incidents Feed (sidebar on home screen):
  Auto-refreshes every 5 minutes via Timer.periodic
  Sources: ReliefWeb API + GDACS RSS + USGS Earthquake API
  Merged, deduplicated by (country + crisis_type), sorted by severity then date
  User can click "Generate Report" on any incident -> triggers full 4-agent pipeline
```

---

## 🗂️ Directory Structure
```text
ciro_project/
├── ciro_backend/
│   ├── main.py                  # FastAPI app, all endpoints
│   ├── adk_runner.py            # Google ADK pipeline runner
│   ├── adk_agents.py            # 4 ADK agent definitions
│   ├── groq_pipeline.py         # Groq fallback pipeline
│   ├── tools/
│   │   ├── incidents_tool.py    # ReliefWeb + GDACS + USGS fetcher
│   │   ├── weather_tool.py      # WeatherAPI integration
│   │   └── traffic_tool.py      # Google Maps traffic
│   ├── agents/                  # Agent prompt/config markdown files
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.yaml                # Cloud Run env vars (not committed)
└── ciro_app/
    ├── lib/
    │   ├── main.dart
    │   ├── screens/
    │   │   ├── input_screen.dart    # Home screen + live incidents feed
    │   │   └── results_screen.dart  # Analysis results display
    │   └── services/
    │       └── api_service.dart     # Dio HTTP client, configurable base URL
    ├── pubspec.yaml
    └── firebase.json
```

---

## ⚙️ Local Development Setup
### Backend
```bash
cd ciro_backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
create a .env file with GOOGLE_API_KEY, GROQ_API_KEYS, WEATHERAPI_KEY, GOOGLE_MAPS_KEY

uvicorn main:app --reload --port 8000
```

### Flutter mobile
```bash
cd ciro_app
flutter pub get
flutter run
```

### Flutter web (pointing to Cloud Run backend)
```bash
flutter run -d chrome --dart-define=API_BASE_URL=https://ciro-backend-421829186296.us-central1.run.app
```

---

## 🚀 Deployment
### Backend → Google Cloud Run
```bash
cd ciro_backend
gcloud run deploy ciro-backend --source . --env-vars-file .env.yaml --region us-central1 --allow-unauthenticated
```

### Flutter Web → Firebase Hosting
```bash
cd ciro_app
flutter build web --dart-define=API_BASE_URL=https://ciro-backend-421829186296.us-central1.run.app
firebase deploy
```
