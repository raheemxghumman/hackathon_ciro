# CIRO — Crisis Intelligence & Response Orchestrator

> Multi-agent crisis-response system for Islamabad, orchestrated through **Google Antigravity**, powered by **Groq LLaMA-3.3-70B**, and integrated with **Google Maps**, **WeatherAPI**, and a polished **Flutter** mobile experience.

CIRO ingests noisy multi-source signals (citizen reports in Urdu / Roman Urdu / English, live weather, simulated traffic, social-media chatter), detects emerging crises, generates a coordinated response plan, and simulates execution with realistic tickets, citizen alerts and before/after impact — all within a single end-to-end agentic workflow.

---

## ✦ The challenge

Metropolitan cities — Islamabad in particular — face frequent localized crises (flash floods, road accidents, heatwaves, infrastructure failures, security incidents). Response systems are **fragmented, reactive, and slow to coordinate**. Critical signals already exist across social media, maps, weather and citizen reports, but are not converted into actionable decisions in real time.

CIRO is the missing layer: an agentic AI that converts those signals into coordinated action within seconds.

---

## ✦ Demo flow

1. A citizen reports a crisis in any language: *"G-10 mein pani bhar gaya hai, gaariyan phans gayi hain"*
2. **Ingest agent** parses the report, pulls live weather + simulated traffic + social signals, and structures the situation.
3. **Detect agent** classifies the crisis type, severity, and explains its reasoning.
4. **Plan agent** generates a coordinated response — calling out specific agencies (Islamabad Police, Rescue 1122, NDMA, etc.) — and queries the Google Maps Directions API for live route alternatives.
5. **Execute agent** simulates the response: tickets created across agencies, citizen alerts broadcast, before/after impact computed.
6. The mobile app renders a complete **incident report** with a visual Google Static Map, route polylines, ranked alternates, system logs and an archivable share flow.

---

## ✦ Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                     GOOGLE ANTIGRAVITY                             │
│                Multi-Agent Workflow Orchestrator                   │
│   (planning, prompt iteration, agent contracts, run traces)        │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                  ciro_backend/orchestrator.py                      │
│         run_pipeline(text) → JSONL trace per agent step            │
└────────────────────────────────────────────────────────────────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
┌────────┐    ┌────────┐    ┌────────┐    ┌────────────┐
│ Ingest │──▶ │ Detect │──▶ │  Plan  │──▶ │  Execute   │
│ Agent  │    │ Agent  │    │ Agent  │    │   Agent    │
└────┬───┘    └────────┘    └───┬────┘    └────────────┘
     │                          │
     │                          │   ┌─────────────────┐
     │                          ├──▶│  Google Maps    │
     │                          │   │  Directions +   │
     │                          │   │  Static Maps    │
     │                          │   └─────────────────┘
     │
     │   ┌───────────────┐
     ├──▶│  WeatherAPI   │   live conditions
     │   └───────────────┘
     │
     │   ┌───────────────┐
     ├──▶│  Traffic mock │   ambient context
     │   └───────────────┘
     │
     │   ┌───────────────┐
     └──▶│  Social mock  │   amplification signal
         └───────────────┘

           ▲
           │ HTTP /analyze, /signals
           │
┌──────────┴───────────────────────────────────────────────────────┐
│                  ciro_app/ (Flutter, iOS / Android)              │
│  Input → Trace → Results → History (SharedPreferences archive)   │
└──────────────────────────────────────────────────────────────────┘
```

Every `/analyze` request produces a structured JSONL run-trace under `ciro_backend/logs/run_<timestamp>.jsonl` — one line per agent step, including tools called, duration, and a compact input/output summary.

---

## ✦ Google Antigravity usage

The 25%-weighted Antigravity deliverable is satisfied at **two layers**:

1. **Authoring orchestration** — every agent contract, prompt, and integration in this repo was planned and iterated through Antigravity's Agent Manager in Plan mode (Gemini 3.1 Pro High). The session conversations are preserved as screenshots in `ciro_backend/antigravity_traces/` covering:
   - Building the CIRO Crisis System
   - Reviewing Crisis Signal Ingestion
   - Analyzing Crisis Detection Logic
   - Documenting Agent Response Planning
   - Documenting Agent Action Execution
   - Verifying the end-to-end pipeline

2. **Runtime orchestration** — declarative agent specs live in `ciro_backend/agents/*.md` (one file per agent: role, IO schema, tools, upstream/downstream wiring, reasoning contract). The `orchestrator.py` runner loads these specs, sequences the four agents with explicit handoff, and writes a JSONL trace that mirrors how Antigravity itself logs multi-step agent workflows.

A judge can reproduce a full end-to-end run with a single command:

```bash
python orchestrator.py "G-10 mein pani bhar gaya hai gaariyan phans gayi hain"
```

…and inspect the trace in `logs/run_<timestamp>.jsonl`.

---

## ✦ Agents & responsibilities

| Agent | Role | Inputs | Outputs | Tools |
|---|---|---|---|---|
| **Ingest** | Parse the noisy multi-source signal soup | citizen text + weather + traffic + social | event_type, location, urgency, language, cleaned summary | WeatherAPI, traffic mock, social mock |
| **Detect** | Classify the crisis | structured ingestion | crisis_type, severity, confidence, **reasoning**, impact analysis | — |
| **Plan** | Generate coordinated response | detection | overall_strategy, ranked actions, agency assignments, public advisory | **Google Maps Directions** |
| **Execute** | Simulate the response | plan | before/after state, execution log (ticket IDs + citizen SMS bodies), simulation summary | — |

The pipeline supports the full crisis taxonomy: `flooding · accident · heatwave · infrastructure · hazmat · crime · medical · fire · civil_unrest · utility_outage`. Each event type routes to the appropriate agency set (Islamabad Police via Emergency 15, Rescue 1122, Fire Brigade Emergency 16, Edhi Ambulance, NDMA, CDA / WASA, Islamabad Traffic Police, Bomb Disposal Squad).

---

## ✦ Tools & APIs integrated

| Tool / API | Role | Live? |
|---|---|---|
| **Google Antigravity** (Gemini 3.1 Pro High, Plan mode) | Multi-agent workflow design & orchestration | ✅ |
| **Google Maps Directions API** | Real-time alternate route generation | ✅ |
| **Google Maps Static Maps API** | Map preview with route polylines drawn on the mobile report | ✅ |
| **Groq LLaMA-3.3-70B-versatile** | All agent reasoning (4 sequential calls per crisis) | ✅ |
| **WeatherAPI.com** | Live weather conditions for Islamabad | ✅ |
| Traffic API mock | Ambient congestion / blocked-road context | simulated |
| Social-media mock | Amplification & sentiment signal | simulated |

Multi-key rotation is built in for Groq — when a key hits its rate limit, `crisis_agents.call_llm` rotates to the next available key transparently.

---

## ✦ Mobile app

The Flutter app (`ciro_app/`) is a polished mobile-first experience:

- **Input screen** — quick-pick scenarios in Urdu / Roman Urdu / English, live weather + traffic chips, history list, "Powered by Antigravity · Google Maps · WeatherAPI" credibility footer
- **Trace screen** — animated vertical timeline of the four agents as they execute, with a dark "system log" panel showing real reasoning extracts
- **Results screen** — severity-stripe crisis header, custom-painted confidence ring, **agent reasoning** card, corroborating signals card, dispatched actions with priority stripes, **Google Maps panel** with static-map preview + ranked alternates, before/after metrics derived from real signals, dark execution-log terminal with ticket-ID chips + citizen-SMS quote boxes, strategy card with public advisory
- **History screen** — `SharedPreferences`-persisted archive of every report, capped at 50, tap to re-open

---

## ✦ Project structure

```
ciro_project/
├── ciro_backend/
│   ├── agents/                     ← declarative agent contracts (.md)
│   ├── antigravity_traces/         ← Agent Manager session screenshots
│   ├── tools/
│   │   ├── maps_tool.py            ← Google Maps Directions + Static Maps
│   │   └── search_tool.py          ← grounded context fallback
│   ├── crisis_agents.py            ← 4 agent functions + call_llm
│   ├── orchestrator.py             ← multi-agent runner + JSONL traces
│   ├── mock_signals.py             ← live WeatherAPI + traffic / social mocks
│   ├── main.py                     ← FastAPI app: /analyze, /signals, /health
│   ├── WORKFLOW.md                 ← architecture & orchestration narrative
│   ├── .env.example                ← copy → .env and fill in keys
│   └── requirements.txt
└── ciro_app/
    └── lib/
        ├── screens/                ← input, trace, results, history
        ├── services/               ← api_service, history_service
        ├── theme.dart              ← CiroColors, CiroType, Pill, SectionLabel
        └── main.dart
```

---

## ✦ Running locally

### Backend

```bash
cd ciro_backend
python -m venv venv
source venv/bin/activate            # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cp .env.example .env                # then fill in the keys (see below)
uvicorn main:app --reload
```

The API is then live at `http://localhost:8000` with three endpoints:
- `POST /analyze` — body: `{"text": "..."}` → full pipeline output
- `GET /signals` — live weather + traffic snapshot
- `GET /health` — liveness probe

### API keys

Copy `ciro_backend/.env.example` to `.env` and fill in:

| Variable | Where to get it | Required? |
|---|---|---|
| `GROQ_API_KEYS` | [console.groq.com/keys](https://console.groq.com/keys) — free, comma-separated for rotation | **yes** |
| `WEATHERAPI_KEY` | [weatherapi.com/signup.aspx](https://www.weatherapi.com/signup.aspx) — free tier | optional (mock fallback) |
| `GOOGLE_MAPS_KEY` | [console.cloud.google.com](https://console.cloud.google.com/) → enable **Directions API** + **Maps Static API**, then create credential | optional (mock fallback) |

Only `GROQ_API_KEYS` is strictly required; both Google Maps and WeatherAPI gracefully fall back to realistic mocks when their keys are absent.

### Mobile app

```bash
cd ciro_app
flutter pub get
flutter run                         # connects to http://localhost:8000 by default
```

For iOS, point `flutter run -d <simulator-udid>` at a booted simulator (e.g. iPhone 17).

### Running a one-shot agent trace from the CLI

```bash
cd ciro_backend
python orchestrator.py "Flash flood at G-10 Markaz, gaariyan phans gayi hain"
```

This prints a multi-agent trace to stdout and writes the same trace as JSONL to `logs/run_<timestamp>.jsonl`.

---

## ✦ Assumptions

- **Single city scope.** All location parsing, agency assignment, and routing is tuned for Islamabad sectors (G-10, F-7, E-11, Blue Area, Kashmir Highway, etc.). Extending to other cities would mean swapping the agency directory and seeding the ingest prompt with the relevant geography.
- **Traffic + social signals are simulated.** Real APIs (Google Maps Traffic, Twitter/X firehose) require commercial agreements and exceed hackathon scope, so we expose stable mock endpoints that produce structurally realistic signals.
- **Mobile-only client.** The web client is optional per the challenge brief and was descoped in favor of a polished mobile experience.
- **Simulation, not dispatch.** No real emergency agency is contacted — every "dispatch" is a labeled mock that prints to the execution log. The system is designed to slot behind a future real-dispatch adapter without changing the agent contracts.
- **Demo language.** English / Urdu / Roman Urdu citizen reports are first-class; other Pakistani languages would require minor prompt extension.

---

## ✦ How the rubric is satisfied

| Criterion | Weight | Where it's demonstrated |
|---|---:|---|
| **Use of Google Antigravity** | 25% | `ciro_backend/agents/`, `orchestrator.py`, `antigravity_traces/`, `WORKFLOW.md` |
| **Agentic reasoning & coordination** | 20% | 4-agent pipeline with explicit `reasoning` field on the detect agent; results screen surfaces it verbatim |
| **Situation detection & analysis** | 20% | Multi-source synthesis in `ingest_signal`, severity classifier with confidence + reasoning, impact analysis tied to event type |
| **Action planning & simulation** | 15% | Agency directory, action types per crisis class, ticket IDs, citizen SMS, before/after derived from real signals, live Google Maps routing |
| **Technical implementation** | 10% | Clean module split, env-driven config, graceful fallbacks, `requirements.txt` + `.env.example`, JSONL trace logs |
| **Innovation & UX** | 10% | Bright editorial mobile design, severity stripes, animated trace timeline, history archive, "Powered by" credibility chips |

---

## ✦ Author

**Abdul Raheem** — Computer-engineering student, building CIRO solo for the hackathon qualifier.

GitHub: [@raheemxghumman](https://github.com/raheemxghumman)
