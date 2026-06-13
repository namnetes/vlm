#!/usr/bin/env python3

"""Convertit un fichier XML VLM nettoyé en fichier JSON structuré.

Terminologie mainframe IBM z/OS (utilisée dans ce module) :
- VLM      : View Load Module — fonction d'IBM File Manager qui analyse les
             load modules d'une bibliothèque z/OS. Le rapport XML nettoyé
             est l'entrée de ce script.
- Loadlib  : Load Library — bibliothèque PDS/PDSE contenant des loadmods.
- Loadmod  : Load Module — programme exécutable lié (binaire z/OS).
- CSECT    : Control SECTion — unité de code compilée à l'intérieur d'un loadmod.
- COPT     : Compilation OPTions — options passées au compilateur COBOL/C++/PL/I.
- LEINFO   : pseudo-option COPT contenant des métadonnées internes (filtrée ici).

Le fichier JSON produit est ensuite exploité par export_csv.sh via l'outil jq.

Exemple :
    python src/build_json.py -f datas/clean_vlm.xml -o datas/vlm.json -e utf-8
"""

import argparse
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from utils import load_config, setup_logging

LOGGER = logging.getLogger("build_json")


def split_copt_options(raw: str) -> list[str]:
    """Découpe une chaîne COPT brute en liste propre d'options de compilation.

    Pourquoi ne pas utiliser un simple ``.split()`` ?
    - ``.split()`` coupe sur chaque espace, ce qui casse les options contenant
      des espaces *à l'intérieur* de parenthèses. Exemple :
      ``"CSECT(CODE, MCONFIG)"`` deviendrait ``["CSECT(CODE,", "MCONFIG)"]``.

    Stratégie (parcours caractère par caractère) :
    1. Nettoyer LEINFO=(...) qui est une métadonnée, pas une vraie option.
    2. Normaliser les espaces et sauts de ligne en un seul espace.
    3. Compter la profondeur des parenthèses (depth).
    4. Couper les tokens uniquement quand depth == 0 (hors parenthèses).

    Exemple de résultat :
        ``"CSECT(CODE, MCONFIG) OPT2"`` → ``["CSECT(CODE,MCONFIG)", "OPT2"]``

    Args:
        raw: Chaîne d'options brutes telle que présente dans l'attribut XML.

    Returns:
        Liste de chaînes, chaque élément représentant une option de compilation.

    """
    # CDbiPathBase() peut apparaître à l'intérieur d'un bloc LEINFO=(...).
    # On l'efface en premier car il contient lui-même des parenthèses qui
    # perturberaient la suppression du LEINFO global.
    # (?:NON-)? capture aussi la variante NON-LEINFO produite par
    # reformat_copt.py en mode placeholder.
    raw = re.sub(
        r"(\b(?:NON-)?LEINFO=\([^)]*)CDbiPathBase\(\)", r"\1", raw
    )

    # Supprime LEINFO=(...) et NON-LEINFO=(...) avant la normalisation des
    # espaces — ce sont des métadonnées Language Environment, pas de vraies
    # options de compilation.
    # - \b : limite de mot (évite de capturer NOTLEINFO).
    # - (?:NON-)? : préfixe optionnel pour traiter NON-LEINFO comme un seul
    #   bloc ; sans lui, seul "LEINFO=(N)" serait retiré et le résidu "NON-"
    #   resterait comme fausse option.
    # - .*? : quantificateur non-greedy — s'arrête au premier ')' rencontré
    #   (et non au dernier), pour ne supprimer qu'un seul bloc à la fois.
    # - re.DOTALL : le point '.' correspond aussi aux sauts de ligne (\n),
    #   car LEINFO peut s'étendre sur plusieurs lignes dans le rapport.
    raw_without_leinfo: str = re.sub(
        r"\b(?:NON-)?LEINFO=\(.*?\)",
        "",
        raw,
        flags=re.DOTALL,
    )

    # .split() sans argument découpe sur tout espace/tabulation/saut de ligne
    # et ignore les séquences vides. " ".join(...) recolle avec un seul espace.
    normalized: str = " ".join(raw_without_leinfo.split())

    tokens: list[str] = []
    current: list[str] = []  # Buffer pour le token en cours de construction.
    paren_depth: int = 0  # Profondeur de parenthèses imbriquées.

    for ch in normalized:
        if ch == "(":
            paren_depth += 1
            current.append(ch)
            continue

        if ch == ")":
            # Protection contre les ')' en excès (XML malformé) :
            # on garde le caractère mais on n'autorise pas depth < 0.
            if paren_depth > 0:
                paren_depth -= 1
            current.append(ch)
            continue

        # Espace à l'intérieur d'une parenthèse → ignoré (on nettoie).
        # Exemple : "CSECT(CODE, MCONFIG)" → "CSECT(CODE,MCONFIG)".
        if ch.isspace() and paren_depth > 0:
            continue

        if ch.isspace() and paren_depth == 0:
            # Espace hors parenthèse = séparateur entre deux options.
            # On finalise le token courant s'il est non vide.
            if current:
                tokens.append("".join(current))
                current = []
            continue

        current.append(ch)

    # Dernier token sans espace final (fin de chaîne).
    if current:
        tokens.append("".join(current))

    return tokens


def parse_args() -> argparse.Namespace:
    """Analyse et valide les arguments de ligne de commande.

    argparse est la bibliothèque standard Python pour les arguments CLI.
    Elle génère automatiquement le texte ``--help`` et affiche une erreur
    claire si un argument invalide est fourni.

    Returns:
        Namespace argparse avec les attributs :
        ``file`` (XML en entrée), ``output`` (JSON en sortie),
        ``encoding`` (encodage du XML).

    """
    parser = argparse.ArgumentParser(
        description="Convertit un fichier XML VLM nettoyé en JSON structuré."
    )
    parser.add_argument(
        "-f",
        "--file",
        required=False,
        default="clean_vlm.xml",
        help="Fichier XML en entrée (défaut : clean_vlm.xml)",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        default="vlm.json",
        help="Fichier JSON en sortie (défaut : vlm.json)",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        required=False,
        default="iso8859-1",
        help="Encodage du fichier XML en entrée (défaut : iso8859-1)",
    )
    return parser.parse_args()


def check_xml_well_formed(xml_path: str) -> bool:
    """Vérifie que le fichier XML est syntaxiquement correct.

    "Bien formé" signifie : balises ouvrantes/fermantes équilibrées,
    imbrication correcte, encodage déclaré respecté. ``ET.parse()`` lève
    une ``ParseError`` si le fichier ne respecte pas ces règles.

    Cette fonction capture l'exception et retourne un booléen plutôt
    que de laisser le programme planter.

    Args:
        xml_path: Chemin du fichier XML à vérifier.

    Returns:
        ``True`` si le fichier est bien formé, ``False`` sinon.

    """
    try:
        ET.parse(xml_path)
    except ET.ParseError as e:
        LOGGER.error("Erreur de syntaxe XML dans %s : %s", xml_path, e)
        return False
    else:
        LOGGER.debug("%s est bien formé.", xml_path)
        return True


def xml_to_json(xml_path: str, json_path: str, encoding: str) -> None:
    """Convertit un fichier XML VLM nettoyé en fichier JSON structuré.

    Parcourt l'arbre XML niveau par niveau (Loadlib → Loadmod → CSECT)
    et construit une liste Python de dictionnaires, puis la sérialise en JSON.

    Structure du JSON produit (hiérarchie à 3 niveaux) ::

        [                                   ← liste de Loadlibs
          {
            "Loadlib": "SYS1.LINKLIB",
            "MemberCount": 42,
            "Loadmods": [                   ← liste de loadmods
              {
                "Name": "MONPGM",
                "CSECTs": [                 ← liste de CSECTs
                  {
                    "Name": "MONPGM",
                    "ThreadSafe": false,
                    "CICS": false,
                    "DB2": false,
                    "WMQ": false,
                    "Copt": ["OPT2", "THREAD"]
                  }
                ]
              }
            ]
          }
        ]

    Champs booléens dérivés (calculés automatiquement depuis le nom du CSECT) :
    - ``ThreadSafe`` : vrai si le CSECT s'appelle ``CEEUOPT``.
    - ``CICS``       : vrai si le CSECT s'appelle ``DFHECI``.
    - ``DB2``        : vrai si le nom contient un stub DB2 connu.
    - ``WMQ``        : vrai si le nom contient un stub WMQ connu.

    Args:
        xml_path: Chemin du fichier XML d'entrée (bien formé, encodage déclaré).
        json_path: Chemin du fichier JSON à créer.
        encoding: Encodage du fichier XML (ex. ``utf-8``, ``iso8859-1``).

    """
    # Pattern pour valider le format de l'attribut "Identify" d'un CSECT.
    # Exemple attendu : "CCBD01/51EBC3AD/DYA0000005"
    # - Partie 1 (1-8 chars alphanum, _, @, à) : code application.
    # - Partie 2 (1-8 chars alphanum)           : hash ou version.
    # - Partie 3 (DY|DA + 2 chars + 6 chiffres) : code de package.
    pattern: str = (
        r"^[A-Za-z0-9_@à]{1,8}"  # Partie 1 : code application
        r"/"
        r"[A-Za-z0-9]{1,8}"  # Partie 2 : hash/version
        r"/"
        r"(DY|DA)[A-Za-z0-9]{2}[0-9]{6}$"  # Partie 3 : code package
    )

    LOGGER.info("Début de la conversion : %s → %s", xml_path, json_path)

    # ET.parse() charge le fichier XML en mémoire sous forme d'arbre d'objets.
    # ET.XMLParser(encoding=...) force l'encodage déclaré dans l'argument CLI.
    tree: ET.ElementTree[ET.Element] = ET.parse(
        xml_path, parser=ET.XMLParser(encoding=encoding)
    )
    # getroot() retourne l'élément racine ou None si l'arbre est vide.
    # ET.parse() garantit une racine présente, mais le type annoté est
    # Element | None : on lève une erreur explicite si ce cas impossible survient.
    root: ET.Element = tree.getroot()
    if root is None:
        raise ValueError(
            f"Le fichier XML '{xml_path}' ne contient pas d'élément racine."
        )
    vlm_list: list[dict[str, Any]] = []  # Accumulera toutes les Loadlibs.
    nb_loadmods: int = 0
    nb_csects: int = 0

    # root.findall("vlm") retourne la liste de tous les éléments <vlm> fils directs.
    for vlm in root.findall("vlm"):
        # .get("loadlib") lit l'attribut XML loadlib="..." de la balise <vlm>.
        loadlib: str | None = vlm.get("loadlib")
        member_count_elem: ET.Element | None = vlm.find("memberCount")
        if member_count_elem is not None:
            # .get("value") retourne str | None ; on substitue "0" si absent.
            member_count: int = int(member_count_elem.get("value") or "0")
        else:
            member_count = 0

        loadmods: list[dict[str, Any]] = []

        for loadmod in vlm.findall("Loadmod"):
            nb_loadmods += 1
            # Construction du dictionnaire du loadmod depuis ses attributs XML.
            loadmod_data: dict[str, Any] = {
                "Name": loadmod.get("Name"),
                "Linkedon": loadmod.get("Linkedon"),
                "Linkedat": loadmod.get("Linkedat"),
                "Linkedby": loadmod.get("Linkedby"),
                "EPA": loadmod.get("EPA"),
                "MSize": loadmod.get("MSize"),
                "TTR": loadmod.get("TTR"),
                "SSI": loadmod.get("SSI"),
                "AC": loadmod.get("AC"),
                "AM": loadmod.get("AM"),
                "RM": loadmod.get("RM"),
                "CSECTs": [],
            }

            for csect in loadmod.findall("CSECT"):
                nb_csects += 1
                csect_data: dict[str, Any] = {
                    "Name": csect.get("Name"),
                    "Type": csect.get("Type"),
                    "Class": csect.get("Class"),
                    "Address": csect.get("Address"),
                    "Size": csect.get("Size"),
                    "RMODE": csect.get("ARMODE"),
                    "Compiler1": csect.get("Compiler1"),
                    "Date": csect.get("Date"),
                }

                # Champs booléens dérivés du nom du CSECT.
                # En Python, une comparaison (==) retourne directement True/False,
                # ce qui permet de stocker le résultat comme booléen JSON.
                csect_data["ThreadSafe"] = csect_data["Name"] == "CEEUOPT"
                csect_data["CICS"] = csect_data["Name"] == "DFHECI"

                # any(iterable) retourne True si au moins un élément est vrai.
                # Ici : True si le nom du CSECT contient l'un des stubs DB2 connus.
                csect_data["DB2"] = any(
                    sub in csect_data["Name"]
                    for sub in ("DSNCLI", "DSNELI", "DSNULI")
                )
                # Même logique pour les stubs WMQ (WebSphere MQ / IBM MQ).
                csect_data["WMQ"] = any(
                    sub in csect_data["Name"]
                    for sub in (
                        "DFHMQSTB",
                        "CSQBSTUB",
                        "CSQBRRSI",
                        "CSQBRSTB",
                        "CSQCSTUB",
                        "CSQQSTUB",
                        "CSQXSTUB",
                        "CSQASTUB",
                    )
                )

                # Recherche de la balise <Identify> (identifiant de package).
                identify_elem: ET.Element | None = csect.find("Identify")
                if identify_elem is not None:
                    val: str | None = identify_elem.attrib.get("Val")
                    if val and re.match(pattern, val):
                        # Le format est valide : on garde uniquement la 3e partie
                        # (code package) après découpe sur '/'.
                        i: list[str] = val.split("/")
                        package: str = i[-1]
                        csect_data["Identify"] = package
                    else:
                        csect_data["Identify"] = None

                # Recherche de la balise <Copt> contenant les options de compilation.
                copt_elem: ET.Element | None = csect.find("Copt")
                if copt_elem is not None:
                    # .get("Val") retourne None si l'attribut est absent ;
                    # `or ""` le remplace par une chaîne vide pour éviter
                    # un crash dans split_copt_options.
                    copt_val: str = copt_elem.get("Val") or ""
                    options: list[str] = split_copt_options(copt_val)
                    csect_data["Copt"] = options

                loadmod_data["CSECTs"].append(csect_data)
            loadmods.append(loadmod_data)

        vlm_list.append(
            {
                "Loadlib": loadlib,
                "MemberCount": member_count,
                "Loadmods": loadmods,
            }
        )

    LOGGER.debug(
        "Éléments traités : %d loadlib(s), %d loadmod(s), %d CSECT(s).",
        len(vlm_list),
        nb_loadmods,
        nb_csects,
    )

    # json.dump() sérialise la liste Python en JSON dans le fichier ouvert.
    # - indent=2 : indentation de 2 espaces pour un fichier lisible.
    # - ensure_ascii=False : conserve les caractères non-ASCII (accents, etc.)
    #   tels quels au lieu de les encoder en \uXXXX.
    with Path(json_path).open("w", encoding="utf-8") as f:
        json.dump(vlm_list, f, indent=2, ensure_ascii=False)

    LOGGER.info("JSON écrit avec succès : %s", json_path)


def main() -> None:
    """Point d'entrée CLI — orchestre validation et conversion XML → JSON.

    Séquence d'exécution :
    1. Parse les arguments (fichiers d'entrée/sortie, encodage).
    2. Vérifie que le fichier XML source existe.
    3. Vérifie que le répertoire de sortie est accessible en écriture.
    4. Vérifie que le XML est bien formé.
    5. Lance la conversion XML → JSON.

    Raises:
        SystemExit:
            - Code 2 : fichier introuvable ou répertoire de sortie invalide.

    """
    args: argparse.Namespace = parse_args()
    setup_logging(load_config(), "build_json")
    input_path: Path = Path(args.file)

    if not input_path.is_file():
        LOGGER.error("Fichier d'entrée '%s' introuvable.", args.file)
        sys.exit(2)

    # Si --output n'est pas fourni, le nom JSON reprend le nom du XML source.
    output_file: str = args.output if args.output else f"{input_path.stem}.json"
    output_path: Path = Path(output_file)

    # Validation du répertoire de sortie.
    # output_path.parent vaut Path('.') si le nom de fichier n'a pas de répertoire.
    output_dir: Path = (
        output_path.parent if output_path.parent != Path() else Path()
    )
    if not output_dir.exists() or not output_dir.is_dir():
        LOGGER.error(
            "Répertoire de sortie '%s' introuvable ou invalide.", output_dir
        )
        sys.exit(2)

    # Test d'écriture : on crée puis supprime un fichier temporaire.
    try:
        testfile = output_dir / ".__vlm_write_test__"
        with testfile.open("w"):
            pass
        testfile.unlink()
    except OSError:
        LOGGER.error(
            "Répertoire de sortie '%s' non accessible en écriture.", output_dir
        )
        sys.exit(2)

    check_xml_well_formed(str(input_path))
    xml_to_json(str(input_path), str(output_path), args.encoding)


# Ce bloc garantit que main() n'est appelé que si le script est exécuté
# directement (python build_json.py), et pas s'il est importé comme module.
if __name__ == "__main__":
    main()
