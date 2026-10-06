# Résultats de benchmark vérifiés

Ce rapport contient uniquement des mesures réalisées dans ce projet sur le
MacBook Pro Apple M3 Pro avec 18 Go de mémoire, Ollama et la sortie JSON
structurée de `tactical_agent.py`.

## Méthode

- Une décision est envoyée à Ollama avec `stream: false`.
- Le temps mesuré est le temps total de `agent.process(...)`.
- `think` est désactivé (`"think": false`).
- Le premier appel peut inclure le chargement du modèle en mémoire.
- Les résultats ci-dessous ne sont pas extrapolés à Windows, Linux ou à un
  autre matériel.

## Mesures observées

| Modèle Ollama | Taille affichée par Ollama | Mesures observées | Résultat |
|---|---:|---|---|
| `qwen3:14b` | 9,3 Go | 9,4191 s sur une décision réelle | Au-dessus de 3 s |
| `qwen3:8b` | 5,2 Go | 5,3246 s sur une décision réelle | Au-dessus de 3 s |
| `qwen3:4b` | 2,5 Go | 10 essais : moyenne 2,9450 s ; minimum 1,6207 s ; maximum 3,8754 s | Moyenne sous 3 s, mais essais individuels au-dessus |
| `qwen3:1.7b` | 1,4 Go | 10 essais exécutés, tous en repli failsafe ; aucune inférence LLM valide mesurée | Non concluant |

Pour le dernier benchmark `qwen3:4b`, les 10 réponses étaient du JSON valide :
`10/10 (100 %)`. Le temps total mesuré pour ces 10 essais était de
`29,4499 s`.

## Limite fonctionnelle constatée

Le benchmark valide le format JSON et la latence, mais il ne valide pas la
conformité des décisions aux règles tactiques. Pendant le benchmark
`qwen3:4b`, le modèle a notamment renvoyé `continue_mission` pour les
scénarios de batterie critique et d'obstacle. Ces réponses ne correspondent
pas aux décisions attendues du moteur déterministe.

Le moteur failsafe reste donc la référence de sécurité. Une validation
fonctionnelle supplémentaire est nécessaire avant de considérer le LLM comme
autonome pour les règles de mission.

## Conclusion actuelle

Sur cette machine, `qwen3:4b` est le premier modèle testé dont la moyenne sur
une série de 10 essais est sous le seuil de 3 secondes. Le seuil n'est
toutefois pas respecté sur chaque décision : le maximum observé est de
3,8754 s. `qwen3:1.7b` n'a pas fourni de réponse LLM valide avec
l'intégration actuelle et a déclenché le failsafe.

Ces mesures ne constituent pas une validation générale des performances sur
d'autres ordinateurs ni une validation fonctionnelle complète des décisions
tactiques.
