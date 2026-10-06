#!/usr/bin/env python3
"""
Failsafe Cognitive COHOMA - Tactical Agent (Agent Tactique Autonome)
Edge AI Brain for autonomous ground robots during C2 communication loss.
Cross-platform compatible (Windows, macOS, Linux).
"""

import os
import sys
import json
import time
import re
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from pydantic import BaseModel, Field, ValidationError

SYSTEM_PROMPT = (
    "Tu es le cerveau tactique de secours d'un robot militaire autonome. La communication C2 est coupée (comm_link_c2 = 'LOST').\n"
    "Tu dois analyser la télémétrie reçue et choisir la meilleure décision tactique en appliquant STRICTEMENT les règles par ordre de priorité :\n\n"
    "1. RÈGLE 1 (SURVIE CRITIQUE) : Si 'battery_pct' < 20, la décision DOIT être 'return_to_base'.\n"
    "2. RÈGLE 2 (OBSTACLE) : Si 'sensor_front' contient 'OBSTACLE' et battery_pct >= 20, la décision DOIT être 'bypass_obstacle'.\n"
    "3. RÈGLE 3 (ZONE LIMA) : Si 'current_zone' contient 'LIMA', sans obstacle et battery_pct >= 20, la décision DOIT être 'hold_position' pour ne pas franchir la ligne sans ordre.\n"
    "4. NOMINALE (VOIE LIBRE) : Si aucune règle ci-dessus ne s'applique, la décision DOIT être 'continue_mission'.\n\n"
    "Champ 'tactical_decision' : DOIT être exactement l'une de ces 4 valeurs : ['return_to_base', 'bypass_obstacle', 'hold_position', 'continue_mission'].\n"
    "Retourne UNIQUEMENT un objet JSON valide avec la structure :\n"
    "{\n"
    '  "tactical_decision": "<valeur_strictement_parmi_les_4>",\n'
    '  "justification": "<explication_tactique_courte>",\n'
    '  "target_speed_ms": <nombre_flottant_entre_0.0_et_2.0>\n'
    "}"
)

DEFAULT_CONFIG_PATH = Path("config.json")


class TelemetryInput(BaseModel):
    timestamp: str = Field(description="ISO 8601 timestamp")
    comm_link_c2: str = Field(description="Status of communication link with Command & Control")
    battery_pct: int = Field(ge=0, le=100, description="Battery percentage (0-100)")
    current_zone: str = Field(description="Current tactical operational zone")
    sensor_front: str = Field(description="Front sensor status or obstacle detection")
    mission_status: str = Field(description="Current mission phase or status")


class TacticalDecision(BaseModel):
    tactical_decision: str = Field(description="Action command (return_to_base, bypass_obstacle, hold_position, continue_mission)")
    justification: str = Field(description="Tactical rationale for the decision")
    target_speed_ms: float = Field(ge=0.0, le=5.0, description="Target speed in meters per second")


class TacticalAgent:
    """
    Autonomous Tactical Agent designed for Edge execution on ground robots (Tank/Travelers).
    Queries local LLMs (Ollama / LM Studio / llama.cpp) based on config.json or parameters,
    and applies deterministic failsafe rules if LLM is offline or timed out.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        platform: Optional[str] = None,
        backend_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_sec: Optional[float] = None,
    ):
        self.config = self._load_config(config_path or DEFAULT_CONFIG_PATH)

        self.platform = platform or self.config.get("platform", "ollama")
        self.model_name = model_name or self.config.get("model", "mistral:latest")
        self.timeout_sec = timeout_sec or self.config.get("timeout_sec", 3.0)
        self.fallback_enabled = self.config.get("fallback_to_failsafe", True)

        platforms_cfg = self.config.get("platforms_config", {})
        selected_platform_cfg = platforms_cfg.get(self.platform, {})

        if backend_url:
            self.backend_url = backend_url
        else:
            self.backend_url = selected_platform_cfg.get("url", "http://localhost:11434")

    def _load_config(self, path: Path) -> Dict[str, Any]:
        """Loads configuration file if present, else returns sensible defaults."""
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Impossible de lire {path}: {e}. Utilisation de la configuration par défaut.", file=sys.stderr)
        return {
            "platform": "ollama",
            "model": "mistral:latest",
            "platforms_config": {
                "ollama": {"url": "http://localhost:11434"},
                "lm_studio": {"url": "http://localhost:1234"},
                "llama_cpp": {"url": "http://localhost:8080"}
            },
            "timeout_sec": 3.0,
            "fallback_to_failsafe": True
        }

    def evaluate_rules(self, telemetry: TelemetryInput) -> TacticalDecision:
        """
        Deterministic Tactical Rules Engine (Failsafe Cognitive Engine).
        Applied as fallback or ground-truth validator for strict mission safety rules:
        - Priority 1 (Rule 1): battery_pct < 20% -> return_to_base
        - Priority 2 (Rule 2): sensor_front contains OBSTACLE -> bypass_obstacle
        - Priority 3 (Rule 3): current_zone contains LIMA -> hold_position
        - Default: continue_mission
        """
        # Priority 1: Battery safety (Rule 1)
        if telemetry.battery_pct < 20:
            return TacticalDecision(
                tactical_decision="return_to_base",
                justification=(
                    f"Batterie critique ({telemetry.battery_pct}% < 20%). "
                    "Repli immédiat vers la base conformément à la Règle 1."
                ),
                target_speed_ms=1.0,
            )

        # Priority 2: Obstacle avoidance (Rule 2)
        if "OBSTACLE" in telemetry.sensor_front.upper():
            return TacticalDecision(
                tactical_decision="bypass_obstacle",
                justification=(
                    f"Obstacle détecté ({telemetry.sensor_front}) en zone {telemetry.current_zone}. "
                    "Batterie suffisante, contournement de l'obstacle selon la Règle 2."
                ),
                target_speed_ms=0.5,
            )

        # Priority 3: LIMA zone restriction (Rule 3)
        if "LIMA" in telemetry.current_zone.upper() and telemetry.comm_link_c2.upper() == "LOST":
            return TacticalDecision(
                tactical_decision="hold_position",
                justification=(
                    f"Maintien de position en zone {telemetry.current_zone}. "
                    "Interdiction de franchir la ligne LIMA sans ordre C2 direct (Règle 3)."
                ),
                target_speed_ms=0.0,
            )

        # Default Nominal Operation
        return TacticalDecision(
            tactical_decision="continue_mission",
            justification=f"Poursuite de la mission {telemetry.mission_status} en autonomie locale (voie libre hors LIMA).",
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
        Queries the local LLM endpoint according to configured platform (Ollama / LM Studio / llama.cpp).
        Returns (TacticalDecision, latency_seconds, mode_description).
        """
        import requests

        user_content = json.dumps(telemetry.model_dump(), indent=2)
        start_time = time.perf_counter()

        # Platform: Ollama API (/api/chat)
        if self.platform == "ollama" or "/api" in self.backend_url or "11434" in self.backend_url:
            chat_url = f"{self.backend_url.rstrip('/')}/api/chat"
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "stream": False,
                "format": "json",
            }
            try:
                resp = requests.post(chat_url, json=payload, timeout=self.timeout_sec)
                elapsed = time.perf_counter() - start_time
                if resp.status_code == 200:
                    raw_content = resp.json().get("message", {}).get("content", "")
                    cleaned = self._clean_json_string(raw_content)
                    decision = TacticalDecision.model_validate_json(cleaned)
                    return decision, elapsed, f"LLM Ollama ({self.model_name})"
            except Exception:
                pass

        # Platform: LM Studio / llama.cpp / OpenAI-compatible (/v1/chat/completions)
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
                return decision, elapsed, f"LLM {self.platform.upper()} ({self.model_name})"
        except Exception:
            pass

        return None, time.perf_counter() - start_time, "LLM Non Disponible / Timeout"

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
                    "platform": self.platform,
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
            "backend": "Failsafe Cognitive Engine (Moteur de Règles Déterministe)",
            "platform": "failsafe_engine",
            "latency_sec": round(rule_latency, 6),
            "model": "Mistral-Tactical-Rules-RuleEngine-v1",
            "status": "FAILSAFE_ACTIVE",
        }
        return output


def run_enhanced_benchmark(agent: TacticalAgent, test_scenarios: Optional[List[Dict[str, Any]]] = None):
    """
    Enhanced terminal benchmark with per-test conditions, individual detailed timing,
    decision verification against expected output (KPI 3 - Respect des règles/Véracité),
    and a comprehensive summary report covering all 3 CoHoMa 4 KPIs.
    """
    if not test_scenarios:
        test_scenarios = [
            {
                "name": "Scénario Standard - Obstacle en zone LIMA (Règle 2 > Règle 3)",
                "expected_decision": "bypass_obstacle",
                "telemetry": {
                    "timestamp": "2026-10-06T12:00:00Z",
                    "comm_link_c2": "LOST",
                    "battery_pct": 35,
                    "current_zone": "LIMA_1",
                    "sensor_front": "OBSTACLE_DETECTED_2M",
                    "mission_status": "RECONNAISSANCE",
                }
            },
            {
                "name": "Scénario Batterie Critique (Règle 1 : Survie Prioritaire)",
                "expected_decision": "return_to_base",
                "telemetry": {
                    "timestamp": "2026-10-06T12:01:00Z",
                    "comm_link_c2": "LOST",
                    "battery_pct": 12,
                    "current_zone": "LIMA_1",
                    "sensor_front": "OBSTACLE_DETECTED_2M",
                    "mission_status": "RECONNAISSANCE",
                }
            },
            {
                "name": "Scénario Interdiction Zone LIMA sans obstacle (Règle 3)",
                "expected_decision": "hold_position",
                "telemetry": {
                    "timestamp": "2026-10-06T12:02:00Z",
                    "comm_link_c2": "LOST",
                    "battery_pct": 60,
                    "current_zone": "LIMA_2",
                    "sensor_front": "CLEAR",
                    "mission_status": "PATROL",
                }
            },
            {
                "name": "Scénario Voie Libre Hors Zone LIMA (Mode Nominal)",
                "expected_decision": "continue_mission",
                "telemetry": {
                    "timestamp": "2026-10-06T12:03:00Z",
                    "comm_link_c2": "LOST",
                    "battery_pct": 80,
                    "current_zone": "ALPHA_3",
                    "sensor_front": "CLEAR",
                    "mission_status": "RECONNAISSANCE",
                }
            },
        ]
        # Duplicate to reach 10 trials total for full benchmark suite
        extra_trials = []
        for i in range(5, 11):
            scen = test_scenarios[(i - 1) % len(test_scenarios)].copy()
            scen["name"] = f"Répétition Test {i:02d} ({scen['name']})"
            extra_trials.append(scen)
        test_scenarios = test_scenarios + extra_trials

    total_runs = len(test_scenarios)
    print("=" * 82)
    print("      BENCHMARK DÉTAILLÉ - AGENT TACTIQUE AUTONOME (CHALLENGE COHOMA 4)")
    print(f"  Plateforme : {agent.platform.upper()} | Modèle : {agent.model_name} | Seuil Latence: < 3.0s")
    print("=" * 82)

    valid_json_count = 0
    correct_decision_count = 0
    latencies = []
    total_benchmark_start = time.perf_counter()

    for idx, scen in enumerate(test_scenarios, 1):
        name = scen.get("name", f"Test {idx}")
        telemetry = scen["telemetry"]
        expected_decision = scen.get("expected_decision", "N/A")

        # Format brief condition summary
        cond_str = (
            f"Batterie: {telemetry['battery_pct']}% | "
            f"C2: {telemetry['comm_link_c2']} | "
            f"Capteur: {telemetry['sensor_front']} | "
            f"Zone: {telemetry['current_zone']}"
        )

        t_start = time.perf_counter()
        result = agent.process(telemetry)
        t_elapsed = time.perf_counter() - t_start
        latencies.append(t_elapsed)

        meta = result.pop("_execution_metadata", {})
        backend = meta.get("backend", "Inconnu")

        # Validate JSON strictness (KPI 1)
        json_valid = False
        try:
            TacticalDecision.model_validate(result)
            valid_json_count += 1
            json_valid = True
            status_json = "OK [JSON 100% Parsable]"
        except Exception as e:
            status_json = f"ÉCHEC [{e}]"

        actual_decision = result.get("tactical_decision", "N/A")
        speed = result.get("target_speed_ms", 0.0)

        # Validate Decision Veracity / Survival Rule Respect (KPI 3)
        is_decision_correct = (actual_decision == expected_decision)
        if is_decision_correct:
            correct_decision_count += 1
            status_veracity = "✅ CONFORME AUX RÈGLES"
        else:
            status_veracity = f"❌ ÉCHEC (Attendu: '{expected_decision}', Obtenu: '{actual_decision}')"

        latency_status = "✅ < 3.0s" if t_elapsed < 3.0 else "❌ TROP LENT"

        print(f"\n▶ TEST {idx:02d}/{total_runs:02d} : {name}")
        print(f"  ├─ Conditions  : {cond_str}")
        print(f"  ├─ Décision    : Obtenu='{actual_decision}' | Attendu='{expected_decision}' ({speed} m/s)")
        print(f"  ├─ Moteur      : {backend}")
        print(f"  ├─ KPI 1 (JSON): {status_json}")
        print(f"  ├─ KPI 2 (Temps): {t_elapsed:.4f} s ({latency_status})")
        print(f"  └─ KPI 3 (Règles): {status_veracity}")

    total_benchmark_time = time.perf_counter() - total_benchmark_start
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    kpi1_ok = (valid_json_count == total_runs)
    kpi2_ok = (avg_latency < 3.0)
    kpi3_ok = (correct_decision_count == total_runs)

    print("\n" + "=" * 82)
    print("                         RAPPORT ET CONCLUSION DES 3 KPIS")
    print("=" * 82)
    print(f"• Nombre total de tests exécutés       : {total_runs}")
    print(f"• Temps total du benchmark             : {total_benchmark_time:.4f} s")
    print(f"• Latence moyenne par décision        : {avg_latency:.4f} s")
    print("-" * 82)
    print(f"• KPI 1 - Formatage JSON 100% Valide   : {valid_json_count}/{total_runs} ({valid_json_count/total_runs*100:.1f}%) -> {'✅ VALIDÉ' if kpi1_ok else '❌ ÉCHEC'}")
    print(f"• KPI 2 - Latence Inférence < 3.0s    : {avg_latency:.4f}s -> {'✅ VALIDÉ' if kpi2_ok else '❌ ÉCHEC'}")
    print(f"• KPI 3 - Respect des Règles Survie   : {correct_decision_count}/{total_runs} ({correct_decision_count/total_runs*100:.1f}%) -> {'✅ VALIDÉ' if kpi3_ok else '❌ ÉCHEC'}")
    print("=" * 82)


def main():
    parser = argparse.ArgumentParser(description="Failsafe Cognitive COHOMA - Tactical Agent")
    parser.add_argument("--config", type=str, default="config.json", help="Chemin du fichier de configuration JSON")
    parser.add_argument("--platform", type=str, choices=["ollama", "lm_studio", "llama_cpp"], help="Plateforme LLM locale")
    parser.add_argument("--model", type=str, help="Nom du modèle local (ex: mistral:latest, qwen2.5:8b, qwen3-14b)")
    parser.add_argument("--backend-url", type=str, help="URL personnalisée de l'API LLM")
    parser.add_argument("--telemetry-file", type=str, help="Fichier JSON de télémétrie")
    parser.add_argument("--battery", type=int, default=35, help="Pourcentage de batterie (0-100)")
    parser.add_argument("--sensor", type=str, default="OBSTACLE_DETECTED_2M", help="État du capteur avant")
    parser.add_argument("--zone", type=str, default="LIMA_1", help="Zone tactique actuelle")
    parser.add_argument("--c2-link", type=str, default="LOST", help="Statut liaison C2")
    parser.add_argument("--benchmark", action="store_true", help="Lancer le benchmark de performance détaillé")
    parser.add_argument("--force-failsafe", action="store_true", help="Forcer le moteur de règles déterministe hors-ligne")

    args = parser.parse_args()

    config_path = Path(args.config)
    agent = TacticalAgent(
        config_path=config_path,
        platform=args.platform,
        backend_url=args.backend_url,
        model_name=args.model,
    )

    if args.telemetry_file and Path(args.telemetry_file).exists():
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
        run_enhanced_benchmark(agent)
    else:
        print("=" * 60)
        print(f" AGENT TACTIQUE AUTONOME (Plateforme: {agent.platform.upper()} | Modèle: {agent.model_name})")
        print("=" * 60)
        print("TÉLÉMÉTRIE ENTRANTE (ROS2 Input):")
        print(json.dumps(telemetry_data, indent=2, ensure_ascii=False))
        print("\n" + "-" * 60 + "\n")

        output = agent.process(telemetry_data, force_failsafe=args.force_failsafe)
        meta = output.pop("_execution_metadata", {})

        print("DÉCISION TACTIQUE SORTANTE (ROS2 Output):")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print("\n" + "=" * 60)
        print(f"Moteur exécuté : {meta.get('backend')}")
        print(f"Modèle         : {meta.get('model')}")
        print(f"Latence        : {meta.get('latency_sec')} s")


if __name__ == "__main__":
    main()
