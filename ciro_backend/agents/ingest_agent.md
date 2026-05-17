# Ingest Agent Specification

## Role
Crisis signal parser for Islamabad, Pakistan. Understands Urdu, Roman Urdu, and English.

## Input Schema
- Citizen Report (string)
- Weather API data (JSON string)
- Traffic API data (JSON string)
- Social Media data (JSON string)

## Output Schema
```json
{
  "location": "string",
  "event_type": "string",
  "language_detected": "string",
  "urgency_level": "string",
  "cleaned_text": "string",
  "sources_count": "number",
  "weather_context": "string",
  "traffic_context": "string",
  "corroborating_signals": "boolean"
}
```

## Tools
- `search_crisis_context` (mock)

## Upstream / Downstream
- Upstream: Raw signal inputs from APIs and citizens
- Downstream: `Detect Agent`

## Reasoning Contract
The agent must analyze all input sources simultaneously and normalize the text into a clean English summary. It must synthesize contextual insights for weather and traffic to aid downstream decision making.
