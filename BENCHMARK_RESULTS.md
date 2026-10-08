# Benchmark & Rapport d'Analyse de Performance Matérielle (CoHoMa 4)

Ce document sert de **base de travail et de modèle de rapport** pour consigner les résultats de benchmark obtenus lors des tests d'inférence locale sur le matériel de test.

---

## 1. Contexte & Objectif du Benchmark

L'objectif de ce benchmark est de mesurer et comparer la capacité de différents modèles de langage locaux (Edge AI) à faire office de **Cerveau Tactique de Secours (Failsafe Cognitive Engine)** lors de la perte de liaison de données (C2) avec le robot terrestre.

### Les 3 Critères de Succès (KPIs) :
1. **KPI 1 - Structure JSON 100 % Valide :** Formatage parfait et parsable par le code ROS2 (10/10).
2. **KPI 2 - Temps de Latence Inférence :** Génération de la décision en **moins de 3,0 secondes**.
3. **KPI 3 - Respect des Règles de Survie (Véracité) :** Adhésion stricte aux règles de priorité tactiques (Batterie < 20% > Obstacle > Zone LIMA > Nominal).

---

## 2. Tableau Récapitulatif des Modèles Testés

> *Note : Ce tableau est à remplir avec les résultats obtenus lors de l'exécution de la commande `python3 tactical_agent.py --benchmark`.*

| Modèle Local | Taille / Quantification | Structure JSON (KPI 1) | Latence Moyenne (KPI 2) | Latence Min - Max | Véracité (KPI 3) | KPI Total (Verdict) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| *[Nom Modèle 1]* | *[Taille]* | /10 | s | s – s | /10 | *[SUCCÈS / ÉCHEC]* |
| *[Nom Modèle 2]* | *[Taille]* | /10 | s | s – s | /10 | *[SUCCÈS / ÉCHEC]* |
| *[Nom Modèle 3]* | *[Taille]* | /10 | s | s – s | /10 | *[SUCCÈS / ÉCHEC]* |
| *[Nom Modèle 4]* | *[Taille]* | /10 | s | s – s | /10 | *[SUCCÈS / ÉCHEC]* |
| *[Nom Modèle 5]* | *[Taille]* | /10 | s | s – s | /10 | *[SUCCÈS / ÉCHEC]* |
| **failsafe_engine** | < 10 Mo | /10 | s | s – s | /10 | **SUCCÈS** |

---

## 3. Configuration Matérielle du Test

- **Machine de Test :** *[Ex: Apple MacBook Pro M3 Pro / PC Portable]*
- **Processeur (CPU) & NPU/GPU :** *[Ex: Apple M3 Pro 12-core / Intel i7]*
- **Mémoire RAM / VRAM Disponibles :** *[Ex: 18 Go RAM Unifiée / 16 Go DDR5]*
- **Plateforme d'Inférence Locale :** *[Ex: Ollama v0.4 / LM Studio / llama.cpp]*
- **Système d'Exploitation :** *[Ex: macOS / Ubuntu 22.04 LTS / Windows 11]*

---

## 4. Analyse des Résultats & Recommandations

### 4.1 Analyse de la Latence (Seuil < 3.0s)
*[Rédiger ici l'analyse sur les modèles qui respectent ou dépassent le seuil de 3.0s]*

### 4.2 Analyse du Respect des Consignes (Véracité)
*[Rédiger ici l'analyse sur le taux de réussite du suivi d'instructions par les modèles]*

### 4.3 Recommandation Finale pour Déploiement Embarqué
*[Conclure sur le meilleur modèle à intégrer dans le mini PC ThinkCentre embarqué du robot]*
