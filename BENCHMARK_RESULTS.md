# Benchmark vérifié des modèles locaux

Ce rapport contient uniquement les mesures réalisées dans ce projet sur le
MacBook Pro Apple M3 Pro avec 18 Go de mémoire, Ollama et
[`tactical_agent.py`](./tactical_agent.py).

## Trois KPI mesurés

1. **Structure** : la réponse respecte le schéma JSON `TacticalDecision`.
2. **Latence** : temps total de `agent.process(...)`, seuil demandé `< 3 s`.
3. **Véracité** : `tactical_decision` est identique à la décision attendue du
   moteur déterministe pour la même télémétrie et les trois règles :
   batterie critique, obstacle et ligne LIMA.

Chaque benchmark contient 10 essais : les quatre scénarios sont exécutés puis
répétés pour obtenir 10 décisions. Le champ `obtenue` est la décision du
modèle ou du failsafe ; le champ `attendue` est la référence calculée par
`evaluate_rules`.

## Résultats des 10 essais par modèle

| Modèle Ollama | Taille | Structure JSON | Latence moyenne | Latence min-max | Véracité | KPI latence |
|---|---:|---:|---:|---:|---:|---|
| `mistral:latest` | 4,4 Go | 10/10 (100 %) | 7,9895 s | 2,3341–11,3520 s | 10/10 (100 %) | ÉCHEC |
| `qwen3:14b` | 9,3 Go | 10/10 (100 %) | 8,0812 s | 5,6309–15,0222 s | 5/10 (50 %) | ÉCHEC |
| `qwen3:8b` | 5,2 Go | 10/10 (100 %) | 5,1193 s | 3,0032–10,9902 s | 5/10 (50 %) | ÉCHEC |
| `qwen3:4b` | 2,5 Go | 10/10 (100 %) | 1,8084 s | 1,6413–2,2653 s | 2/10 (20 %) | SUCCÈS |
| `qwen3:1.7b` | 1,4 Go | 10/10 (100 %) | 7,1751 s | 4,1349–10,4758 s | 10/10 (100 %) | ÉCHEC |

Les mesures ci-dessus sont les sorties réelles des benchmarks relancés après
l'ajout du KPI de véracité. La latence du modèle `qwen3:4b` est sous 3 secondes
sur ces 10 essais, mais sa véracité n'est que de 20 %. `mistral:latest` est le
seul modèle testé avec 100 % de véracité et il dépasse le budget de latence.

## Décisions observées

Les quatre scénarios de référence attendent, dans cet ordre :

```text
bypass_obstacle
return_to_base
hold_position
continue_mission
```

Sur les 10 essais :

- `mistral:latest` a produit cette séquence attendue sur les 10 essais ;
- `qwen3:1.7b` a produit cette séquence attendue sur les 10 essais, mais avec
  une latence supérieure à 3 secondes ;
- `qwen3:8b` et `qwen3:14b` ont généralement produit
  `continue_mission` pour les scénarios obstacle et LIMA ;
- `qwen3:4b` a produit `continue_mission` pour les scénarios obstacle,
  batterie critique et LIMA, et n'a été correct que sur le scénario voie libre.

Le rapport terminal affiche pour chaque essai la télémétrie, la décision
`obtenue`, la décision `attendue`, la validité JSON, la véracité et la latence.

## Conclusion

Aucun des modèles testés ne satisfait simultanément les trois KPI dans cette
configuration :

- `qwen3:4b` satisfait la latence, mais pas la véracité ;
- `mistral:latest` et `qwen3:1.7b` satisfont la véracité, mais pas la latence ;
- `qwen3:8b` et `qwen3:14b` ne satisfont ni la latence ni la véracité complète.

Le moteur déterministe reste donc nécessaire comme garde-fou de sécurité. Les
résultats ne sont pas extrapolables à un autre ordinateur, système ou
configuration Ollama.
