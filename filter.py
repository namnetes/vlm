#!/home/galan/workspace/vlm/.venv/bin/python
# -*- coding: utf-8 -*-

import argparse
import sys
import re
from pathlib import Path

def process_line(line, mode):
    """Analyser une ligne du fichier lue.

    Args:
        line (str): Ligne à analyser0

        mode (str): Mode de filtrage (match ou donotmatch).
        - 'match'permet de sélectionner les lignes qui correspondent aux
          motifs définis dans le dictionnaire des regex.
        
        - 'donotmatch' permet de sélectionner les lignes qui ne correspondent
          pas aux motifs définis dans le dictionnaire des regex
    """
    print(line, end='')


def parse_stdin(mode):
    """Affiche le contenu de l'entrée standard sur la sortie standard.

    Args:
        mode (str): Mode de filtrage ('match' ou 'donotmatch').
    """
    for line in sys.stdin:
        process_line(line, mode)


def parse_file(filename, mode):
    """Lit un fichier physique et affiche son contenu sur la sortie standard.

    Args:
        filename (str): Nom et chemin du fichier à lire.
        mode (str): Mode de filtrage (match ou donotmatch).
    """
    try:
        with open(filename, 'r', encoding='latin1') as f:
            for line in f:
                process_line(line, mode)

    except FileNotFoundError as e:
        print(f"The file {filename} was not found.")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")


def get_arguments():
    """Analyse les arguments de la ligne de commande.

    Returns:
        tuple: Le nom et chemin du fichier à traiter, et le mode de filtrage
        (match ou donotmatch).
    """
    parser = argparse.ArgumentParser(
        description='Filter the records of the file to be processed.')

    parser.add_argument('pathfile',
        type=str,
        default=['-'],
        help='Name and path of the file to be processed')

    parser.add_argument('--mode',
        type=str,
        choices=['match', 'donotmatch'],
        default='donotmatch',
        help='Display the lines that match or do not match the defined patterns')

    args = parser.parse_args()

    return args.pathfile.lower(), args.mode.lower()


if __name__ == "__main__":
    """Point d'entrée du programme."""

    # dictionnaire des expressions régulières qui permettent de filtrer les
    # lignes qui correspondent aux motifs définis dans ce dictionnaire.
    regex_dict = {
        'regex1': r'^[01 ][ ]*\$\$FILEM',         
        'regex2': r'^[01 ][ ]*IBM File Manager',
        'regex3': r'^[01 ][ ]*Load Module Information',
        'regex4': r'^[01 ][ ]*FMNBA215[ ]*[0-9]+[ ]*Control sections processed',
        'regex5': r'^[01 ][ ]*^[01 ]FMNBB437[ ]+[0-9]+[ ]+member\(s\)[ ]+read',
        'regex6': r'^[01 ][ ]*FMNBE329 The PDS contains no members',
        'regex7': r'^[ ]*$'
    }

    # Analyse les arguments de la ligne de commande.
    filename, mode = get_arguments()
    if mode not in ['match', 'donotmatch']:
        print("Error: mode must be either 'match' or 'donotmatch'")

    # Parse le fichier spécifié en argument ou son équivalent sur l'entrée
    # standard stdin.
    if '-' in filename:
        parse_stdin(mode)
    else:
        parse_file(filename, mode)
