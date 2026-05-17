import os
import urllib.parse
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
                "route_name": "Alternative 1 via I-8",
                "distance_km": 12.5,
                "eta_min": 25,
                "description": f"Reroute bypassing {blocked_area} taking Kashmir Highway to I-8.",
            },
            {
                "route_name": "Alternative 2 via F-7",
                "distance_km": 14.0,
                "eta_min": 30,
                "description": f"Reroute bypassing {blocked_area} taking Margalla Road to F-7.",
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
