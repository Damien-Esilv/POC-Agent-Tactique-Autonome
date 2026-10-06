# Failsafe Cognitive COHOMA - Agent Tactique Autonome

POC d'un agent tactique local pour analyser une télémétrie robot et produire
une décision JSON exploitable par ROS2 en cas de perte de liaison C2.

## Configuration actuelle

La configuration par défaut se trouve dans [`config.json`](./config.json).
Elle utilise Ollama et le modèle `qwen3:4b`, téléchargé avec :

```bash
ollama pull qwen3:4b
```

Le modèle configuré par défaut est `mistral:latest`, choisi pour sa véracité
de 10/10 dans le benchmark. Les résultats réels, y compris le dépassement du
budget de latence, sont dans
[`BENCHMARK_RESULTS.md`](./BENCHMARK_RESULTS.md).

Le champ `think` d'Ollama est désactivé par défaut afin de limiter la latence :

```json
{
  "platform": "ollama",
  "model": "mistral:latest",
  "timeout_sec": 60.0,
  "think": false,
  "ollama_options": {
    "temperature": 0.0,
    "num_predict": 160
  },
  "fallback_to_failsafe": true
}
```

Le code retente automatiquement sans le champ `think` si l'instance Ollama
répond que cette option n'est pas supportée. Une réponse LLM invalide ou
indisponible déclenche le moteur de règles déterministe.

## Installation

```bash
python3 -m venv .venv-tactical-brain
source .venv-tactical-brain/bin/activate
python -m pip install -r requirements.txt
```

Sous Windows PowerShell :

```powershell
py -m venv .venv-tactical-brain
.venv-tactical-brain\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Utilisation

Lancer avec les valeurs de [`config.json`](./config.json) :

```bash
python tactical_agent.py
```

Forcer le moteur déterministe hors ligne :

```bash
python tactical_agent.py --force-failsafe
```

Lancer le benchmark mesuré :

```bash
python tactical_agent.py --benchmark
```

Le benchmark mesure trois KPI : structure JSON, latence et véracité de la
décision par rapport aux trois règles du moteur déterministe. Les options de
ligne de commande peuvent surcharger ponctuellement la configuration, mais le
fichier JSON reste la configuration par défaut.

## Tests

```bash
python -m pytest -q
```

## Compatibilité

Le code Python et l'API Ollama sont prévus pour macOS, Windows et Linux.
Les mesures du benchmark ne sont toutefois valables que pour le matériel et
la configuration indiqués dans [`BENCHMARK_RESULTS.md`](./BENCHMARK_RESULTS.md).
