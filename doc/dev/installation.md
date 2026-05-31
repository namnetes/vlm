# Installation

## Prérequis

| Outil | Rôle | Installation |
|-------|------|-------------|
| [uv](https://docs.astral.sh/uv/) | Gestionnaire de paquets Python | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python 3.12+ | Interpréteur (installé automatiquement par uv) | via `uv` |
| `lsof` | Détection du port libre pour MkDocs | présent par défaut sur Ubuntu |
| [jq](https://jqlang.github.io/jq/) | Requis par `script/export_csv.sh` | `sudo apt install jq` |

## Installation

```bash
# Cloner le dépôt
git clone <url-du-dépôt>
cd vlm

# Installer toutes les dépendances (prod + dev)
uv sync
```

`uv sync` crée automatiquement le virtualenv dans `.venv/` et installe les
dépendances déclarées dans `pyproject.toml`.

Pour ajouter une dépendance :

```bash
uv add <paquet>          # dépendance de production
uv add --dev <paquet>    # dépendance de développement uniquement
```

## Variables d'environnement

Copier `.env.example` en `.env` et renseigner les valeurs si nécessaire :

```bash
cp .env.example .env
```

| Variable | Rôle | Exemple |
|----------|------|---------|
| `APP_ENV` | Environnement d'exécution | `development` |
| `LOG_LEVEL` | Niveau de log global | `INFO` |
| `VLM_DATA_DIR` | Répertoire de base pour `export_csv.sh` | `/chemin/vers/datas` |

`VLM_DATA_DIR` est utilisé uniquement par `script/export_csv.sh` pour préfixer
les chemins relatifs passés en argument.
