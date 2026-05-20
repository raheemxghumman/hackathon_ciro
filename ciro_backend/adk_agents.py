import warnings
warnings.filterwarnings("ignore")

import crisis_agents
from google.adk.agents import Agent

# Per-run pipeline state — cleared in adk_runner.py before each run
_pipeline_state: dict = {}


async def ingest_signal_tool(crisis_text: str) -> dict:
    """
    CIRO Stage 1 — Ingest Agent.
    Parse the citizen crisis report, extract the location, and pull live signals:
    weather conditions (WeatherAPI), traffic congestion (Google Maps Distance Matrix),
    and recent earthquake data (USGS). Returns structured signal envelope with
    location, event_type, country, province, and all live signals.
    """
    try:
        result = await crisis_agents.ingest_signal(crisis_text)
        _pipeline_state["ingestion"] = result
        return {
            "stage": "ingest",
            "status": "complete",
            "location": result.get("location", ""),
            "event_type": result.get("event_type", ""),
            "country": result.get("country", ""),
            "weather_condition": result.get("weather_signal", {}).get("data", {}).get("condition", ""),
            "traffic_congestion_pct": result.get("traffic_signal", {}).get("data", {}).get("congestion_percent", 0),
        }
    except Exception as e:
        print(f"[ingest_signal_tool] Error: {e}")
        return {"stage": "ingest", "status": "error", "error": str(e)}


async def detect_crisis_tool(_stage_input: str = "detect") -> dict:
    """
    CIRO Stage 2 — Detect Agent.
    Analyse the ingested multi-source signals to classify the crisis and assess severity.
    Determines crisis_type, severity (Low/Medium/High/Critical), confidence_percent,
    reasoning explanation, and impact analysis bullet points.
    Must be called after ingest_signal_tool.
    """
    try:
        ingested = _pipeline_state.get("ingestion", {})
        result = await crisis_agents.detect_crisis(ingested)
        _pipeline_state["detection"] = result
        return {
            "stage": "detect",
            "status": "complete",
            "crisis_type": result.get("crisis_type", ""),
            "severity": result.get("severity", ""),
            "confidence_percent": result.get("confidence_percent", 0),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        print(f"[detect_crisis_tool] Error: {e}")
        return {"stage": "detect", "status": "error", "error": str(e)}


async def plan_response_tool(_stage_input: str = "plan") -> dict:
    """
    CIRO Stage 3 — Plan Agent.
    Generate a coordinated multi-agency response plan based on the detected crisis.
    Uses Google Maps Directions API to find real alternative routes for traffic incidents.
    Assigns jurisdiction-correct agencies (Punjab Police for Punjab, NYPD for New York,
    Met Police for London, etc). Must be called after detect_crisis_tool.
    """
    try:
        ingested = _pipeline_state.get("ingestion", {})
        detected = _pipeline_state.get("detection", {})
        country  = ingested.get("country") or (ingested.get("geocode") or {}).get("country")
        province = ingested.get("province_or_state")
        if province:
            detected["province_or_state"] = province
        if not detected.get("requested_destination"):
            detected["requested_destination"] = ingested.get("requested_destination")
        result = await crisis_agents.plan_response(detected, country=country, province=province)
        _pipeline_state["plan"]     = result
        _pipeline_state["country"]  = country
        _pipeline_state["province"] = province
        return {
            "stage": "plan",
            "status": "complete",
            "actions_count": len(result.get("actions", [])),
            "response_strategy": result.get("response_strategy", ""),
            "agencies": [a.get("responsible_agency", "") for a in result.get("actions", [])[:3]],
            "coordinates": result.get("coordinates"),
            "recommended_resources": result.get("recommended_resources"),
            "stakeholder_messages": result.get("stakeholder_messages"),
        }
    except Exception as e:
        print(f"[plan_response_tool] Error: {e}")
        return {"stage": "plan", "status": "error", "error": str(e)}


async def execute_response_tool(_stage_input: str = "execute") -> dict:
    """
    CIRO Stage 4 — Execute Agent.
    Simulate coordinated execution of the response plan:
    create emergency tickets with agency-prefixed IDs (PP-15-001, R1122-PB-002, FDNY-001),
    dispatch services, broadcast citizen alerts, and compute before/after impact
    (traffic congestion %, emergency coverage, public alerts sent).
    Must be called after plan_response_tool.
    """
    try:
        detected = _pipeline_state.get("detection", {})
        plan     = _pipeline_state.get("plan", {})
        country  = _pipeline_state.get("country")
        province = _pipeline_state.get("province")
        location = detected.get("location")
        result = await crisis_agents.execute_actions(
            plan, country=country, province=province, location=location
        )
        _pipeline_state["execution"] = result
        return {
            "stage": "execute",
            "status": "complete",
            "simulation_summary": result.get("simulation_summary", ""),
            "tickets_created": len(result.get("execution_log", [])),
            "simulation_data": result.get("simulation_data"),
        }
    except Exception as e:
        print(f"[execute_response_tool] Error: {e}")
        return {"stage": "execute", "status": "error", "error": str(e)}


ciro_adk_agent = Agent(
    name="ciro_orchestrator",
    model="gemini-2.5-flash",
    instruction="""You are CIRO — Crisis Intelligence & Response Orchestrator, \
powered by Google Antigravity (ADK).

Your role is to coordinate a 4-stage multi-agent crisis response pipeline.

When given a crisis report in ANY language (English, Urdu, Roman Urdu, or others), \
execute ALL FOUR stages in strict order:

STEP 1: Call ingest_signal_tool(crisis_text) — pass the original report text verbatim
STEP 2: Call detect_crisis_tool("detect")    — classify crisis type and severity
STEP 3: Call plan_response_tool("plan")      — generate coordinated response with real routes
STEP 4: Call execute_response_tool("execute")— simulate dispatch, tickets, and alerts

You MUST call ALL 4 tools in order without skipping any stage.
After all 4 tools complete, provide a concise incident summary covering:
- What happened and where
- Severity and confidence
- Key response actions taken
- Before/after impact estimate""",
    tools=[
        ingest_signal_tool,
        detect_crisis_tool,
        plan_response_tool,
        execute_response_tool,
    ],
)
