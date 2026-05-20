# CIRO — Crisis Intelligence & Response Orchestrator

> Multi-agent crisis-response system with **global coverage**, orchestrated through **Google Antigravity (ADK)** with **Gemini 2.5 Flash**, integrated with **Google Maps**, **WeatherAPI**, **USGS**, and a polished **Flutter** mobile experience.

CIRO ingests noisy multi-source signals (citizen reports in any language — Urdu, Roman Urdu, English, or others — plus live weather, real traffic, and seismic data), detects emerging crises, generates a coordinated response plan with jurisdiction-correct agencies, verifies the incident against independent public feeds, and simulates execution with realistic tickets, citizen alerts and before/after impact — all within a single end-to-end Google ADK agentic workflow.

---

## ✦ The challenge

Metropolitan cities globally face frequent localised crises (flash floods, road accidents, heatwaves, infrastructure failures, security incidents). Response systems are **fragmented, reactive, and slow to coordinate**. Critical signals already exist across social media, maps, weather and citizen reports, but are not converted into actionable decisions in real time.

CIRO is the missing layer: an agentic AI that converts those signals into coordinated action within seconds, for any location in the world.

---

## ✦ Demo flow

1. A citizen reports a crisis in any language: *"G-10 mein pani bhar gaya hai, gaariyan phans gayi hain"*
2. **Google ADK Runner** receives the report via `POST /analyze-adk` and starts an `InMemorySession`
3. **Gemini 2.5 Flash** (the ADK orchestrator) calls the 4 agent tools in sequence:
   - `ingest_signal_tool` — pulls live weather (WeatherAPI), traffic (Google Maps Distance Matrix), earthquake (USGS)
   - `detect_crisis_tool` — classifies crisis type, severity, and confidence with reasoning
   - `plan_response_tool` — generates response actions + queries Google Maps Directions API for real alternate routes
   - `execute_response_tool` — simulates dispatch: agency tickets, citizen alerts, before/after impact
4. The ADK response includes a full `adk_trace` (session ID, tools called, event count)
5. The Flutter app renders a complete **incident report** with a "Google ADK" badge, incident verification card (GDELT · EONET · GDACS), visual Google Static Map with route polylines, ranked alternates, system logs, and before/after metrics

---

## ✦ Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│           GOOGLE ANTIGRAVITY  —  Agent Development Kit (ADK)       │
│   Runner · InMemorySessionService · Gemini 2.5 Flash               │
│   adk_agents.py  ·  adk_runner.py  ·  POST /analyze-adk           │
└────────────────────────────────────────────────────────────────────┘
                              │  ADK tool-calling orchestration
                              ▼
         ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
         │  Ingest  │──▶│  Detect  │──▶│   Plan   │──▶│ Execute  │
         │  Agent   │   │  Agent   │   │  Agent   │   │  Agent   │
         │  (tool)  │   │  (tool)  │   │  (tool)  │   │  (tool)  │
         └────┬─────┘   └──────────┘   └────┬─────┘   └──────────┘
              │                             │
              │  ┌──────────────────┐       │  ┌───────────────────┐
              ├─▶│   WeatherAPI     │       ├─▶│  Google Maps      │
              │  └──────────────────┘       │  │  Directions +     │
              │  ┌──────────────────┐       │  │  Static Maps      │
              ├─▶│  Google Maps     │       │  └───────────────────┘
              │  │  Distance Matrix │
              │  └──────────────────┘       ┌───────────────────────┐
              │  ┌──────────────────┐       │  Verification Layer   │
              └─▶│   USGS Seismic   │       │  GDELT · EONET · GDACS│
                 └──────────────────┘       └───────────────────────┘

           ▲
           │ HTTP POST /analyze-adk  (primary — Google ADK)
           │ HTTP GET  /signals, /verify, /health
           │
┌──────────┴────────────────────────────────────────────────────────┐
│                  ciro_app/ (Flutter, iOS / Android)               │
│  Input → ADK pipeline → Results · History · Google ADK badge      │
└───────────────────────────────────────────────────────────────────┘
```

---

## ✦ Google Antigravity usage

CIRO uses **Google ADK (Antigravity)** as the live runtime orchestrator. Every crisis report processed by the app flows through the ADK framework.

### How it works

**`ciro_backend/adk_agents.py`** defines:
- A single `ciro_orchestrator` — a `google.adk.agents.Agent` running **Gemini 2.5 Flash**
- 4 async tool functions registered on the agent: `ingest_signal_tool`, `detect_crisis_tool`, `plan_response_tool`, `execute_response_tool`
- Each tool wraps the corresponding crisis pipeline stage and stores results in a shared session state dict

**`ciro_backend/adk_runner.py`** wires up:
- `google.adk.runners.Runner` with `app_name="ciro"`
- `google.adk.sessions.InMemorySessionService` — a fresh session per request
- Streams `runner.run_async(...)` events, capturing `get_function_calls()` for the trace
- Applies post-processing (traffic uplift, before/after state, incident verification) after all 4 tools complete

**`POST /analyze-adk`** is the primary endpoint — all Flutter app requests go here.

### Verifiable proof in every response

Every `/analyze-adk` response includes an `adk_trace` field:

```json
"adk_trace": {
  "framework":    "Google Agent Development Kit (Antigravity)",
  "model":        "gemini-2.5-flash",
  "session_id":   "2ed4b85d-0745-430e-a...",
  "agent":        "ciro_orchestrator",
  "tools_called": ["ingest_signal_tool", "detect_crisis_tool", "plan_response_tool", "execute_response_tool"],
  "event_count":  9
}
```

The `session_id` is a live ADK-generated UUID — proof that the request ran through the ADK `InMemorySessionService`, not a custom loop.

### Reproduce a run

```bash
cd ciro_backend
source venv/bin/activate
uvicorn main:app --reload

# In another terminal:
curl -X POST http://localhost:8000/analyze-adk \
  -H "Content-Type: application/json" \
  -d '{"text": "Flash flood at G-10 Islamabad, cars stuck"}'
```

Inspect the `adk_trace` in the response, and the per-step JSONL trace in `logs/run_<timestamp>.jsonl`.

### ADK web UI (live agent trace)

```bash
cd ciro_backend
source venv/bin/activate
adk web
```

Opens a browser UI (Google's own ADK interface) showing Gemini orchestrating the 4 agents in real time — the most direct visual demonstration of the Antigravity framework.

---

## ✦ Agents & responsibilities

| Agent | ADK Role | Inputs | Outputs | External Tools |
|---|---|---|---|---|
| **Ingest** | `ingest_signal_tool` | citizen text | event_type, location, country, signals | WeatherAPI, Google Maps Distance Matrix, USGS |
| **Detect** | `detect_crisis_tool` | ingested signals | crisis_type, severity, confidence, reasoning, impact analysis | — |
| **Plan** | `plan_response_tool` | detection | response strategy, ranked actions, agency assignments | Google Maps Directions + Static Maps |
| **Execute** | `execute_response_tool` | plan | execution log (ticket IDs), before/after state, simulation summary | — |

Supports 11 crisis types: `flooding · accident · fire · heatwave · infrastructure · hazmat · crime · medical · civil_unrest · utility_outage · earthquake`. Agencies are jurisdiction-correct globally — Punjab Police / CTP for Pakistan's Punjab, NYPD / FDNY for New York, Met Police / TfL for London, etc.

---

## ✦ Tools & APIs integrated

| Tool / API | Role | Live? |
|---|---|---|
| **Google ADK** (`google-adk`) | Multi-agent runtime orchestration via Gemini 2.5 Flash | ✅ |
| **Google Maps Directions API** | Real alternate route generation for traffic crises | ✅ |
| **Google Maps Static Maps API** | Map preview with route polylines on the mobile report | ✅ |
| **Google Maps Distance Matrix API** | Live traffic congestion % for any location globally | ✅ |
| **Google Maps Geocoding API** | Resolves any free-text location to coordinates (global coverage) | ✅ |
| **Groq LLaMA-3.3-70B-versatile** | Agent reasoning inside each ADK tool function | ✅ |
| **WeatherAPI.com** | Live weather conditions for any global location | ✅ |
| **USGS Earthquake API** | Real seismic data, free, global, no key required | ✅ |
| **GDELT Project API** | News-based incident verification (free, no key) | ✅ |
| **NASA EONET API** | Natural event verification — floods, fires, earthquakes (free) | ✅ |
| **GDACS API** | UN/EU declared disaster verification — floods, EQ, wildfire (free) | ✅ |
| Social-media signal | Amplification & reach estimate | simulated |

---

## ✦ Mobile app

The Flutter app (`ciro_app/`) provides:

- **Input screen** — quick-pick scenarios in any language, live weather + traffic + seismic chips (refresh every 30 s), history list
- **Results screen** — "Google ADK" badge in AppBar, severity-stripe crisis header, confidence ring, INCIDENT VERIFICATION card (CONFIRMED / LIKELY / UNVERIFIED with source chips and news headlines), CORROBORATING SIGNALS card, dispatched actions with priority stripes, Google Maps panel with static-map preview + ranked alternates, before/after metrics, execution-log terminal with ticket-ID chips
- **History screen** — `SharedPreferences`-persisted archive of every report, capped at 50

---

## ✦ Project structure

```
ciro_project/
├── ciro_backend/
│   ├── adk_agents.py               ← Google ADK agent definition (ciro_orchestrator + 4 tools)
│   ├── adk_runner.py               ← ADK Runner + InMemorySessionService + post-processing
│   ├── crisis_agents.py            ← 4 agent functions + Groq LLM calls
│   ├── orchestrator.py             ← Groq pipeline runner + JSONL traces (fallback)
│   ├── mock_signals.py             ← live WeatherAPI + traffic + earthquake signals
│   ├── main.py                     ← FastAPI: /analyze-adk, /analyze, /signals, /verify
│   ├── tools/
│   │   ├── maps_tool.py            ← Google Maps Directions, Static Maps, Geocoding, Distance Matrix
│   │   ├── earthquake_tool.py      ← USGS earthquake feed
│   │   ├── verification_tool.py    ← GDELT + NASA EONET + GDACS verification
│   │   └── search_tool.py          ← grounded context fallback
│   ├── logs/                       ← JSONL agent traces (one file per run)
│   ├── requirements.txt
│   └── .env
└── ciro_app/
    └── lib/
        ├── screens/                ← input_screen, results_screen
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
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Endpoints:
- `POST /analyze-adk` — **primary** (Google ADK / Antigravity pipeline)
- `POST /analyze` — Groq-only fallback pipeline
- `GET  /signals?location=Islamabad` — live ambient signals for any location
- `GET  /verify?location=Tokyo&event_type=earthquake` — test verification APIs directly
- `GET  /health` — liveness probe

### API keys

Fill in `ciro_backend/.env`:

| Variable | Where to get it | Required? |
|---|---|---|
| `GOOGLE_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → Get API key → Create API key (Default Gemini project) | **yes** (ADK/Gemini) |
| `GROQ_API_KEYS` | [console.groq.com/keys](https://console.groq.com/keys) — free, comma-separated for rotation | **yes** (agent reasoning) |
| `GOOGLE_MAPS_KEY` | [console.cloud.google.com](https://console.cloud.google.com/) → enable Directions + Static Maps + Distance Matrix + Geocoding APIs | yes (real routing + traffic) |
| `WEATHERAPI_KEY` | [weatherapi.com/signup.aspx](https://www.weatherapi.com/signup.aspx) — free tier | yes (live weather) |

### Mobile app

```bash
cd ciro_app
flutter pub get
flutter run
```

### ADK web UI (visual agent trace)

```bash
cd ciro_backend
source venv/bin/activate
adk web
```

### CLI one-shot trace

```bash
cd ciro_backend
python orchestrator.py "Flash flood at G-10 Markaz, gaariyan phans gayi hain"
# trace written to logs/run_<timestamp>.jsonl
```

---

## ✦ Assumptions

- **Simulation, not real dispatch.** No actual emergency agency is contacted — every "dispatch" is a labelled simulation in the execution log. The system is designed to slot behind a real-dispatch adapter without changing the agent contracts.
- **Social signal is simulated.** Real-time social media firehose APIs (Twitter/X) require commercial agreements, so a structurally realistic mock is used.
- **Global coverage.** Any location worldwide is supported via Google Maps Geocoding — agencies, weather, traffic, and earthquake data are resolved for any city the citizen mentions.
- **Mobile-only client.** The web client is optional per the challenge brief and was descoped in favour of a polished mobile experience.

---

## ✦ How the rubric is satisfied

| Criterion | Weight | Where it's demonstrated |
|---|---:|---|
| **Use of Google Antigravity** | 25% | `adk_agents.py` (ADK Agent + 4 tools), `adk_runner.py` (Runner + Session), `POST /analyze-adk`, `adk_trace.session_id` in every response |
| **Agentic reasoning & coordination** | 20% | 4-agent ADK pipeline; `reasoning` field from detect agent surfaced verbatim in UI; JSONL trace in `logs/` |
| **Situation detection & analysis** | 20% | Multi-source synthesis (weather + traffic + seismic + social); severity classifier with confidence ring and impact analysis; incident verified against GDELT + EONET + GDACS |
| **Action planning & simulation** | 15% | Jurisdiction-correct agencies globally; Google Maps real routing; agency-prefixed ticket IDs; before/after congestion metrics |
| **Technical implementation** | 10% | Clean module split; env-driven config; graceful fallbacks on every external API; `requirements.txt`; JSONL trace logs |
| **Innovation & UX** | 10% | Global coverage in any language; incident verification layer; "Google ADK" badge in UI; SEISMIC signal card; LIVE traffic pill |

---

## ✦ Author

**Abdul Raheem** — Computer-engineering student, building CIRO solo for the hackathon qualifier.

GitHub: [@raheemxghumman](https://github.com/raheemxghumman)
