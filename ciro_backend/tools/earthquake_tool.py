"""USGS Earthquake API client — free, no key required, global coverage.

Docs: https://earthquake.usgs.gov/fdsnws/event/1/

We query recent earthquakes within a radius of a given lat/lng and return
the most significant ones. The orchestrator uses this for any 'earthquake'
event_type, and also as a corroborating signal whenever a crisis is
reported in a seismically active area.
"""
from datetime import datetime, timedelta
import httpx


USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


async def get_recent_earthquakes(
    lat: float,
    lng: float,
    radius_km: int = 500,
    days_back: int = 7,
    min_magnitude: float = 3.0,
    limit: int = 10,
) -> dict:
    """Fetch earthquakes near (lat, lng) within `radius_km` over the last
    `days_back` days with magnitude >= `min_magnitude`.

    Returns a dict suitable to embed as a 'signal' in the pipeline.
    """
    starttime = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "format": "geojson",
        "latitude": lat,
        "longitude": lng,
        "maxradiuskm": radius_km,
        "starttime": starttime,
        "minmagnitude": min_magnitude,
        "orderby": "magnitude",
        "limit": limit,
    }

    fallback = {
        "source": "USGS_Earthquake",
        "is_real": False,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "event_count": 0,
            "max_magnitude": None,
            "max_magnitude_place": None,
            "events": [],
            "search_radius_km": radius_km,
            "lookback_days": days_back,
            "note": "USGS lookup failed — no recent quakes returned.",
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(USGS_URL, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])
            events = []
            max_mag = None
            max_place = None
            for f in features:
                props = f.get("properties", {})
                geom = f.get("geometry", {})
                coords = geom.get("coordinates", [None, None, None])
                mag = props.get("mag")
                place = props.get("place")
                time_ms = props.get("time")
                try:
                    when = datetime.utcfromtimestamp(time_ms / 1000).isoformat() + "Z" if time_ms else None
                except Exception:
                    when = None

                events.append({
                    "magnitude": mag,
                    "place": place,
                    "time": when,
                    "depth_km": coords[2],
                    "lat": coords[1],
                    "lng": coords[0],
                    "tsunami": props.get("tsunami") == 1,
                    "felt_reports": props.get("felt"),
                    "alert_level": props.get("alert"),
                    "url": props.get("url"),
                })
                if mag is not None and (max_mag is None or mag > max_mag):
                    max_mag = mag
                    max_place = place

            return {
                "source": "USGS_Earthquake",
                "is_real": True,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "event_count": len(events),
                    "max_magnitude": max_mag,
                    "max_magnitude_place": max_place,
                    "events": events,
                    "search_radius_km": radius_km,
                    "lookback_days": days_back,
                    "search_origin": {"lat": lat, "lng": lng},
                },
            }
    except Exception as e:
        print(f"USGS earthquake error: {e}")
        fallback["data"]["note"] = f"USGS error: {e}"
        return fallback
