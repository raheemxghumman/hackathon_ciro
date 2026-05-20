# Ingest Agent — ADK Tool Specification

**ADK tool name:** `ingest_signal_tool`
**ADK stage:** 1 of 4
**Model:** Groq LLaMA-3.3-70B (via `crisis_agents.ingest_signal`)

## Role

Global crisis signal parser. Accepts citizen reports in any language (English,
Urdu, Roman Urdu, or others) from any location worldwide. Extracts structured
location metadata, pulls live ambient signals from three external APIs, and
assembles a unified signal envelope for the Detect Agent.

## External APIs called

| API | Purpose |
|---|---|
| Google Maps Geocoding | Resolve free-text location → lat/lng, country, province/state |
| WeatherAPI.com | Live weather conditions, temperature, alert level |
| Google Maps Distance Matrix | Live traffic congestion % for the incident location |
| USGS Earthquake Feed | Recent seismic events within 500 km |

## Input

```
crisis_text: str   — raw citizen report, any language
```

## Output schema

```json
{
  "location":          "string  — normalised place name",
  "event_type":        "string  — flooding | accident | fire | heatwave | ...",
  "country":           "string  — ISO country name",
  "province_or_state": "string  — province/state for jurisdiction routing",
  "language_detected": "string",
  "geocode": {
    "lat": "number", "lng": "number",
    "city": "string", "country": "string"
  },
  "weather_signal": {
    "source": "string", "data": {
      "condition": "string", "temperature_c": "number",
      "humidity_percent": "number", "alert_level": "string"
    }
  },
  "traffic_signal": {
    "source": "string", "data": {
      "congestion_percent": "number", "congestion_level": "string",
      "is_real": "boolean"
    }
  },
  "earthquake_signal": {
    "source": "string", "data": {
      "event_count": "number", "max_magnitude": "number | null"
    }
  },
  "social_signal": {
    "source": "string (SocialMedia_Simulated)",
    "data": {
      "estimated_reach": "number", "report_count": "number",
      "amplification_score": "number"
    }
  }
}
```

## Upstream / Downstream

- Upstream: Citizen report text (ADK orchestrator)
- Downstream: `detect_crisis_tool` (reads `_pipeline_state["ingestion"]`)

## Notes

- Global coverage: any city, country, or region is supported via Geocoding.
- Social signal is structurally realistic but synthetic (no real social-media firehose API).
- All external API calls have graceful fallbacks if keys are missing or APIs are unavailable.
