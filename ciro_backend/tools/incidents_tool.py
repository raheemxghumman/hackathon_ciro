"""
Global crisis incidents feed — merges GDACS RSS, USGS, and NASA EONET into a
single ranked list for the /incidents endpoint.

Note: ReliefWeb v1 was decommissioned (410 Gone); v2 requires an approved appname.
GDACS JSON API returned 404 after a format change; RSS feed is used instead.
"""
import asyncio
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone

import httpx

GDACS_RSS_URL = "https://www.gdacs.org/xml/rss.xml"
USGS_URL      = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
EONET_URL     = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=15"

_GDACS_NS = {"gdacs": "http://www.gdacs.org", "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"}

_GDACS_TYPE_MAP = {
    "EQ": "earthquake",
    "TC": "flooding",
    "FL": "flooding",
    "VO": "hazmat",
    "WF": "fire",
    "DR": "heatwave",
}

_GDACS_SEVERITY = {
    "Red":    "Critical",
    "Orange": "High",
    "Green":  "Medium",
}

_EONET_TYPE_MAP = {
    "Wildfires":          "fire",
    "Floods":             "flooding",
    "Volcanoes":          "hazmat",
    "Earthquakes":        "earthquake",
    "Severe Storms":      "flooding",
    "Drought":            "heatwave",
    "Landslides":         "accident",
    "Sea and Lake Ice":   "heatwave",
    "Snow":               "heatwave",
    "Dust and Haze":      "heatwave",
    "Temperature Extreme":"heatwave",
    "Manmade":            "accident",
    "Water Color":        "hazmat",
}

_CRISIS_EMOJI = {
    "flooding":       "🌊",
    "earthquake":     "🌐",
    "fire":           "🔥",
    "heatwave":       "🌡",
    "hazmat":         "☢",
    "medical":        "🏥",
    "civil_unrest":   "⚠",
    "accident":       "🚧",
    "infrastructure": "⚡",
    "utility_outage": "💡",
    "crime":          "🚨",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _fetch_gdacs_rss(client: httpx.AsyncClient) -> list:
    try:
        r = await client.get(GDACS_RSS_URL, timeout=10.0)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[incidents] GDACS RSS failed: {e}")
        return []

    incidents = []
    for item in root.findall(".//item"):
        alert  = item.findtext("gdacs:alertlevel", "Green", _GDACS_NS)
        etype  = item.findtext("gdacs:eventtype",  "",      _GDACS_NS)
        country = item.findtext("gdacs:country",   "Unknown", _GDACS_NS)
        title  = item.findtext("title", "")
        pub    = item.findtext("pubDate", "")
        event_id = item.findtext("gdacs:eventid",  "", _GDACS_NS)
        episode  = item.findtext("gdacs:episodeid","", _GDACS_NS)

        # Only include Orange/Red and non-drought Green events
        if alert == "Green" and etype == "DR":
            continue

        crisis_t = _GDACS_TYPE_MAP.get(etype, "unknown")
        severity = _GDACS_SEVERITY.get(alert, "Medium")
        emoji    = _CRISIS_EMOJI.get(crisis_t, "🆘")

        try:
            date_iso = parsedate_to_datetime(pub).isoformat() if pub else _now_iso()
        except Exception:
            date_iso = _now_iso()

        # Take first country when multiple listed
        first_country = country.split(",")[0].strip()

        report_text = (
            f"{crisis_t.title()} emergency in {first_country}. {title}. "
            f"GDACS {alert} alert issued. Assess the situation and coordinate emergency response."
        )

        incidents.append({
            "id":          f"gdacs_{episode}_{event_id}",
            "title":       title,
            "location":    first_country,
            "country":     first_country,
            "crisis_type": crisis_t,
            "severity":    severity,
            "date_iso":    date_iso,
            "source":      "GDACS",
            "emoji":       emoji,
            "description": f"{alert} alert · {etype} · {first_country}",
            "report_text": report_text,
        })

    return incidents


async def _fetch_usgs(client: httpx.AsyncClient) -> list:
    try:
        r = await client.get(USGS_URL, timeout=10.0)
        r.raise_for_status()
        features = r.json().get("features", [])
    except Exception as e:
        print(f"[incidents] USGS failed: {e}")
        return []

    incidents = []
    for f in features[:10]:
        props  = f.get("properties", {})
        title  = props.get("title", "")
        mag    = props.get("mag")
        place  = props.get("place", "")
        ts_ms  = props.get("time", 0)
        eq_id  = f.get("id", "")

        if mag is None:
            continue

        mag_f = float(mag)
        if mag_f >= 7.0:
            severity = "Critical"
        elif mag_f >= 6.0:
            severity = "High"
        elif mag_f >= 5.0:
            severity = "Medium"
        else:
            severity = "Low"

        try:
            date_iso = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
        except Exception:
            date_iso = _now_iso()

        country = _extract_country_from_place(place)
        report_text = (
            f"Magnitude {mag_f:.1f} earthquake {place}. "
            f"USGS has recorded a significant seismic event. "
            f"Assess structural damage, casualties, and coordinate emergency response."
        )

        incidents.append({
            "id":          f"usgs_{eq_id}",
            "title":       title,
            "location":    place,
            "country":     country,
            "crisis_type": "earthquake",
            "severity":    severity,
            "date_iso":    date_iso,
            "source":      "USGS",
            "emoji":       "🌐",
            "description": f"M{mag_f:.1f} · {place}",
            "report_text": report_text,
        })

    return incidents


async def _fetch_eonet(client: httpx.AsyncClient) -> list:
    try:
        r = await client.get(EONET_URL, timeout=10.0)
        r.raise_for_status()
        events = r.json().get("events", [])
    except Exception as e:
        print(f"[incidents] NASA EONET failed: {e}")
        return []

    incidents = []
    for e in events[:10]:
        title  = e.get("title", "")
        cats   = e.get("categories", [])
        cat    = cats[0].get("title", "") if cats else ""
        geoms  = e.get("geometry", [])
        geo    = geoms[-1] if geoms else {}
        date_iso = geo.get("date", _now_iso())
        event_id = e.get("id", "")

        crisis_t = _EONET_TYPE_MAP.get(cat, "unknown")
        emoji    = _CRISIS_EMOJI.get(crisis_t, "🆘")

        # Infer country from title best-effort
        country = title.split(",")[-1].strip() if "," in title else "Global"

        report_text = (
            f"{cat} event: {title}. "
            f"NASA EONET open event. Assess impact and coordinate appropriate emergency response."
        )

        incidents.append({
            "id":          f"eonet_{event_id}",
            "title":       title,
            "location":    country,
            "country":     country,
            "crisis_type": crisis_t,
            "severity":    "Medium",
            "date_iso":    date_iso,
            "source":      "NASA EONET",
            "emoji":       emoji,
            "description": f"{cat} · NASA EONET",
            "report_text": report_text,
        })

    return incidents


def _extract_country_from_place(place: str) -> str:
    if not place:
        return "Unknown"
    parts = place.split(",")
    if len(parts) >= 2:
        return parts[-1].strip()
    return place.strip()


_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


async def fetch_latest_incidents(limit: int = 5) -> list:
    """Fetch, merge, deduplicate, and rank latest global crisis incidents."""
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _fetch_gdacs_rss(client),
            _fetch_usgs(client),
            _fetch_eonet(client),
            return_exceptions=True,
        )

    all_incidents = []
    for r in results:
        if isinstance(r, list):
            all_incidents.extend(r)

    # Sort: severity first (Critical before High), then by date (newest first)
    all_incidents.sort(
        key=lambda x: (
            _SEVERITY_ORDER.get(x.get("severity", "Medium"), 2),
            -(0 if not x.get("date_iso") else _parse_ts(x["date_iso"])),
        )
    )

    # Deduplicate by (country + crisis_type) — keep first (highest severity)
    seen: set = set()
    deduped = []
    for inc in all_incidents:
        key = (inc.get("country", "").lower(), inc.get("crisis_type", "").lower())
        if key not in seen:
            seen.add(key)
            deduped.append(inc)

    return deduped[:limit]


def _parse_ts(iso: str) -> float:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0
