# Execute Agent — ADK Tool Specification

**ADK tool name:** `execute_response_tool`
**ADK stage:** 4 of 4
**Model:** Groq LLaMA-3.3-70B (via `crisis_agents.execute_actions`)

## Role

Global emergency response simulator. Processes the response plan from the Plan
Agent and simulates coordinated execution: creates agency-prefixed ticket IDs,
dispatches services, broadcasts citizen alerts, and computes before/after
impact metrics for any location worldwide.

## Agency-prefixed ticket ID examples

| Agency | Ticket format | Example |
|---|---|---|
| Punjab Police | PP-`<severity>`-`<seq>` | PP-15-001 |
| Rescue 1122 (Punjab) | R1122-PB-`<seq>` | R1122-PB-002 |
| NYPD | NYPD-`<seq>` | NYPD-001 |
| FDNY | FDNY-`<seq>` | FDNY-001 |
| Met Police | MET-`<seq>` | MET-001 |

Ticket prefixes are jurisdiction-correct — resolved from the `country` and
`province_or_state` fields.

## Input

Reads `_pipeline_state["plan"]`, `_pipeline_state["country"]`,
`_pipeline_state["province"]`, and `detection.location`.

## Output schema

```json
{
  "execution_log": [
    {
      "action_id":           "string",
      "ticket_id":           "string — agency-prefixed ID",
      "status":              "string — dispatched | acknowledged | en_route",
      "simulated_result":    "string — human-readable outcome",
      "alert_message_body":  "string | null — citizen SMS/alert text"
    }
  ],
  "simulation_summary": "string"
}
```

`before_state` and `after_state` are computed by `adk_runner.py`
post-processing (not the LLM) to ensure consistent traffic uplift logic
across both ADK and Groq pipelines.

## Tools

None. Reasoning performed by the LLM. All dispatch is a clearly labelled
simulation — no real emergency agency is contacted.

## Upstream / Downstream

- Upstream: `plan_response_tool` → `_pipeline_state["plan"]`
- Downstream: Final pipeline output → `/analyze-adk` response
