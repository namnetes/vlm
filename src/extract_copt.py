#!/usr/bin/env python3

# Extrait les options de compilation (COPT) par CSECT depuis le fichier JSON des VLM
# produit par build_json.py et écrit deux types de sortie :
#
#   1. Un fichier CSV récapitulatif (délimité par ';') — une ligne par CSECT
#      ayant des options de compilation. Format de chaque ligne :
#
#        préfixe;loadlib;load_name;csect_name;compilateur;nb_options
#
#      - préfixe   : "1" si le CSECT porte le même nom que son loadmod (CSECT
#                    principal en COBOL IBM), "0" si c'est un CSECT secondaire
#                    (stub DB2, CICS, sous-programme inclus…).
#      - loadlib   : bibliothèque de chargement IBM z/OS (ex. SYS1.LINKLIB).
#      - load_name : nom du module de chargement (ex. MONPGM).
#      - csect_name: nom de la section compilée à l'intérieur du module.
#      - compilateur: identifiant du compilateur (ex. "COBOL").
#      - nb_options: nombre total d'options de compilation présentes.
#
#   2. Un fichier texte détaillé par CSECT, enregistré sous :
#        <répertoire_sortie>/loadlibs/<loadlib>/<load_name>_<csect_name>.txt
#      Ce fichier liste chaque option de compilation sur une ligne séparée.
#
# Contexte mainframe IBM z/OS :
#   VLM   = View Load Module — fonction d'IBM File Manager qui analyse les
#           load modules d'une bibliothèque z/OS. Son rapport (vlm.xml) est
#           la matière première du pipeline.
#   COPT  = Compilation OPTions — options passées au compilateur IBM COBOL 6.5.
#   CSECT = Control SECTion — unité de code compilée à l'intérieur d'un loadmod.
#   Loadmod = Load Module — module exécutable contenu dans une loadlib.
#   Loadlib = Load Library — bibliothèque PDS/PDSE qui contient les loadmods.
#
# Usage :
#   python extract_copt.py -f datas/vlm.json -o datas/copt_summary.csv

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from utils import load_config, setup_logging

# Alias de type : donne un nom lisible à la structure d'une ligne de sortie.
# Un tuple nommé de 6 éléments : (préfixe, loadlib, load_name, csect_name,
# compilateur, liste_options). La dernière colonne est une liste de chaînes
# car un CSECT peut avoir plusieurs dizaines d'options de compilation.
CsectRow = tuple[str, str, str, str, str, list[str]]

# Logger nommé "extract_copt" — le nom apparaît dans chaque ligne de log.
# On utilise un logger nommé (plutôt que le root logger) pour que les messages
# de ce script soient identifiables dans le fichier pipeline.log partagé.
LOGGER = logging.getLogger("extract_copt")

# Correspondance nom complet du compilateur → code abrégé utilisé dans les
# noms de fichiers générés. Les clés sont les chaînes exactes du champ
# "Compiler1" du JSON produit par build_json.py (issu du rapport VLM IBM).
# Pour ajouter un compilateur : récupérer la valeur exacte de "Compiler1"
# dans vlm.json et lui associer un code court unique.
COMPILERS = {
    # --- COBOL ---
    "COBOL/370 for MVS V1R1": "c370v11",
    "COBOL/370 for MVS V1R2": "c370v12",
    "COBOL for OS/390 & VM V2R1": "cos390v21",
    "COBOL for OS/390 & VM V2R2": "cos390v22",
    "Enterpr.COBOL for z/OS V3R1": "cbv31",
    "Enterpr.COBOL for z/OS V3R2": "cbv32",
    "Enterpr.COBOL for z/OS V3R3": "cbv33",
    "Enterpr.COBOL for z/OS V3R4": "cbv34",
    "Enterpr.COBOL for z/OS V4R1": "cbv41",
    "Enterpr.COBOL for z/OS V4R2": "cbv42",
    "Enterpr.COBOL for z/OS V6R3": "cbv63",
    "OS/VS COBOL V1R2": "osvsv12",
    "OS/VS COBOL V2R0": "osvsv20",
    "OS/VS COBOL z/OS": "osvszos",
    "VS COBOL II V1R2": "vsc2v12",
    "VS COBOL II V1R3": "vsc2v13",
    "VS COBOL II V1R4": "vsc2v14",
    # --- C/C++ ---
    "C/C++ for z/OS V2R1": "cppz21",
    "C/C++ for z/OS V2R2": "cppz22",
    "C/C++ for z/OS V2R3": "cppz23",
    "C/C++ for z/OS V2R4": "cppz24",
    "C/C++ OS/390 R4 V2R0": "cpp390v20",
    "C/C++ OS/390 R4 V2R4": "cpp390v24",
    "C/C++ OS/390 R4 V2R6": "cpp390v26",
    "C/C++ OS/390 R4 V2R9": "cpp390v29",
    "C/C++ z/OS R5 V1R0": "cppz10",
    "C/C++ z/OS R5 V1R1": "cppz11",
    "C/C++ z/OS R5 V1R2": "cppz12",
    "C/C++ z/OS R5 V1R3": "cppz13",
    "C/C++ z/OS R5 V1R6": "cppz16",
    "C/C++ z/OS R5 V1R7": "cppz17",
    "C/C++ z/OS R5 V1R8": "cppz18",
    "C/C++ z/OS R5 V1R9": "cppz19",
    # --- PL/I ---
    "Enterpr. PL/I for z/OS V3R1": "pliv31",
}


def parse_args() -> argparse.Namespace:
    """Analyse et retourne les arguments passés sur la ligne de commande.

    argparse génère automatiquement le message --help et affiche une erreur
    explicite si un argument obligatoire est manquant.

    Returns:
        Namespace argparse dont les attributs ``file`` et ``output``
        contiennent les chemins fournis par l'utilisateur.

    """
    # ArgumentParser est l'objet central d'argparse ; description apparaît
    # dans le message --help.
    parser = argparse.ArgumentParser(
        description="Extrait les options COPT par CSECT depuis le JSON VLM."
    )
    # Chaque add_argument déclare une option acceptée. Les formes -f et --file
    # sont équivalentes. required=True bloque le démarrage si l'option manque.
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="Fichier JSON en entrée (obligatoire).",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Fichier CSV en sortie (obligatoire).",
    )
    # parse_args() lit sys.argv, valide les arguments et retourne un Namespace.
    # Accès aux valeurs : args.file, args.output.
    return parser.parse_args()


def load_json(path: Path) -> list[Any]:
    """Ouvre le fichier JSON pointé par *path* et retourne son contenu analysé.

    Le fichier VLM JSON est un tableau de loadlibs, chacune contenant une liste
    de loadmods, eux-mêmes contenant une liste de CSECTs avec leurs options.

    Args:
        path: Chemin absolu ou relatif vers le fichier JSON à lire.

    Returns:
        Le contenu du fichier sous forme de liste Python (un élément par loadlib).

    Raises:
        SystemExit:
            - code 2 si le fichier est absent ou si la lecture est refusée par l'OS
            - code 3 si le contenu n'est pas du JSON valide
            - code 10 en cas d'erreur I/O inattendue

    """
    try:
        with path.open(encoding="utf-8") as f:
            # json.load() lit le flux et convertit le JSON en objets Python
            # (dict, list, str, int…). Lève JSONDecodeError si le format est invalide.
            data: list[Any] = json.load(f)
    except FileNotFoundError:
        # Le fichier n'existe pas à l'emplacement indiqué.
        LOGGER.error("Fichier '%s' introuvable.", path)
        sys.exit(2)
    except PermissionError:
        # Le fichier existe mais l'utilisateur n'a pas le droit de le lire.
        LOGGER.error("Accès refusé en lecture sur '%s'.", path)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        # Le fichier est lisible mais son contenu n'est pas du JSON valide.
        # exc contient le détail de l'erreur (ligne, colonne).
        LOGGER.error("'%s' n'est pas un JSON valide : %s", path, exc)
        sys.exit(3)
    except OSError as exc:
        # OSError est la classe parente de la plupart des erreurs système
        # (disque plein, fichier verrouillé…). Filet de sécurité pour les cas
        # non couverts par FileNotFoundError et PermissionError.
        LOGGER.error("Erreur I/O lors de la lecture de '%s' : %s", path, exc)
        sys.exit(10)
    else:
        LOGGER.debug(
            "JSON chargé depuis '%s' : %d loadlib(s) présente(s).",
            path,
            len(data),
        )
        return data


def iter_csect_copt(data: list[Any]) -> Iterator[CsectRow]:
    """Parcourt le JSON VLM et génère une ligne par CSECT ayant des options COPT.

    Le JSON VLM est structuré sur trois niveaux imbriqués :
    - Loadlib  : bibliothèque de chargement (ex. SYS1.LINKLIB)
    - Loadmod  : module de chargement (ex. MONPGM)
    - CSECT    : section de code compilée à l'intérieur du module

    Seuls les CSECTs dont le champ ``Copt`` est présent et non vide sont
    émis ; les autres sont silencieusement ignorés.

    Le préfixe ``"1"`` indique que le nom du CSECT est identique à celui du module
    (CSECT principal en COBOL IBM) ; ``"0"`` signale un CSECT secondaire (stubs
    DB2, CICS, sous-programmes inclus…).

    Args:
        data: Contenu JSON analysé, tel que retourné par ``load_json``.

    Yields:
        ``CsectRow`` — tuple à 6 éléments dans l'ordre :
        ``(préfixe, loadlib, load_name, csect_name, compilateur, copt)``

        - *préfixe*    : ``"1"`` si load_name == csect_name, ``"0"`` sinon.
        - *loadlib*    : nom de la bibliothèque de chargement.
        - *load_name*  : nom du module de chargement.
        - *csect_name* : nom de la section compilée.
        - *compilateur*: chaîne identifiant le compilateur (ex. ``"COBOL"``).
        - *copt*       : liste des options de compilation.

    """
    for lib in data:
        # .get("Loadlib") retourne None si la clé est absente ;
        # `or ""` la remplace par une chaîne vide pour éviter des erreurs de
        # concaténation ou de comparaison plus loin dans le code.
        loadlib: str = lib.get("Loadlib") or ""

        # .get("Loadmods", []) retourne une liste vide si la clé manque,
        # ce qui évite un crash lorsqu'un nœud de la hiérarchie est absent.
        for module in lib.get("Loadmods", []):
            load_name: str = module.get("Name") or ""

            for csect in module.get("CSECTs", []):
                copt = csect.get("Copt")
                # `not copt` est True pour None (clé absente) ET pour [] (liste
                # vide) : dans les deux cas le CSECT n'a pas d'options COPT et
                # on passe silencieusement au suivant.
                if not copt:
                    continue

                csect_name: str = csect.get("Name") or ""
                compiler: str = csect.get("Compiler1") or ""
                # Préfixe "1" = CSECT principal (même nom que le module, cas normal
                # en IBM COBOL). Préfixe "0" = CSECT secondaire (stub DB2, CICS…).
                prefix = "1" if load_name == csect_name else "0"

                # yield suspend la fonction et retourne le tuple à l'appelant.
                # À l'itération suivante, l'exécution reprend juste après ce yield.
                # Cela évite de construire une liste complète en mémoire avant
                # d'écrire la première ligne.
                yield prefix, loadlib, load_name, csect_name, compiler, copt


def generate_copt_file(output_file: Path, compiler_options: list[str]) -> None:
    """Écrit les options de compilation dans un fichier texte dédié au CSECT.

    Le fichier est créé ainsi que tous les répertoires parents manquants.
    Chaque option occupe une ligne dans le fichier.

    Args:
        output_file: Chemin complet du fichier à créer.
        compiler_options: Liste des options de compilation à écrire.

    """
    # parents=True : crée tous les sous-répertoires manquants (équivalent mkdir -p).
    # exist_ok=True : ne lève pas d'erreur si le répertoire existe déjà.
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open(mode="w", encoding="utf-8") as f:
        for option in compiler_options:
            f.write(f"{option}\n")

    LOGGER.debug(
        "Fichier détail créé : %s (%d option(s)).",
        output_file,
        len(compiler_options),
    )


def write_csv(rows: Iterator[CsectRow], output_path: Path) -> int:
    """Écrit les lignes COPT dans un fichier texte délimité par des points-virgules.

    Chaque ligne du fichier de sortie suit le format ::

        <préfixe>;<loadlib>;<load_name>;<csect_name>;<compilateur>;<nb_opts>

    Pour chaque ligne du CSV, un fichier texte détaillé est aussi créé sous
    ``<répertoire_sortie>/loadlibs/<loadlib>/<load_name>_<csect_name>_<compiler_short>.txt``.

    Args:
        rows: Itérateur de ``CsectRow`` produit par ``iter_csect_copt``.
            Un itérateur est consommé une seule fois ; cette fonction en épuise
            le contenu ligne par ligne sans stocker toutes les lignes en mémoire.
        output_path: Chemin du fichier CSV de sortie.

    Returns:
        Nombre total de lignes écrites dans le fichier CSV.

    Raises:
        SystemExit: code 10 si une erreur système survient pendant l'écriture
            (disque plein, droits révoqués en cours d'écriture…).

    """
    try:
        count = 0
        # basedir est calculé une seule fois avant la boucle car il ne change
        # pas d'une itération à l'autre.
        basedir = output_path.parent
        # mode="w" crée le fichier s'il n'existe pas (ou l'écrase). Les fins de
        # ligne sont écrites explicitement via f.write(f"...\n").
        with output_path.open(mode="w", encoding="utf-8") as f:
            for prefix, loadlib, load_name, csect_name, compiler, copt in rows:
                # len(copt) = nombre total d'options de compilation du CSECT.
                f.write(
                    f"{prefix};{loadlib};{load_name};"
                    f"{csect_name};{compiler};{len(copt)}\n"
                )
                LOGGER.debug(
                    "CSECT traité : %s / %s / %s — %s - %d option(s).",
                    loadlib,
                    load_name,
                    csect_name,
                    compiler,
                    len(copt),
                )
                # Résolution du code abrégé depuis COMPILERS (COBOL, C/C++, PL/I).
                compiler_short = COMPILERS.get(compiler, "unknown")
                if compiler_short == "unknown":
                    LOGGER.warning(
                        "Compilateur inconnu pour %s/%s/%s",
                        loadlib,
                        load_name,
                        csect_name,
                    )
                # Chemin du fichier détail :
                #   <basedir>/loadlibs/<loadlib>/<load_name>_<csect_name>_<compiler_short>.txt
                output_file = (
                    basedir
                    / "loadlibs"
                    / loadlib
                    / f"{load_name}_{csect_name}_{compiler_short}.txt"
                )
                generate_copt_file(output_file, copt)
                count += 1
    except OSError as exc:
        LOGGER.error(
            "Erreur I/O lors de l'écriture de '%s' : %s", output_path, exc
        )
        sys.exit(10)
    else:
        return count


def main() -> None:
    """Point d'entrée du script : orchestre la validation, le chargement et l'écriture.

    Séquence d'exécution :

    1. Analyse les arguments de la ligne de commande.
    2. Vérifie que le fichier d'entrée existe.
    3. Vérifie que le fichier de sortie n'existe pas déjà.
    4. Vérifie que le répertoire de sortie est accessible en écriture.
    5. Charge le JSON.
    6. Parcourt la hiérarchie et écrit le CSV et les fichiers détail.
    7. Affiche le bilan.

    Raises:
        SystemExit: code 2 pour tout problème lié aux chemins de fichiers.

    """
    args = parse_args()
    # setup_logging configure le logger "extract_copt" défini en haut du module.
    # load_config() lit config.toml pour récupérer le niveau de log et le chemin
    # du fichier journal.
    setup_logging(load_config(), "extract_copt")

    # Path() transforme une chaîne de caractères en objet chemin portable
    # (fonctionne aussi bien sur Linux que sur Windows).
    input_path = Path(args.file)
    output_path = Path(args.output)

    LOGGER.debug(
        "Arguments reçus : entrée='%s', sortie='%s'.", input_path, output_path
    )

    # Vérification 1 : le fichier source doit exister et être un fichier régulier
    # (pas un répertoire).
    if not input_path.is_file():
        LOGGER.error("Le fichier d'entrée '%s' n'existe pas.", input_path)
        sys.exit(2)

    # Vérification 2 : on refuse d'écraser un fichier de sortie existant pour
    # éviter toute perte de données accidentelle.
    if output_path.exists():
        LOGGER.error("Le fichier de sortie '%s' existe déjà.", output_path)
        sys.exit(2)

    # output_path.parent vaut Path('.') pour un nom de fichier sans répertoire
    # (ex. "out.csv" → parent = ".").
    output_dir = output_path.parent
    if not output_dir.is_dir():
        LOGGER.error("Le répertoire de sortie '%s' n'existe pas.", output_dir)
        sys.exit(2)
    try:
        # On crée puis supprime immédiatement un fichier temporaire pour tester
        # les droits d'écriture sans laisser de fichier parasite.
        testfile = output_dir / ".__vlm_write_test__"
        testfile.touch()
        testfile.unlink()
    except OSError:
        LOGGER.error(
            "Le répertoire de sortie '%s' n'est pas accessible en écriture.",
            output_dir,
        )
        sys.exit(2)

    LOGGER.info("Début de l'extraction : '%s' → '%s'.", input_path, output_path)

    data = load_json(input_path)
    LOGGER.info("JSON chargé : %d loadlib(s) à traiter.", len(data))

    # iter_csect_copt() est passé directement à write_csv() sans stocker les
    # lignes dans une liste intermédiaire : elles sont générées et écrites une
    # par une, ce qui limite la consommation mémoire sur de grands fichiers.
    count = write_csv(iter_csect_copt(data), output_path)
    LOGGER.info(
        "Extraction terminée : %d CSECT(s) écrits dans '%s'.",
        count,
        output_path,
    )


# Ce bloc garantit que main() n'est appelé que si le script est exécuté
# directement (python extract_copt.py), et pas s'il est importé comme module
# par un autre script Python (ex. dans les tests unitaires).
if __name__ == "__main__":
    main()
