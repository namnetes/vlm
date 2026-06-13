# Image légère pour exécuter le pipeline VLM (clean → copt → json → extract)
# et interroger le résultat (export_csv.sh), sans installer Python ni uv sur
# l'hôte. Basée sur python:3.12-alpine, disponible en linux/amd64,
# linux/arm64 et linux/s390x.
FROM python:3.12-alpine

# make  : pilotage du pipeline via les cibles du Makefile
# bash  : SHELL du Makefile et shebang de script/export_csv.sh
# jq    : requis par script/export_csv.sh (cible `make query`)
# less  : requis par `make log`
# pip désinstallé : src/ ne dépend que de la stdlib, pip n'est jamais
# utilisé à l'exécution. Sa présence expose inutilement l'image aux CVE
# suivantes (toutes corrigées uniquement dans pip ≥ 26.1.2) :
#   CVE-2026-8643 (CVSS 5.5) — entry points installés hors du répertoire cible
#   CVE-2026-6357 (CVSS 5.3) — import de modules post-installation (CWE-829)
#   CVE-2026-3219 (CVSS 4.6) — archives tar+ZIP traitées comme ZIP (CWE-434)
#   CVE-2026-1703 (CVSS 2.0) — path traversal à l'extraction d'un wheel (CWE-22)
#   CVE-2025-8869 (CVSS 5.9) — liens symboliques hors répertoire cible (CWE-59)
RUN apk add --no-cache make bash jq less \
    && pip uninstall -y pip

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
