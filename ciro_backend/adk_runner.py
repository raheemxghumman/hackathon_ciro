import warnings
warnings.filterwarnings("ignore")

import os
import json
import time
import asyncio
from datetime import datetime

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adk_agents import ciro_adk_agent, _pipeline_state
from tools.verification_tool import verify_incident

_session_service = InMemorySessionService()
_runner = Runner(
    app_name="ciro",
    agent=ciro_adk_agent,
    session_service=_session_service,
)

# Same crisis-impact traffic baselines as orchestrator.py
_CRISIS_TRAFFIC = {
    "flooding":       {"Low": 35, "Medium": 60, "High": 80, "Critical": 95},
    "accident":       {"Low": 25, "Medium": 50, "High": 70, "Critical": 90},
    "fire":           {"Low": 20, "Medium": 45, "High": 70, "Critical": 90},
    "hazmat":         {"Low": 45, "Medium": 70, "High": 85, "Critical": 95},
    "civil_unrest":   {"Low": 25, "Medium": 50, "High": 75, "Critical": 90},
    "infrastructure": {"Low": 20, "Medium": 40, "High": 65, "Critical": 85},
    "earthquake":     {"Low": 30, "Medium": 60, "High": 85, "Critical": 95},
    "crime":          {"Low": 0,  "Medium": 5,  "High": 15, "Critical": 25},
    "medical":        {"Low": 0,  "Medium": 0,  "High": 5,  "Critical": 10},
    "heatwave":       {"Low": 0,  "Medium": 0,  "High": 0,  "Critical": 5},
    "utility_outage": {"Low": 5,  "Medium": 15, "High": 30, "Critical": 50},
    "unknown":        {"Low": 5,  "Medium": 15, "High": 30, "Critical": 50},
}


async def run_adk_pipeline(text: str) -> dict:
    """Run the full CIRO pipeline via Google ADK (Antigravity) multi-agent framework.

    Gemini 2.5 Flash orchestrates 4 specialised agents (Ingest → Detect → Plan → Execute)
    via ADK's Runner and tool-calling mechanism. Post-processing (traffic uplift, before/after
    state, verification) is applied identically to the Groq pipeline so the Flutter app
    receives the same structured output from both endpoints.
    """
    # Clear shared state from any previous run
    _pipeline_state.clear()

    # Create a fresh ADK session for this run
    session = await _session_service.create_session(
        app_name="ciro",
        user_id="operator",
    )
    session_id = session.id or "unknown"

    # Run the ADK agent — Gemini calls the 4 tools in sequence
    adk_summary  = ""
    tools_called = []
    event_count  = 0
    run_start    = time.time()

    async def _collect_events():
        nonlocal adk_summary, tools_called, event_count
        async for event in _runner.run_async(
            user_id="operator",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=text)],
            ),
        ):
            event_count += 1
            for fc in event.get_function_calls():
                tools_called.append(fc.name)
            if event.is_final_response() and event.content and event.content.parts:
                adk_summary = event.content.parts[0].text

    try:
        await asyncio.wait_for(_collect_events(), timeout=180.0)
    except asyncio.TimeoutError:
        raise RuntimeError("ADK pipeline timed out after 180 seconds — Gemini did not complete")

    adk_duration_ms = (time.time() - run_start) * 1000

    # Read results captured by the 4 tool functions
    result1 = _pipeline_state.get("ingestion", {})
    result2 = _pipeline_state.get("detection", {})
    result3 = _pipeline_state.get("plan", {})
    result4 = _pipeline_state.get("execution", {})

    # Validate all 4 stages completed — if Gemini skipped any, raise so fallback triggers
    missing = [s for s in ("ingestion", "detection", "plan", "execution") if not _pipeline_state.get(s)]
    if missing:
        raise RuntimeError(f"ADK pipeline incomplete — stages not executed: {missing}")

    # ── Orchestrator-level transforms (mirrors orchestrator.py) ──────────

    country  = result1.get("country") or (result1.get("geocode") or {}).get("country")
    province = result1.get("province_or_state")
    if province:
        result2["province_or_state"] = province
    if not result2.get("requested_destination"):
        result2["requested_destination"] = result1.get("requested_destination")

    # Incident verification (GDELT + NASA EONET + GDACS) — graceful on failure
    geo = result1.get("geocode") or {}
    try:
        result_verify = await verify_incident(
            location=result2.get("location") or result1.get("location", ""),
            event_type=result1.get("event_type", "unknown"),
            lat=geo.get("lat"),
            lng=geo.get("lng"),
        )
    except Exception as verify_err:
        print(f"[ADK] Verification failed ({verify_err}), continuing without it")
        result_verify = {
            "verified": False,
            "confidence": "unverified",
            "summary": "Verification APIs unavailable — could not cross-reference public feeds.",
            "sources": {},
        }

    # Crisis traffic uplift
    ambient_traffic_pct = (
        result1.get("traffic_signal", {})
               .get("data", {})
               .get("congestion_percent", 0)
    )
    social_reach = (
        result1.get("social_signal", {})
               .get("data", {})
               .get("estimated_reach", 0)
    )
    severity   = (result2.get("severity") or "Medium")
    event_type = (result1.get("event_type") or "unknown").lower()

    crisis_pct = (
        _CRISIS_TRAFFIC
        .get(event_type, _CRISIS_TRAFFIC["unknown"])
        .get(severity, 20)
    )
    crisis_traffic_pct = max(ambient_traffic_pct, crisis_pct)

    if "traffic_signal" in result1 and isinstance(result1["traffic_signal"], dict):
        td = result1["traffic_signal"].setdefault("data", {})
        td["ambient_congestion_percent"] = ambient_traffic_pct
        td["congestion_percent"]         = crisis_traffic_pct
        if crisis_traffic_pct >= 90:
            td["congestion_level"] = "Critical"
        elif crisis_traffic_pct >= 75:
            td["congestion_level"] = "Severe"
        elif crisis_traffic_pct >= 55:
            td["congestion_level"] = "High"
        elif crisis_traffic_pct >= 30:
            td["congestion_level"] = "Moderate"
        else:
            td["congestion_level"] = "Low"
        td["crisis_impacted"] = crisis_pct > ambient_traffic_pct

    reduction_map = {"Low": 0.20, "Medium": 0.40, "High": 0.55, "Critical": 0.70}
    reduction = reduction_map.get(severity, 0.40)
    after_pct = max(5, int(round(crisis_traffic_pct * (1 - reduction))))

    result4.setdefault("before_state", {})
    result4.setdefault("after_state", {})
    result4["before_state"]["traffic_congestion_percent"]  = crisis_traffic_pct
    result4["before_state"]["emergency_services_deployed"] = False
    result4["before_state"]["public_alerts_sent"]          = 0
    result4["after_state"]["traffic_congestion_percent"]   = after_pct
    result4["after_state"]["emergency_services_deployed"]  = True
    result4["after_state"]["public_alerts_sent"]           = int(social_reach)

    # ── Write ADK JSONL trace log (mirrors orchestrator.py pattern) ──────
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"adk_run_{timestamp_str}.jsonl")
        stages_trace = [
            {
                "agent": "Ingest Agent (ingest_signal_tool)",
                "tools_called": ["WeatherAPI", "Google Maps Distance Matrix", "USGS"],
                "output_summary": f"location={result1.get('location','')} event_type={result1.get('event_type','')}",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "agent": "Detect Agent (detect_crisis_tool)",
                "tools_called": [],
                "output_summary": f"crisis_type={result2.get('crisis_type','')} severity={result2.get('severity','')} confidence={result2.get('confidence_percent',0)}%",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "agent": "Plan Agent (plan_response_tool)",
                "tools_called": ["Google Maps Directions API", "Google Maps Static Maps API"],
                "output_summary": f"actions={len(result3.get('actions',[]))} strategy={result3.get('response_strategy','')[:80]}",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "agent": "Execute Agent (execute_response_tool)",
                "tools_called": [],
                "output_summary": result4.get("simulation_summary", ""),
                "timestamp": datetime.now().isoformat(),
            },
        ]
        adk_log = {
            "framework": "Google ADK (Antigravity)",
            "model": "gemini-2.5-flash",
            "session_id": session_id,
            "agent": "ciro_orchestrator",
            "tools_called": tools_called,
            "event_count": event_count,
            "duration_ms": round(adk_duration_ms),
            "input_text": text[:200],
            "stages": stages_trace,
            "timestamp": datetime.now().isoformat(),
        }
        with open(log_file, "w") as f:
            for entry in stages_trace:
                f.write(json.dumps(entry) + "\n")
            f.write(json.dumps({k: v for k, v in adk_log.items() if k != "stages"}) + "\n")
        print(f"[ADK] Trace written to {log_file} ({event_count} events, {round(adk_duration_ms)}ms)")
    except Exception as log_err:
        print(f"[ADK] Could not write log: {log_err}")

    return {
        "ingestion":    result1,
        "detection":    result2,
        "plan":         result3,
        "execution":    result4,
        "verification": result_verify,
        "signals": {
            "weather":    result1.get("weather_signal", {}),
            "traffic":    result1.get("traffic_signal", {}),
            "earthquake": result1.get("earthquake_signal", {}),
            "social":     result1.get("social_signal", {}),
        },
        "country":     country,
        "geocode":     result1.get("geocode"),
        "adk_summary": adk_summary,
        "framework":   "Google ADK (Antigravity) · Gemini 2.5 Flash",
        "adk_trace": {
            "framework":    "Google Agent Development Kit (Antigravity)",
            "model":        "gemini-2.5-flash",
            "session_id":   session_id,
            "agent":        "ciro_orchestrator",
            "tools_called": tools_called,
            "event_count":  event_count,
            "stages": [
                "ingest_signal_tool",
                "detect_crisis_tool",
                "plan_response_tool",
                "execute_response_tool",
            ],
        },
    }
