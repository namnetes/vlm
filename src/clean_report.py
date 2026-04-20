#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Nettoie un rapport VLM File Manager et produit un XML bien formé.

Terminologie mainframe IBM z/OS (utilisée dans ce module) :
- VLM         : View Load Module — fonction d'IBM File Manager qui analyse les
                load modules d'une bibliothèque z/OS (loadlib). Le rapport brut
                produit (vlm.xml) est l'entrée de ce script.
- Loadlib     : Load Library — bibliothèque PDS/PDSE contenant des modules exécutables.
- memberCount : nombre de membres (programmes) lus dans la loadlib.
- ASA         : caractère de contrôle imprimante (héritage mainframe) en tête de ligne.
- DSN/DSNIN  : Data Set Name — nom du jeu de données (fichier) mainframe.

Le rapport d'entrée est un mélange de lignes de texte brut et de balises
XML. Ce script filtre le contenu hétérogène pour ne conserver qu'un XML
UTF-8 encapsulé dans une balise ``<root>``, enrichi des attributs ``loadlib``
et ``memberCount``.

Exemple :
    python src/clean_report.py -f datas/vlm.xml -o datas/clean_vlm.xml -e iso8859-1
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Iterator

from utils import load_config, setup_logging

# -------------------------------------------------------------------------------------
# Constantes module
# -------------------------------------------------------------------------------------

LOGGER = logging.getLogger("clean_report")

# --- Expressions régulières (regex) pré-compilées ---
# re.compile() compile la regex une seule fois au chargement du module,
# ce qui est plus efficace que de la recompiler à chaque appel de fonction.

# Extrait le nom de la loadlib depuis "DSNIN=SYS1.LINKLIB" → "SYS1.LINKLIB".
# \w = [a-zA-Z0-9_], \. = un point littéral ; groupe 1 = la valeur capturée.
_RE_DSN: re.Pattern[str] = re.compile(r"DSNIN=([\w\.]+)")

# Extrait le nombre de membres depuis "FMNBB437 42 member(s) read" → "42".
# \s+ = un ou plusieurs espaces, \d+ = un ou plusieurs chiffres (groupe 1).
_RE_COUNT: re.Pattern[str] = re.compile(r"FMNBB437\s+(\d+)\s+member\(s\) read")

# Détecte une bibliothèque vide (aucun membre à lire).
_RE_EMPTY: re.Pattern[str] = re.compile(r"FMNBE329\s+The PDS contains no members")

# Détecte l'erreur métier FMNBF427 et capture son message (groupe 1).
_RE_ERROR: re.Pattern[str] = re.compile(r"FMNBF427\s+(.*)")

# Ensemble des préfixes de lignes à ignorer dans le rapport brut.
# frozenset est un ensemble immuable : optimisé pour les tests d'appartenance (in).
# Ces lignes sont des métadonnées File Manager sans intérêt pour le XML final.
_NOISE_PREFIXES: frozenset[str] = frozenset(
    {
        "IBM File",   # En-tête du rapport File Manager
        "FMNBA001",   # Message de démarrage
        "FMNBA010",   # Message de fin
        "DEFAULT SET",
        "PRINTOUT=",
        "PRINTLEN=",
        "PAGESIZE=",
        "PRTTRANS=",
        "SMFNO=",
        "TEMP UNIT=",
        "PERM UNIT=",
        "TRACECLS=",
        "$$FILEM",    # Sauf "$$FILEM VLM" qui contient le nom de la loadlib
    }
)


# -------------------------------------------------------------------------------------
# Fonctions pures
# -------------------------------------------------------------------------------------


def strip_asa_char(line: str) -> str:
    """Supprime le caractère de contrôle ASA en tête de ligne.

    ASA (American Standard Association) est un héritage des imprimantes
    mainframe : chaque ligne du rapport commence par un caractère spécial
    indiquant le saut de ligne à effectuer avant l'impression :
    - ``' '`` (espace) : impression normale sur la ligne courante.
    - ``'0'``           : saut d'une ligne avant impression.
    - ``'1'``           : saut de page avant impression.
    - ``'-'``           : retour en arrière d'une ligne.

    Ce caractère n'a aucun intérêt dans un fichier XML ; il faut le supprimer.

    Args:
        line: Ligne brute issue du fichier rapport (avec caractère ASA en position 0).

    Returns:
        Ligne sans le premier caractère, avec espaces de début/fin supprimés.
    """
    return line[1:].strip()


def is_noise_line(line: str) -> bool:
    """Indique si une ligne est du bruit technique à ignorer.

    Une ligne est considérée comme du bruit si elle commence par l'un des
    préfixes de ``_NOISE_PREFIXES``, sauf ``$$FILEM VLM`` qui porte le
    nom de la loadlib et doit être conservé.

    Args:
        line: Ligne déjà passée par :func:`strip_asa_char`.

    Returns:
        ``True`` si la ligne doit être ignorée.
    """
    if not line:
        return True
    if line.startswith("$$FILEM VLM"):
        return False
    return any(line.startswith(prefix) for prefix in _NOISE_PREFIXES)


def read_member_count(f_in: Iterator[str]) -> int:
    """Lit la ligne suivante du flux et en extrait le nombre de membres.

    File Manager émet le message ``FMNBB437 N member(s) read`` juste
    après la balise fermante ``</vlm>``. Cette fonction consomme cette
    unique ligne et retourne le compte, ou ``0`` si le message est absent.

    Args:
        f_in: Itérateur positionné juste après ``</vlm>``.

    Returns:
        Nombre de membres lus, ou ``0`` si non trouvé.
    """
    next_line = next(f_in, None)
    if next_line is None:
        return 0
    match = _RE_COUNT.search(strip_asa_char(next_line))
    return int(match.group(1)) if match else 0


# -------------------------------------------------------------------------------------
# Validation des chemins
# -------------------------------------------------------------------------------------


def validate_input_file(path: Path) -> None:
    """Vérifie que le fichier d'entrée existe.

    Args:
        path: Chemin du fichier rapport VLM.

    Raises:
        FileNotFoundError: Si le fichier est absent.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Fichier d'entrée introuvable : '{path}'")


def validate_output_dir(path: Path) -> None:
    """Vérifie que le répertoire de sortie existe et est accessible en écriture.

    Args:
        path: Chemin du fichier de sortie.

    Raises:
        NotADirectoryError: Si le répertoire parent n'existe pas.
        PermissionError: Si le répertoire n'est pas accessible en écriture.
    """
    output_dir = path.parent if path.parent != Path("") else Path(".")
    if not output_dir.is_dir():
        raise NotADirectoryError(f"Répertoire de sortie introuvable : '{output_dir}'")
    test_file = output_dir / ".__vlm_write_test__"
    try:
        test_file.touch()
        test_file.unlink()
    except OSError as exc:
        raise PermissionError(
            f"Répertoire de sortie non accessible en écriture : '{output_dir}'"
        ) from exc


# -------------------------------------------------------------------------------------
# Traitement principal
# -------------------------------------------------------------------------------------


def convert_report(input_path: Path, output_path: Path, encoding: str) -> None:
    """Transforme le rapport VLM brut en XML propre.

    Lit le rapport ligne par ligne, élimine le bruit, injecte les attributs
    ``loadlib`` et ``memberCount`` dans les balises ``<vlm>``, et écrit
    un XML UTF-8 bien formé encapsulé dans ``<root>``.

    Args:
        input_path: Rapport VLM brut (encodage mainframe).
        output_path: Fichier XML de sortie (UTF-8).
        encoding: Encodage du fichier source, ex : ``iso8859-1``.

    Raises:
        SystemExit: Code 1 si l'erreur métier FMNBF427 est détectée.
    """
    LOGGER.info("Début du traitement : %s → %s", input_path, output_path)
    current_loadlib = ""

    # Syntaxe "with (...) as ..., ... as ...:" (Python 3.10+) :
    # ouvre les deux fichiers simultanément et garantit leur fermeture
    # automatique même en cas d'exception, sans avoir à écrire try/finally.
    with (
        input_path.open("r", encoding=encoding) as f_in,
        output_path.open("w", encoding="utf-8") as f_out,
    ):
        f_out.write('<?xml version="1.0" encoding="UTF-8"?>\n<root>\n')

        for line in f_in:
            line_str = strip_asa_char(line)

            if is_noise_line(line_str):
                continue

            dsn_match = _RE_DSN.search(line_str)
            if dsn_match:
                current_loadlib = dsn_match.group(1).rstrip(",")
                LOGGER.debug("Loadlib détectée : %s", current_loadlib)
                continue

            error_match = _RE_ERROR.search(line_str)
            if error_match:
                LOGGER.error("Erreur métier FMNBF427 : %s", error_match.group(1))
                sys.exit(1)

            if _RE_EMPTY.search(line_str):
                LOGGER.debug("Bibliothèque vide : %s (memberCount=0)", current_loadlib)
                f_out.write(f'<vlm loadlib="{current_loadlib}">\n')
                f_out.write('  <memberCount value="0"/>\n')
                f_out.write("</vlm>\n")
                continue

            if line_str.startswith("<vlm>"):
                f_out.write(f'<vlm loadlib="{current_loadlib}">\n')
            else:
                if line_str.startswith("</vlm>"):
                    member_count = read_member_count(f_in)
                    f_out.write(f'<memberCount value="{member_count}"/>')
                f_out.write(line_str + "\n")

        f_out.write("</root>")

    LOGGER.info("XML écrit avec succès : %s", output_path)


# -------------------------------------------------------------------------------------
# Point d'entrée CLI
# -------------------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Lit et valide les arguments de ligne de commande.

    Returns:
        Namespace contenant ``file``, ``output`` et ``encoding``.
    """
    parser = argparse.ArgumentParser(
        description="Nettoie un rapport VLM File Manager et produit un XML bien formé."
    )
    parser.add_argument(
        "-f",
        "--file",
        default="vlm.xml",
        help="Fichier rapport VLM en entrée (défaut : vlm.xml)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="clean_vlm.xml",
        help="Fichier XML de sortie (défaut : clean_vlm.xml)",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        default="iso8859-1",
        help="Encodage du fichier source (défaut : iso8859-1)",
    )
    return parser.parse_args()


def main() -> None:
    """Point d'entrée CLI — parse les arguments, valide les chemins et lance le traitement.

    Raises:
        SystemExit:
            - Code 1  : erreur métier FMNBF427 dans le rapport (détectée dans convert_report).
            - Code 2  : répertoire de sortie invalide ou non accessible en écriture.
            - Code 10 : fichier introuvable ou erreur I/O inattendue.
    """
    args = parse_args()

    _config = load_config()
    setup_logging(_config, "clean_report")

    input_path = Path(args.file)
    output_path = Path(args.output)

    try:
        validate_input_file(input_path)
        validate_output_dir(output_path)
        convert_report(input_path, output_path, args.encoding)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        sys.exit(10)
    except (NotADirectoryError, PermissionError) as exc:
        LOGGER.error("%s", exc)
        sys.exit(2)
    except IOError as exc:
        LOGGER.error("Erreur E/S : %s", exc)
        sys.exit(10)


if __name__ == "__main__":
    main()
