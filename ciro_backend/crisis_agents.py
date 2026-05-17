import os
import re
import json
import traceback
from dotenv import load_dotenv
import groq
from mock_signals import get_weather_signal, get_traffic_signal, get_social_media_signal, get_real_weather
from tools.maps_tool import get_route_alternatives

load_dotenv()

# Kept the API key rotation logic from the previous step
api_keys_str = os.getenv("GROQ_API_KEYS", "")
GROQ_API_KEYS = [key.strip() for key in api_keys_str.split(",") if key.strip()]
current_key_index = 0

MODEL = "llama-3.3-70b-versatile"

def parse_json(text: str) -> dict:
    text = re.sub(r'```json|```', '', text).strip()
    start = text.find('{')
    end = text.rfind('}') + 1
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

async def ingest_signal(raw_text: str) -> dict:
    weather = await get_real_weather("Islamabad")
    traffic = get_traffic_signal("Islamabad")
    social = get_social_media_signal(raw_text)
    weather_json = json.dumps(weather)
    traffic_json = json.dumps(traffic)
    social_json = json.dumps(social)
    try:
        prompt = f"""You are a crisis signal parser for Islamabad, Pakistan.
You understand Urdu, Roman Urdu, and English.

SOURCE 1 - Citizen Report (THIS IS THE PRIMARY EVENT — what is actually happening): {raw_text}

SOURCE 2 - Weather API (AMBIENT CONTEXT — describes background weather conditions, NOT necessarily the crisis): {weather_json}

SOURCE 3 - Traffic API (AMBIENT CONTEXT — generic city traffic, NOT necessarily caused by the citizen's report): {traffic_json}

SOURCE 4 - Social Media (AMPLIFICATION SIGNAL — corroborates citizen volume): {social_json}

CRITICAL RULES:
1. The PRIMARY event_type must be derived from SOURCE 1 (citizen report). NEVER classify a robbery as a traffic accident just because SOURCE 3 shows congestion.
2. SOURCE 2 and SOURCE 3 are ambient — they describe what's happening in the city generally, not what the citizen is reporting.
3. Use weather/traffic ONLY as enrichment context, not to override the citizen's claim.

Return ONLY valid JSON:
{{
  "location": "specific Islamabad area mentioned in the citizen report (e.g. G-10, F-7 Markaz, E-11, Kashmir Highway)",
  "event_type": "one of: flooding/accident/heatwave/infrastructure/hazmat/crime/medical/fire/civil_unrest/utility_outage/unknown",
  "event_subtype": "more specific descriptor e.g. robbery/burglary/assault for crime; heart_attack for medical; flash_flood for flooding; etc.",
  "language_detected": "one of: urdu/roman_urdu/english/mixed",
  "urgency_level": "one of: immediate/urgent/moderate",
  "cleaned_text": "1-sentence normalized English summary of the citizen's report ONLY (do not blend in traffic/weather)",
  "sources_count": 4,
  "weather_context": "one sentence on whether ambient weather is relevant to the reported event",
  "traffic_context": "one sentence on whether ambient traffic is relevant to the reported event",
  "corroborating_signals": true
}}
Return ONLY valid JSON. No markdown, no explanation."""
        result = parse_json(call_llm(prompt))
    except Exception:
        print(f"ERROR in ingest_signal: {traceback.format_exc()}")
        result = {"location": "Unknown", "event_type": "unknown", "language_detected": "unknown", "urgency_level": "moderate", "cleaned_text": raw_text}
    result["weather_signal"] = weather
    result["traffic_signal"] = traffic
    result["social_signal"] = social
    return result

async def detect_crisis(signal: dict) -> dict:
    try:
        prompt = f"""You are a crisis severity classifier for Islamabad, Pakistan.
Given this parsed signal: {json.dumps(signal)}

CRITICAL: The event_type field is authoritative. If event_type is "crime", classify this as a crime/security event. Do NOT relabel it as a traffic incident just because the ambient traffic_signal shows congestion. Examples of correct mappings:
  - event_type=crime, subtype=robbery → crisis_type "Armed Robbery" or "Robbery in Progress"
  - event_type=medical → crisis_type "Medical Emergency"
  - event_type=fire → crisis_type "Structure Fire" or similar
  - event_type=flooding → "Urban Flooding"
  - event_type=accident → "Road Accident"

Impact_analysis MUST match the actual event. A robbery has impacts like "Threat to civilian life", "Need for armed response", "Crime scene preservation" — NOT "Traffic congestion".

Return ONLY valid JSON, no markdown, no explanation:
{{
  "crisis_type": "descriptive name matching the event_type (e.g. Armed Robbery, Urban Flooding, Medical Emergency, Structure Fire)",
  "location": "specific Islamabad area from the signal",
  "severity": "one of: Low/Medium/High/Critical",
  "confidence_percent": 85,
  "reasoning": "2-3 sentence explanation of WHY this severity was chosen, citing the citizen report and ONLY signals that are actually relevant to this event type. Do NOT cite traffic congestion when classifying a crime/medical event unless directly relevant.",
  "impact_analysis": ["impact 1 specific to this event type", "impact 2", "impact 3"],
  "requires_immediate_action": true
}}"""
        return parse_json(call_llm(prompt))
    except Exception:
        print(f"ERROR in detect_crisis: {traceback.format_exc()}")
        return {"crisis_type": "Unknown", "severity": "Low", "confidence_percent": 0, "reasoning": "Unable to classify — fallback used due to upstream error.", "impact_analysis": [], "requires_immediate_action": False}

async def plan_response(detection: dict) -> dict:
    try:
        prompt = f"""You are an emergency response coordinator for Islamabad, Pakistan.

AGENCIES AVAILABLE (pick the ones that fit the crisis type):
  - Islamabad Police (Emergency 15) — for crime, robbery, assault, civil unrest, security
  - Rescue 1122 (Emergency 1122) — for medical emergencies, accidents, rescues, evacuations
  - Islamabad Fire Brigade (Emergency 16) — for fires, hazmat
  - Edhi Ambulance — for medical transport, mass casualty
  - NDMA — for disaster response, public alerts, large-scale coordination
  - Islamabad Traffic Police — ONLY when traffic is actually impacted or rerouting is needed
  - CDA / WASA — for infrastructure failures, water, sewerage, utilities
  - Bomb Disposal Squad — for explosive threats, hazmat

ACTION TYPE GUIDANCE — pick action_type values that match the crisis:
  - Crime/Robbery: action_type="police_dispatch", "armed_response", "scene_lockdown", "public_safety_alert"
  - Medical: action_type="medical_dispatch", "ambulance_dispatch", "hospital_prep"
  - Fire: action_type="fire_dispatch", "evacuation", "hazmat_response"
  - Flooding/Accident: action_type="traffic_reroute", "emergency_dispatch", "public_alert"
  - Civil unrest: action_type="police_dispatch", "crowd_control", "public_safety_alert"

RULES:
1. Generate ONLY actions that make sense for THIS crisis. A robbery does NOT need a traffic_reroute action. A medical emergency does NOT need crowd control.
2. Use action_type="traffic_reroute" ONLY when the crisis is actually blocking or causing traffic disruption (flooding, road accident, infrastructure failure on a road, fire on a road).
3. For crime/robbery in a sector like E-11, the FIRST action should be police_dispatch to Islamabad Police via Emergency 15.

Given this crisis: {json.dumps(detection)}

Return ONLY valid JSON, no markdown, no explanation:
{{
  "overall_strategy": "1-2 sentence strategy specific to this crisis type",
  "actions": [
    {{"action_id": "ACT-001", "action_type": "appropriate_type_for_this_crisis", "description": "specific action matching the crisis type", "responsible_agency": "matching agency from the list above", "priority": "P1", "estimated_time_minutes": 5}},
    {{"action_id": "ACT-002", "action_type": "appropriate_type", "description": "specific action", "responsible_agency": "matching agency", "priority": "P1", "estimated_time_minutes": 10}},
    {{"action_id": "ACT-003", "action_type": "appropriate_type", "description": "specific action", "responsible_agency": "matching agency", "priority": "P2", "estimated_time_minutes": 2}}
  ],
  "public_advisory": "short citizen-facing message appropriate for this crisis (e.g. for robbery: 'Avoid the area, stay indoors, do not interfere. Call 15 if you have information.')"
}}"""
        result = parse_json(call_llm(prompt))
        blocked = detection.get("location") or "G-10"
        origin = f"{blocked}, Islamabad"
        destination = "Blue Area, Islamabad"
        for action in result.get("actions", []):
            if action.get("action_type") == "traffic_reroute":
                route_data = await get_route_alternatives(origin, destination, blocked)
                action["route_data"] = route_data
                action["route_origin"] = origin
                action["route_destination"] = destination
                action["route_blocked_area"] = blocked
        return result
    except Exception:
        print(f"ERROR in plan_response: {traceback.format_exc()}")
        return {"overall_strategy": "Error", "actions": [], "public_advisory": "Error"}

async def execute_actions(plan: dict) -> dict:
    try:
        prompt = f"""You are simulating emergency response execution in Islamabad, Pakistan.
Given this plan: {json.dumps(plan)}

For each execution_log entry, include:
- ticket_id: realistic agency mock id matching the responsible_agency. Use these prefixes:
  * Islamabad Police → POLICE-15-#xxxxx
  * Rescue 1122 → RESCUE-1122-#xxxxx
  * Islamabad Fire Brigade → FIRE-16-#xxxxx
  * Edhi Ambulance → EDHI-AMB-#xxxxx
  * NDMA → NDMA-ALERT-#xxxxx
  * Islamabad Traffic Police → ITP-RT-#xxxxx
  * CDA / WASA → CDA-INF-#xxxxx
  * Bomb Disposal Squad → BDS-#xxxxx
- alert_message_body: realistic SMS-style citizen alert appropriate to this action and crisis (under 160 chars, mention location and instruction). For police actions: "Police Alert: ...". For medical: "Rescue 1122: ...". For fire: "Fire Brigade: ...". DO NOT write traffic advisories for crime or medical events.
- simulated_result: detailed outcome description matching the action type (e.g. for police_dispatch: "Patrol units arrived in 6 min, suspect detained")

Return ONLY valid JSON, no markdown, no explanation:
{{
  "before_state": {{"traffic_congestion_percent": 0, "emergency_services_deployed": false, "public_alerts_sent": 0}},
  "after_state": {{"traffic_congestion_percent": 0, "emergency_services_deployed": true, "public_alerts_sent": 0}},
  "execution_log": [
    {{"action_id": "ACT-001", "status": "simulated_complete", "ticket_id": "AGENCY-PREFIX-#xxxxx matching responsible_agency", "alert_message_body": "SMS-style citizen alert matching this action", "simulated_result": "detailed outcome description"}}
  ],
  "simulation_summary": "2 sentence summary of overall outcome"
}}"""
        return parse_json(call_llm(prompt))
    except Exception:
        print(f"ERROR in execute_actions: {traceback.format_exc()}")
        return {"before_state": {}, "after_state": {}, "execution_log": [], "simulation_summary": "Error"}
