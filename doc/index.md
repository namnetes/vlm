# VLM Pipeline — Documentation

> **VLM = View Load Module** — fonction d'IBM File Manager qui analyse
> les load modules d'une bibliothèque z/OS. Le rapport brut produit (vlm.xml)
> est la matière première de ce pipeline.

---

## Vue d'ensemble

Le pipeline transforme un rapport brut IBM mainframe en données structurées
interrogeables via CSV.

```
vlm.xml  (ISO-8859-1)
   │
   ▼
clean_report.py   →  clean_vlm.xml       Nettoyage, suppression du bruit
   │
   ▼
reformat_copt.py  →  clean_vlm_copt.xml  Reformatage des options COPT
   │
   ▼
build_json.py     →  vlm.json            Conversion XML → JSON structuré
   │
   ▼
extract_copt.py   →  CSV + TXT           Extraction des options par CSECT
```

## Documents disponibles

| Script | Rôle |
|---|---|
| [pipeline.py](pipeline/business_rules.md) | Orchestrateur — exécute les 4 étapes en séquence |
| [clean_report.py](clean_report/business_rules.md) | Étape 1 — nettoyage du rapport VLM brut |
| [reformat_copt.py](reformat_copt/business_rules.md) | Étape 2 — reformatage des balises COPT |
| [build_json.py](build_json/business_rules.md) | Étape 3 — conversion XML → JSON |
| [extract_copt.py](extract_copt/business_rules.md) | Étape 4 — extraction COPT par CSECT → CSV |
| [inspect_copt.py](inspect_copt/business_rules.md) | Utilitaire — inspection des balises COPT d'un XML |
| [export_csv.sh](export_csv/guide.md) | Script Bash — export du JSON vers CSV (3 modes) |

## Commandes rapides

```bash
# Installer l'environnement
uv sync

# Lancer le pipeline complet
uv run python src/pipeline.py

# Lancer une ou plusieurs étapes
uv run python src/pipeline.py 3        # étape 3 uniquement
uv run python src/pipeline.py 2-4     # étapes 2 à 4
uv run python src/pipeline.py extract # étape 4 par alias

# Exporter en CSV
bash script/export_csv.sh -i datas/vlm.json -o datas/output.csv -g

# Générer cette documentation (mode prévisualisation)
bash script/serve_docs.sh
# ou : uv run mkdocs serve

# Générer cette documentation (HTML statique)
uv run mkdocs build
```

## Développement

```bash
make test        # tests unitaires
make lint        # vérification du style (ruff)
make type-check  # vérification des types (mypy)
make check       # lint + type-check + tests en une commande
make help        # liste complète des cibles disponibles
```

## Environnement technique

- **Mainframe** : IBM z/OS 3.2
- **Compilateur** : IBM Enterprise COBOL 6.5
- **Python** : 3.12+, gestionnaire de paquets `uv`
- **Format de sortie** : JSON + CSV (délimiteur `;`, encodage UTF-8)
