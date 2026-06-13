#!/usr/bin/env python3
"""Exécute la chaîne de traitement VLM complète ou un sous-ensemble d'étapes.

VLM = View Load Module — fonction d'IBM File Manager qui analyse les load
modules d'une bibliothèque z/OS (loadlib). Le rapport brut produit par
cette fonction (vlm.xml) est la matière première de ce pipeline.

Étapes disponibles :
  1  clean    — Nettoyage du rapport VLM brut        (clean_report.py)
  2  copt     — Reformatage des balises COPT          (reformat_copt.py)
  3  json     — Conversion XML → JSON                 (build_json.py)
  4  extract  — Extraction COPT par CSECT → CSV       (extract_copt.py)

Usage :
    python src/pipeline.py                  # toutes les étapes (1-4)
    python src/pipeline.py --steps 3        # étape 3 uniquement
    python src/pipeline.py --steps 3-4      # étapes 3 et 4
    python src/pipeline.py --steps 2-4      # étapes 2 à 4

Les chemins configurables (entrée/sorties) sont définis dans config.toml.
Les fichiers intermédiaires sont câblés dans ce script.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from utils import load_config, setup_logging

# Racine du projet et répertoire des scripts — constantes structurelles.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# Chargement de la configuration depuis config.toml.
# _config   = dictionnaire complet : { "logging": {...}, "settings": {...} }
# _settings = sous-section "settings" contenant les chemins vlm_input, final_json, copt_csv.
_config = load_config()
_settings = _config.get("settings", {})

# Logger du pipeline — initialiser tôt pour que toutes les étapes soient tracées.
LOGGER = logging.getLogger("pipeline")
setup_logging(_config, "pipeline")

# Chemins configurables dans config.toml.
VLM_INPUT = PROJECT_ROOT / _settings["vlm_input"]
FINAL_JSON = PROJECT_ROOT / _settings["final_json"]
COPT_CSV = PROJECT_ROOT / _settings["copt_csv"]

# Fichiers intermédiaires — codés en dur, non configurables dans config.toml.
# Chaque étape produit exactement un fichier passé en entrée à l'étape suivante.
CLEAN_XML = PROJECT_ROOT / "datas/clean_vlm.xml"  # Sortie de l'étape 1
COPT_XML = PROJECT_ROOT / "datas/clean_vlm_copt.xml"  # Sortie de l'étape 2
COPT_IGNORED = PROJECT_ROOT / "datas/copt_ignored.txt"  # Trace LEINFO (étape 2)

STEP_COUNT = 4

# Alias nommés → numéro d'étape.
# dict[str, int] = dictionnaire dont les clés sont des chaînes (noms)
# et les valeurs des entiers (numéros d'étape).
# Permet d'écrire "pipeline.py extract" au lieu de "pipeline.py 4".
STEP_ALIASES: dict[str, int] = {
    "clean": 1,
    "copt": 2,
    "json": 3,
    "extract": 4,
}


def parse_steps(value: str) -> list[int]:
    """Parse un sélecteur d'étapes : '3', '2-4', 'extract', 'copt-extract'.

    Formats acceptés :
        N          étape unique par numéro (ex : 3)
        N-M        plage par numéro        (ex : 2-4)
        name       étape unique par alias  (ex : extract)
        name-name  plage par alias         (ex : copt-extract)

    Args:
        value: Chaîne saisie par l'utilisateur.

    Returns:
        Liste triée d'entiers représentant les étapes à exécuter.

    Raises:
        argparse.ArgumentTypeError: Si le format est invalide ou hors plage.

    """

    def resolve(token: str) -> int:
        """Convertit un token (numéro ou alias) en indice d'étape."""
        if token in STEP_ALIASES:
            return STEP_ALIASES[token]
        try:
            return int(token)
        except ValueError:
            known = ", ".join(
                f"{v}={k}"
                for k, v in sorted(STEP_ALIASES.items(), key=lambda x: x[1])
            )
            raise argparse.ArgumentTypeError(
                f"Étape inconnue : '{token}'. "
                f"Valeurs acceptées : numéro 1-{STEP_COUNT} ou alias ({known})."
            ) from None

    if "-" in value:
        # Sépare sur le premier tiret qui n'est pas dans un alias nommé.
        # On tente d'abord une découpe simple ; si l'un des tokens est
        # invalide, argparse remonte l'erreur via resolve().
        parts = value.split("-", 1)
        start, end = resolve(parts[0]), resolve(parts[1])
    else:
        start = end = resolve(value)

    if not (1 <= start <= STEP_COUNT and 1 <= end <= STEP_COUNT):
        raise argparse.ArgumentTypeError(
            f"Les indices d'étapes doivent être compris entre 1 et {STEP_COUNT}."
        )
    if start > end:
        raise argparse.ArgumentTypeError(
            f"L'étape de départ ({start}) doit être ≤ à l'étape de fin ({end})."
        )

    return list(range(start, end + 1))


def build_parser() -> argparse.ArgumentParser:
    """Construit le parseur d'arguments du pipeline."""
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description=(
            "Chaîne de traitement VLM — transforme un rapport IBM mainframe "
            "en JSON et CSV.\n\n"
            "Étapes disponibles :\n"
            "  1  clean    Nettoyage du rapport VLM brut         (clean_report.py)\n"
            "  2  copt     Reformatage des balises COPT          (reformat_copt.py)\n"
            "  3  json     Conversion XML → JSON                 (build_json.py)\n"
            "  4  extract  Extraction COPT par CSECT → CSV       (extract_copt.py)\n"
        ),
        epilog=(
            "Exemples :\n"
            "  pipeline.py             # toutes les étapes\n"
            "  pipeline.py 3           # étape 3 uniquement\n"
            "  pipeline.py 2-4         # étapes 2 à 4\n"
            "  pipeline.py extract     # étape 4 par alias\n"
            "  pipeline.py copt-json   # étapes 2-3 par alias\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "steps",
        metavar="STEPS",
        nargs="?",
        type=parse_steps,
        default=list(range(1, STEP_COUNT + 1)),
        help=(
            "Étape(s) à exécuter : N, N-M, alias ou alias-alias. "
            "Par défaut : toutes les étapes (1-4)."
        ),
    )
    return parser


def run_step(cmd: list[str], step_num: int, label: str) -> None:
    """Exécute une commande subprocess et interrompt le pipeline en cas d'échec.

    Args:
        cmd: Commande à exécuter.
        step_num: Numéro de l'étape (pour les messages).
        label: Nom court de l'étape (pour les messages).

    Raises:
        SystemExit: Si le code de retour est non nul.

    """
    # check=False : on gère nous-mêmes le code de retour ci-dessous pour
    # afficher un message d'étape clair avant de propager le code de sortie.
    ret = subprocess.run(cmd, check=False)
    if ret.returncode != 0:
        LOGGER.error(
            "Échec de l'étape %d (%s) — code de retour %d.",
            step_num,
            label,
            ret.returncode,
        )
        print(f"Erreur lors de l'étape {step_num} ({label})")
        sys.exit(ret.returncode)
    LOGGER.info("Étape %d (%s) terminée avec succès.", step_num, label)


def main() -> None:
    """Point d'entrée principal du pipeline."""
    parser = build_parser()
    args = parser.parse_args()
    steps: list[int] = args.steps

    LOGGER.info(
        "Démarrage du pipeline — étapes %s : entrée='%s', JSON='%s', COPT='%s'.",
        steps,
        VLM_INPUT,
        FINAL_JSON,
        COPT_CSV,
    )

    total = len(steps)

    # --- Étape 1 : Nettoyage du rapport VLM ---
    if 1 in steps:
        idx = steps.index(1) + 1
        print(f"[{idx}/{total}] Nettoyage du rapport VLM...")
        LOGGER.info(
            "[%d/%d] Nettoyage : '%s' → '%s'.", idx, total, VLM_INPUT, CLEAN_XML
        )
        run_step(
            [
                sys.executable,
                str(SRC_DIR / "clean_report.py"),
                "-f",
                str(VLM_INPUT),
                "-o",
                str(CLEAN_XML),
                "-e",
                "iso8859-1",
            ],
            step_num=1,
            label="clean_report.py",
        )

    # --- Étape 2 : Reformatage des balises COPT ---
    if 2 in steps:
        idx = steps.index(2) + 1
        print(f"[{idx}/{total}] Reformatage des balises Copt...")
        LOGGER.info(
            "[%d/%d] Reformatage : '%s' → '%s'.",
            idx,
            total,
            CLEAN_XML,
            COPT_XML,
        )
        run_step(
            [
                sys.executable,
                str(SRC_DIR / "reformat_copt.py"),
                "-f",
                str(CLEAN_XML),
                "-o",
                str(COPT_XML),
                "-e",
                "utf-8",
                "--ignored-file",
                str(COPT_IGNORED),
            ],
            step_num=2,
            label="reformat_copt.py",
        )

    # --- Étape 3 : Conversion XML → JSON ---
    if 3 in steps:
        idx = steps.index(3) + 1
        print(f"[{idx}/{total}] Conversion XML → JSON...")
        LOGGER.info(
            "[%d/%d] Conversion : '%s' → '%s'.",
            idx,
            total,
            COPT_XML,
            FINAL_JSON,
        )
        run_step(
            [
                sys.executable,
                str(SRC_DIR / "build_json.py"),
                "-f",
                str(COPT_XML),
                "-o",
                str(FINAL_JSON),
                "-e",
                "utf-8",
            ],
            step_num=3,
            label="build_json.py",
        )

    # --- Étape 4 : Extraction COPT par CSECT → CSV ---
    if 4 in steps:
        idx = steps.index(4) + 1
        print(f"[{idx}/{total}] Extraction des options COPT par CSECT...")
        LOGGER.info(
            "[%d/%d] Extraction : '%s' → '%s'.",
            idx,
            total,
            FINAL_JSON,
            COPT_CSV,
        )
        # extract_copt.py refuse d'écraser un fichier existant.
        if COPT_CSV.exists():
            LOGGER.debug("Suppression du CSV existant : '%s'.", COPT_CSV)
            COPT_CSV.unlink()
        run_step(
            [
                sys.executable,
                str(SRC_DIR / "extract_copt.py"),
                "-f",
                str(FINAL_JSON),
                "-o",
                str(COPT_CSV),
            ],
            step_num=4,
            label="extract_copt.py",
        )

    LOGGER.info(
        "Pipeline terminé avec succès. JSON : '%s' | COPT CSV : '%s'.",
        FINAL_JSON,
        COPT_CSV,
    )
    print("Pipeline terminé avec succès !")
    if 3 in steps:
        print(f"Fichier JSON final : {FINAL_JSON}")
    if 4 in steps:
        print(f"Fichier COPT CSV  : {COPT_CSV}")


if __name__ == "__main__":
    main()
