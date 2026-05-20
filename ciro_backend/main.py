from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import crisis_agents
from mock_signals import (
    get_real_weather,
    get_real_traffic,
    get_real_earthquake,
)
from tools.verification_tool import verify_incident
from tools.maps_tool import geocode_location

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextRequest(BaseModel):
    text: str


@app.get("/health")
async def health():
    return {"status": "ok"}


import orchestrator
import adk_runner


@app.post("/analyze")
async def analyze(body: TextRequest):
    try:
        return await orchestrator.run_pipeline(body.text)
    except Exception as e:
        return {"error": str(e)}


@app.post("/analyze-adk")
async def analyze_adk(body: TextRequest):
    """Google ADK (Antigravity) orchestrated pipeline — Gemini 2.0 Flash coordinates
    4 specialised agents: Ingest → Detect → Plan → Execute.
    Falls back to the Groq pipeline automatically if ADK/Gemini is unavailable."""
    try:
        return await adk_runner.run_adk_pipeline(body.text)
    except Exception as adk_err:
        print(f"[ADK] Pipeline failed ({adk_err}), falling back to Groq pipeline")
        adk_err_str = str(adk_err)
        if "429" in adk_err_str or "RESOURCE_EXHAUSTED" in adk_err_str or "quota" in adk_err_str.lower():
            fallback_reason = "Groq LLaMA-3.3-70B (Gemini daily quota exceeded — ADK fallback active)"
        elif "GOOGLE_API_KEY" in adk_err_str or "API key" in adk_err_str:
            fallback_reason = "Groq LLaMA-3.3-70B (ADK unavailable — invalid GOOGLE_API_KEY)"
        else:
            fallback_reason = f"Groq LLaMA-3.3-70B (ADK error: {type(adk_err).__name__})"
        try:
            result = await orchestrator.run_pipeline(body.text)
            result["framework"]  = fallback_reason
            result["adk_error"]  = adk_err_str
            result["adk_trace"]  = {"framework": "fallback", "reason": adk_err_str}
            return result
        except Exception as e:
            return {"error": str(e)}


@app.get("/verify")
async def verify(location: str, event_type: str = "unknown"):
    """Test the verification APIs directly.
    Example: GET /verify?location=Tokyo&event_type=earthquake
    """
    geo = await geocode_location(location)
    result = await verify_incident(
        location=location,
        event_type=event_type,
        lat=geo.get("lat") if geo else None,
        lng=geo.get("lng") if geo else None,
    )
    return {
        "location": location,
        "event_type": event_type,
        "geocode": geo,
        "verification": result,
    }


@app.get("/incidents")
async def get_latest_incidents(limit: int = 5):
    """Return latest global crisis incidents merged from ReliefWeb, GDACS, and USGS.
    The Flutter app polls this every 5 minutes to refresh the Global Incidents feed.
    """
    from tools.incidents_tool import fetch_latest_incidents
    try:
        incidents = await fetch_latest_incidents(limit=limit)
        return {"incidents": incidents, "count": len(incidents)}
    except Exception as e:
        return {"incidents": [], "count": 0, "error": str(e)}


@app.get("/signals")
async def get_live_signals(location: str = "Islamabad"):
    """Return live ambient signals for `location`. The mobile app polls this
    every 30 seconds to keep the home-page chips fresh. Supports any location
    globally — pass `?location=Tokyo` or `?location=New York` etc.
    """
    weather = await get_real_weather(location)
    traffic = await get_real_traffic(location)
    earthquake = await get_real_earthquake(location)
    return {
        "weather": weather,
        "traffic": traffic,
        "earthquake": earthquake,
        "location": location,
        "timestamp": "live",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
