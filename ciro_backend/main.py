from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import crisis_agents
from mock_signals import get_weather_signal, get_traffic_signal, get_social_media_signal, get_real_weather

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

@app.get("/signals")
async def get_live_signals():
    return {
        "weather": await get_real_weather("Islamabad"),
        "traffic": get_traffic_signal("Islamabad"),
        "timestamp": "live"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
