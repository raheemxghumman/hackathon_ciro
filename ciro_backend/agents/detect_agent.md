# Detect Agent — ADK Tool Specification

**ADK tool name:** `detect_crisis_tool`
**ADK stage:** 2 of 4
**Model:** Groq LLaMA-3.3-70B (via `crisis_agents.detect_crisis`)

## Role

Global crisis classifier. Synthesises the multi-source signal envelope from the
Ingest Agent to determine the crisis type, severity, confidence, and impact.
Supports all locations worldwide — agencies and context are inferred from the
`country` and `province_or_state` fields passed forward from ingestion.

## Input

Reads `_pipeline_state["ingestion"]` — the full output of `ingest_signal_tool`.

## Output schema

```json
{
  "crisis_type":       "string — flooding | accident | fire | heatwave | infrastructure | hazmat | crime | medical | civil_unrest | utility_outage | earthquake",
  "severity":          "string — Low | Medium | High | Critical",
  "confidence_percent": "number — 0–100",
  "reasoning":         "string — LLM explanation of classification decision",
  "impact_analysis":   ["string — bullet-point impact dimensions"],
  "location":          "string — resolved from ingestion",
  "province_or_state": "string — forwarded for jurisdiction routing"
}
```

## Tools

None. All reasoning is performed by the LLM using the signal envelope.

## Upstream / Downstream

- Upstream: `ingest_signal_tool` → `_pipeline_state["ingestion"]`
- Downstream: `plan_response_tool` (reads `_pipeline_state["detection"]`)

## Reasoning contract

The LLM must cross-reference weather, traffic, seismic, and social signals
together with the citizen report text to produce a classification. The
`reasoning` field is surfaced verbatim in the Flutter UI under "AGENT REASONING"
so it must be a coherent natural-language explanation (2–4 sentences).
