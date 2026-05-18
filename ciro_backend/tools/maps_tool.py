import os
import urllib.parse
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()


def _static_map_url(api_key: str, polylines: list[str], origin: str, destination: str) -> str:
    """Build a Google Static Maps URL with the route polylines drawn.

    polylines: list of encoded polyline strings from the Directions API. The
    first one is drawn in blue (primary/fastest), subsequent ones in grey.
    """
    base = "https://maps.googleapis.com/maps/api/staticmap"
    parts = [
        f"size=640x320",
        f"scale=2",
        f"maptype=roadmap",
        f"markers=color:0x34A853%7Clabel:A%7C{urllib.parse.quote(origin)}",
        f"markers=color:0xEA4335%7Clabel:B%7C{urllib.parse.quote(destination)}",
    ]
    palette = ["0x1A73E8FF", "0x9AA0A6FF"]
    for i, poly in enumerate(polylines[:2]):
        color = palette[i] if i < len(palette) else "0x9AA0A6FF"
        weight = "5" if i == 0 else "4"
        parts.append(
            f"path=color:{color}%7Cweight:{weight}%7Cenc:{urllib.parse.quote(poly, safe='')}"
        )
    parts.append(f"key={api_key}")
    return base + "?" + "&".join(parts)


async def get_route_alternatives(origin: str, destination: str, blocked_area: str) -> dict:
    api_key = os.getenv("GOOGLE_MAPS_KEY", "").strip()

    mock_response = {
        "alternatives": [
            {
                "route_name": "Alternative 1",
                "distance_km": 12.5,
                "eta_min": 25,
                "description": f"Reroute bypassing {blocked_area}.",
            },
            {
                "route_name": "Alternative 2",
                "distance_km": 14.0,
                "eta_min": 30,
                "description": f"Reroute bypassing {blocked_area}.",
            },
        ],
        "static_map_url": None,
        "is_live": False,
    }

    if not api_key:
        return mock_response

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "alternatives": "true",
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                return mock_response

            routes = data.get("routes", [])
            if not routes:
                return mock_response

            parsed_routes = []
            polylines = []
            for i, route in enumerate(routes[:2]):
                leg = route["legs"][0]
                dist_m = leg["distance"]["value"]
                time_s = leg["duration"]["value"]
                # Drop bogus routes — Directions sometimes returns a 0-length
                # loop when origin and destination resolve to the same place.
                if dist_m < 300 or time_s < 30:
                    continue
                summary = route.get("summary", f"Route {i+1}")
                parsed_routes.append(
                    {
                        "route_name": f"Alternative {i+1} ({summary})",
                        "distance_km": round(dist_m / 1000, 1),
                        "eta_min": round(time_s / 60),
                        "description": "Google Maps route bypassing current conditions.",
                    }
                )
                poly = route.get("overview_polyline", {}).get("points")
                if poly:
                    polylines.append(poly)

            if not parsed_routes:
                return mock_response

            return {
                "alternatives": parsed_routes,
                "static_map_url": _static_map_url(api_key, polylines, origin, destination)
                if polylines
                else None,
                "is_live": True,
            }

    except Exception as e:
        print(f"Maps API error: {e}")
        return mock_response


async def geocode_location(location: str) -> Optional[dict]:
    """Resolve a free-text place name to {lat, lng, formatted_address, country}.

    Returns None if geocoding fails. Used to support global coverage — any
    location reported by a citizen can be resolved to coordinates so that
    weather, traffic and earthquake signals can be pulled for that area.
    """
    api_key = os.getenv("GOOGLE_MAPS_KEY", "").strip()
    if not api_key or not location:
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": api_key}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=6.0)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "OK" or not data.get("results"):
                return None
            result = data["results"][0]
            loc = result["geometry"]["location"]
            country = None
            country_code = None
            for comp in result.get("address_components", []):
                if "country" in comp.get("types", []):
                    country = comp.get("long_name")
                    country_code = comp.get("short_name")
                    break
            return {
                "lat": loc["lat"],
                "lng": loc["lng"],
                "formatted_address": result.get("formatted_address"),
                "country": country,
                "country_code": country_code,
            }
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


async def get_traffic_congestion(location: str) -> dict:
    """Estimate real traffic congestion % for a location using Google Maps
    Distance Matrix API.

    Geocodes the location, then queries a short route (~5 km radius around
    the city centre) with `departure_time=now` so the API returns both
    `duration` (free-flow) and `duration_in_traffic` (current). The ratio
    is converted to a 0–100 congestion percentage.

    Falls back to a structurally realistic mock when the API key is missing
    or the call fails — so the pipeline never breaks on signal lookup.
    """
    api_key = os.getenv("GOOGLE_MAPS_KEY", "").strip()

    def _mock(reason: str = "no_api_key") -> dict:
        import random
        pct = random.randint(20, 55)
        level = (
            "Critical" if pct >= 90 else
            "Severe" if pct >= 75 else
            "High" if pct >= 55 else
            "Moderate" if pct >= 30 else "Low"
        )
        return {
            "is_real": False,
            "fallback_reason": reason,
            "congestion_level": level,
            "congestion_percent": pct,
            "average_speed_kmh": max(5, 60 - pct // 2),
            "sample_route": None,
        }

    if not api_key:
        return _mock("no_api_key")

    geo = await geocode_location(location)
    if not geo:
        return _mock("geocode_failed")

    lat, lng = geo["lat"], geo["lng"]
    # Sample a destination ~5 km east of the centre so we always hit a road.
    dest_lat, dest_lng = lat, lng + 0.05

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{lat},{lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=8.0)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "OK":
                return _mock(f"api_status_{data.get('status')}")
            rows = data.get("rows", [])
            if not rows or not rows[0].get("elements"):
                return _mock("no_rows")
            element = rows[0]["elements"][0]
            if element.get("status") != "OK":
                return _mock(f"element_status_{element.get('status')}")

            duration_s = element["duration"]["value"]
            duration_traffic_s = element.get(
                "duration_in_traffic", {}
            ).get("value", duration_s)
            distance_m = element["distance"]["value"]

            # Congestion ratio capped at 100. duration_in_traffic == 2x
            # free-flow duration is 100% congestion.
            if duration_s <= 0:
                pct = 0
            else:
                ratio = (duration_traffic_s - duration_s) / duration_s
                pct = max(0, min(100, round(ratio * 100)))

            level = (
                "Critical" if pct >= 90 else
                "Severe" if pct >= 75 else
                "High" if pct >= 55 else
                "Moderate" if pct >= 30 else "Low"
            )
            avg_kmh = round((distance_m / max(duration_traffic_s, 1)) * 3.6, 1)

            return {
                "is_real": True,
                "congestion_level": level,
                "congestion_percent": pct,
                "average_speed_kmh": avg_kmh,
                "free_flow_seconds": duration_s,
                "in_traffic_seconds": duration_traffic_s,
                "sample_distance_km": round(distance_m / 1000, 2),
                "sample_route": f"{geo.get('formatted_address') or location} (5km radial sample)",
            }
    except Exception as e:
        print(f"Distance Matrix error: {e}")
        return _mock("api_exception")
