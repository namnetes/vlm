.PHONY: install test test-cov lint lint-fix format type-check check \
        pre-commit clean docs-serve docs-build help

install:
	uv sync

test:
	uv run pytest

test-cov:
	uv run pytest --cov=src --cov-report=html
	@echo "Rapport de couverture : htmlcov/index.html"

lint:
	uv run ruff check src/ tests/

lint-fix:
	uv run ruff check --fix src/ tests/

format:
	uv run ruff format src/ tests/

type-check:
	uv run mypy src/

check: lint type-check test

pre-commit:
	uv run pre-commit run --all-files

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	rm -f .coverage 2>/dev/null || true

docs-serve:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build
	@echo "Site construit dans site/"

.DEFAULT_GOAL := help

help:
	@printf '\033[1mCibles disponibles :\033[0m\n'
	@printf '  %-22s %s\n' install       'Installer les dépendances (uv sync)'
	@printf '  %-22s %s\n' test          'Lancer la suite de tests'
	@printf '  %-22s %s\n' test-cov      'Tests avec rapport de couverture HTML'
	@printf '  %-22s %s\n' lint          'Vérifier le style avec ruff'
	@printf '  %-22s %s\n' lint-fix      'Corriger automatiquement les erreurs ruff'
	@printf '  %-22s %s\n' format        'Formater le code avec ruff format'
	@printf '  %-22s %s\n' type-check    'Vérifier les types avec mypy'
	@printf '  %-22s %s\n' check         'lint + type-check + test'
	@printf '  %-22s %s\n' pre-commit    'Exécuter tous les hooks pre-commit'
	@printf '  %-22s %s\n' clean         'Supprimer les artefacts et caches'
	@printf '  %-22s %s\n' docs-serve    'Démarrer MkDocs en local (http://127.0.0.1:8000)'
	@printf '  %-22s %s\n' docs-build    'Compiler la documentation MkDocs'
