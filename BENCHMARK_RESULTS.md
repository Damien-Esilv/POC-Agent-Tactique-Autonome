# Benchmark & Rapport d'Analyse de Performance Matérielle (CoHoMa 4)

Ce document consignes les résultats officiels du benchmark d'inférence locale exécuté sur la plateforme de test.

---

## 1. Contexte & Objectif du Benchmark

L'objectif de ce benchmark est de mesurer et comparer la capacité de différents modèles de langage locaux (Edge AI) à faire office de **Cerveau Tactique de Secours (Failsafe Cognitive Engine)** lors de la perte de liaison de données (C2) avec le robot terrestre.

### Les 3 Critères de Succès (KPIs) :

1. **KPI 1 - Structure JSON 100 % Valide :** Formatage parfait et parsable par le code ROS2 (10/10).
2. **KPI 2 - Temps de Latence Inférence :** Génération de la décision en **moins de 3,0 secondes**.
3. **KPI 3 - Respect des Règles de Survie (Véracité) :** Adhésion stricte aux règles de priorité tactiques (Batterie < 20% > Obstacle > Zone LIMA > Nominal).

---

## 2. Tableau Récapitulatif des Modèles Testés

| Modèle Local | Taille / Quantification | Warmup | Structure JSON (KPI 1) | Latence Moyenne (KPI 2) | Latence Min - Max | Véracité (KPI 3) | KPI Total (Verdict) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **mistral:latest** | ~7.2B | 6.7012 s | 10/10 (100 %) | **2.8561 s** | 1.9009 – 3.9198 s | 10/10 (100 %) | **SUCCÈS** |
| **qwen3:14b** | ~14.8B | 20.8432 s | 10/10 (100 %) | **15.5359 s** | 11.3476 – 21.5677 s | 10/10 (100 %) | **ÉCHEC** |
| **qwen3:8b** | ~8.2B | 21.0165 s | 10/10 (100 %) | **13.8974 s** | 10.4717 – 19.0131 s | 10/10 (100 %) | **ÉCHEC** |
| **qwen3:4b** | ~4.0B | 26.1985 s | 10/10 (100 %) | **22.2704 s** | 11.4100 – 41.3863 s | 10/10 (100 %) | **ÉCHEC** |
| **qwen3:1.7b** | ~2.0B | 5.5746 s | 10/10 (100 %) | **3.6790 s** | 2.5663 – 4.8930 s | 10/10 (100 %) | **ÉCHEC** |
| **failsafe_engine** | < 10 Mo | N/A | 10/10 (100 %) | **0.0002 s** | 0.0000 – 0.0020 s | 10/10 (100 %) | **SUCCÈS** |

---

## 3. Configuration Matérielle du Test

* **Machine de Test :** Apple MacBook Pro (16-inch)
* **Processeur (CPU) & NPU/GPU :** Apple M3 Pro (Architecture RAM Unifiée & Metal GPU)
* **Mémoire RAM / VRAM Disponibles :** 18 Go / 36 Go RAM Unifiée
* **Plateforme d'Inférence Locale :** Ollama API v0.4+ (Backends `/api/chat` et `/api/generate`)
* **Système d'Exploitation :** macOS Golden Gate

---

## 4. Analyse des Résultats & Recommandations

### 4.1 Analyse de la Latence (Seuil < 3.0s)

* **Mistral 7B (`mistral:latest`)** est le **seul LLM à valider le KPI 2** avec une latence moyenne de **2.8561 s** (< 3.0s). Il répond au cahier des charges opérationnel.
* **Série Qwen3 Reasoning (1.7B à 14B)** : Tous les modèles Qwen3 échouent au KPI 2.
* Malgré une taille plus réduite, **qwen3:4b** (22.27s moy.) s'avère plus lent que **qwen3:8b** (13.89s moy.) et **qwen3:14b** (15.53s moy.). Cela s'explique par la nature des modèles de raisonnement (*Thinking Models*) : plus le modèle est petit, plus il produit un grand nombre de tokens de réflexion interne (`<think>...</think>`), ce qui dégrade l'overhead de génération.
* **qwen3:1.7b** frôle le seuil avec **3.6790 s** en moyenne et des temps minimums à **2.5663 s**, mais reste disqualifié par la moyenne générale.


* **Moteur de Règles (`failsafe_engine`)** : Offre des temps de réponse quasi-instantanés de **0.0002 s** (0.2 ms), garantissant une sécurité critique temps réel sans charge matérielle.

### 4.2 Analyse du Respect des Consignes (Véracité & JSON)

* **KPI 1 (JSON) : 100 % (10/10)** sur tous les modèles. Le formatage strict demandé dans le prompt système est parfaitement respecté et parsable par Pydantic.
* **KPI 3 (Véracité) : 100 % (10/10)** sur tous les modèles. La logique de priorité (Règle 1 Batterie < 20% > Règle 2 Obstacle > Règle 3 Zone LIMA > Mode Nominal) est appliquée de manière déterministe et conforme aux exigences COHOMA.

### 4.3 Recommandation Finale pour Déploiement Embarqué

1. **Modèle Primaire (LLM Edge) : `mistral:latest**`
C'est le seul LLM qualifié offrant le parfait compromis entre intelligence contextuelle, respect strict des règles et latence sous la barre des 3 secondes.
2. **Fallback Obligatoire : `failsafe_engine` (Code Python Déterministe)**
Il doit servir de filet de sécurité principal si la latence réseau/Ollama dépasse 3.0s ou si le LLM est indisponible.
3. **Piste d'Optimisation (Qwen) :** Pour utiliser Qwen, il est fortement recommandé de remplacer la branche `qwen3` (reasoning) par les versions d'instruction pures **`qwen2.5:7b`** ou **`qwen2.5:3b`**, qui ne souffrent pas du surcoût de génération des tokens de réflexion.