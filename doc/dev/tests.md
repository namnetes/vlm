# Tests

Les tests utilisent [pytest](https://docs.pytest.org/) avec couverture de code.
La configuration est dans `pyproject.toml` (`[tool.pytest.ini_options]`).

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
    `make clean` supprime le répertoire `htmlcov/` ainsi que le fichier `.coverage`.
