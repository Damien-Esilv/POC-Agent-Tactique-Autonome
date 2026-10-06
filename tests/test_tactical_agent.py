import json
from pathlib import Path
import pytest
from tactical_agent import TacticalAgent, TelemetryInput, TacticalDecision, run_enhanced_benchmark


@pytest.fixture
def agent():
    return TacticalAgent()


def test_config_loading_and_selection(tmp_path):
    custom_config = {
        "platform": "lm_studio",
        "model": "qwen2.5:8b",
        "platforms_config": {
            "lm_studio": {"url": "http://localhost:1234"}
        },
        "timeout_sec": 2.5,
        "fallback_to_failsafe": True
    }
    cfg_file = tmp_path / "custom_config.json"
    cfg_file.write_text(json.dumps(custom_config), encoding="utf-8")

    custom_agent = TacticalAgent(config_path=cfg_file)
    assert custom_agent.platform == "lm_studio"
    assert custom_agent.model_name == "qwen2.5:8b"
    assert custom_agent.backend_url == "http://localhost:1234"


def test_rule_1_battery_low_priority(agent):
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


def test_rule_nominal_continue_mission(agent):
    telemetry = {
        "timestamp": "2026-10-06T12:00:00Z",
        "comm_link_c2": "LOST",
        "battery_pct": 80,
        "current_zone": "ALPHA_3",
        "sensor_front": "CLEAR",
        "mission_status": "RECONNAISSANCE",
    }
    output = agent.process(telemetry, force_failsafe=True)
    assert output["tactical_decision"] == "continue_mission"
    assert output["target_speed_ms"] == 1.0


def test_json_strictness_and_schema(agent):
    telemetry = {
        "timestamp": "2026-10-06T12:00:00Z",
        "comm_link_c2": "LOST",
        "battery_pct": 35,
        "current_zone": "LIMA_1",
        "sensor_front": "OBSTACLE_DETECTED_2M",
        "mission_status": "RECONNAISSANCE",
    }
    for _ in range(5):
        output = agent.process(telemetry)
        meta = output.pop("_execution_metadata", None)
        assert meta is not None
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


def test_enhanced_benchmark_with_kpi3_accuracy(agent, capsys):
    scenarios = [
        {
            "name": "Test Batterie Basse",
            "expected_decision": "return_to_base",
            "telemetry": {
                "timestamp": "2026-10-06T12:00:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 10,
                "current_zone": "LIMA_1",
                "sensor_front": "CLEAR",
                "mission_status": "PATROL",
            }
        },
        {
            "name": "Test Obstacle",
            "expected_decision": "bypass_obstacle",
            "telemetry": {
                "timestamp": "2026-10-06T12:01:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 50,
                "current_zone": "ALPHA_1",
                "sensor_front": "OBSTACLE_2M",
                "mission_status": "RECONNAISSANCE",
            }
        }
    ]
    run_enhanced_benchmark(agent, test_scenarios=scenarios)
    captured = capsys.readouterr().out
    assert "BENCHMARK DÉTAILLÉ" in captured
    assert "KPI 1 - Formatage JSON" in captured
    assert "KPI 2 - Latence Inférence" in captured
    assert "KPI 3 - Respect des Règles Survie" in captured
    assert "✅ VALIDÉ" in captured
