# Detect Agent Specification

## Role
Crisis severity classifier for Islamabad, Pakistan.

## Input Schema
- Output from Ingest Agent (JSON)

## Output Schema
```json
{
  "crisis_type": "string",
  "severity": "string",
  "confidence_percent": "number",
  "impact_analysis": ["string"],
  "requires_immediate_action": "boolean"
}
```

## Tools
None

## Upstream / Downstream
- Upstream: `Ingest Agent`
- Downstream: `Plan Agent`

## Reasoning Contract
The agent must evaluate the severity of the crisis and generate a confidence score. It is required to outline the multi-dimensional impact (traffic, safety, infrastructure) to assist emergency responders.
