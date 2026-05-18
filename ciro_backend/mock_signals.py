import random
from datetime import datetime
import httpx
import os
from dotenv import load_dotenv

from tools.maps_tool import get_traffic_congestion, geocode_location
from tools.earthquake_tool import get_recent_earthquakes

load_dotenv()


def get_weather_signal(location: str) -> dict:
    """Mock weather signal — only used when the live WeatherAPI call fails."""
    weather_conditions = [
        {
            "condition": "Heavy Rainfall",
            "alert_level": "High",
            "rainfall_mm_per_hour": random.randint(40, 120),
            "visibility_km": random.randint(1, 4),
            "wind_speed_kmh": random.randint(30, 60),
            "flood_risk": "High",
        },
        {
            "condition": "Extreme Heat",
            "alert_level": "High",
            "temperature_c": random.randint(42, 48),
            "humidity_percent": random.randint(60, 85),
            "heat_index_c": random.randint(48, 58),
            "heatstroke_risk": "Critical",
        },
        {
            "condition": "Thunderstorm",
            "alert_level": "Critical",
            "rainfall_mm_per_hour": random.randint(80, 200),
            "lightning_strikes_per_hour": random.randint(20, 80),
            "flood_risk": "Critical",
        },
        {
            "condition": "Clear",
            "alert_level": "Low",
            "temperature_c": random.randint(20, 32),
            "humidity_percent": random.randint(30, 50),
            "flood_risk": "Low",
        },
    ]
    chosen = random.choice(weather_conditions)
    return {
        "source": "WeatherAPI_Simulated",
        "location": location,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": chosen,
    }


def get_traffic_signal_mock(location: str) -> dict:
    """Mock traffic signal — kept as a fallback only. Live traffic is fetched
    via `get_real_traffic` (Google Maps Distance Matrix)."""
    congestion_levels = ["Low", "Moderate", "High", "Severe", "Critical"]
    level = random.choice(congestion_levels)
    percent_map = {
        "Low": random.randint(10, 30),
        "Moderate": random.randint(30, 55),
        "High": random.randint(55, 75),
        "Severe": random.randint(75, 90),
        "Critical": random.randint(90, 100),
    }
    return {
        "source": "TrafficAPI_Simulated",
        "location": location,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "congestion_level": level,
            "congestion_percent": percent_map[level],
            "incidents_reported": random.randint(0, 8),
            "average_speed_kmh": random.randint(5, 45),
            "estimated_clearance_minutes": random.randint(15, 120),
        },
    }


async def get_real_weather(location: str = "Islamabad") -> dict:
    """Pull live weather for `location` via WeatherAPI. WeatherAPI accepts any
    free-form place name (city, country, postcode) — works globally.
    """
    try:
        api_key = os.getenv("WEATHERAPI_KEY")
        if not api_key:
            return get_weather_signal(location)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.weatherapi.com/v1/current.json",
                params={"key": api_key, "q": location, "aqi": "no"},
                timeout=6.0,
            )

            if response.status_code != 200:
                print(f"WeatherAPI error: {response.status_code}")
                return get_weather_signal(location)

            data = response.json()
            current = data["current"]
            condition_text = current["condition"]["text"]
            temp_c = current["temp_c"]
            humidity = current["humidity"]
            wind_kph = current["wind_kph"]
            precip_mm = current["precip_mm"]
            feelslike_c = current["feelslike_c"]
            vis_km = current["vis_km"]
            uv = current["uv"]

            alert_level = "Low"
            flood_risk = "Low"
            condition_lower = condition_text.lower()
            if any(w in condition_lower for w in ["thunder", "tornado", "blizzard"]):
                alert_level = "Critical"
                flood_risk = "Critical"
            elif any(w in condition_lower for w in ["heavy rain", "torrential", "downpour"]):
                alert_level = "High"
                flood_risk = "High"
            elif any(w in condition_lower for w in ["rain", "drizzle", "shower"]):
                alert_level = "Medium"
                flood_risk = "Medium"
            elif temp_c > 42:
                alert_level = "Critical"
            elif temp_c > 38:
                alert_level = "High"
            elif precip_mm > 10:
                alert_level = "High"
                flood_risk = "High"

            loc = data["location"]
            return {
                "source": "WeatherAPI_Live",
                "location": f"{loc.get('name')}, {loc.get('country')}",
                "country": loc.get("country"),
                "lat": loc.get("lat"),
                "lng": loc.get("lon"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "is_real": True,
                "data": {
                    "condition": condition_text,
                    "alert_level": alert_level,
                    "temperature_c": temp_c,
                    "feels_like_c": feelslike_c,
                    "humidity_percent": humidity,
                    "wind_speed_kmh": wind_kph,
                    "precipitation_mm": precip_mm,
                    "visibility_km": vis_km,
                    "uv_index": uv,
                    "flood_risk": flood_risk,
                    "last_updated": current["last_updated"],
                },
            }
    except Exception as e:
        print(f"WeatherAPI error: {e}, using simulated fallback")
        return get_weather_signal(location)


async def get_real_traffic(location: str = "Islamabad") -> dict:
    """Pull live traffic congestion % for `location` via Google Maps Distance
    Matrix. Wraps `tools.maps_tool.get_traffic_congestion` and packages it
    into the same envelope the other signals use.
    """
    data = await get_traffic_congestion(location)
    source = "GoogleMaps_Live" if data.get("is_real") else "TrafficAPI_Simulated"
    return {
        "source": source,
        "location": location,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "is_real": data.get("is_real", False),
        "data": data,
    }


async def get_real_earthquake(location: str = "Islamabad") -> dict:
    """Pull recent earthquakes near `location` via USGS. Geocodes the place
    name first; falls back to an empty signal if geocoding fails.
    """
    geo = await geocode_location(location)
    if not geo:
        return {
            "source": "USGS_Earthquake",
            "location": location,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "is_real": False,
            "data": {
                "event_count": 0,
                "max_magnitude": None,
                "events": [],
                "note": "Could not geocode location for USGS lookup.",
            },
        }
    quake = await get_recent_earthquakes(geo["lat"], geo["lng"])
    quake["location"] = location
    return quake


def get_social_media_signal(crisis_text: str) -> dict:
    return {
        "source": "SocialMedia_Simulated",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "original_report": crisis_text,
            "estimated_reach": random.randint(500, 15000),
            "report_count": random.randint(3, 47),
            "sentiment": "urgent",
            "platform": random.choice(["Twitter/X", "WhatsApp", "Facebook"]),
            "verified": False,
        },
    }


# Backwards-compat alias — older callers in this repo imported
# `get_traffic_signal` from this module. Keep it pointing at the mock so any
# legacy import paths still resolve.
get_traffic_signal = get_traffic_signal_mock
