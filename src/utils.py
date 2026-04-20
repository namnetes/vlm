#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utilitaires partagés : configuration et logging du pipeline VLM.

VLM = View Load Module — fonction d'IBM File Manager qui analyse les load
modules d'une bibliothèque z/OS (loadlib). Le rapport produit (vlm.xml)
est la matière première du pipeline.

Ce module est le point d'entrée unique pour la configuration et le logging
de tous les scripts du pipeline. Il garantit que clean_report.py, reformat_copt.py
et build_json.py écrivent dans le même fichier ``pipeline.log`` avec un format
uniforme identifiant le script source via ``%(name)s``.

Exemple :
    from utils import load_config, setup_logging

    config = load_config()
    logger = setup_logging(config, "vlm")
    logger.info("Démarrage du traitement")
    logger.error("Fichier introuvable : %s", path)
"""

from __future__ import annotations

import logging
import sys
import tomllib
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Racine du projet : deux niveaux au-dessus de src/utils.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = _PROJECT_ROOT / "config.toml"


def load_config(config_path: Path = _DEFAULT_CONFIG) -> dict:
    """Charge et valide le fichier de configuration TOML.

    Args:
        config_path: Chemin vers ``config.toml``.
            Par défaut : racine du projet détectée automatiquement.

    Returns:
        Dictionnaire de configuration issu du TOML.

    Raises:
        SystemExit: Code 2 si le fichier est absent, code 3 si illisible.
    """
    if not config_path.is_file():
        print(
            f"[FATAL] Fichier de configuration introuvable : {config_path}",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        with config_path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        print(
            f"[FATAL] Erreur de décodage TOML dans {config_path} : {exc}",
            file=sys.stderr,
        )
        sys.exit(3)


def setup_logging(config: dict, logger_name: str) -> logging.Logger:
    """Initialise un logger nommé avec rotation fichier et sortie console.

    Deux handlers sont attachés au logger :

    * **RotatingFileHandler** — écrit tous les messages au niveau configuré
      dans ``logs/pipeline.log``. La rotation se déclenche quand le fichier
      atteint ``max_bytes`` ; ``backup_count`` archives sont conservées.

    * **StreamHandler** (stderr) — affiche uniquement les niveaux WARNING et
      supérieurs pour ne pas polluer le terminal en exécution normale.

    Le logger est isolé du root logger (``propagate = False``) afin d'éviter
    les doublons si d'autres bibliothèques configurent aussi le logging.

    Args:
        config: Dictionnaire retourné par :func:`load_config`.
        logger_name: Nom affiché dans la colonne ``%(name)s`` du format.
            Utiliser le nom du script appelant : ``"vlm"``, ``"copt"``,
            ``"xml2json"``, ``"pipeline"``.

    Returns:
        Logger prêt à l'emploi.
    """
    log_cfg: dict = config.get("logging", {})

    level_str: str = log_cfg.get("level", "INFO").upper()
    # getattr(objet, "nom", défaut) récupère un attribut par son nom en chaîne.
    # Ici : convertit la chaîne "INFO" en la constante logging.INFO (valeur entière).
    # Si level_str est invalide (ex: "VERBOSE"), le fallback logging.INFO s'applique.
    level: int = getattr(logging, level_str, logging.INFO)

    log_file: Path = _PROJECT_ROOT / log_cfg.get("file", "logs/pipeline.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    fmt: str = log_cfg.get(
        "format",
        "%(asctime)s | %(levelname)-8s | %(name)-12s | %(message)s",
    )
    formatter = logging.Formatter(fmt)

    # Handler fichier avec rotation par taille
    file_handler = RotatingFileHandler(
        filename=log_file,
        mode=log_cfg.get("mode", "a"),
        maxBytes=log_cfg.get("max_bytes", 2 * 1024**3),
        backupCount=log_cfg.get("backup_count", 5),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Handler console : WARNING+ seulement pour ne pas noyer le terminal
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Empêche la remontée vers le root logger (évite les messages en double)
    logger.propagate = False

    return logger
