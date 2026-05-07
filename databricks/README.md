# Databricks Asset Bundle — Pipeline Qualité de l'Eau

## Présentation

Ce bundle définit et versionne le pipeline **qualite_eau_pipeline** sur Databricks.
Il orchestre 4 notebooks en cascade pour traiter les données de qualité de l'eau
distribuée en France (départements 31, 33, 40, 64, 65 — années 2023 à 2025).

---

## Pipeline

| Ordre | Tâche | Notebook | Durée moyenne | Rôle |
|-------|-------|----------|---------------|------|
| 1 | `bronze` | `01_Bronze_Ingestion` | ~59s | Lecture des JSON Hub'Eau → table Delta brute |
| 2 | `silver` | `02_Silver_Transformation` | ~24s | Nettoyage, typage, enrichissement |
| 3 | `quality` | `04_Quality_Checks` | ~15s | Validation des règles métier |
| 4 | `gold` | `03_Gold_Aggregations` | ~23s | Agrégations pour analyse |

**Durée totale** : ~2 minutes  
**Schedule** : tous les jours à 02h00 (Europe/Paris)  
**Compute** : Serverless

---

## Déploiement

### Depuis Databricks (interface web)

1. Ouvre le panneau **Déploiements** 🚀 dans la barre latérale gauche
2. Clique sur **Déployer**
3. Pour lancer manuellement : survole le job dans le panneau et clique **Exécuter**

### Depuis la CLI (local)

```bash
# Installation
pip install databricks-cli

# Configuration
databricks configure --token

# Validation du bundle
databricks bundle validate

# Déploiement
databricks bundle deploy --target dev

# Lancement manuel
databricks bundle run qualite_eau_pipeline
```

---

## Configuration

Le fichier `databricks.yml` à la racine du projet contient :
- La définition des 4 tâches et leurs dépendances
- Le schedule cron
- Les chemins vers les notebooks
- La configuration compute (Serverless)

---

## Documentation Databricks

- [Bundles dans le workspace](https://docs.databricks.com/aws/en/dev-tools/bundles/workspace-bundles)
- [Référence de configuration](https://docs.databricks.com/aws/en/dev-tools/bundles/reference)