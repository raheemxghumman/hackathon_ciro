# Plan Agent — ADK Tool Specification

**ADK tool name:** `plan_response_tool`
**ADK stage:** 3 of 4
**Model:** Groq LLaMA-3.3-70B (via `crisis_agents.plan_response`)

## Role

Global emergency response coordinator. Generates a prioritised, multi-agency
response plan with jurisdiction-correct agencies for any location worldwide.
Calls the Google Maps Directions API to compute real alternate routes when the
crisis involves traffic disruption.

## Jurisdiction-correct agency examples

| Location | Agencies used |
|---|---|
| Punjab, Pakistan | Punjab Police · CTP · Rescue 1122 · WASA Punjab |
| Islamabad, Pakistan | Islamabad Police · ICT · CDA · NDMA |
| New York, USA | NYPD · FDNY · NYC DOT · FEMA |
| London, UK | Met Police · LFB · TfL · NHS Ambulance |
| Tokyo, Japan | Tokyo MPD · Tokyo FD · MLIT · JMA |

Agencies are resolved dynamically from `country` and `province_or_state`
fields — not hardcoded for a single city.

## External APIs called

| API | Purpose |
|---|---|
| Google Maps Directions API | Real alternate routes from incident origin to destination |
| Google Maps Static Maps API | Map image URL with route polylines for the Flutter UI |

## Input

Reads `_pipeline_state["detection"]` plus `country` and `province_or_state`
forwarded from the ingestion stage.

## Output schema

```json
{
  "overall_strategy":    "string",
  "response_strategy":   "string",
  "public_advisory":     "string",
  "actions": [
    {
      "action_id":              "string — ACT-001 etc.",
      "action_type":            "string — deploy_emergency_services | traffic_reroute | ...",
      "description":            "string",
      "responsible_agency":     "string — jurisdiction-correct agency",
      "priority":               "string — P1 | P2 | P3",
      "estimated_time_minutes": "number",
      "route_data":             "object | null — present for traffic_reroute actions",
      "route_origin":           "string | null",
      "route_destination":      "string | null",
      "route_blocked_area":     "string | null"
    }
  ]
}
```

## Upstream / Downstream

- Upstream: `detect_crisis_tool` → `_pipeline_state["detection"]`
- Downstream: `execute_response_tool` (reads `_pipeline_state["plan"]`)
