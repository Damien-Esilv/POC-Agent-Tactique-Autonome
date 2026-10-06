# Failsafe Cognitive COHOMA - Agent Tactique Autonome (Edge AI)

[![Challenge CoHoMa 4](https://img.shields.io/badge/Challenge-CoHoMa%204-blue.svg)](https://cohoma.fr)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![Mistral AI / Qwen](https://img.shields.io/badge/LLM-Mistral%207B%20%2F%20Qwen%207B-orange.svg)](https://mistral.ai)
[![Cross-Platform](https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](#)
[![Offline Ready](https://img.shields.io/badge/Execution-100%25%20Offline-red.svg)](#)

Ce dépôt contient la preuve de concept (**POC**) du **Cerveau Tactique de Secours** développé pour le challenge **CoHoMa 4**.
Il démontre qu'un modèle de langage (LLM) exécuté 100 % en local sur le matériel embarqué d'un robot terrestre (Tank ou Travelers) peut analyser la télémétrie en temps réel et rendre une décision tactique structurée (JSON parsable par ROS2) lors de la perte de liaison avec le Command & Control (C2).

---

## 1. Modèles & Configuration Éléments de Choix (`config.json`)

Vous pouvez modifier le modèle LLM et la plateforme d'inférence en un clic via le fichier `config.json` ou via les arguments en ligne de commande.

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
- **Mistral 7B Instruct v0.3 / Qwen 2.5 7B (Q4_K_M)** : **RECOMMANDÉS (1.1s à 2.2s)**. Offrent le meilleur compromis entre vitesse d'inférence (< 3.0s sur CPU/GPU Edge) et précision de raisonnement tactique.
- **Qwen3 14B / Modèles > 10B** : *Note d'Analyse Performance* - Téléchargeable et compatible, mais **trop lourd** pour le budget latence de 3.0s en Edge Computing (> 4.5s à 12s d'inférence). Voir [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md).

---

## 2. Installation & Démarrage Rapide

### Dépendances

```bash
pip install -r requirements.txt
```

### Lancement avec Configuration Personnalisée (Ollama / LM Studio)

```bash
# Lancer avec la configuration définie dans config.json
python3 tactical_agent.py

# Changer de plateforme et de modèle en ligne de commande
python3 tactical_agent.py --platform lm_studio --model qwen2.5:8b
python3 tactical_agent.py --platform ollama --model mistral:latest

# Exécuter en mode benchmark détaillé avec récapitulatif par test
python3 tactical_agent.py --benchmark
```

---

## 3. Exemple d'Affichage Amélioré du Benchmark (`--benchmark`)

Chaque test du benchmark affiche les conditions de télémétrie associées, la décision prise, le moteur utilisé, la latence séquentielle et un rapport de conclusion :

```text
==============================================================================
      BENCHMARK DÉTAILLÉ - AGENT TACTIQUE AUTONOME (COHOMA 4)
  Plateforme : OLLAMA | Modèle : mistral:latest | Target: < 3.0s
==============================================================================

▶ TEST 01/10 : Scénario Standard - Obstacle devant
  ├─ Conditions : Batterie: 35% | C2: LOST | Capteur: OBSTACLE_DETECTED_2M | Zone: LIMA_1
  ├─ Décision   : 'bypass_obstacle' (Vitesse: 0.5 m/s)
  ├─ Moteur     : Failsafe Cognitive Engine (Moteur de Règles Déterministe)
  ├─ Statut     : ✅ VALIDE [JSON 100% Parsable]
  └─ Temps Séquentiel : 0.1663 s

▶ TEST 02/10 : Scénario Batterie Critique (Règle 1)
  ├─ Conditions : Batterie: 12% | C2: LOST | Capteur: OBSTACLE_DETECTED_2M | Zone: LIMA_1
  ├─ Décision   : 'return_to_base' (Vitesse: 1.0 m/s)
  ├─ Moteur     : Failsafe Cognitive Engine (Moteur de Règles Déterministe)
  ├─ Statut     : ✅ VALIDE [JSON 100% Parsable]
  └─ Temps Séquentiel : 0.0046 s

...

==============================================================================
                         RAPPORT ET CONCLUSION
==============================================================================
• Nombre total de tests exécutés : 10
• Temps total du benchmark       : 0.2019 s
• Latence moyenne par décision  : 0.0202 s
• KPI 1 (Formatage JSON 100%)    : 10/10 (100.0%)
• Statut KPI 1 (JSON Strict)     : ✅ SUCCÈS
• Statut KPI 2 (Latence < 3.0s)  : ✅ SUCCÈS
==============================================================================
```

---

## 4. Tests Unitaires & Portabilité Multi-OS (Mac, Windows, Linux)

Le projet est nativement compatible sur **Windows, macOS (Apple Silicon M-Series) et Linux**.

Pour lancer les tests unitaires :
```bash
python3 -m pytest -v
```

---

## 5. Documentation Complémentaire
- **[BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md)** : Rapport complet de performance hardware (Apple M3 Pro vs Lenovo ThinkCentre Edge vs Intel Xeon) et justification du choix des modèles 7B/8B vs 14B.
