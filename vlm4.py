#! /home/galan/Workspace/py/vlm/.venv/bin/python
# -*- coding: utf-8 *-*

import re
import sys
import argparse
from tqdm import tqdm

def traiter_lignes(fichier, args):
    """
    TODO: Ajoutez une description de ce que fait cette fonction.
    """
    # Initialiser une liste pour stocker chaque groupe de lignes associées à un même module
    groupes = []
    # Initialiser une liste qui contiendra les lignes du groupe courant
    groupe_courant = None

    # Obtenir le nombre total de lignes dans le fichier pour la barre de progression
    total_lignes = sum(1 for _ in fichier)
    fichier.seek(0)  # Revenir au début du fichier

    # Utiliser tqdm pour créer une barre de progression
    for ligne in tqdm(fichier, total=total_lignes, desc="Traitement des lignes", disable=args.quiet):
        # Ignorer les lignes vides et les lignes composées uniquement d'espaces
        if not ligne.strip():
            continue
        # Ignorer les lignes contenant certains motifs
        elif re.search(r'\$\$FILEM|IBM File Manager for z/OS|Attributes|Name      Type|---------', ligne):
            continue

        # Remplacer '0 ' ou '1 ' par un espace en début de ligne
        ligne = ligne.replace('0 ', ' ').replace('1 ', ' ')

        # Vérifier le motif de fin de groupe
        if 'FMNBA215' in ligne:
            # Utiliser une expression régulière pour extraire le nombre de CSECT de la ligne
            match = re.search(r'\b(\d+)\b', ligne)
            if match:
                # Récupérer le nombre de CSECT extrait
                numero_fmnba215 = int(match.group(1))
            else:
                # Si pas de nombre, forcer le nombre de CSECT à zéro
                numero_fmnba215 = 0

            # Ajouter au tout début de la liste le nombre de CSECT au groupe courant
            groupe_courant.insert(0, numero_fmnba215)

            # Ajouter le groupe courant à la liste des groupes
            groupes.append(groupe_courant)

            # Réinitialiser le groupe courant
            groupe_courant = None
        else:
            # Vérifier le motif de début de groupe
            if 'Load Module Information' in ligne:
                # Si un groupe est en cours, l'ajouter à la liste
                if groupe_courant:
                    groupes.append(groupe_courant)

                # Initialiser une nouvelle liste
                groupe_courant = []

            # Ajouter les lignes à la liste du groupe en cours (en excluant celles spécifiées)
            if groupe_courant is not None:
                groupe_courant.append(ligne)

    return groupes

def main():
    """
    TODO: Ajoutez une description de ce que fait cette fonction.
    """
    # Mise en place de l'analyseur d'arguments en ligne de commande
    parser = argparse.ArgumentParser(description="TODO: Ajoutez une description du script.")
    parser.add_argument('-f', '--input_file', default='./vlm.txt', help="Chemin vers le fichier à traiter.")
    parser.add_argument('-q', '--quiet', action='store_true', help="Désactiver l'affichage de la barre de progression.")

    # Analyser les arguments de la ligne de commande
    args = parser.parse_args()

    chemin_fichier = args.input_file

    try:
        # Ouvrir le fichier en mode lecture
        with open(chemin_fichier, 'r') as fichier:
            # Appeler la fonction pour traiter les lignes et passer les arguments
            groupes = traiter_lignes(fichier, args)

        # Imprimer les résultats finaux pour déboguer
        print(f"Nombre total de groupes : {len(groupes)}")

    except FileNotFoundError:
        print(f"Le fichier {chemin_fichier} n'a pas été trouvé.")

if __name__ == "__main__":
    main()
