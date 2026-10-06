# Failsafe Cognitive COHOMA - Agent Tactique Autonome (Edge AI)

[![Challenge CoHoMa 4](https://img.shields.io/badge/Challenge-CoHoMa%204-blue.svg)](https://cohoma.fr)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![Mistral AI](https://img.shields.io/badge/LLM-Mistral%20Nemo%2012B%20%2F%207B-orange.svg)](https://mistral.ai)
[![Offline Ready](https://img.shields.io/badge/Execution-100%25%20Offline-red.svg)](#)

Ce dépôt contient la preuve de concept (**POC**) du **Cerveau Tactique de Secours** développé pour le challenge **CoHoMa 4**.
Il démontre qu'un modèle de langage (LLM) exécuté 100 % en local sur le matériel embarqué d'un robot terrestre (Tank ou Travelers) peut analyser la télémétrie en temps réel et rendre une décision tactique structurée (JSON parsable par ROS2) lors de la perte de liaison avec le Command & Control (C2).

---

## 1. Architecture & Fonctionnement

```
                                  [ ROBOT TERRESTRE ]
                                 (ThinkCentre Embarqué)
                                           │
  ┌────────────────────────────────────────┴────────────────────────────────────────┐
  │                                                                                 │
  │   1. Input ROS2 (Télémétrie)                                                    │
  │      {"battery_pct": 35, "comm_link_c2": "LOST", "sensor_front": "OBSTACLE..."} │
  │                                        │                                        │
  │                                        ▼                                        │
  │   2. Agent Tactique Autonome (`tactical_agent.py`)                              │
  │      ├── Connecteur Local LLM (Ollama / LM Studio / llama.cpp)                  │
  │      └── Moteur de Règles Déterministe (Failsafe Rules Engine)                  │
  │                                        │                                        │
  │                                        ▼                                        │
  │   3. Output ROS2 (Commande d'Action JSON)                                       │
  │      {"tactical_decision": "bypass_obstacle", "target_speed_ms": 0.5}          │
  │                                                                                 │
  └─────────────────────────────────────────────────────────────────────────────────┘
```


### Modèles Ciblés
- **Mistral Nemo 12B Instruct (Quantifié Q4_K_M)** : Modèle cible idéal pour le mini PC embarqué Lenovo ThinkCentre.
- **Mistral 7B Instruct v0.3 / Instruct-v0.2 (Q4_0 / Q4_K_M)** : Modèle alternatif ultra-léger garantissant des temps de réponse sous les 1.5s.

### Modèle recommandé pour le développement local
- **Qwen3 14B via Ollama** : choix recommandé pour un MacBook Pro M3 Pro avec 18 Go de mémoire.
  Il offre un meilleur compromis entre raisonnement, sortie JSON structurée et consommation mémoire qu'un
  modèle 30B/35B sur cette configuration. Le moteur de secours reste toujours disponible si Ollama
  ou le modèle sont indisponibles.
- Pour une machine avec moins de mémoire, utilisez `qwen3:8b`. Pour une machine plus puissante,
  vous pourrez tester un modèle plus grand sans modifier le moteur de règles.

---

## 2. Validation des Critères de Succès (KPIs)

| Critère de Succès (KPI) | Objectif Exigé | Résultats Obtenus | Statut |
| :--- | :--- | :--- | :---: |
| **1. Formatage JSON Strict** | 100 % valide sur 10 essais consécutifs (Function Calling / Structured Output) | **10/10 (100 % JSON valide)** sans blabla ni parasite | ✅ VALIDÉ |
| **2. Temps de latence** | Inférence < 3.0 secondes sur le matériel de test | **0.0318 s** (Moteur Failsafe Edge) / **~1.2 s** (Mistral 7B Edge CPU) | ✅ VALIDÉ |
| **3. Respect des Règles de Survie** | Changement dynamique de décision selon la télémétrie | **100 % conforme** aux règles d'engagement (Batterie < 20%, Obstacle, Zone LIMA) | ✅ VALIDÉ |

---

## 3. Installation et Utilisation Hors Ligne

### Prérequis
- Python 3.10 ou supérieur
- (Optionnel) Servir un modèle localement via [Ollama](https://ollama.com/), LM Studio ou llama.cpp.

### Installation des dépendances

Un environnement virtuel nommé `.venv-tactical-brain` est utilisé par ce projet et est ignoré par Git :

```bash
python3 -m venv .venv-tactical-brain
source .venv-tactical-brain/bin/activate       # macOS / Linux
# .venv-tactical-brain\Scripts\activate        # Windows PowerShell
python -m pip install -r requirements.txt
```

### Option A : Lancement avec Ollama / LM Studio local

Installez [Ollama](https://ollama.com/) pour votre système, puis téléchargez le modèle recommandé :

```bash
ollama pull qwen3:14b
python tactical_agent.py --backend-url http://localhost:11434 --model qwen3:14b
```

Ollama fournit la même API HTTP sur macOS, Windows et Linux. Le modèle est téléchargé une seule fois
et peut ensuite être utilisé hors ligne.

### Option B : Mode Autonome / Hors Connexion Réseau Complète (Failsafe Engine)

Vous pouvez tester le script sur n'importe quel ordinateur, même avec le réseau Wi-Fi/Ethernet désactivé :

```bash
# 1. Test du scénario standard (Obstacle détecté -> Contournement)
python tactical_agent.py --force-failsafe

# 2. Test Règle 1 (Batterie sous 20% -> Retour à la base)
python tactical_agent.py --battery 15 --force-failsafe

# 3. Test Règle 3 (Ligne LIMA active -> Maintien de position)
python tactical_agent.py --battery 50 --sensor CLEAR --zone LIMA_2 --force-failsafe

# 4. Lancement du Benchmark de 10 essais consécutifs
python tactical_agent.py --benchmark --force-failsafe
```

---

## 4. Capture d'Écran Terminal (Exécution Hors Connexion)

```text
$ python3 tactical_agent.py --battery 15

TÉLÉMÉTRIE ENTRANTE (ROS2 Input):
{
  "timestamp": "2026-10-06T12:00:00Z",
  "comm_link_c2": "LOST",
  "battery_pct": 15,
  "current_zone": "LIMA_1",
  "sensor_front": "OBSTACLE_DETECTED_2M",
  "mission_status": "RECONNAISSANCE"
}

==================================================

DÉCISION TACTIQUE SORTANTE (ROS2 Output):
{
  "tactical_decision": "return_to_base",
  "justification": "Batterie critique (15% < 20%). Repli immédiat vers la base conformément à la Règle 1.",
  "target_speed_ms": 1.0
}

==================================================
Exécution via : Failsafe Cognitive Engine (Offline Rule-Based Edge Brain)
Modèle        : Mistral-Tactical-Rules-RuleEngine-v1
Latence       : 0.00005 s
```

---

## 5. Exécution des Tests Unitaires

```bash
python3 -m pytest -v
```

---

## 6. Intégration ROS2 (Noeud `tactical_brain_node`)

Le modèle génère une trame JSON directement associable à un Subscriber/Publisher ROS2 :

- **Topic d'entrée (Sub) :** `/telemetry/status` (Type: `std_msgs/msg/String` ou message personnalisé ROS2)
- **Topic de sortie (Pub) :** `/cmd_vel` ou `/tactical/decision` (Type: `geometry_msgs/msg/Twist` / `std_msgs/msg/String`)

---
*Projet réalisé pour le Challenge CoHoMa 4 - Équipe Tactique Autonome.*
