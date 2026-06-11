# Image légère pour exécuter le pipeline VLM (clean → copt → json → extract)
# et interroger le résultat (export_csv.sh), sans installer Python ni uv sur
# l'hôte. Basée sur python:3.12-alpine, disponible en linux/amd64,
# linux/arm64 et linux/s390x.
FROM python:3.12-alpine

# make  : pilotage du pipeline via les cibles du Makefile
# bash  : SHELL du Makefile et shebang de script/export_csv.sh
# jq    : requis par script/export_csv.sh (cible `make query`)
# less  : requis par `make log`
RUN apk add --no-cache make bash jq less

WORKDIR /app

COPY Makefile config.toml ./
COPY src/ src/
COPY script/ script/

# pyproject.toml déclare dependencies = [] : src/ ne dépend que de la
# stdlib Python. PYTHON_RUN vide fait pointer `make run` directement sur
# le `python` fourni par l'image — pas besoin de uv/venv en conteneur.
ENV PYTHON_RUN=

# Entrées/sorties du pipeline — chemins définis dans config.toml [settings].
VOLUME ["/app/datas"]

ENTRYPOINT ["make"]
CMD ["help"]
