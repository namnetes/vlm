# Qualité du code

## Lint — ruff

La configuration est dans `ruff.toml` (longueur de ligne 88, cible py312).

```bash
# Vérifier sans corriger
uv run ruff check src/ tests/

# Corriger automatiquement les erreurs corrigibles
uv run ruff check --fix src/ tests/

# Formater le code
uv run ruff format src/ tests/
```

## Vérification des types — mypy

La configuration est dans `pyproject.toml` — mode `strict` activé.

```bash
uv run mypy src/
```

## Tout en une commande

```bash
uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest
```

## Hooks pre-commit

Le projet utilise [pre-commit](https://pre-commit.com/) pour automatiser les
vérifications à chaque commit. Les hooks sont déclarés dans `.pre-commit-config.yaml`.

```bash
# Installer les hooks dans le dépôt git local (à faire une seule fois)
uv run pre-commit install

# Lancer manuellement tous les hooks sur tous les fichiers
uv run pre-commit run --all-files
```
