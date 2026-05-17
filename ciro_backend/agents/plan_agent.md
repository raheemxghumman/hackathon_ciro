# Plan Agent Specification

## Role
Emergency response coordinator for Islamabad, Pakistan. Available Agencies: NDMA, Rescue 1122, CDA, WASA, Islamabad Traffic Police.

## Input Schema
- Output from Detect Agent (JSON)

## Output Schema
```json
{
  "overall_strategy": "string",
  "actions": [
    {
      "action_id": "string",
      "action_type": "string",
      "description": "string",
      "responsible_agency": "string",
      "priority": "string",
      "estimated_time_minutes": "number"
    }
  ],
  "public_advisory": "string"
}
```

## Tools
- `maps_tool` (called at orchestration layer if `traffic_reroute` action generated)

## Upstream / Downstream
- Upstream: `Detect Agent`
- Downstream: `Execute Agent`

## Reasoning Contract
The agent must strategize response actions according to the detected severity and impact. It should formulate actions with specific `action_type` identifiers. For traffic issues, it should generate `traffic_reroute` actions to trigger the Maps routing capability in the orchestrator.
