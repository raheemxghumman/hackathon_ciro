# CIRO Backend Workflow

This document explains the architecture and workflow of the CIRO (Crisis Intelligence & Response Orchestrator) backend, driven by Antigravity orchestration and integrating the Groq LLaMA-3.3-70B model.

## Architecture Diagram

```ascii
                      +------------------+
Citizen Report ---->  |   main.py API    |
                      +------------------+
                               |
                               v
                     +-------------------+
                     |  orchestrator.py  |
                     +-------------------+
                               |
      +-------------------------------------------------+
      |                                                 |
      v                                                 v
+----------------+                              +-----------------+
|  Ingest Agent  | --- calls search_tool --->   |  Detect Agent   |
+----------------+                              +-----------------+
      |                                                 |
      |-------------------------------------------------|
      v                                                 v
+----------------+                              +-----------------+
|   Plan Agent   | --- calls maps_tool ----->   |  Execute Agent  |
+----------------+                              +-----------------+
```

## Antigravity Orchestration

The Antigravity orchestration layer in `orchestrator.py` dynamically links the four core agents (`Ingest`, `Detect`, `Plan`, and `Execute`). It ensures that:
- Inputs and outputs flow correctly from one agent to the next.
- External tools like `search_tool` and `maps_tool` are called conditionally based on the LLM's planned actions (e.g., when a "traffic_reroute" action is identified).
- The end-to-end trace is logged in `logs/` as a structured JSONL for debugging and tracking the system's reasoning at each step.

## Google Maps Tool Integration

The `maps_tool` provides realistic routing capabilities for emergency response:
- Called automatically by the orchestrator (via `plan_response`) when a traffic-related crisis demands rerouting.
- Uses `httpx` to query the Google Maps Directions API using the `GOOGLE_MAPS_KEY` defined in the `.env` file.
- Provides a robust mock fallback for specific Islamabad sectors (G-10, F-7, Blue Area, I-8) in case of API limits or errors, ensuring the system remains operational and can test the UI reliably.

The backend guarantees a complete, 4-stage processing pipeline for every incoming crisis report, converting raw multi-modal signals into actionable and logged response plans.
