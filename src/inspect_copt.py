#!/usr/bin/env python3

"""Affiche le contenu brut de chaque balise Copt d'un fichier XML VLM.

Utilitaire de débogage pour inspecter les options de compilation (COPT)
avant ou après reformatage par reformat_copt.py.

Terminologie :
- COPT  : Compilation OPTions — options passées au compilateur IBM (COBOL, C++, PL/I).
- Chaque balise XML <Copt> porte un attribut "Val" contenant ces options.

Exemple :
    python src/inspect_copt.py -f datas/clean_vlm.xml
    python src/inspect_copt.py -f datas/clean_vlm_copt.xml
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Analyse et valide les arguments de ligne de commande.

    Returns:
        Namespace argparse avec les attributs :
        ``file`` (chemin du XML) et ``encoding`` (encodage à utiliser).

    """
    parser = argparse.ArgumentParser(
        description="Affiche le contenu de chaque balise Copt d'un XML VLM."
    )
    parser.add_argument(
        "-f",
        "--file",
        required=False,
        default="datas/clean_vlm.xml",
        help="Fichier XML en entrée (défaut : datas/clean_vlm.xml)",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        required=False,
        default="utf-8",
        help="Encodage du fichier XML (défaut : utf-8)",
    )
    return parser.parse_args()


def main() -> None:
    """Point d'entrée CLI — charge le XML et affiche chaque balise Copt.

    Charge le fichier XML en mémoire, recherche toutes les balises <Copt>
    quelle que soit leur profondeur d'imbrication, puis affiche leur
    attribut "Val" numéroté.

    Affichage :
    - Si aucune balise Copt n'est trouvée : message informatif.
    - Sinon : liste ``[1] valeur``, ``[2] valeur``, etc.

    Raises:
        SystemExit:
            - Code 2 : fichier introuvable.
            - Code 3 : XML syntaxiquement invalide.

    """
    args = parse_args()
    input_path = Path(args.file)

    # .is_file() retourne True uniquement pour un fichier régulier.
    # Les répertoires ou chemins inexistants retournent False.
    if not input_path.is_file():
        print(
            f"Erreur : le fichier '{input_path}' n'existe pas.", file=sys.stderr
        )
        sys.exit(2)

    try:
        # ET.parse() charge le XML en mémoire sous forme d'arbre d'objets.
        # ET.XMLParser(encoding=...) force l'encodage indiqué en argument.
        # Lève ET.ParseError si le XML est syntaxiquement invalide.
        tree = ET.parse(
            str(input_path), parser=ET.XMLParser(encoding=args.encoding)
        )
    except ET.ParseError as exc:
        # exc contient le détail de l'erreur (ligne, colonne, message).
        print(f"Erreur XML : {exc}", file=sys.stderr)
        sys.exit(3)

    # .//Copt = expression XPath signifiant « tous les éléments <Copt>
    # à n'importe quelle profondeur dans l'arbre » (pas seulement les fils directs).
    copt_elements = tree.findall(".//Copt")

    if not copt_elements:
        print("Aucune balise Copt trouvée.")
        return

    # enumerate(iterable, start=1) retourne des paires (index, valeur).
    # start=1 commence la numérotation à 1 (plus lisible que 0 pour l'utilisateur).
    for i, copt in enumerate(copt_elements, start=1):
        # .get("Val", "") retourne la valeur de l'attribut "Val",
        # ou une chaîne vide "" si l'attribut est absent.
        val = copt.get("Val", "")
        print(f"[{i}] {val}")


# Ce bloc garantit que main() n'est appelé que si le script est exécuté
# directement (python inspect_copt.py), et pas s'il est importé comme module.
if __name__ == "__main__":
    main()
