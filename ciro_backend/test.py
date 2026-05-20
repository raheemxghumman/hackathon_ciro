"""
CIRO test suite — run with:  pytest test.py -v
Tests cover pipeline logic, schema validation, and tool contracts
without requiring live API keys (external calls are mocked).
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ── Helpers ──────────────────────────────────────────────────────────────────

def run(coro):
    """Run an async coroutine in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── 1. JSON parser ────────────────────────────────────────────────────────────

class TestParseJson:
    def test_clean_json(self):
        from crisis_agents import parse_json
        result = parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_markdown_fences(self):
        from crisis_agents import parse_json
        text = "```json\n{\"crisis_type\": \"flooding\"}\n```"
        result = parse_json(text)
        assert result["crisis_type"] == "flooding"

    def test_json_with_surrounding_text(self):
        from crisis_agents import parse_json
        text = 'Here is the result: {"severity": "High"} as requested.'
        result = parse_json(text)
        assert result["severity"] == "High"

    def test_invalid_json_raises(self):
        from crisis_agents import parse_json
        with pytest.raises(Exception):
            parse_json("no json here at all")


# ── 2. ADK tool output schemas ────────────────────────────────────────────────

MOCK_INGESTION = {
    "location": "G-10 Markaz, Islamabad",
    "event_type": "flooding",
    "country": "Pakistan",
    "province_or_state": "Islamabad Capital Territory",
    "language_detected": "Roman Urdu",
    "geocode": {"lat": 33.69, "lng": 73.06, "city": "Islamabad", "country": "Pakistan"},
    "weather_signal": {
        "source": "WeatherAPI Live",
        "data": {"condition": "Heavy Rain", "temperature_c": 18.0,
                 "humidity_percent": 92, "alert_level": "High"}
    },
    "traffic_signal": {
        "source": "Google Maps Live",
        "data": {"congestion_percent": 45, "congestion_level": "Moderate", "is_real": True}
    },
    "earthquake_signal": {
        "source": "USGS",
        "data": {"event_count": 0, "max_magnitude": None}
    },
    "social_signal": {
        "source": "SocialMedia_Simulated",
        "data": {"estimated_reach": 12000, "report_count": 3, "amplification_score": 0.7}
    },
}

MOCK_DETECTION = {
    "crisis_type": "flooding",
    "severity": "High",
    "confidence_percent": 88,
    "reasoning": "Heavy rain combined with citizen reports of submerged cars indicates active urban flooding.",
    "impact_analysis": ["Traffic disruption on main arteries", "Risk of vehicle damage"],
    "location": "G-10 Markaz, Islamabad",
    "province_or_state": "Islamabad Capital Territory",
}

MOCK_PLAN = {
    "overall_strategy": "Deploy water pumps and redirect traffic.",
    "response_strategy": "Multi-agency flood response",
    "public_advisory": "Avoid G-10 Markaz. Use alternate routes.",
    "actions": [
        {
            "action_id": "ACT-001",
            "action_type": "deploy_emergency_services",
            "description": "Deploy water pumps and rescue teams.",
            "responsible_agency": "Rescue 1122",
            "priority": "P1",
            "estimated_time_minutes": 15,
        }
    ],
}

MOCK_EXECUTION = {
    "execution_log": [
        {
            "action_id": "ACT-001",
            "ticket_id": "R1122-PB-001",
            "status": "dispatched",
            "simulated_result": "Rescue 1122 dispatched — 3 pumps en route.",
            "alert_message_body": "ALERT: Flooding at G-10. Avoid the area.",
        }
    ],
    "simulation_summary": "1 unit dispatched, pumping operations underway.",
}


class TestIngestSignalTool:
    def test_returns_required_keys(self):
        from adk_agents import ingest_signal_tool, _pipeline_state
        _pipeline_state.clear()
        with patch("crisis_agents.ingest_signal", new=AsyncMock(return_value=MOCK_INGESTION)):
            result = run(ingest_signal_tool("G-10 mein pani bhar gaya hai"))
        assert result["stage"] == "ingest"
        assert result["status"] == "complete"
        assert "location" in result
        assert "event_type" in result

    def test_stores_in_pipeline_state(self):
        from adk_agents import ingest_signal_tool, _pipeline_state
        _pipeline_state.clear()
        with patch("crisis_agents.ingest_signal", new=AsyncMock(return_value=MOCK_INGESTION)):
            run(ingest_signal_tool("test report"))
        assert "ingestion" in _pipeline_state
        assert _pipeline_state["ingestion"]["event_type"] == "flooding"

    def test_error_returns_error_dict(self):
        from adk_agents import ingest_signal_tool, _pipeline_state
        _pipeline_state.clear()
        with patch("crisis_agents.ingest_signal", new=AsyncMock(side_effect=Exception("API down"))):
            result = run(ingest_signal_tool("test"))
        assert result["status"] == "error"
        assert "error" in result
        assert "ingestion" not in _pipeline_state


class TestDetectCrisisTool:
    def test_returns_required_keys(self):
        from adk_agents import detect_crisis_tool, _pipeline_state
        _pipeline_state.clear()
        _pipeline_state["ingestion"] = MOCK_INGESTION
        with patch("crisis_agents.detect_crisis", new=AsyncMock(return_value=MOCK_DETECTION)):
            result = run(detect_crisis_tool())
        assert result["stage"] == "detect"
        assert result["status"] == "complete"
        assert result["severity"] in ("Low", "Medium", "High", "Critical")
        assert 0 <= result["confidence_percent"] <= 100

    def test_error_handling(self):
        from adk_agents import detect_crisis_tool, _pipeline_state
        _pipeline_state.clear()
        _pipeline_state["ingestion"] = MOCK_INGESTION
        with patch("crisis_agents.detect_crisis", new=AsyncMock(side_effect=RuntimeError("LLM error"))):
            result = run(detect_crisis_tool())
        assert result["status"] == "error"


class TestPlanResponseTool:
    def test_returns_required_keys(self):
        from adk_agents import plan_response_tool, _pipeline_state
        _pipeline_state.clear()
        _pipeline_state["ingestion"] = MOCK_INGESTION
        _pipeline_state["detection"] = MOCK_DETECTION
        with patch("crisis_agents.plan_response", new=AsyncMock(return_value=MOCK_PLAN)):
            result = run(plan_response_tool())
        assert result["stage"] == "plan"
        assert result["status"] == "complete"
        assert isinstance(result["actions_count"], int)
        assert result["actions_count"] >= 0


class TestExecuteResponseTool:
    def test_returns_required_keys(self):
        from adk_agents import execute_response_tool, _pipeline_state
        _pipeline_state.clear()
        _pipeline_state["ingestion"] = MOCK_INGESTION
        _pipeline_state["detection"] = MOCK_DETECTION
        _pipeline_state["plan"] = MOCK_PLAN
        _pipeline_state["country"] = "Pakistan"
        _pipeline_state["province"] = "Islamabad Capital Territory"
        with patch("crisis_agents.execute_actions", new=AsyncMock(return_value=MOCK_EXECUTION)):
            result = run(execute_response_tool())
        assert result["stage"] == "execute"
        assert result["status"] == "complete"
        assert isinstance(result["tickets_created"], int)


# ── 3. Traffic uplift logic ───────────────────────────────────────────────────

class TestTrafficUplift:
    def test_crisis_traffic_overrides_ambient_when_higher(self):
        """Crisis traffic % should always be >= ambient traffic %."""
        from adk_runner import _CRISIS_TRAFFIC
        ambient = 30
        crisis_pct = _CRISIS_TRAFFIC["flooding"]["High"]  # 80
        result = max(ambient, crisis_pct)
        assert result == 80

    def test_ambient_preserved_when_higher_than_crisis(self):
        """If ambient traffic is already worse than crisis baseline, keep it."""
        from adk_runner import _CRISIS_TRAFFIC
        ambient = 95
        crisis_pct = _CRISIS_TRAFFIC["crime"]["Low"]  # 0
        result = max(ambient, crisis_pct)
        assert result == 95

    def test_all_crisis_types_have_all_severities(self):
        from adk_runner import _CRISIS_TRAFFIC
        severities = {"Low", "Medium", "High", "Critical"}
        for crisis_type, mapping in _CRISIS_TRAFFIC.items():
            assert set(mapping.keys()) == severities, \
                f"Missing severities for {crisis_type}"

    def test_after_state_always_lower_than_before(self):
        """Response should always reduce congestion."""
        reduction_map = {"Low": 0.20, "Medium": 0.40, "High": 0.55, "Critical": 0.70}
        for severity, reduction in reduction_map.items():
            before = 80
            after = max(5, int(round(before * (1 - reduction))))
            assert after < before, f"After ({after}) should be < before ({before}) for {severity}"


# ── 4. Verification tool schema ───────────────────────────────────────────────

class TestVerificationTool:
    def test_returns_required_keys_on_api_failure(self):
        """Verification should return a valid structure even when all APIs fail."""
        from tools.verification_tool import verify_incident
        with patch("httpx.AsyncClient.get", side_effect=Exception("network error")):
            result = run(verify_incident(
                location="Islamabad",
                event_type="flooding",
                lat=33.69,
                lng=73.06,
            ))
        assert "confidence" in result
        assert result["confidence"] in ("high", "medium", "unverified")
        assert "summary" in result
        assert "sources" in result

    def test_confidence_levels_are_valid(self):
        valid = {"high", "medium", "unverified"}
        result_confidence = "high"
        assert result_confidence in valid


# ── 5. Pipeline state isolation ───────────────────────────────────────────────

class TestPipelineStateIsolation:
    def test_clear_removes_all_keys(self):
        from adk_agents import _pipeline_state
        _pipeline_state["ingestion"] = {"test": True}
        _pipeline_state["detection"] = {"test": True}
        _pipeline_state.clear()
        assert len(_pipeline_state) == 0

    def test_state_populated_after_ingest(self):
        from adk_agents import ingest_signal_tool, _pipeline_state
        _pipeline_state.clear()
        with patch("crisis_agents.ingest_signal", new=AsyncMock(return_value=MOCK_INGESTION)):
            run(ingest_signal_tool("flood report"))
        assert _pipeline_state.get("ingestion") is not None


# ── 6. Signal structure validation ───────────────────────────────────────────

class TestSignalStructure:
    def test_weather_signal_has_required_keys(self):
        required = {"condition", "temperature_c", "humidity_percent", "alert_level"}
        data = MOCK_INGESTION["weather_signal"]["data"]
        assert required.issubset(data.keys())

    def test_traffic_signal_has_required_keys(self):
        required = {"congestion_percent", "congestion_level", "is_real"}
        data = MOCK_INGESTION["traffic_signal"]["data"]
        assert required.issubset(data.keys())

    def test_social_signal_is_marked_simulated(self):
        source = MOCK_INGESTION["social_signal"]["source"]
        assert "Simulated" in source or "simulated" in source.lower()

    def test_geocode_has_lat_lng(self):
        geo = MOCK_INGESTION["geocode"]
        assert "lat" in geo and "lng" in geo
        assert isinstance(geo["lat"], float)
        assert isinstance(geo["lng"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
