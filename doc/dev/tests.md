# Tests

Les tests utilisent [pytest](https://docs.pytest.org/) avec couverture de code.
La configuration est dans `pyproject.toml` (`[tool.pytest.ini_options]`).

!!! note "Aucun test pour le moment"
    Le répertoire `tests/` est vide pour l'instant (seul `tests/__init__.py`
    existe). Lancer `uv run pytest` affichera donc `no tests ran` avec un
    code de sortie `5` — c'est normal. Les exemples ci-dessous montrent la
    syntaxe à utiliser **dès qu'un fichier de test sera ajouté**.

## Convention de nommage

- Un fichier de test pour `src/mon_module.py` s'appelle
  `tests/test_mon_module.py`.
- Une fonction de test commence par `test_`, par exemple
  `def test_ma_fonctionnalite(): ...`.
- pytest découvre automatiquement ces fichiers et fonctions, sans
  configuration supplémentaire.

## Lancer les tests

```bash
# Tous les tests avec rapport de couverture (terminal)
uv run pytest

# Un seul fichier de tests
uv run pytest tests/test_clean_report.py -v

# Un seul test par nom
uv run pytest tests/test_clean_report.py::test_strip_asa_char -v
```

## Rapport de couverture HTML

```bash
uv run pytest --cov=src --cov-report=html
```

Ouvrir ensuite `htmlcov/index.html` dans un navigateur.

!!! note
    `make clean` supprime le répertoire `htmlcov/` ainsi que le fichier
    `.coverage` (voir [Le Makefile](makefile.md#7-nettoyage--make-clean)).
