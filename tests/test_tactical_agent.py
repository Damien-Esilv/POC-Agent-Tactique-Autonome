import json
import pytest
from tactical_agent import TacticalAgent, TelemetryInput, TacticalDecision


@pytest.fixture
def agent():
    return TacticalAgent(timeout_sec=3.0)


def test_rule_1_battery_low(agent):
    telemetry = {
        "timestamp": "2026-10-06T12:00:00Z",
        "comm_link_c2": "LOST",
        "battery_pct": 15,
        "current_zone": "LIMA_1",
        "sensor_front": "OBSTACLE_DETECTED_2M",
        "mission_status": "RECONNAISSANCE",
    }
    output = agent.process(telemetry, force_failsafe=True)
    assert output["tactical_decision"] == "return_to_base"
    assert "Batterie critique" in output["justification"]
    assert output["target_speed_ms"] == 1.0


def test_rule_2_obstacle_bypass(agent):
    telemetry = {
        "timestamp": "2026-10-06T12:00:00Z",
        "comm_link_c2": "LOST",
        "battery_pct": 35,
        "current_zone": "LIMA_1",
        "sensor_front": "OBSTACLE_DETECTED_2M",
        "mission_status": "RECONNAISSANCE",
    }
    output = agent.process(telemetry, force_failsafe=True)
    assert output["tactical_decision"] == "bypass_obstacle"
    assert output["target_speed_ms"] == 0.5


def test_rule_3_lima_zone_hold(agent):
    telemetry = {
        "timestamp": "2026-10-06T12:00:00Z",
        "comm_link_c2": "LOST",
        "battery_pct": 50,
        "current_zone": "LIMA_2",
        "sensor_front": "CLEAR",
        "mission_status": "RECONNAISSANCE",
    }
    output = agent.process(telemetry, force_failsafe=True)
    assert output["tactical_decision"] == "hold_position"
    assert "ligne LIMA" in output["justification"]


def test_json_strictness_and_schema(agent):
    telemetry = {
        "timestamp": "2026-10-06T12:00:00Z",
        "comm_link_c2": "LOST",
        "battery_pct": 35,
        "current_zone": "LIMA_1",
        "sensor_front": "OBSTACLE_DETECTED_2M",
        "mission_status": "RECONNAISSANCE",
    }
    for _ in range(10):
        output = agent.process(telemetry)
        meta = output.pop("_execution_metadata", None)
        assert meta is not None
        # Validate pydantic schema
        decision = TacticalDecision.model_validate(output)
        assert decision.tactical_decision in ["bypass_obstacle", "return_to_base", "hold_position", "continue_mission"]
        assert isinstance(decision.target_speed_ms, float)


def test_clean_json_string_extractor(agent):
    dirty_llm_response = """
    Voici la décision tactique demandée :
    ```json
    {
      "tactical_decision": "bypass_obstacle",
      "justification": "Obstacle détecté",
      "target_speed_ms": 0.5
    }
    ```
    N'hésitez pas si vous avez d'autres questions.
    """
    cleaned = agent._clean_json_string(dirty_llm_response)
    decision = TacticalDecision.model_validate_json(cleaned)
    assert decision.tactical_decision == "bypass_obstacle"
