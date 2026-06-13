# Développement — Vue d'ensemble

Cette section regroupe tout ce qu'il faut savoir pour développer et
maintenir le pipeline VLM : installer l'environnement, piloter le projet
via le `Makefile`, écrire des tests et respecter les standards de qualité
de code (lint, typage, hooks pre-commit).

!!! info "Prérequis"
    Aucune connaissance préalable de `uv`, `make`, `pytest`, `ruff` ou
    `mypy` n'est nécessaire — chaque page part de zéro.

<div class="grid cards" markdown>

-   :material-download: **[Installation](installation.md)**

    Prérequis, installation des dépendances avec `uv` et configuration des
    variables d'environnement.

-   :material-cog-play: **[Le Makefile](makefile.md)**

    Toutes les cibles `make` du projet : pipeline, export CSV, journal,
    nettoyage, conteneurisation et documentation.

-   :material-test-tube: **[Tests](tests.md)**

    Convention de nommage `pytest`, exécution des tests et rapport de
    couverture.

-   :material-check-decagram: **[Qualité du code](qualite.md)**

    Lint avec `ruff`, vérification des types avec `mypy` et hooks
    `pre-commit`.

</div>
