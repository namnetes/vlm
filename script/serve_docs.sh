#!/usr/bin/env bash
# Démarre le serveur MkDocs en mode prévisualisation locale.
# La documentation est disponible sur http://127.0.0.1:8000
# Arrêt : Ctrl+C

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if ! command -v uv &>/dev/null; then
    echo "Erreur : 'uv' est introuvable. Installer depuis https://docs.astral.sh/uv/" \
        >&2
    exit 1
fi

echo "Documentation disponible sur http://127.0.0.1:8000 (Ctrl+C pour arrêter)"
uv run mkdocs serve
