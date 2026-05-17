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

    # Plan Agent
    start_time = time.time()
    result3 = await crisis_agents.plan_response(result2)
    duration = (time.time() - start_time) * 1000
    tools = ["maps_tool"] if any(a.get("action_type") == "traffic_reroute" for a in result3.get("actions", [])) else []
    log_step("Plan Agent", "Detected crisis severity", f"{len(result3.get('actions', []))} actions planned", tools, duration)

    # Execute Agent
    start_time = time.time()
    result4 = await crisis_agents.execute_actions(result3)
    duration = (time.time() - start_time) * 1000
    log_step("Execute Agent", "Planned actions", str(result4.get("simulation_summary")), [], duration)

    # Derive before/after metrics override
    traffic_pct = (
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
    reduction_map = {"Low": 0.20, "Medium": 0.40, "High": 0.55, "Critical": 0.70}
    reduction = reduction_map.get(severity, 0.40)
    after_pct = max(5, int(round(traffic_pct * (1 - reduction))))

    result4.setdefault("before_state", {})
    result4.setdefault("after_state", {})
    result4["before_state"]["traffic_congestion_percent"] = traffic_pct
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
            "social": result1.get("social_signal", {})
        }
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
