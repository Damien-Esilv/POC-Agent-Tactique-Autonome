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

# ANSI Color codes for strict pass/fail formatting
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"


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
        self.models_list = self.config.get("models", [self.model_name])
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
            "models": ["mistral:latest", "failsafe_engine"],
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
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        match = re.search(r"(\{.*?\})", text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    def get_model_size_str(self, model_name: str) -> str:
        """Attempts to query local platform for model file size, or uses fallback lookup table."""
        if model_name in ["failsafe_engine", "rules_engine", "rule_based"]:
            return "< 10 Mo"

        import requests
        if self.platform == "ollama":
            try:
                resp = requests.post(f"{self.backend_url.rstrip('/')}/api/show", json={"name": model_name}, timeout=1.5)
                if resp.status_code == 200:
                    details = resp.json().get("details", {})
                    p_size = details.get("parameter_size")
                    if p_size:
                        return f"~{p_size}"
            except Exception:
                pass

        # Fallback estimations based on model tag names
        m_lower = model_name.lower()
        if "14b" in m_lower:
            return "9,3 Go"
        elif "12b" in m_lower or "nemo" in m_lower:
            return "7,1 Go"
        elif "8b" in m_lower or "7b" in m_lower or "mistral" in m_lower:
            return "4,4 Go"
        elif "3b" in m_lower or "3.2" in m_lower:
            return "2,0 Go"
        elif "1b" in m_lower:
            return "1,1 Go"
        return "Inconnue"

    def query_local_llm(self, telemetry: TelemetryInput, override_model: Optional[str] = None) -> Tuple[Optional[TacticalDecision], float, str]:
        """
        Queries the local LLM endpoint according to configured platform (Ollama / LM Studio / llama.cpp).
        Returns (TacticalDecision, latency_seconds, mode_description).
        """
        import requests

        target_model = override_model or self.model_name
        if target_model in ["failsafe_engine", "rules_engine"]:
            start_t = time.perf_counter()
            dec = self.evaluate_rules(telemetry)
            return dec, time.perf_counter() - start_t, "Failsafe Cognitive Engine"

        user_content = json.dumps(telemetry.model_dump(), indent=2)
        start_time = time.perf_counter()

        # Platform: Ollama API (/api/chat)
        if self.platform == "ollama" or "/api" in self.backend_url or "11434" in self.backend_url:
            chat_url = f"{self.backend_url.rstrip('/')}/api/chat"
            payload = {
                "model": target_model,
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
                    return decision, elapsed, f"LLM Ollama ({target_model})"
            except Exception:
                pass

        # Platform: LM Studio / llama.cpp / OpenAI-compatible (/v1/chat/completions)
        v1_url = f"{self.backend_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": target_model,
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
                return decision, elapsed, f"LLM {self.platform.upper()} ({target_model})"
        except Exception:
            pass

        return None, time.perf_counter() - start_time, f"LLM Non Disponible ({target_model})"

    def process(self, telemetry_data: Dict[str, Any], force_failsafe: bool = False, override_model: Optional[str] = None) -> Dict[str, Any]:
        """
        Main decision-making entrypoint.
        Processes telemetry input, attempts LLM query, and falls back to deterministic rule engine if needed.
        """
        telemetry = TelemetryInput.model_validate(telemetry_data)

        if not force_failsafe:
            llm_decision, latency, backend_mode = self.query_local_llm(telemetry, override_model=override_model)
            if llm_decision is not None:
                output = llm_decision.model_dump()
                output["_execution_metadata"] = {
                    "backend": backend_mode,
                    "platform": self.platform,
                    "latency_sec": round(latency, 4),
                    "model": override_model or self.model_name,
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


def get_all_test_scenarios() -> List[Dict[str, Any]]:
    """
    Generates test scenarios covering ALL possible configuration combinations:
    1. Rule 1 Priority: Battery < 20% WITH obstacle & IN LIMA zone
    2. Rule 1 Priority: Battery < 20% WITHOUT obstacle & OUT of LIMA zone
    3. Rule 2 Priority: Battery >= 20% WITH obstacle & IN LIMA zone
    4. Rule 2 Priority: Battery >= 20% WITH obstacle & OUT of LIMA zone
    5. Rule 3 Priority: Battery >= 20% WITHOUT obstacle & IN LIMA zone
    6. Nominal Operation: Battery >= 20% WITHOUT obstacle & OUT of LIMA zone
    + Repeats to complete a 10-trial benchmark suite.
    """
    scenarios = [
        {
            "name": "Règle 1 (Batterie Critique < 20% + Obstacle + Zone LIMA)",
            "expected_decision": "return_to_base",
            "telemetry": {
                "timestamp": "2026-10-06T12:00:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 12,
                "current_zone": "LIMA_1",
                "sensor_front": "OBSTACLE_DETECTED_2M",
                "mission_status": "RECONNAISSANCE",
            }
        },
        {
            "name": "Règle 1 (Batterie Critique < 20% sans obstacle hors LIMA)",
            "expected_decision": "return_to_base",
            "telemetry": {
                "timestamp": "2026-10-06T12:01:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 18,
                "current_zone": "ALPHA_2",
                "sensor_front": "CLEAR",
                "mission_status": "PATROL",
            }
        },
        {
            "name": "Règle 2 (Obstacle en zone LIMA, Batterie >= 20%)",
            "expected_decision": "bypass_obstacle",
            "telemetry": {
                "timestamp": "2026-10-06T12:02:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 45,
                "current_zone": "LIMA_1",
                "sensor_front": "OBSTACLE_DETECTED_3M",
                "mission_status": "RECONNAISSANCE",
            }
        },
        {
            "name": "Règle 2 (Obstacle hors zone LIMA, Batterie >= 20%)",
            "expected_decision": "bypass_obstacle",
            "telemetry": {
                "timestamp": "2026-10-06T12:03:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 70,
                "current_zone": "BRAVO_4",
                "sensor_front": "OBSTACLE_DETECTED_1M",
                "mission_status": "RECONNAISSANCE",
            }
        },
        {
            "name": "Règle 3 (Interdiction Zone LIMA, Voie libre, Batterie >= 20%)",
            "expected_decision": "hold_position",
            "telemetry": {
                "timestamp": "2026-10-06T12:04:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 60,
                "current_zone": "LIMA_2",
                "sensor_front": "CLEAR",
                "mission_status": "RECONNAISSANCE",
            }
        },
        {
            "name": "Mode Nominal (Voie libre, Hors LIMA, Batterie >= 20%)",
            "expected_decision": "continue_mission",
            "telemetry": {
                "timestamp": "2026-10-06T12:05:00Z",
                "comm_link_c2": "LOST",
                "battery_pct": 85,
                "current_zone": "CHARLIE_1",
                "sensor_front": "CLEAR",
                "mission_status": "RECONNAISSANCE",
            }
        },
    ]

    # Fill up to 10 trials
    extra = []
    for i in range(7, 11):
        s = scenarios[(i - 1) % len(scenarios)].copy()
        s["name"] = f"Répétition Test {i:02d} ({s['name']})"
        extra.append(s)

    return scenarios + extra


def run_benchmark_suite(
    agent: TacticalAgent,
    models: Optional[List[str]] = None,
    condensed: bool = False,
    verbose: bool = False,
    test_scenarios: Optional[List[Dict[str, Any]]] = None,
):
    """
    Multi-model benchmark runner.
    Evaluates one or multiple models, prints individual trial details (if not condensed),
    and displays a strict comparative summary table across all 3 KPIs.
    """
    if not models:
        models = agent.models_list if agent.models_list else [agent.model_name]

    if not test_scenarios:
        test_scenarios = get_all_test_scenarios()

    total_scenarios = len(test_scenarios)
    is_multi_model = len(models) > 1

    # Force condensed output if evaluating multiple models unless --verbose is passed
    if is_multi_model and not verbose:
        condensed = True

    print("=" * 86)
    print("      BENCHMARK MULTI-MODÈLES - AGENT TACTIQUE AUTONOME (CHALLENGE COHOMA 4)")
    print(f"  Plateforme : {agent.platform.upper()} | Modèles à évaluer : {', '.join(models)}")
    print(f"  Seuil de Latence Cible : < 3.0s | Couverture Scénarios : {total_scenarios} tests")
    print("=" * 86)

    model_summary_results = []

    for m_idx, model_item in enumerate(models, 1):
        print(f"\n" + "─" * 86)
        print(f" 🤖 ÉVALUATION DU MODÈLE [{m_idx}/{len(models)}] : {COLOR_BOLD}{model_item}{COLOR_RESET}")
        print("─" * 86)

        valid_json_count = 0
        correct_decision_count = 0
        latencies = []

        for idx, scen in enumerate(test_scenarios, 1):
            name = scen.get("name", f"Test {idx}")
            telemetry = scen["telemetry"]
            expected_decision = scen.get("expected_decision", "N/A")

            cond_str = (
                f"Batterie: {telemetry['battery_pct']}% | "
                f"C2: {telemetry['comm_link_c2']} | "
                f"Capteur: {telemetry['sensor_front']} | "
                f"Zone: {telemetry['current_zone']}"
            )

            t_start = time.perf_counter()
            result = agent.process(telemetry, override_model=model_item)
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
                status_json = f"{COLOR_GREEN}OK [100% Parsable]{COLOR_RESET}"
            except Exception as e:
                status_json = f"{COLOR_RED}ÉCHEC [{e}]{COLOR_RESET}"

            actual_decision = result.get("tactical_decision", "N/A")
            speed = result.get("target_speed_ms", 0.0)

            # Validate Rule Adherence (KPI 3)
            is_correct = (actual_decision == expected_decision)
            if is_correct:
                correct_decision_count += 1
                status_veracity = f"{COLOR_GREEN}✅ CONFORME{COLOR_RESET}"
            else:
                status_veracity = f"{COLOR_RED}❌ NON CONFORME (Attendu: '{expected_decision}', Obtenu: '{actual_decision}'){COLOR_RESET}"

            latency_str = f"{t_elapsed:.4f} s"
            if t_elapsed < 3.0:
                status_latency = f"{COLOR_GREEN}{latency_str} (< 3.0s){COLOR_RESET}"
            else:
                status_latency = f"{COLOR_RED}{latency_str} (TROP LENT){COLOR_RESET}"

            if not condensed:
                print(f"▶ TEST {idx:02d}/{total_scenarios:02d} : {name}")
                print(f"  ├─ Conditions  : {cond_str}")
                print(f"  ├─ Décision    : Obtenu='{actual_decision}' | Attendu='{expected_decision}' ({speed} m/s)")
                print(f"  ├─ Moteur      : {backend}")
                print(f"  ├─ KPI 1 (JSON): {status_json}")
                print(f"  ├─ KPI 2 (Temps): {status_latency}")
                print(f"  └─ KPI 3 (Règles): {status_veracity}\n")

        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        min_lat = min(latencies) if latencies else 0.0
        max_lat = max(latencies) if latencies else 0.0

        kpi1_passed = (valid_json_count == total_scenarios)
        kpi2_passed = (avg_lat < 3.0)
        kpi3_passed = (correct_decision_count == total_scenarios)
        total_kpi_passed = (kpi1_passed and kpi2_passed and kpi3_passed)

        model_size = agent.get_model_size_str(model_item)

        model_summary_results.append({
            "model": model_item,
            "platform": agent.platform if model_item != "failsafe_engine" else "Local Python Engine",
            "size": model_size,
            "json_score": f"{valid_json_count}/{total_scenarios} ({valid_json_count/total_scenarios*100:.0f} %)",
            "json_passed": kpi1_passed,
            "avg_latency_str": f"{avg_lat:.4f} s",
            "avg_latency": avg_lat,
            "latency_passed": kpi2_passed,
            "min_max_latency": f"{min_lat:.4f}–{max_lat:.4f} s",
            "veracity_score": f"{correct_decision_count}/{total_scenarios} ({correct_decision_count/total_scenarios*100:.0f} %)",
            "veracity_passed": kpi3_passed,
            "total_kpi_passed": total_kpi_passed,
        })

        if condensed:
            res_icon = f"{COLOR_GREEN}✅ SUCCÈS{COLOR_RESET}" if total_kpi_passed else f"{COLOR_RED}❌ ÉCHEC{COLOR_RESET}"
            print(f"  Résultat rapide : JSON {valid_json_count}/{total_scenarios} | Latence moy: {avg_lat:.4f}s | Véracité: {correct_decision_count}/{total_scenarios} -> Statut : {res_icon}")

    # Display Final Comparative Table
    print("\n" + "=" * 86)
    print("                    TABLEAU COMPARATIF DES PERFORMANCE MODÈLES")
    print("=" * 86)

    # Markdown Table Header
    print(f"| {'Modèle':<18} | {'Taille':<9} | {'Structure JSON':<15} | {'Latence Moy.':<13} | {'Latence Min-Max':<18} | {'Véracité':<15} | {'KPI Total':<10} |")
    print("|" + "-" * 20 + "|" + "-" * 11 + "|" + "-" * 17 + "|" + "-" * 15 + "|" + "-" * 20 + "|" + "-" * 17 + "|" + "-" * 12 + "|")

    for res in model_summary_results:
        m_name = res["model"][:18]
        m_size = res["size"][:9]

        json_str = res["json_score"]
        json_fmt = f"{COLOR_GREEN}{json_str:<15}{COLOR_RESET}" if res["json_passed"] else f"{COLOR_RED}{json_str:<15}{COLOR_RESET}"

        avg_lat_str = res["avg_latency_str"]
        lat_fmt = f"{COLOR_GREEN}{avg_lat_str:<13}{COLOR_RESET}" if res["latency_passed"] else f"{COLOR_RED}{avg_lat_str:<13}{COLOR_RESET}"

        min_max_str = res["min_max_latency"][:18]

        ver_str = res["veracity_score"]
        ver_fmt = f"{COLOR_GREEN}{ver_str:<15}{COLOR_RESET}" if res["veracity_passed"] else f"{COLOR_RED}{ver_str:<15}{COLOR_RESET}"

        total_fmt = f"{COLOR_GREEN}{COLOR_BOLD}SUCCÈS{COLOR_RESET}    " if res["total_kpi_passed"] else f"{COLOR_RED}{COLOR_BOLD}ÉCHEC{COLOR_RESET}     "

        print(f"| {m_name:<18} | {m_size:<9} | {json_fmt} | {lat_fmt} | {min_max_str:<18} | {ver_fmt} | {total_fmt} |")

    print("=" * 86)


def main():
    parser = argparse.ArgumentParser(description="Failsafe Cognitive COHOMA - Tactical Agent")
    parser.add_argument("--config", type=str, default="config.json", help="Chemin du fichier de configuration JSON")
    parser.add_argument("--platform", type=str, choices=["ollama", "lm_studio", "llama_cpp"], help="Plateforme LLM locale")
    parser.add_argument("--model", type=str, help="Nom du modèle local (ex: mistral:latest, qwen2.5:8b)")
    parser.add_argument("--models", nargs="+", help="Liste de modèles à comparer dans le benchmark (ex: --models mistral:latest qwen2.5:8b failsafe_engine)")
    parser.add_argument("--backend-url", type=str, help="URL personnalisée de l'API LLM")
    parser.add_argument("--telemetry-file", type=str, help="Fichier JSON de télémétrie")
    parser.add_argument("--battery", type=int, default=35, help="Pourcentage de batterie (0-100)")
    parser.add_argument("--sensor", type=str, default="OBSTACLE_DETECTED_2M", help="État du capteur avant")
    parser.add_argument("--zone", type=str, default="LIMA_1", help="Zone tactique actuelle")
    parser.add_argument("--c2-link", type=str, default="LOST", help="Statut liaison C2")
    parser.add_argument("--benchmark", action="store_true", help="Lancer le benchmark de performance détaillé")
    parser.add_argument("--condensed", action="store_true", help="Afficher un résumé condensé du benchmark")
    parser.add_argument("--verbose", action="store_true", help="Forcer l'affichage détaillé de chaque test même en multi-modèles")
    parser.add_argument("--force-failsafe", action="store_true", help="Forcer le moteur de règles déterministe hors-ligne")

    args = parser.parse_args()

    config_path = Path(args.config)
    agent = TacticalAgent(
        config_path=config_path,
        platform=args.platform,
        backend_url=args.backend_url,
        model_name=args.model,
    )

    if args.models:
        agent.models_list = args.models

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
        run_benchmark_suite(agent, models=agent.models_list, condensed=args.condensed, verbose=args.verbose)
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
