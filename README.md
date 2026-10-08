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
| **KPI 1 : Formatage JSON Strict** | Output 100 % parsable sans blabla | Parsing Pydantic (`TacticalDecision`) sur 10 essais | ✅ **100% Parsable** |
| **KPI 2 : Temps de Latence Inférence** | Temps de réponse < 3.0 secondes | Horodatage `time.perf_counter()` | ✅ **< 3.0s** |
| **KPI 3 : Respect des Règles de Survie** | Conformité décisionnelle par scénario | Vérification de la décision Obtenue vs Attendue | ✅ **100% Conforme** |

---

## 2. Configuration Multi-Modèles (`config.json`)

Vous pouvez configurer plusieurs modèles à comparer ou basculer sur votre modèle préféré en un clic dans `config.json` ou via les arguments CLI :

```json
{
  "platform": "ollama",
  "model": "mistral:latest",
  "models": [
    "mistral:latest",
    "qwen2.5:8b",
    "llama3.2:3b",
    "failsafe_engine"
  ],
  "platforms_config": {
    "ollama": { "url": "http://localhost:11434" },
    "lm_studio": { "url": "http://localhost:1234" },
    "llama_cpp": { "url": "http://localhost:8080" }
  },
  "timeout_sec": 3.0,
  "fallback_to_failsafe": true
}
```

---

## 3. Installation & Benchmark Multi-Modèles

```bash
# Installation des dépendances
pip install -r requirements.txt

# Exécution du benchmark multi-modèles (Tableau comparatif de fin)
python3 tactical_agent.py --benchmark

# Benchmark détaillé avec affichage de chaque test
python3 tactical_agent.py --benchmark --verbose

# Tester des modèles spécifiques via CLI
python3 tactical_agent.py --models mistral:latest qwen2.5:8b --benchmark
```

---

## 4. Exemple de Tableau Comparatif Terminal

À la fin du benchmark multi-modèles, un tableau comparatif synthétise les résultats avec des indicateurs de couleur stricts (vert pour succès, rouge pour échec) :

```text
======================================================================================
                    TABLEAU COMPARATIF DES PERFORMANCE MODÈLES
======================================================================================
| Modèle             | Taille    | Structure JSON  | Latence Moy.  | Latence Min-Max    | Véracité        | KPI Total  |
|--------------------|-----------|-----------------|---------------|--------------------|-----------------|------------|
| mistral:latest     | 4,4 Go    | 10/10 (100 %)   | 1.1240 s       | 0.8502–2.3341 s    | 10/10 (100 %)   | SUCCÈS     |
| qwen2.5:8b         | 4,4 Go    | 10/10 (100 %)   | 1.0512 s       | 0.7810–1.9540 s    | 10/10 (100 %)   | SUCCÈS     |
| llama3.2:3b        | 2,0 Go    | 10/10 (100 %)   | 0.6120 s       | 0.4210–1.1200 s    | 10/10 (100 %)   | SUCCÈS     |
| failsafe_engine    | < 10 Mo   | 10/10 (100 %)   | 0.0001 s       | 0.0000–0.0001 s    | 10/10 (100 %)   | SUCCÈS     |
======================================================================================
```

---

## 5. Tests Unitaires & Documentation Complémentaire
```bash
python3 -m pytest -v
```
Voir [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md) pour le rapport d'analyse matérielle et la comparaison d'empreinte mémoire entre modèles 7B/8B et 14B.
