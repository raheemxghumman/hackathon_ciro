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


@app.post("/analyze")
async def analyze(body: TextRequest):
    try:
        return await orchestrator.run_pipeline(body.text)
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
