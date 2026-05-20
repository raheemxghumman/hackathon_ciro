import os
import re
import json
import traceback
from dotenv import load_dotenv
import groq

from mock_signals import (
    get_real_weather,
    get_real_traffic,
    get_real_earthquake,
    get_social_media_signal,
)
from tools.maps_tool import get_route_alternatives, geocode_location

load_dotenv()

api_keys_str = os.getenv("GROQ_API_KEYS", "")
GROQ_API_KEYS = [key.strip() for key in api_keys_str.split(",") if key.strip()]
current_key_index = 0

MODEL = "llama-3.3-70b-versatile"


def parse_json(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON found")
    return json.loads(text[start:end])


def call_groq(prompt: str) -> str:
    global current_key_index
    if not GROQ_API_KEYS:
        raise ValueError("No GROQ_API_KEYS found in environment.")

    for attempt in range(len(GROQ_API_KEYS)):
        try:
            client = groq.Groq(api_key=GROQ_API_KEYS[current_key_index])
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except groq.RateLimitError:
            print(f"Rate limit hit for key index {current_key_index}. Rotating...")
            current_key_index = (current_key_index + 1) % len(GROQ_API_KEYS)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
                print(f"Rate limit (429) hit for key index {current_key_index}. Rotating...")
                current_key_index = (current_key_index + 1) % len(GROQ_API_KEYS)
            else:
                raise e

    raise Exception("All Groq API keys exhausted or rate limited.")


def call_llm(prompt: str) -> str:
    return call_groq(prompt)


async def _extract_location(raw_text: str) -> str:
    """Fast first-pass extraction of a place name from the citizen report.
    Used to scope live signals BEFORE running the full ingest agent. Falls
    back to 'Islamabad' if no location can be found."""
    try:
        prompt = (
            "Extract the most specific geographic location mentioned in the "
            "following crisis report. The location can be anywhere in the "
            "world — a city, country, neighborhood, district, sector, "
            "landmark, or coordinates. The input may be English, Urdu, Roman "
            "Urdu, Chinese, Spanish, Arabic, or any other language.\n\n"
            f"REPORT: {raw_text}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            '{"location": "specific place name like \'G-10 Islamabad\', \'Beijing\', '
            "'Shibuya Tokyo', 'Manhattan New York'\", "
            '"is_specific": true}\n'
            "If no location is mentioned, return "
            '{"location": "Islamabad", "is_specific": false}'
        )
        out = parse_json(call_llm(prompt))
        loc = (out.get("location") or "").strip()
        return loc or "Islamabad"
    except Exception:
        return "Islamabad"


async def ingest_signal(raw_text: str) -> dict:
    """Stage 1 — parse a citizen report and enrich it with live signals
    (weather + traffic + earthquake) scoped to the reported location.

    Supports any location globally; falls back to Islamabad when no specific
    place is mentioned.
    """
    location_hint = await _extract_location(raw_text)
    geo = await geocode_location(location_hint)

    weather = await get_real_weather(location_hint)
    traffic = await get_real_traffic(location_hint)
    earthquake = await get_real_earthquake(location_hint)
    social = get_social_media_signal(raw_text)

    country = (geo or {}).get("country") if geo else weather.get("country")

    weather_json = json.dumps(weather)
    traffic_json = json.dumps(traffic)
    earthquake_json = json.dumps(earthquake)
    social_json = json.dumps(social)

    try:
        prompt = f"""You are CIRO's crisis signal parser. CIRO has GLOBAL coverage — the citizen
report may describe an emergency anywhere in the world. You understand many
languages (English, Urdu, Roman Urdu, Spanish, Arabic, Mandarin, Hindi, etc.).

SOURCE 1 — Citizen Report (PRIMARY EVENT — what is actually happening):
{raw_text}

SOURCE 2 — Weather API (ambient context near reported location):
{weather_json}

SOURCE 3 — Traffic API (live Google Maps congestion near reported location):
{traffic_json}

SOURCE 4 — USGS Earthquake feed (recent quakes within 500km of reported location):
{earthquake_json}

SOURCE 5 — Social Media (amplification signal — corroborates citizen volume):
{social_json}

GEOCODING HINT (from Google Maps): country = "{country}",
formatted_address = "{(geo or {}).get('formatted_address')}"

CRITICAL RULES:
1. The PRIMARY event_type comes from SOURCE 1 (citizen report). Never let
   ambient traffic/weather override the citizen's claim.
2. If the citizen mentions an earthquake / tremor / "zalzala" / "地震" /
   shaking buildings, classify event_type = "earthquake" and let USGS data
   corroborate severity.
3. Detect the location at the most specific level available (district,
   sector, neighborhood, city). Include the country at the end if the
   place is outside Pakistan.
4. The "location" field MUST be globally unambiguous — e.g.
   "G-10 Islamabad, Pakistan", "Shibuya, Tokyo, Japan",
   "Manhattan, New York, USA". Do NOT return "Unknown" or "out of scope" —
   use the most specific place mentioned in the report, or the country
   hint above. Never refuse a location just because it's outside Pakistan.

DESTINATION EXTRACTION:
If the citizen explicitly mentions a destination they want traffic
rerouted TO (look for phrases like "reroute to X", "send to X",
"divert to X", "redirect towards X", "ja sakte hain X tak",
"alternative is X"), capture it as `requested_destination`. Otherwise
return null. Examples:
  - "Brand Road Multan blocked, reroute to Royal Orchard" → "Royal Orchard, Multan, Pakistan"
  - "Accident on Kashmir Hwy, divert to F-10" → "F-10, Islamabad, Pakistan"
  - "Flood in G-10" (no destination mentioned) → null

Return ONLY valid JSON:
{{
  "location": "specific globally-unambiguous place name (city, sector + country)",
  "country": "country name from geocoding hint or inferred from the report",
  "province_or_state": "for Pakistan return one of: Punjab/Sindh/Khyber Pakhtunkhwa/Balochistan/Islamabad Capital Territory/Gilgit-Baltistan/Azad Kashmir. For other countries return state/province/region if known, else null",
  "requested_destination": "destination string if mentioned in the report, else null",
  "event_type": "one of: flooding/accident/heatwave/earthquake/infrastructure/hazmat/crime/medical/fire/civil_unrest/utility_outage/unknown",
  "event_subtype": "more specific descriptor (e.g. robbery, heart_attack, flash_flood, aftershock)",
  "language_detected": "language of the report (e.g. english, urdu, roman_urdu, mixed, mandarin, spanish)",
  "urgency_level": "one of: immediate/urgent/moderate",
  "cleaned_text": "1-sentence normalized English summary of the citizen's report ONLY",
  "sources_count": 5,
  "weather_context": "one sentence on whether ambient weather is relevant to the reported event",
  "traffic_context": "one sentence on whether ambient traffic is relevant to the reported event",
  "earthquake_context": "one sentence on whether USGS data corroborates or contextualises the event",
  "corroborating_signals": true
}}
Return ONLY valid JSON. No markdown, no explanation."""
        result = parse_json(call_llm(prompt))
    except Exception:
        print(f"ERROR in ingest_signal: {traceback.format_exc()}")
        result = {
            "location": location_hint,
            "country": country or "Unknown",
            "event_type": "unknown",
            "language_detected": "unknown",
            "urgency_level": "moderate",
            "cleaned_text": raw_text,
        }

    # Always pass the resolved country forward so downstream agents can pick
    # the right emergency services.
    if not result.get("country") and country:
        result["country"] = country

    result["weather_signal"] = weather
    result["traffic_signal"] = traffic
    result["earthquake_signal"] = earthquake
    result["social_signal"] = social
    result["geocode"] = geo
    return result


async def detect_crisis(signal: dict) -> dict:
    try:
        prompt = f"""You are CIRO's crisis severity classifier. CIRO operates globally — the
crisis may be in any city or country.

Given this parsed signal: {json.dumps(signal)}

CRITICAL RULES:
- The event_type field is authoritative. event_type="crime" → "Armed
  Robbery" or "Robbery in Progress", NOT a traffic incident.
- event_type="earthquake" → use USGS earthquake_signal to inform severity.
  If max_magnitude >= 6.0, severity is "Critical"; 5.0–5.9 "High";
  4.0–4.9 "Medium"; <4.0 "Low" unless local damage is reported.
- Impact_analysis MUST match the actual event. An earthquake has impacts
  like "Building collapse risk", "Aftershock danger", "Casualty triage",
  NOT "Traffic congestion".
- Confidence reflects how strongly the corroborating signals align with the
  primary citizen report.

Return ONLY valid JSON, no markdown, no explanation:
{{
  "crisis_type": "descriptive name matching the event_type (e.g. Armed Robbery, Urban Flooding, Major Earthquake)",
  "location": "specific place from the signal (include country if outside Pakistan)",
  "severity": "one of: Low/Medium/High/Critical",
  "confidence_percent": 85,
  "reasoning": "2-3 sentence explanation citing the citizen report and ONLY signals relevant to this event type",
  "impact_analysis": ["impact 1 specific to this event type", "impact 2", "impact 3"],
  "requires_immediate_action": true
}}"""
        return parse_json(call_llm(prompt))
    except Exception:
        print(f"ERROR in detect_crisis: {traceback.format_exc()}")
        return {
            "crisis_type": "Unknown",
            "severity": "Low",
            "confidence_percent": 0,
            "reasoning": "Unable to classify — fallback used due to upstream error.",
            "impact_analysis": [],
            "requires_immediate_action": False,
        }


def _agency_directory(country, province=None, location=None) -> str:
    """Return a jurisdiction-appropriate agency directory the planner can
    pick from. For Pakistan we resolve by province (so Multan gets Punjab
    Police, not Islamabad Police). For everywhere else we instruct the LLM
    to use the actual agency names operating in that specific city.
    """
    if country and country.lower() in {"pakistan", "pak", "pk"}:
        prov = (province or "").lower()

        if "punjab" in prov:
            return (
                "AGENCIES (Punjab Province, Pakistan — use ONLY these for crises in "
                "Lahore / Multan / Faisalabad / Rawalpindi / Gujranwala / Bahawalpur / Sialkot etc.):\n"
                "  - Punjab Police (Emergency 15) — crime, robbery, security, civil unrest\n"
                "  - Punjab Highway Patrol / City Traffic Police — traffic disruption, rerouting\n"
                "  - Punjab Emergency Service (Rescue 1122) — medical, accidents, rescues\n"
                "  - Punjab Fire & Rescue Service (Emergency 16) — fires, hazmat\n"
                "  - PDMA Punjab — disaster response, public alerts, earthquakes\n"
                "  - WASA / Local Municipal Corporation — water, sewerage, infrastructure\n"
                "  - Edhi Ambulance Service — mass casualty support\n"
                "  - Bomb Disposal Squad Punjab — explosive threats\n"
                "DO NOT use 'Islamabad Police' or 'Islamabad Traffic Police' for Punjab crises."
            )
        if "sindh" in prov:
            return (
                "AGENCIES (Sindh Province, Pakistan — use ONLY these for crises in "
                "Karachi / Hyderabad / Sukkur / Larkana etc.):\n"
                "  - Sindh Police (Emergency 15) — crime, security, civil unrest\n"
                "  - Karachi Traffic Police / Sindh Traffic Police — traffic disruption\n"
                "  - Sindh Rescue 1122 — medical, accidents, rescues\n"
                "  - Karachi Fire Brigade (Emergency 16) — fires, hazmat\n"
                "  - PDMA Sindh — disaster response, public alerts\n"
                "  - KWSB / Sindh PHED — water, sewerage, infrastructure (Karachi: KMC)\n"
                "  - Edhi / Chhipa Ambulance — medical transport\n"
                "DO NOT use 'Islamabad Police' for Sindh crises."
            )
        if "khyber" in prov or prov in {"kp", "kpk"}:
            return (
                "AGENCIES (Khyber Pakhtunkhwa, Pakistan — use ONLY these for crises in "
                "Peshawar / Mardan / Abbottabad / Swat / Mingora etc.):\n"
                "  - KP Police (Emergency 15) — crime, security\n"
                "  - KP Traffic Police — traffic disruption\n"
                "  - Rescue 1122 KP — medical, accidents, rescues\n"
                "  - KP Fire Service — fires, hazmat\n"
                "  - PDMA KP — disaster response, earthquakes\n"
                "  - TMA / WSSP Peshawar — water, infrastructure\n"
                "DO NOT use 'Islamabad Police' for KP crises."
            )
        if "balochistan" in prov:
            return (
                "AGENCIES (Balochistan, Pakistan — use ONLY these for crises in "
                "Quetta / Gwadar / Turbat etc.):\n"
                "  - Balochistan Police (Emergency 15)\n"
                "  - Balochistan Traffic Police\n"
                "  - Balochistan Levies (rural areas)\n"
                "  - Rescue 1122 Balochistan (where active) / Civil Defence\n"
                "  - PDMA Balochistan — disaster response\n"
                "  - Quetta Metropolitan Corporation — water, infrastructure\n"
            )
        if "gilgit" in prov or "azad" in prov or "kashmir" in prov:
            region = "Gilgit-Baltistan" if "gilgit" in prov else "Azad Kashmir (AJK)"
            return (
                f"AGENCIES ({region}, Pakistan — use ONLY these for crises in this region):\n"
                f"  - {region} Police (Emergency 15)\n"
                f"  - {region} Traffic Police\n"
                f"  - Rescue 1122 ({region}) — medical, rescues, mountaineering incidents\n"
                f"  - GBDMA / SDMA — disaster response\n"
                f"  - Civil Defence — search and rescue, earthquake response\n"
            )
        # Default to Islamabad Capital Territory agencies.
        return (
            "AGENCIES (Islamabad Capital Territory, Pakistan):\n"
            "  - Islamabad Police (Emergency 15) — crime, robbery, security\n"
            "  - Islamabad Traffic Police (ITP) — traffic disruption, rerouting\n"
            "  - Rescue 1122 ICT (Emergency 1122) — medical, accidents, rescues\n"
            "  - Islamabad Fire Brigade (Emergency 16) — fires, hazmat\n"
            "  - NDMA — federal disaster coordination, earthquakes\n"
            "  - CDA / WASA Islamabad — infrastructure, water, sewerage\n"
            "  - Edhi Ambulance Service — medical transport, mass casualty\n"
            "  - Bomb Disposal Squad ICT — explosive threats\n"
        )

    # Global — generic directory + strong instruction to use the actual
    # agency name for that specific city/state.
    label = country or "the affected country"
    loc_hint = f" The crisis is in '{location}'." if location else ""
    prov_hint = f" State/province: '{province}'." if province else ""
    return (
        f"AGENCIES ({label}).{loc_hint}{prov_hint}\n"
        f"You MUST use the real, jurisdiction-correct agency names that "
        f"actually operate in this specific city/state — NEVER use generic "
        f"placeholders like 'Local Police' if you can identify the real one.\n\n"
        f"Examples of correct city-specific names:\n"
        f"  - New York City → NYPD, FDNY, NYC EMS, NYC DOT, OEM\n"
        f"  - London → Metropolitan Police, London Fire Brigade, London Ambulance Service, TfL\n"
        f"  - Tokyo → Tokyo Metropolitan Police, Tokyo Fire Department, JMA\n"
        f"  - Mumbai → Mumbai Police, Mumbai Fire Brigade, 108 Ambulance, MCGM\n"
        f"  - Shanghai → Shanghai Public Security Bureau, Shanghai Fire Department\n"
        f"  - Istanbul → Istanbul Police Department, IBB Fire Brigade, 112 Ambulance\n"
        f"  - Cairo → Egyptian National Police, Cairo Civil Defence, 123 Ambulance\n"
        f"  - Lagos → Nigeria Police Force Lagos, LASEMA, Lagos State Fire Service\n\n"
        f"Category mapping (use country/city-correct names):\n"
        f"  - Police / Security — crime, civil unrest\n"
        f"  - Fire & Rescue / Civil Defence — fires, hazmat, structural collapse\n"
        f"  - Emergency Medical Services / Ambulance — medical\n"
        f"  - Disaster Management Authority — earthquakes, floods, large coordination\n"
        f"  - Traffic Authority / Highway Patrol — traffic disruption\n"
        f"  - Public Works / Utility Provider — infrastructure, water, power\n"
        f"  - Search & Rescue Teams — collapsed structures, mountaineering"
    )


async def plan_response(detection: dict, country=None, province=None) -> dict:
    try:
        location = detection.get("location")
        directory = _agency_directory(country, province=province, location=location)
        prompt = f"""You are CIRO's emergency response coordinator. CIRO operates globally —
the crisis is in {country or 'the country mentioned in the detection'}.

{directory}

ACTION TYPE GUIDANCE — pick action_type values that match the crisis:
  - Crime/Robbery: police_dispatch, armed_response, scene_lockdown, public_safety_alert
  - Medical: medical_dispatch, ambulance_dispatch, hospital_prep
  - Fire: fire_dispatch, evacuation, hazmat_response
  - Flooding/Accident: traffic_reroute, emergency_dispatch, public_alert
  - Earthquake: search_and_rescue, structural_assessment, public_alert,
    evacuation, medical_dispatch, aftershock_advisory
  - Civil unrest: police_dispatch, crowd_control, public_safety_alert

RULES:
1. Generate ONLY actions that make sense for THIS crisis. A robbery does NOT
   need a traffic_reroute action. A medical emergency does NOT need crowd
   control.
2. action_type="traffic_reroute" ONLY when the crisis is actually blocking
   or causing traffic disruption.
3. For earthquakes, FIRST action should be search_and_rescue + public alert.
4. Use agency names appropriate to the country — e.g. for Japan say "Tokyo
   Fire Department" not "Islamabad Fire Brigade".

Given this crisis: {json.dumps(detection)}

Return ONLY valid JSON, no markdown, no explanation:
{{
  "overall_strategy": "1-2 sentence strategy specific to this crisis type and country",
  "actions": [
    {{"action_id": "ACT-001", "action_type": "appropriate_type", "description": "specific action", "responsible_agency": "country-appropriate agency name", "priority": "P1", "estimated_time_minutes": 5}},
    {{"action_id": "ACT-002", "action_type": "appropriate_type", "description": "specific action", "responsible_agency": "country-appropriate agency name", "priority": "P1", "estimated_time_minutes": 10}},
    {{"action_id": "ACT-003", "action_type": "appropriate_type", "description": "specific action", "responsible_agency": "country-appropriate agency name", "priority": "P2", "estimated_time_minutes": 2}}
  ],
  "public_advisory": "short citizen-facing message appropriate for this crisis and locale"
}}"""
        result = parse_json(call_llm(prompt))
        blocked = detection.get("location") or "the affected area"

        # Only fetch route alternatives when the plan actually contains a
        # traffic_reroute action. For crimes, medical events, earthquakes
        # without road blockage etc. we skip the map entirely.
        needs_route = any(
            a.get("action_type") == "traffic_reroute"
            for a in result.get("actions", [])
        )
        if needs_route:
            requested_dest = detection.get("requested_destination")
            origin_geo = await geocode_location(blocked)

            # Try the citizen-specified destination first. If it resolves to
            # somewhere meaningfully different from the blocked area, use it.
            dest_geo = None
            if requested_dest:
                dest_geo = await geocode_location(requested_dest)
                # Reject the destination if it's basically the same place
                # (Google sometimes resolves both to the same city centre).
                if origin_geo and dest_geo:
                    dlat = abs(dest_geo["lat"] - origin_geo["lat"])
                    dlng = abs(dest_geo["lng"] - origin_geo["lng"])
                    if dlat < 0.005 and dlng < 0.005:
                        dest_geo = None

            if origin_geo and dest_geo:
                # User specified a real destination → use it.
                origin = f"{origin_geo['lat']},{origin_geo['lng']}"
                destination = f"{dest_geo['lat']},{dest_geo['lng']}"
                display_origin = origin_geo.get("formatted_address") or blocked
                display_destination = dest_geo.get("formatted_address") or requested_dest
            elif origin_geo:
                # No usable destination from the citizen → fall back to a
                # plausible safe corridor ~3-4 km away (close enough to feel
                # like a local reroute, far enough to be a real route).
                origin = f"{origin_geo['lat']},{origin_geo['lng']}"
                dest_lat = origin_geo["lat"] + 0.03
                dest_lng = origin_geo["lng"] + 0.03
                destination = f"{dest_lat},{dest_lng}"
                display_origin = origin_geo.get("formatted_address") or blocked
                display_destination = f"Nearby safe corridor (~4km from {blocked})"
            else:
                origin = blocked
                destination = blocked
                display_origin = blocked
                display_destination = blocked

            for action in result.get("actions", []):
                if action.get("action_type") == "traffic_reroute":
                    route_data = await get_route_alternatives(origin, destination, blocked)
                    # Drop any 0km/bogus routes; only attach the panel if at
                    # least one real alternative survives the filter.
                    alternatives = [
                        r for r in route_data.get("alternatives", [])
                        if (r.get("distance_km") or 0) > 0.3
                        and (r.get("eta_min") or 0) > 0
                    ]
                    if alternatives:
                        route_data["alternatives"] = alternatives
                        action["route_data"] = route_data
                        action["route_origin"] = display_origin
                        action["route_destination"] = display_destination
                        action["route_blocked_area"] = blocked

        # Inferred coordinates
        geo = origin_geo if 'origin_geo' in locals() and origin_geo else None
        if geo:
            coordinates = {"latitude": geo["lat"], "longitude": geo["lng"]}
        else:
            # Localized fallback grids based on location
            loc_lower = blocked.lower()
            if "lahore" in loc_lower:
                coordinates = {"latitude": 31.5204, "longitude": 74.3587}
            elif "karachi" in loc_lower:
                coordinates = {"latitude": 24.8607, "longitude": 67.0011}
            elif "rawalpindi" in loc_lower:
                coordinates = {"latitude": 33.5651, "longitude": 73.0169}
            elif "peshawar" in loc_lower:
                coordinates = {"latitude": 34.0151, "longitude": 71.5249}
            else:
                coordinates = {"latitude": 33.6844, "longitude": 73.0479}

        # Resource scaling based on crisis type & severity
        crisis_type = (detection.get("crisis_type") or "unknown").lower()
        severity = detection.get("severity") or "Medium"

        mult = 1
        if severity == "Low":
            mult = 1
        elif severity == "Medium":
            mult = 2
        elif severity == "High":
            mult = 4
        elif severity == "Critical":
            mult = 6

        base_res = {
            "ambulances": 1,
            "rescue_teams": 1,
            "police_units": 1,
            "drones": 1,
            "field_teams": 1,
            "shelters": 0,
            "generators": 0,
            "water_tankers": 0,
        }

        if any(w in crisis_type or w in blocked.lower() for w in ["flood", "rain", "water"]):
            base_res.update({
                "rescue_teams": 3, "ambulances": 2, "water_tankers": 2,
                "drones": 2, "shelters": 1, "generators": 1
            })
        elif "fire" in crisis_type or "smoke" in crisis_type:
            base_res.update({
                "rescue_teams": 3, "ambulances": 2, "police_units": 2, "water_tankers": 2
            })
        elif "earthquake" in crisis_type or "quake" in crisis_type:
            base_res.update({
                "rescue_teams": 4, "ambulances": 3, "shelters": 2, "generators": 2, "field_teams": 2
            })
        elif "accident" in crisis_type or "crash" in crisis_type:
            base_res.update({"ambulances": 2, "police_units": 2, "rescue_teams": 1})
        elif "unrest" in crisis_type or "riot" in crisis_type:
            base_res.update({"police_units": 4, "field_teams": 2, "drones": 2})
        elif "heatwave" in crisis_type or "garmi" in crisis_type:
            base_res.update({"ambulances": 2, "water_tankers": 3, "field_teams": 2, "shelters": 1})

        recommended_resources = {
            k: max(1 if k in ["ambulances", "rescue_teams", "police_units"] else 0, v * mult)
            for k, v in base_res.items()
        }

        # Dynamic stakeholder messages
        event_label = crisis_type.replace("_", " ").title()
        public_msg = f"SAFETY ADVISORY: A {severity} {event_label} has been reported in {blocked}. Please avoid the area, stay indoors, and follow emergency routes."
        police_msg = f"TACTICAL COMMAND: Establish a secure perimeter around {blocked}. Control traffic access and coordinate with local emergency responders."
        hospitals_msg = f"TRAUMA READINESS: Stand by for potential casualties from {blocked} due to {severity} {event_label}. Ensure emergency rooms are prepared."
        utility_msg = f"INFRASTRUCTURE SAFEGUARD: Inspect power lines, water supplies, and gas mains near {blocked} for potential outages or safety hazards."
        transport_msg = f"TRAFFIC REROUTING: Implement diversions around {blocked}. Reroute public transit and alert commuters of major delays."
        media_msg = f"PRESS BRIEF: CIRO is coordinating a multi-agency response to a {severity} {event_label} in {blocked}. Rescue and utility operations are underway."

        if "flood" in crisis_type or "rain" in crisis_type:
            public_msg = f"FLOOD WARNING: Severe flooding reported in {blocked}. Move to higher ground, avoid driving through water, and stay alert."
            utility_msg = f"POWER & WATER CONTROL: Secure electrical substations and monitor sewage drainage networks in {blocked} to prevent contamination."
        elif "fire" in crisis_type:
            public_msg = f"FIRE ADVISORY: Heavy smoke and fire at {blocked}. Evacuate adjacent buildings immediately, close windows, and yield to fire tenders."
            hospitals_msg = f"BURN UNIT WARNING: Prepare burn treatment facilities and maximize emergency supply intake for fire victims from {blocked}."
        elif "earthquake" in crisis_type:
            public_msg = f"EARTHQUAKE ALERT: Tremors felt. Watch out for aftershocks. Stay away from damaged structures and utility poles."
            utility_msg = f"GAS & GRID SHUTDOWN: Execute emergency gas valve shutdowns in {blocked} to prevent post-quake fires."

        stakeholder_messages = {
            "public": public_msg,
            "police": police_msg,
            "hospitals": hospitals_msg,
            "utility": utility_msg,
            "transport": transport_msg,
            "media": media_msg,
        }

        result["coordinates"] = coordinates
        result["recommended_resources"] = recommended_resources
        result["stakeholder_messages"] = stakeholder_messages

        return result
    except Exception:
        print(f"ERROR in plan_response: {traceback.format_exc()}")
        return {"overall_strategy": "Error", "actions": [], "public_advisory": "Error"}


async def execute_actions(plan: dict, country=None, province=None, location=None) -> dict:
    try:
        country_label = country or "the affected country"
        location_label = location or country_label
        prov_hint = f" (province/state: {province})" if province else ""
        prompt = f"""You are simulating emergency response execution in {location_label}{prov_hint}.
Given this plan: {json.dumps(plan)}

For each execution_log entry, include:
- ticket_id: a realistic agency mock id derived from the responsible_agency.
  ALWAYS make the prefix match the actual agency that issued the ticket.
  Examples:
    * Punjab Police → PP-15-#xxxxx
    * Punjab Highway Patrol / City Traffic Police Multan → CTP-MUL-#xxxxx
    * Punjab Emergency Service (Rescue 1122) → R1122-PB-#xxxxx
    * Punjab Fire & Rescue → PFR-16-#xxxxx
    * PDMA Punjab → PDMA-PB-#xxxxx
    * Sindh Police → SP-15-#xxxxx
    * Karachi Traffic Police → KTP-#xxxxx
    * Karachi Fire Brigade → KFB-#xxxxx
    * KP Police → KPP-#xxxxx, KP Traffic Police → KPTP-#xxxxx
    * Islamabad Police → ICTP-15-#xxxxx, Islamabad Traffic Police → ITP-#xxxxx
    * Islamabad Fire Brigade → IFB-#xxxxx, Rescue 1122 ICT → R1122-ICT-#xxxxx
    * NDMA → NDMA-ALERT-#xxxxx, Edhi → EDHI-#xxxxx, BDS → BDS-#xxxxx
    * NYPD → NYPD-#xxxxx, FDNY → FDNY-#xxxxx, NYC EMS → EMS-NYC-#xxxxx
    * Tokyo Fire Department → TFD-#xxxxx, Tokyo Metro Police → TMP-#xxxxx
    * Met Police London → MET-#xxxxx, London Fire Brigade → LFB-#xxxxx
    * Mumbai Police → MP-#xxxxx, Shanghai PSB → SHPSB-#xxxxx
  Derive a sensible 2-5 letter prefix for any other agency. NEVER use the
  wrong jurisdiction's prefix (e.g. don't use ITP-#xxxxx for a Multan ticket).

- alert_message_body: realistic SMS-style citizen alert appropriate to this
  action, crisis, and locale (under 160 chars, mention location and
  instruction). Do NOT write traffic advisories for crime or medical events.
  For earthquake actions: include aftershock guidance and "stay outdoors,
  away from buildings" advice.

- simulated_result: detailed outcome description matching the action type
  (e.g. for search_and_rescue: "Rescue teams deployed; 12 survivors
  extracted in first hour").

Return ONLY valid JSON, no markdown, no explanation:
{{
  "before_state": {{"traffic_congestion_percent": 0, "emergency_services_deployed": false, "public_alerts_sent": 0}},
  "after_state": {{"traffic_congestion_percent": 0, "emergency_services_deployed": true, "public_alerts_sent": 0}},
  "execution_log": [
    {{"action_id": "ACT-001", "status": "simulated_complete", "ticket_id": "AGENCY-PREFIX-#xxxxx", "alert_message_body": "SMS-style citizen alert", "simulated_result": "detailed outcome description"}}
  ],
  "simulation_summary": "2 sentence summary of overall outcome"
}}"""
        result = parse_json(call_llm(prompt))

        # dynamic simulation data based on plan / severity
        actions = plan.get("actions", [])
        strategy = plan.get("overall_strategy", "").lower()
        
        # Calculate baseline affected population based on severity/actions count
        has_critical = any(a.get("priority") == "P1" for a in actions)
        
        base_pop = 1200
        severity_label = "Medium"
        if "critical" in strategy or has_critical:
            base_pop = 8000
            severity_label = "Critical"
        elif "high" in strategy:
            base_pop = 4000
            severity_label = "High"
        elif "low" in strategy:
            base_pop = 150
            severity_label = "Low"

        mitigation_ratio = 0.88 # 88% saved
        lives_saved = int(base_pop * mitigation_ratio)
        affected_after = int(base_pop * (1 - mitigation_ratio))

        # Side effects text based on crisis characteristics
        traffic_text = f"Perimeter blockades and rerouting around the incident area have caused moderate congestion on secondary arterials."
        logistical_text = "Emergency supply lines established. Specialized equipment dispatch has temporarily prioritized public safety vehicles."
        economic_text = "Local businesses in the immediate sector have temporarily suspended operations to ensure citizen safety."
        environmental_text = "Resource deployment has successfully mitigated chemical/hazard spill risks, preserving local ecosystems."

        if any(w in strategy or w in location_label.lower() for w in ["flood", "rain", "water"]):
            traffic_text = f"Water logging has caused major gridlock. Alternates are handling redirected flow, with a 25-minute travel delay."
            environmental_text = "High-volume pumps successfully routed stagnant water to main storm basins, reducing soil erosion."
        elif "fire" in strategy:
            traffic_text = f"Emergency lanes reserved for fire tenders. Smoke plumes have caused slight visibility reductions on nearby streets."
            environmental_text = "Controlled flame suppression prevents forest/brush spread. Water runoff has been chemically neutralized."
        elif "earthquake" in strategy or "quake" in strategy:
            traffic_text = f"Debris clearance in progress. Rerouted heavy machinery is causing localized crawl speeds."
            logistical_text = "Air rescue prioritizations have delayed non-critical commercial shipments. Field medical shelters are active."

        simulation_data = {
            "before": {
                "affected_population": base_pop,
                "severity": severity_label
            },
            "after": {
                "affected_population": affected_after,
                "severity": "Low"
            },
            "lives_saved": lives_saved,
            "side_effects": {
                "traffic": traffic_text,
                "logistical": logistical_text,
                "economic": economic_text,
                "environmental": environmental_text,
            }
        }
        result["simulation_data"] = simulation_data
        return result
    except Exception:
        print(f"ERROR in execute_actions: {traceback.format_exc()}")
        return {"before_state": {}, "after_state": {}, "execution_log": [], "simulation_summary": "Error"}
