# Qualité du code

## Lint — ruff

Le **lint** est une analyse automatique du code source qui détecte, sans
l'exécuter, les erreurs de style et certaines erreurs de logique courantes
(variable inutilisée, import manquant, etc.).
La configuration est dans `ruff.toml` (longueur de ligne 80, cible py312).

```bash
# Vérifier sans corriger
uv run ruff check src/ tests/

# Corriger automatiquement les erreurs corrigibles
uv run ruff check --fix src/ tests/

# Formater le code
uv run ruff format src/ tests/
```

## Vérification des types — mypy

Le projet utilise les **annotations de type** Python (ex :
`def f(x: int) -> str:`). `mypy` vérifie que ces annotations sont cohérentes
dans tout le code, ce qui permet de repérer certains bugs avant même
d'exécuter le programme.
La configuration est dans `pyproject.toml` — mode `strict` activé (le niveau
de vérification le plus exigeant).

```bash
uv run mypy src/
```

## Tout en une commande

```bash
uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest
```

`&&` enchaîne les commandes : chacune ne s'exécute que si la précédente a
réussi (code de sortie `0`). Tant qu'aucun test n'existe dans `tests/`,
`uv run pytest` se termine avec le code `5` (« no tests ran »), ce qui
arrêtera la chaîne à cette étape — ce n'est pas une erreur de votre
installation.

## Hooks pre-commit

Le projet utilise [pre-commit](https://pre-commit.com/) pour automatiser les
vérifications à chaque commit. Les hooks sont déclarés dans `.pre-commit-config.yaml`.

```bash
# Installer les hooks dans le dépôt git local (à faire une seule fois)
uv run pre-commit install

# Lancer manuellement tous les hooks sur tous les fichiers
uv run pre-commit run --all-files
```
