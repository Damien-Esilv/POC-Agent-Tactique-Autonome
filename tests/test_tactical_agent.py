import json
from pathlib import Path
import pytest
from tactical_agent import (
    TacticalAgent,
    TelemetryInput,
    TacticalDecision,
    run_benchmark_suite,
    get_all_test_scenarios,
)


@pytest.fixture
def agent():
    return TacticalAgent()


def test_config_loading_and_multi_models(tmp_path):
    custom_config = {
        "platform": "ollama",
        "model": "mistral:latest",
        "models": ["mistral:latest", "qwen2.5:8b", "failsafe_engine"],
        "platforms_config": {
            "ollama": {"url": "http://localhost:11434"}
        },
        "timeout_sec": 2.5,
        "fallback_to_failsafe": True
    }
    cfg_file = tmp_path / "custom_config.json"
    cfg_file.write_text(json.dumps(custom_config), encoding="utf-8")

    custom_agent = TacticalAgent(config_path=cfg_file)
    assert custom_agent.platform == "ollama"
    assert custom_agent.models_list == ["mistral:latest", "qwen2.5:8b", "failsafe_engine"]


def test_scenario_coverage_generation():
    scenarios = get_all_test_scenarios()
    assert len(scenarios) == 10
    expected_decisions = [s["expected_decision"] for s in scenarios]
    assert "return_to_base" in expected_decisions
    assert "bypass_obstacle" in expected_decisions
    assert "hold_position" in expected_decisions
    assert "continue_mission" in expected_decisions


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
    """
    cleaned = agent._clean_json_string(dirty_llm_response)
    decision = TacticalDecision.model_validate_json(cleaned)
    assert decision.tactical_decision == "bypass_obstacle"


def test_multi_model_benchmark_execution(agent, capsys):
    models = ["failsafe_engine"]
    run_benchmark_suite(agent, models=models, condensed=True)
    captured = capsys.readouterr().out
    assert "TABLEAU COMPARATIF DES PERFORMANCE MODÈLES" in captured
    assert "failsafe_engine" in captured
    assert "SUCCÈS" in captured or "ÉCHEC" in captured
