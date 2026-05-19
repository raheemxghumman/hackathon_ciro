import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional

GDELT_URL   = "https://api.gdelt.project/v2/doc/doc"
EONET_URL   = "https://eonet.gsfc.nasa.gov/api/v3/events"
GDACS_URL   = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS"

# GDELT keyword clusters per event type
_GDELT_KW = {
    "flooding":       "flood OR flooding OR inundation",
    "fire":           "fire OR blaze OR wildfire",
    "earthquake":     "earthquake OR tremor OR seismic",
    "accident":       "accident OR collision OR crash",
    "civil_unrest":   "protest OR unrest OR riot OR clashes",
    "hazmat":         "hazmat OR chemical spill OR toxic leak",
    "crime":          "shooting OR attack OR violence OR crime",
    "medical":        "epidemic OR outbreak OR health emergency OR medical",
    "heatwave":       "heatwave OR heat wave OR extreme heat",
    "infrastructure": "power outage OR bridge collapse OR infrastructure failure",
    "unknown":        "emergency OR disaster OR crisis",
}

# NASA EONET category IDs
_EONET_CAT = {
    "flooding":   12,
    "fire":        8,
    "earthquake": 16,
    "heatwave":   19,
}

# GDACS event type codes
_GDACS_TYPE = {
    "earthquake": "EQ",
    "flooding":   "FL",
    "fire":       "WF",
    "heatwave":   "DR",
}


async def _gdelt(query: str, days: int = 3) -> dict:
    params = {
        "query":      query,
        "mode":       "artlist",
        "maxrecords": "5",
        "format":     "json",
        "timespan":   f"{days}d",
        "sort":       "DateDesc",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(GDELT_URL, params=params)
            r.raise_for_status()
            articles = r.json().get("articles", [])
            return {
                "matched": len(articles) > 0,
                "count":   len(articles),
                "items": [
                    {
                        "title":  a.get("title", ""),
                        "source": a.get("domain", ""),
                        "date":   a.get("seendate", ""),
                    }
                    for a in articles[:3]
                ],
            }
    except Exception as e:
        return {"matched": False, "error": str(e)}


async def _eonet(lat: float, lng: float, event_type: str, days: int = 7) -> dict:
    cat = _EONET_CAT.get(event_type)
    if not cat:
        return {"matched": False, "skipped": True}
    params: dict = {
        "status":   "open",
        "days":     str(days),
        "bbox":     f"{lng-2},{lat-2},{lng+2},{lat+2}",
        "category": str(cat),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(EONET_URL, params=params)
            r.raise_for_status()
            events = r.json().get("events", [])
            return {
                "matched": len(events) > 0,
                "count":   len(events),
                "items": [
                    {
                        "title":    e.get("title", ""),
                        "category": (e.get("categories") or [{}])[0].get("title", ""),
                        "date":     (e.get("geometry") or [{}])[0].get("date", ""),
                    }
                    for e in events[:3]
                ],
            }
    except Exception as e:
        return {"matched": False, "error": str(e)}


async def _gdacs(lat: float, lng: float, event_type: str, days: int = 7) -> dict:
    gdacs_type = _GDACS_TYPE.get(event_type)
    if not gdacs_type:
        return {"matched": False, "skipped": True}
    to_d   = datetime.utcnow()
    from_d = to_d - timedelta(days=days)
    params = {
        "eventtypes": gdacs_type,
        "fromDate":   from_d.strftime("%Y-%m-%d"),
        "toDate":     to_d.strftime("%Y-%m-%d"),
        "bbox":       f"{lng-3},{lat-3},{lng+3},{lat+3}",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(GDACS_URL, params=params)
            r.raise_for_status()
            features = r.json().get("features", [])
            return {
                "matched": len(features) > 0,
                "count":   len(features),
                "items": [
                    {
                        "title":    f.get("properties", {}).get("eventname", ""),
                        "severity": f.get("properties", {}).get("alertlevel", ""),
                        "date":     f.get("properties", {}).get("fromdate", ""),
                    }
                    for f in features[:3]
                ],
            }
    except Exception as e:
        return {"matched": False, "error": str(e)}


async def verify_incident(
    location:   str,
    event_type: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict:
    """Cross-reference a reported incident against GDELT, NASA EONET, and GDACS.

    Returns a verification dict with confidence level, matched sources, and
    top news items so the report can show whether the incident is corroborated
    by independent public data feeds.
    """
    etype = (event_type or "unknown").lower()
    kw    = _GDELT_KW.get(etype, "emergency OR disaster")

    tasks: dict = {"GDELT": _gdelt(f"{kw} {location}")}

    has_coords = lat is not None and lng is not None
    if has_coords and etype in _EONET_CAT:
        tasks["NASA_EONET"] = _eonet(lat, lng, etype)
    if has_coords and etype in _GDACS_TYPE:
        tasks["GDACS"] = _gdacs(lat, lng, etype)

    names  = list(tasks.keys())
    values = await asyncio.gather(*tasks.values(), return_exceptions=True)
    sources: dict = {}
    for name, val in zip(names, values):
        sources[name] = val if not isinstance(val, Exception) else {"matched": False, "error": str(val)}

    matched = [s for s, r in sources.items() if r.get("matched")]
    total   = len(sources)

    if len(matched) >= 2:
        confidence = "high"
    elif len(matched) == 1:
        confidence = "medium"
    else:
        confidence = "unverified"

    if matched:
        summary = (
            f"Corroborated by {len(matched)} of {total} source(s) checked: "
            f"{', '.join(matched)}. Independent feeds confirm activity consistent with this report."
        )
    else:
        summary = (
            f"No corroborating data found across {total} public feed(s). "
            "Incident may be too localised, too recent (GDELT has a ~15 min indexing delay), "
            "or below the threshold for international reporting."
        )

    return {
        "verified":        len(matched) > 0,
        "confidence":      confidence,
        "matched_sources": matched,
        "total_sources":   total,
        "summary":         summary,
        "sources":         sources,
    }
