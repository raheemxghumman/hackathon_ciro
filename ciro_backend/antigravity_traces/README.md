# ADK Trace Logs

Every run of the `/analyze-adk` endpoint writes a JSONL trace to `../logs/adk_run_<timestamp>.jsonl`.

## What a trace contains

Each file has 5 lines: 4 per-stage entries + 1 top-level summary.

### Per-stage entry (one per tool called)

```json
{
  "agent": "Ingest Agent (ingest_signal_tool)",
  "tools_called": ["WeatherAPI", "Google Maps Distance Matrix", "USGS"],
  "output_summary": "location=G-10 Markaz Islamabad event_type=flooding",
  "timestamp": "2024-01-15T14:32:01.123456"
}
```

### Top-level ADK summary (last line)

```json
{
  "framework":    "Google ADK (Antigravity)",
  "model":        "gemini-2.5-flash",
  "session_id":   "2ed4b85d-0745-430e-a914-f7c3e1a2b8d9",
  "agent":        "ciro_orchestrator",
  "tools_called": [
    "ingest_signal_tool",
    "detect_crisis_tool",
    "plan_response_tool",
    "execute_response_tool"
  ],
  "event_count":  9,
  "duration_ms":  4821,
  "input_text":   "G-10 mein pani bhar gaya hai, gaariyan phans gayi hain",
  "timestamp":    "2024-01-15T14:32:05.987654"
}
```

## Key fields

| Field | Meaning |
|---|---|
| `session_id` | Live UUID from `InMemorySessionService` — proves this request ran through the ADK runtime |
| `tools_called` | Names of the ADK tool functions Gemini chose to call |
| `event_count` | Total ADK events streamed (typically 9: 4 tool calls + 4 tool responses + 1 final) |
| `duration_ms` | Wall-clock time for the full Gemini + 4-tool pipeline |

## Viewing traces in the ADK browser UI

```bash
cd ciro_backend
source venv/bin/activate
adk web
```

This opens Google's own ADK UI showing the Gemini agent orchestrating the 4 tools in real time — the most direct visual demonstration of the Antigravity framework.

## Reading a trace from the command line

```bash
# View the most recent ADK run
cat $(ls -t logs/adk_run_*.jsonl | head -1) | python3 -m json.tool
```
