import os
import json
import time
import asyncio
from datetime import datetime
from pydantic import BaseModel
import crisis_agents

async def run_pipeline(text: str) -> dict:
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"run_{timestamp}.jsonl")

    trace = []

    def log_step(agent_name: str, input_summary: str, output_summary: str, tools_called: list, duration_ms: float):
        entry = {
            "agent": agent_name,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "tools_called": tools_called,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }
        trace.append(entry)
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        print(f"[{agent_name}] thinking... calling tools: {tools_called}... done in {duration_ms:.0f}ms")

    # Ingest Agent
    start_time = time.time()
    result1 = await crisis_agents.ingest_signal(text)
    duration = (time.time() - start_time) * 1000
    log_step("Ingest Agent", "Raw text, weather, traffic, social signals", str(result1.get("event_type")), ["search_crisis_context"], duration)

    # Detect Agent
    start_time = time.time()
    result2 = await crisis_agents.detect_crisis(result1)
    duration = (time.time() - start_time) * 1000
    log_step("Detect Agent", "Ingested signal", str(result2.get("severity")), [], duration)

    # The country + province are resolved by the ingest agent (via Google
    # geocoding + weather location). Pass them forward so plan/execute pick
    # jurisdiction-appropriate agencies — supports global coverage AND
    # province-level resolution within Pakistan (Multan→Punjab Police etc.)
    country = result1.get("country") or (result1.get("geocode") or {}).get("country")
    province = result1.get("province_or_state")
    # Carry province on the detection so the detect agent's output also has it.
    if province:
        result2["province_or_state"] = province
    if not result2.get("requested_destination"):
        result2["requested_destination"] = result1.get("requested_destination")

    # Plan Agent
    start_time = time.time()
    result3 = await crisis_agents.plan_response(result2, country=country, province=province)
    duration = (time.time() - start_time) * 1000
    tools = ["maps_tool"] if any(a.get("action_type") == "traffic_reroute" for a in result3.get("actions", [])) else []
    log_step("Plan Agent", "Detected crisis severity", f"{len(result3.get('actions', []))} actions planned", tools, duration)

    # Execute Agent
    start_time = time.time()
    result4 = await crisis_agents.execute_actions(
        result3,
        country=country,
        province=province,
        location=result2.get("location"),
    )
    duration = (time.time() - start_time) * 1000
    log_step("Execute Agent", "Planned actions", str(result4.get("simulation_summary")), [], duration)

    # Live ambient traffic from Google Maps (could be near 0% when the
    # surrounding road network is genuinely quiet).
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
    severity = (result2.get("severity") or "Medium")
    event_type = (result1.get("event_type") or "unknown").lower()

    # Crisis-impact uplift: a flood, accident or fire on a road blocks
    # traffic FAR more than the ambient base. We fold this into the
    # corroborating-signal traffic + the "before" metric so the report
    # reflects the actual crisis state, not just the city-wide ambient.
    crisis_traffic_impact = {
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
    crisis_pct = crisis_traffic_impact.get(event_type, crisis_traffic_impact["unknown"]).get(severity, 20)
    # Combine: at minimum the ambient, but bumped to reflect crisis impact.
    crisis_traffic_pct = max(ambient_traffic_pct, crisis_pct)

    # Reflect the bumped value in the corroborating-signals card on the
    # report so the operator sees realistic crisis-time congestion, not the
    # quiet ambient reading from Google Maps.
    if "traffic_signal" in result1 and isinstance(result1["traffic_signal"], dict):
        td = result1["traffic_signal"].setdefault("data", {})
        td["ambient_congestion_percent"] = ambient_traffic_pct
        td["congestion_percent"] = crisis_traffic_pct
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
    result4["before_state"]["traffic_congestion_percent"] = crisis_traffic_pct
    result4["before_state"]["emergency_services_deployed"] = False
    result4["before_state"]["public_alerts_sent"] = 0
    result4["after_state"]["traffic_congestion_percent"] = after_pct
    result4["after_state"]["emergency_services_deployed"] = True
    result4["after_state"]["public_alerts_sent"] = int(social_reach)

    return {
        "ingestion": result1,
        "detection": result2,
        "plan": result3,
        "execution": result4,
        "signals": {
            "weather": result1.get("weather_signal", {}),
            "traffic": result1.get("traffic_signal", {}),
            "earthquake": result1.get("earthquake_signal", {}),
            "social": result1.get("social_signal", {})
        },
        "country": country,
        "geocode": result1.get("geocode")
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        text = "Flash flood happening at G-10 for past 30 mins"
    
    print(f"Running pipeline for: '{text}'")
    final_output = asyncio.run(run_pipeline(text))
    print("\nPipeline execution complete. Logs written to logs/ directory.")
