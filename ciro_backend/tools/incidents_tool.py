"""
Global crisis incidents feed — merges ReliefWeb, GDACS, and USGS into a
single ranked list for the /incidents endpoint.
"""
import asyncio
import httpx
from datetime import datetime, timedelta, timezone

RELIEFWEB_URL = "https://api.reliefweb.int/v1/disasters"
GDACS_URL     = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS"
USGS_URL      = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"

# ReliefWeb disaster type → CIRO crisis_type
_RW_TYPE_MAP = {
    "Flood":              "flooding",
    "Flash Flood":        "flooding",
    "Tropical Cyclone":   "flooding",
    "Typhoon":            "flooding",
    "Hurricane":          "flooding",
    "Storm Surge":        "flooding",
    "Earthquake":         "earthquake",
    "Tsunami":            "earthquake",
    "Volcano":            "hazmat",
    "Wild Fire":          "fire",
    "Wildfire":           "fire",
    "Forest Fires":       "fire",
    "Drought":            "heatwave",
    "Cold Wave":          "heatwave",
    "Heat Wave":          "heatwave",
    "Epidemic":           "medical",
    "Disease":            "medical",
    "Conflict":           "civil_unrest",
    "Landslide":          "accident",
    "Mudslide":           "accident",
    "Chemical Hazard":    "hazmat",
    "Industrial Accident":"hazmat",
    "Power Outage":       "utility_outage",
}

# ReliefWeb disaster type → severity
_RW_SEVERITY = {
    "Earthquake":       "Critical",
    "Tsunami":          "Critical",
    "Tropical Cyclone": "Critical",
    "Typhoon":          "Critical",
    "Hurricane":        "Critical",
    "Flood":            "High",
    "Flash Flood":      "High",
    "Volcano":          "High",
    "Wild Fire":        "High",
    "Wildfire":         "High",
    "Forest Fires":     "High",
    "Epidemic":         "High",
    "Conflict":         "High",
    "Landslide":        "High",
    "Mudslide":         "High",
    "Drought":          "Medium",
    "Cold Wave":        "Medium",
    "Heat Wave":        "Medium",
    "Disease":          "Medium",
    "Chemical Hazard":  "High",
    "Power Outage":     "Medium",
}

# GDACS event code → CIRO crisis_type
_GDACS_TYPE_MAP = {
    "EQ": "earthquake",
    "TC": "flooding",
    "FL": "flooding",
    "VO": "hazmat",
    "WF": "fire",
    "DR": "heatwave",
}

# GDACS alert level → severity
_GDACS_SEVERITY = {
    "Red":    "Critical",
    "Orange": "High",
    "Green":  "Medium",
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


async def _fetch_reliefweb(client: httpx.AsyncClient) -> list:
    params = {
        "appname": "ciro",
        "profile": "list",
        "preset":  "latest",
        "slim":    "1",
        "limit":   "10",
        "fields[include][]": ["name", "date.created", "country", "type", "status"],
    }
    try:
        r = await client.get(RELIEFWEB_URL, params=params, timeout=10.0)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception as e:
        print(f"[incidents] ReliefWeb failed: {e}")
        return []

    incidents = []
    for item in data:
        fields  = item.get("fields", {})
        name    = fields.get("name", "")
        status  = fields.get("status", "")
        if status not in ("ongoing", "alert", "current"):
            continue

        countries = fields.get("country", [])
        country   = countries[0].get("name", "Unknown") if countries else "Unknown"

        types    = fields.get("type", [])
        rw_type  = types[0].get("name", "") if types else ""
        crisis_t = _RW_TYPE_MAP.get(rw_type, "unknown")
        severity = _RW_SEVERITY.get(rw_type, "Medium")

        date_created = (fields.get("date") or {}).get("created", _now_iso())

        emoji = _CRISIS_EMOJI.get(crisis_t, "🆘")
        report_text = (
            f"{rw_type or crisis_t.title()} emergency in {country}. "
            f"{name}. Ongoing situation requires coordinated response. "
            f"Assess severity and deploy appropriate emergency resources."
        )

        incidents.append({
            "id":         f"rw_{item.get('id', '')}",
            "title":      name,
            "location":   country,
            "country":    country,
            "crisis_type": crisis_t,
            "severity":   severity,
            "date_iso":   date_created,
            "source":     "ReliefWeb",
            "emoji":      emoji,
            "description": f"{rw_type} · {status} · {country}",
            "report_text": report_text,
        })

    return incidents


async def _fetch_gdacs(client: httpx.AsyncClient) -> list:
    from_d = datetime.utcnow() - timedelta(days=30)
    to_d   = datetime.utcnow()
    params = {
        "eventtypes": "EQ,TC,FL,VO,WF",
        "fromDate":   from_d.strftime("%Y-%m-%d"),
        "toDate":     to_d.strftime("%Y-%m-%d"),
    }
    try:
        r = await client.get(GDACS_URL, params=params, timeout=10.0)
        r.raise_for_status()
        features = r.json().get("features", [])
    except Exception as e:
        print(f"[incidents] GDACS failed: {e}")
        return []

    incidents = []
    for f in features[:10]:
        props     = f.get("properties", {})
        etype     = props.get("eventtype", "")
        country   = props.get("country", "Unknown")
        alert     = props.get("alertlevel", "Green")
        name      = props.get("eventname") or props.get("name") or f"{etype} event in {country}"
        date_str  = props.get("todate") or props.get("fromdate") or _now_iso()
        episode   = props.get("episodeid", "")
        event_id  = props.get("eventid", "")

        crisis_t = _GDACS_TYPE_MAP.get(etype, "unknown")
        severity = _GDACS_SEVERITY.get(alert, "Medium")
        emoji    = _CRISIS_EMOJI.get(crisis_t, "🆘")

        try:
            date_iso = datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except Exception:
            date_iso = _now_iso()

        report_text = (
            f"{crisis_t.title()} emergency in {country}. {name}. "
            f"GDACS {alert} alert issued. Assess the situation and coordinate emergency response."
        )

        incidents.append({
            "id":          f"gdacs_{episode}_{event_id}",
            "title":       name,
            "location":    country,
            "country":     country,
            "crisis_type": crisis_t,
            "severity":    severity,
            "date_iso":    date_iso,
            "source":      "GDACS",
            "emoji":       emoji,
            "description": f"{alert} alert · {etype} · {country}",
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
        props   = f.get("properties", {})
        title   = props.get("title", "")
        mag     = props.get("mag")
        place   = props.get("place", "")
        ts_ms   = props.get("time", 0)
        eq_id   = f.get("id", "")

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


def _extract_country_from_place(place: str) -> str:
    """Best-effort country extraction from USGS place string like '10km NE of City, Country'."""
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
            _fetch_reliefweb(client),
            _fetch_gdacs(client),
            _fetch_usgs(client),
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
            -(0 if not x.get("date_iso") else
              _parse_ts(x["date_iso"])),
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
