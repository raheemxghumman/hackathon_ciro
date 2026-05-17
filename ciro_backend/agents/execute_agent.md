# Execute Agent Specification

## Role
Simulator for emergency response execution in Islamabad, Pakistan.

## Input Schema
- Output from Plan Agent (JSON)

## Output Schema
```json
{
  "before_state": {
    "traffic_congestion_percent": "number",
    "emergency_services_deployed": "boolean",
    "public_alerts_sent": "number"
  },
  "after_state": {
    "traffic_congestion_percent": "number",
    "emergency_services_deployed": "boolean",
    "public_alerts_sent": "number"
  },
  "execution_log": [
    {
      "action_id": "string",
      "status": "string",
      "simulated_result": "string"
    }
  ],
  "simulation_summary": "string"
}
```

## Tools
None

## Upstream / Downstream
- Upstream: `Plan Agent`
- Downstream: Final response / API output

## Reasoning Contract
The agent must simulate the execution of the planned actions and realistically project the state transition of key metrics (before vs. after). It must produce an execution log for each action passed from the upstream planning stage.
