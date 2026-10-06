# Failsafe Cognitive COHOMA - Agent Tactique Autonome (Edge AI)

[![Challenge CoHoMa 4](https://img.shields.io/badge/Challenge-CoHoMa%204-blue.svg)](https://cohoma.fr)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![Mistral AI / Qwen](https://img.shields.io/badge/LLM-Mistral%207B%20%2F%20Qwen%207B-orange.svg)](https://mistral.ai)
[![Cross-Platform](https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](#)
[![Offline Ready](https://img.shields.io/badge/Execution-100%25%20Offline-red.svg)](#)

Ce dépôt contient la preuve de concept (**POC**) du **Cerveau Tactique de Secours** développé pour le challenge **CoHoMa 4**.
Il démontre qu'un modèle de langage (LLM) exécuté 100 % en local sur le matériel embarqué d'un robot terrestre (Tank ou Travelers) peut analyser la télémétrie en temps réel et rendre une décision tactique structurée (JSON parsable par ROS2) lors de la perte de liaison avec le Command & Control (C2).

---

## 1. Critères de Succès & Synthèse des 3 KPIs

Pour valider le POC dans le cadre du Challenge CoHoMa 4, le système est évalué sur 3 KPIs stricts :

| Critère de Succès (KPI) | Exigence Technique | Validation & Mesure | Statut |
| :--- | :--- | :--- | :---: |
| **KPI 1 : Formatage JSON Strict** | Output 100 % parsable sans blabla | Validé par Pydantic (`TacticalDecision`) sur 10 essais | ✅ **100% Parsable** |
| **KPI 2 : Temps de Latence Inférence** | Temps de réponse < 3.0 secondes | **0.0137s** (Failsafe) / **~1.1s** (Mistral 7B Local) | ✅ **< 3.0s** |
| **KPI 3 : Respect des Règles de Survie** | Conformité décisionnelle par scénario | Vérification de la décision Obtenue vs Attendue | ✅ **100% Conforme** |

### Règles d'Engagement et de Priorité :
1. **Priorité 1 (Batterie < 20%)** : Repli immédiat (`return_to_base`).
2. **Priorité 2 (Obstacle détecté)** : Contournement de l'obstacle (`bypass_obstacle`).
3. **Priorité 3 (Zone LIMA)** : Interdiction de franchir sans ordre C2 (`hold_position`).
4. **Nominale (Voie Libre)** : Poursuite de la mission (`continue_mission`).

---

## 2. Choix du Modèle & Configuration (`config.json`)

Vous pouvez modifier le modèle LLM et la plateforme d'inférence en un clic via le fichier `config.json` ou via les arguments CLI.

### Fichier `config.json`
```json
{
  "platform": "ollama",
  "model": "mistral:latest",
  "platforms_config": {
    "ollama": {
      "url": "http://localhost:11434"
    },
    "lm_studio": {
      "url": "http://localhost:1234"
    },
    "llama_cpp": {
      "url": "http://localhost:8080"
    }
  },
  "timeout_sec": 3.0,
  "fallback_to_failsafe": true
}
```

### Recommandation de Modèles (Taille & Latence Edge)
- **Mistral 7B Instruct v0.3 / Qwen 2.5 7B / Llama 3.2 3B (Q4_K_M)** : **RECOMMANDÉS (1.1s à 2.2s)**. Offrent le meilleur compromis entre vitesse d'inférence (< 3.0s sur CPU/GPU Edge) et respect des consignes tactiques.
- **Qwen3 14B / Modèles > 10B** : *Note d'Analyse Performance* - Téléchargeable et compatible, mais **trop lourd** pour le budget latence de 3.0s en Edge Computing (> 4.5s à 12s d'inférence). Voir [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md).

---

## 3. Installation & Démarrage Rapide

```bash
# Installation des dépendances
pip install -r requirements.txt

# Lancer selon config.json
python3 tactical_agent.py

# Changer de plateforme et de modèle via CLI
python3 tactical_agent.py --platform lm_studio --model qwen2.5:8b
python3 tactical_agent.py --platform ollama --model mistral:latest

# Exécuter le benchmark complet avec rapport des 3 KPIs
python3 tactical_agent.py --benchmark
```

---

## 4. Affichage du Benchmark Détaillé (`--benchmark`)

```text
==================================================================================
      BENCHMARK DÉTAILLÉ - AGENT TACTIQUE AUTONOME (CHALLENGE COHOMA 4)
  Plateforme : OLLAMA | Modèle : mistral:latest | Seuil Latence: < 3.0s
==================================================================================

▶ TEST 01/10 : Scénario Standard - Obstacle en zone LIMA (Règle 2 > Règle 3)
  ├─ Conditions  : Batterie: 35% | C2: LOST | Capteur: OBSTACLE_DETECTED_2M | Zone: LIMA_1
  ├─ Décision    : Obtenu='bypass_obstacle' | Attendu='bypass_obstacle' (0.5 m/s)
  ├─ Moteur      : LLM Ollama (mistral:latest)
  ├─ KPI 1 (JSON): OK [JSON 100% Parsable]
  ├─ KPI 2 (Temps): 1.1240 s (✅ < 3.0s)
  └─ KPI 3 (Règles): ✅ CONFORME AUX RÈGLES

▶ TEST 02/10 : Scénario Batterie Critique (Règle 1 : Survie Prioritaire)
  ├─ Conditions  : Batterie: 12% | C2: LOST | Capteur: OBSTACLE_DETECTED_2M | Zone: LIMA_1
  ├─ Décision    : Obtenu='return_to_base' | Attendu='return_to_base' (1.0 m/s)
  ├─ Moteur      : LLM Ollama (mistral:latest)
  ├─ KPI 1 (JSON): OK [JSON 100% Parsable]
  ├─ KPI 2 (Temps): 0.9850 s (✅ < 3.0s)
  └─ KPI 3 (Règles): ✅ CONFORME AUX RÈGLES

==================================================================================
                         RAPPORT ET CONCLUSION DES 3 KPIS
==================================================================================
• Nombre total de tests exécutés       : 10
• Temps total du benchmark             : 10.4200 s
• Latence moyenne par décision        : 1.0420 s
----------------------------------------------------------------------------------
• KPI 1 - Formatage JSON 100% Valide   : 10/10 (100.0%) -> ✅ VALIDÉ
• KPI 2 - Latence Inférence < 3.0s    : 1.0420s -> ✅ VALIDÉ
• KPI 3 - Respect des Règles Survie   : 10/10 (100.0%) -> ✅ VALIDÉ
==================================================================================
```

---

## 5. Tests Unitaires & Portabilité Multi-OS (Mac, Windows, Linux)

```bash
python3 -m pytest -v
```

---

## 6. Documentation Complémentaire
- **[BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md)** : Rapport d'analyse matérielle et comparatif des 3 KPIs (Apple M3 Pro vs ThinkCentre Edge vs 14B models).
