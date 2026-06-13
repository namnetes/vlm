#!/usr/bin/env python3

"""Reformate l'attribut `Val` des balises `Copt` dans un XML VLM.

Documentation fonctionnelle
Ce programme lit un fichier XML déjà nettoyé, puis modifie uniquement
`Copt@Val` pour rendre la chaîne plus simple à exploiter ensuite.

Concrètement, il:
1. normalise les espaces et les retours à la ligne,
2. découpe correctement les options en tenant compte des parenthèses,
3. supprime les espaces inutiles après les virgules dans `(...)`,
4. traite `LEINFO`/`NON-LEINFO` selon un mode configurable.

Le résultat final reste une chaîne, mais elle est prête pour un `split()`.

Documentation technique
Le cœur du parseur repose sur une profondeur de parenthèses:
- un espace sépare deux options seulement si la profondeur vaut 0,
- les espaces internes à `OPTION(...)` ne cassent donc pas le token.

Les pseudo-options `LEINFO`/`NON-LEINFO` peuvent être:
- conservées (`keep`),
- supprimées (`remove`),
- remplacées par `LEINFO=(N)` avec traçabilité dans un fichier annexe
    (`placeholder`).

Exemple:
python src/reformat_copt.py -f datas/clean_vlm.xml -o datas/clean_vlm_copt.xml
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from utils import load_config, setup_logging

LOGGER = logging.getLogger("reformat_copt")
LEINFO_HEAD_RE = re.compile(r"(?:NON-)?LEINFO=\(", re.IGNORECASE)


@dataclass
class ReformatStats:
    """Porte les métriques globales du traitement XML.

    Attributs:
        total_copt: Nombre total de balises `Copt` rencontrées.
        modified_copt: Nombre de balises dont `Val` a été modifié.
        empty_after_reformat: Nombre de `Val` devenus vides après nettoyage.
        leinfo_replaced: Nombre total de `LEINFO`/`NON-LEINFO` traités.
    """

    total_copt: int = 0
    modified_copt: int = 0
    empty_after_reformat: int = 0
    leinfo_replaced: int = 0


@dataclass
class ReformatState:
    """État mutable partagé pendant le parcours du fichier.

    Le compteur `leinfo_counter` est global à l'exécution afin de garantir
    des identifiants uniques pour les placeholders `LEINFO=(N)`.
    """

    leinfo_counter: int = 0


def parse_args() -> argparse.Namespace:
    """Lit et valide les arguments de ligne de commande.

    Retourne:
        Un `Namespace` prêt à être utilisé par `main()`.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Reformat Copt@Val options so a simple Python split() isolates"
            " each compilation option."
        )
    )
    parser.add_argument(
        "-f",
        "--file",
        required=False,
        default="datas/clean_vlm.xml",
        help="Input XML file (default: datas/clean_vlm.xml)",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        default="datas/clean_vlm_copt.xml",
        help="Output XML file (default: datas/clean_vlm_copt.xml)",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        required=False,
        default="utf-8",
        help="Input XML encoding (default: utf-8)",
    )
    parser.add_argument(
        "--ignored-file",
        required=True,
        help="File used to persist original LEINFO/NON-LEINFO when using placeholder mode.",
    )
    parser.add_argument(
        "--leinfo-mode",
        required=False,
        default="placeholder",
        choices=["placeholder", "remove", "keep"],
        help=(
            "LEINFO handling: placeholder=LEINFO=(N), remove=drop LEINFO token, "
            "keep=keep original token"
        ),
    )
    parser.add_argument(
        "--append-ignored",
        action="store_true",
        help="Append ignored-file instead of truncating it at start",
    )
    return parser.parse_args()


def normalize_whitespace(val: str) -> str:
    """Normalise tous les blancs (espace, tabulation, saut de ligne).

    Args:
        val: Valeur brute de `Copt@Val`.

    Returns:
        Une chaîne avec un seul espace entre les éléments.

    """
    return re.sub(r"\s+", " ", val).strip()


def _consume_balanced_parentheses(text: str, open_index: int) -> int:
    """Trouve la parenthèse fermante qui correspond à `text[open_index]`.

    Args:
    text: Chaîne source complète.
    open_index: Position de la parenthèse ouvrante `(`.

    Returns:
    L'index juste après la parenthèse fermante correspondante.
    Si la fermeture est introuvable, renvoie `len(text)`.

    """
    depth = 0
    idx = open_index
    while idx < len(text):
        ch = text[idx]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return idx + 1
        idx += 1
    return len(text)


def _extract_leinfo_token_at(
    text: str, start_index: int
) -> tuple[str, int] | None:
    """Extrait `LEINFO`/`NON-LEINFO` à partir d'un index donné.

    Args:
        text: Chaîne d'origine.
        start_index: Position où tenter la détection.

    Returns:
        `(token, end_index)` si un token est détecté.
        `None` sinon.

    """
    match = LEINFO_HEAD_RE.match(text, start_index)
    if not match:
        return None
    open_index = match.end() - 1
    end_index = _consume_balanced_parentheses(text, open_index)
    return text[start_index:end_index], end_index


def replace_leinfo_with_placeholder(
    val: str,
    state: ReformatState,
    ignored_writer: TextIO | None,
    mode: str,
) -> tuple[str, int]:
    """Traite les tokens `LEINFO`/`NON-LEINFO` selon le mode sélectionné.

    Modes disponibles:
    - `keep`: conserve les tokens sans modification.
    - `remove`: supprime entièrement ces tokens.
    - `placeholder`: remplace par `LEINFO=(N)` ou `NON-LEINFO=(N)`.

    En mode `placeholder`, la valeur originale est écrite dans
    `ignored_writer` pour permettre une résolution ultérieure.

    Args:
        val: Valeur `Copt@Val` brute.
        state: État global contenant le compteur des placeholders.
        ignored_writer: Flux texte pour tracer les valeurs remplacées.
        mode: Mode de traitement (`keep`, `remove`, `placeholder`).

    Returns:
        Un tuple `(valeur_transformée, nombre_de_remplacements)`.

    """
    if mode == "keep":
        return val, 0

    out: list[str] = []
    idx = 0
    replacements = 0

    while idx < len(val):
        extracted = _extract_leinfo_token_at(val, idx)
        if extracted is None:
            out.append(val[idx])
            idx += 1
            continue

        original_token, end_index = extracted
        replacements += 1

        if mode == "placeholder":
            state.leinfo_counter += 1
            num = state.leinfo_counter
            if ignored_writer is not None:
                ignored_writer.write(f"{num}\t{original_token}\n")
            if original_token.upper().startswith("NON-LEINFO="):
                out.append(f"NON-LEINFO=({num})")
            else:
                out.append(f"LEINFO=({num})")
        elif mode == "remove":
            # Supprime totalement le token LEINFO/NON-LEINFO.
            pass
        else:
            raise ValueError(f"Unsupported leinfo mode: {mode}")

        idx = end_index

    return "".join(out), replacements


def tokenize_options(val: str) -> list[str]:
    """Découpe une chaîne d'options en respectant les parenthèses imbriquées.

    Principe:
    - un espace coupe le token uniquement quand `depth == 0`,
    - dans `OPTION(A, B)`, l'espace après la virgule est donc conservé dans
      le même token jusqu'à l'étape de normalisation fine.

    Args:
        val: Chaîne d'options déjà normalisée en espaces.

    Returns:
        La liste des tokens d'options.

    """
    tokens: list[str] = []
    current: list[str] = []
    depth = 0

    for ch in val:
        if ch == "(":
            depth += 1
            current.append(ch)
            continue

        if ch == ")":
            if depth > 0:
                depth -= 1
            current.append(ch)
            continue

        if ch == " " and depth == 0:
            token = "".join(current).strip()
            if token:
                tokens.append(token)
            current = []
            continue

        current.append(ch)

    token = "".join(current).strip()
    if token:
        tokens.append(token)
    return tokens


def normalize_token(token: str) -> str:
    """Supprime les espaces inutiles après virgule dans les parenthèses.

    Exemple:
        `CSECT(CODE, ACCPRINT)` devient `CSECT(CODE,ACCPRINT)`.
    """
    return re.sub(r",\s+", ",", token)


def reformat_copt_value(
    raw_val: str,
    state: ReformatState,
    ignored_writer: TextIO | None,
    leinfo_mode: str,
) -> tuple[str, int]:
    """Exécute le pipeline complet de reformattage pour un `Copt@Val`.

    Étapes:
    1. traiter `LEINFO`/`NON-LEINFO`,
    2. normaliser les blancs,
    3. tokeniser avec compteur de parenthèses,
    4. normaliser chaque token,
    5. reconstruire une chaîne à espaces simples.

    Args:
        raw_val: Valeur originale de l'attribut `Val`.
        state: État partagé du traitement.
        ignored_writer: Flux pour tracer les `LEINFO` remplacés.
        leinfo_mode: Mode appliqué aux pseudo-options `LEINFO`.

    Returns:
        `(valeur_reformatée, nombre_de_leinfo_traites)`.

    """
    value, replacements = replace_leinfo_with_placeholder(
        val=raw_val,
        state=state,
        ignored_writer=ignored_writer,
        mode=leinfo_mode,
    )
    value = normalize_whitespace(value)
    tokens = tokenize_options(value)
    normalized_tokens = [normalize_token(t) for t in tokens]
    return " ".join(normalized_tokens), replacements


def reformat_tree(
    tree: ET.ElementTree[ET.Element],
    leinfo_mode: str,
    ignored_writer: TextIO | None,
    logger: logging.Logger,
) -> ReformatStats:
    """Reformate en place tous les `Copt@Val` de l'arbre XML.

    Cette fonction parcourt les balises `.//Copt`, applique le pipeline
    de reformattage, met à jour l'attribut `Val` si nécessaire, puis
    agrège les statistiques de traitement.
    """
    stats = ReformatStats()
    state = ReformatState()

    for copt_elem in tree.findall(".//Copt"):
        stats.total_copt += 1
        original_val = copt_elem.get("Val")

        if original_val is None:
            continue

        reformatted_val, replacements = reformat_copt_value(
            raw_val=original_val,
            state=state,
            ignored_writer=ignored_writer,
            leinfo_mode=leinfo_mode,
        )
        stats.leinfo_replaced += replacements

        if reformatted_val != original_val:
            copt_elem.set("Val", reformatted_val)
            stats.modified_copt += 1

        if not reformatted_val:
            stats.empty_after_reformat += 1

    logger.debug("Total Copt processed: %d", stats.total_copt)
    logger.debug("Copt modified: %d", stats.modified_copt)
    logger.debug("LEINFO/NON-LEINFO replaced: %d", stats.leinfo_replaced)
    logger.debug("Copt empty after reformat: %d", stats.empty_after_reformat)
    return stats


def validate_input_file(input_path: Path) -> None:
    """Vérifie que le fichier d'entrée existe bien."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file '{input_path}' does not exist")


def validate_output_dir(output_path: Path) -> None:
    """Vérifie que le dossier de sortie existe et est inscriptible."""
    output_dir = (
        output_path.parent if output_path.parent != Path() else Path()
    )
    if not output_dir.exists() or not output_dir.is_dir():
        raise NotADirectoryError(
            f"Output directory '{output_dir}' does not exist or is not a directory"
        )
    try:
        testfile = output_dir / ".__copt_write_test__"
        with testfile.open("w", encoding="utf-8"):
            pass
        testfile.unlink()
    except OSError as exc:
        raise PermissionError(
            f"Output directory '{output_dir}' is not writable"
        ) from exc


def main() -> None:
    """Point d'entrée CLI.

    Orchestration globale:
    - lecture des arguments,
    - validations d'entrée/sortie,
    - parsing XML,
    - reformattage des balises `Copt`,
    - écriture du fichier XML final,
    - gestion centralisée des erreurs et codes de retour.
    """
    args = parse_args()
    setup_logging(load_config(), "reformat_copt")

    input_path = Path(args.file)
    output_path = Path(args.output)
    ignored_path = Path(args.ignored_file)

    LOGGER.info("Début du reformatage : %s → %s", input_path, output_path)

    try:
        validate_input_file(input_path)
        validate_output_dir(output_path)

        tree = ET.parse(
            str(input_path), parser=ET.XMLParser(encoding=args.encoding)
        )

        ignored_writer: TextIO | None = None
        if args.leinfo_mode == "placeholder":
            ignored_path.parent.mkdir(parents=True, exist_ok=True)
            # Les modes littéraux "a"/"w" garantissent à mypy un retour
            # TextIO (et non IO[Any] comme avec un mode dynamique).
            if args.append_ignored:
                ignored_writer = ignored_path.open("a", encoding="utf-8")
            else:
                ignored_writer = ignored_path.open("w", encoding="utf-8")

        try:
            reformat_tree(
                tree=tree,
                leinfo_mode=args.leinfo_mode,
                ignored_writer=ignored_writer,
                logger=LOGGER,
            )
        finally:
            if ignored_writer is not None:
                ignored_writer.close()

        tree.write(str(output_path), encoding="utf-8", xml_declaration=True)
        LOGGER.info("Output written: %s", output_path)

    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        LOGGER.error("%s", exc)
        sys.exit(2)
    except ET.ParseError as exc:
        LOGGER.error("XML parse error: %s", exc)
        sys.exit(3)
    except OSError as exc:
        LOGGER.error("I/O error: %s", exc)
        sys.exit(10)


if __name__ == "__main__":
    main()
