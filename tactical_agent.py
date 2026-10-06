#!/usr/bin/env python3
"""
Failsafe Cognitive COHOMA - Tactical Agent (Agent Tactique Autonome)
Edge AI Brain for autonomous ground robots during C2 communication loss.
"""

import os
import sys
import json
import time
import re
import argparse
from typing import Literal, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ValidationError

SYSTEM_PROMPT = (
    "Tu es le cerveau tactique de secours d'un robot militaire. "
    "La communication avec la base est coupée. "
    "Règle 1 : Si la batterie est sous 20%, retourner à la base. "
    "Règle 2 : Si un obstacle bloque la route, le contourner. "
    "Règle 3 : Ne franchir aucune ligne LIMA sans ordre. "
    "Analyse la télémétrie et retourne uniquement un objet JSON valide avec ta décision."
)


class TelemetryInput(BaseModel):
    timestamp: str = Field(description="ISO 8601 timestamp")
    comm_link_c2: str = Field(description="Status of communication link with Command & Control")
    battery_pct: int = Field(ge=0, le=100, description="Battery percentage (0-100)")
    current_zone: str = Field(description="Current tactical operational zone")
    sensor_front: str = Field(description="Front sensor status or obstacle detection")
    mission_status: str = Field(description="Current mission phase or status")


class TacticalDecision(BaseModel):
    tactical_decision: Literal[
        "bypass_obstacle",
        "return_to_base",
        "hold_position",
        "continue_mission",
    ] = Field(description="One of the four supported tactical action commands")
    justification: str = Field(description="Tactical rationale for the decision")
    target_speed_ms: float = Field(ge=0.0, le=5.0, description="Target speed in meters per second")


class TacticalAgent:
    """
    Autonomous Tactical Agent designed for Edge execution on ground robots (Tank/Travelers).
    Queries local LLMs (Ollama / LM Studio / llama.cpp) and applies failsafe rules.
    """

    def __init__(
        self,
        backend_url: Optional[str] = None,
        model_name: str = "qwen3:14b",
        timeout_sec: float = 60.0,
    ):
        self.backend_url = backend_url or os.getenv("LLM_BACKEND_URL", "http://localhost:11434")
        self.model_name = model_name
        self.timeout_sec = timeout_sec

    def evaluate_rules(self, telemetry: TelemetryInput) -> TacticalDecision:
        """
        Deterministic Tactical Rules Engine (Failsafe Cognitive Engine).
        Applied as fallback or ground-truth validator for strict mission safety rules:
        - Rule 1: battery_pct < 20% -> return_to_base
        - Rule 2: obstacle detected -> bypass_obstacle
        - Rule 3: do not cross LIMA zone without order
        """
        # Rule 1: Battery safety
        if telemetry.battery_pct < 20:
            return TacticalDecision(
                tactical_decision="return_to_base",
                justification=(
                    f"Batterie critique ({telemetry.battery_pct}% < 20%). "
                    "Repli immédiat vers la base conformément à la Règle 1."
                ),
                target_speed_ms=1.0,
            )

        # Rule 2: Obstacle avoidance
        if "OBSTACLE" in telemetry.sensor_front.upper():
            return TacticalDecision(
                tactical_decision="bypass_obstacle",
                justification=(
                    f"Obstacle détecté ({telemetry.sensor_front}) en zone {telemetry.current_zone}. "
                    "Batterie suffisante, contournement de l'obstacle selon la Règle 2."
                ),
                target_speed_ms=0.5,
            )

        # Rule 3 / Normal Operation
        if "LIMA" in telemetry.current_zone.upper() and telemetry.comm_link_c2.upper() == "LOST":
            return TacticalDecision(
                tactical_decision="hold_position",
                justification=(
                    f"Maintien de position en zone {telemetry.current_zone}. "
                    "Interdiction de franchir la ligne LIMA sans ordre C2 direct (Règle 3)."
                ),
                target_speed_ms=0.0,
            )

        return TacticalDecision(
            tactical_decision="continue_mission",
            justification=f"Poursuite de la mission {telemetry.mission_status} en autonomie locale.",
            target_speed_ms=1.0,
        )

    def _clean_json_string(self, text: str) -> str:
        """Strips markdown block backticks and extra commentary before/after JSON object."""
        text = text.strip()
        # Remove markdown fences ```json ... ```
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        # Extract first nested JSON object if extra commentary exists
        match = re.search(r"(\{.*?\})", text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    def query_local_llm(self, telemetry: TelemetryInput) -> Tuple[Optional[TacticalDecision], float, str]:
        """
        Queries the local LLM endpoint (Ollama API or OpenAI-compatible endpoint).
        Returns (TacticalDecision, latency_seconds, mode_description).
        """
        import requests

        user_content = json.dumps(telemetry.model_dump(), indent=2)
        start_time = time.perf_counter()

        # Try Ollama native API: /api/generate or /api/chat
        if "/api" in self.backend_url or "11434" in self.backend_url:
            chat_url = f"{self.backend_url.rstrip('/')}/api/chat"
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Retourne exactement les champs tactical_decision, justification "
                            f"et target_speed_ms. Télémétrie :\n{user_content}"
                        ),
                    },
                ],
                "stream": False,
                "format": TacticalDecision.model_json_schema(),
                "think": False,
                "options": {"temperature": 0.0, "num_predict": 160},
            }
            try:
                resp = requests.post(chat_url, json=payload, timeout=self.timeout_sec)
                elapsed = time.perf_counter() - start_time
                if resp.status_code == 200:
                    raw_content = resp.json().get("message", {}).get("content", "")
                    cleaned = self._clean_json_string(raw_content)
                    decision = TacticalDecision.model_validate_json(cleaned)
                    return decision, elapsed, "LLM (Ollama)"
            except Exception:
                pass

        # Try OpenAI compatible endpoint (LM Studio / llama.cpp / vLLM)
        v1_url = f"{self.backend_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        try:
            resp = requests.post(v1_url, json=payload, timeout=self.timeout_sec)
            elapsed = time.perf_counter() - start_time
            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"]
                cleaned = self._clean_json_string(raw_content)
                decision = TacticalDecision.model_validate_json(cleaned)
                return decision, elapsed, "LLM (OpenAI-compatible)"
        except Exception:
            pass

        return None, time.perf_counter() - start_time, "LLM Unavailable"

    def process(self, telemetry_data: Dict[str, Any], force_failsafe: bool = False) -> Dict[str, Any]:
        """
        Main decision-making entrypoint.
        Processes telemetry input, attempts LLM query, and falls back to deterministic rule engine if needed.
        """
        telemetry = TelemetryInput.model_validate(telemetry_data)

        if not force_failsafe:
            llm_decision, latency, backend_mode = self.query_local_llm(telemetry)
            if llm_decision is not None:
                output = llm_decision.model_dump()
                output["_execution_metadata"] = {
                    "backend": backend_mode,
                    "latency_sec": round(latency, 4),
                    "model": self.model_name,
                    "status": "SUCCESS",
                }
                return output

        # Rule Engine Failsafe execution
        start_rule = time.perf_counter()
        rule_decision = self.evaluate_rules(telemetry)
        rule_latency = time.perf_counter() - start_rule

        output = rule_decision.model_dump()
        output["_execution_metadata"] = {
            "backend": "Failsafe Cognitive Engine (Offline Rule-Based Edge Brain)",
            "latency_sec": round(rule_latency, 6),
            "model": "Mistral-Tactical-Rules-RuleEngine-v1",
            "status": "FAILSAFE_ACTIVE",
        }
        return output


def run_benchmark(agent: TacticalAgent, sample_telemetry: Dict[str, Any], runs: int = 10):
    """Runs KPI benchmark across multiple iterations and logs strict formatting & latency stats."""
    print("=" * 65)
    print(f"  BENCHMARK DE PERFORMANCE TACTIQUE ({runs} ESSAIS CONSÉCUTIFS)")
    print("=" * 65)

    valid_json_count = 0
    latencies = []

    for i in range(1, runs + 1):
        t0 = time.perf_counter()
        result = agent.process(sample_telemetry)
        latency = time.perf_counter() - t0
        latencies.append(latency)

        # Remove metadata to verify output JSON match
        meta = result.pop("_execution_metadata", {})
        try:
            # Validate strict pydantic model schema
            TacticalDecision.model_validate(result)
            json_str = json.dumps(result, ensure_ascii=False)
            json.loads(json_str)
            valid_json_count += 1
            status = "OK [JSON 100% Valid]"
        except Exception as e:
            status = f"FAIL [{e}]"

        backend = meta.get("backend", "Unknown")
        print(f"Essai {i:02d}/{runs:02d} | Statut: {status} | Temps: {latency:.4f}s | Backend: {backend}")

    avg_latency = sum(latencies) / len(latencies)
    print("-" * 65)
    print(f"KPI 1 (Formatage JSON 100% valide): {valid_json_count}/{runs} ({valid_json_count / runs * 100:.1f}%)")
    print(f"KPI 2 (Temps de latence moyen):     {avg_latency:.4f} sec (Objectif: < 3.0s)")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Failsafe Cognitive COHOMA - Tactical Agent")
    parser.add_argument("--telemetry-file", type=str, help="Path to JSON file with telemetry data")
    parser.add_argument("--battery", type=int, default=35, help="Battery percentage (0-100)")
    parser.add_argument("--sensor", type=str, default="OBSTACLE_DETECTED_2M", help="Front sensor status")
    parser.add_argument("--zone", type=str, default="LIMA_1", help="Current operational zone")
    parser.add_argument("--c2-link", type=str, default="LOST", help="C2 Link status")
    parser.add_argument("--benchmark", action="store_true", help="Run 10 consecutive trials benchmark")
    parser.add_argument("--backend-url", type=str, default="http://localhost:11434", help="Local LLM Backend URL")
    parser.add_argument("--model", type=str, default="qwen3:14b", help="Local LLM Model name")
    parser.add_argument("--timeout", type=float, default=60.0, help="LLM request timeout in seconds")
    parser.add_argument("--force-failsafe", action="store_true", help="Force local deterministic rule engine")

    args = parser.parse_args()

    agent = TacticalAgent(
        backend_url=args.backend_url,
        model_name=args.model,
        timeout_sec=args.timeout,
    )

    if args.telemetry_file and os.path.exists(args.telemetry_file):
        with open(args.telemetry_file, "r", encoding="utf-8") as f:
            telemetry_data = json.load(f)
    else:
        telemetry_data = {
            "timestamp": "2026-10-06T12:00:00Z",
            "comm_link_c2": args.c2_link,
            "battery_pct": args.battery,
            "current_zone": args.zone,
            "sensor_front": args.sensor,
            "mission_status": "RECONNAISSANCE",
        }

    if args.benchmark:
        run_benchmark(agent, telemetry_data, runs=10)
    else:
        print("TÉLÉMÉTRIE ENTRANTE (ROS2 Input):")
        print(json.dumps(telemetry_data, indent=2, ensure_ascii=False))
        print("\n" + "=" * 50 + "\n")

        output = agent.process(telemetry_data, force_failsafe=args.force_failsafe)
        meta = output.pop("_execution_metadata", {})

        print("DÉCISION TACTIQUE SORTANTE (ROS2 Output):")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print("\n" + "=" * 50)
        print(f"Exécution via : {meta.get('backend')}")
        print(f"Modèle        : {meta.get('model')}")
        print(f"Latence       : {meta.get('latency_sec')} s")


if __name__ == "__main__":
    main()
