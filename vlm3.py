#! /home/galan/Workspace/py/vlm/.venv/bin/python
# -*- coding: utf-8 *-*

import re

def traiter_ligne(ligne):
    # Initialiser le dictionnaire de sortie
    infos = {}

    # Remplacer '0 ' ou '1 ' par un espace en début de ligne
    ligne = ligne.replace('0 ', ' ').replace('1 ', ' ')

    # Vérifier le motif de fin de groupe
    if 'FMNBA215' in ligne:
        # Utiliser une expression régulière pour extraire le nombre de CSECT de la ligne
        match = re.search(r'\b(\d+)\b', ligne)
        if match:
            # Récupérer le nombre extrait
            numero_fmnba215 = int(match.group(1))
        else:
            # Si pas de nombre, forcer à zéro
            numero_fmnba215 = 0

        # Ajouter la ligne au groupe en cours avec le nombre associé
        infos['FMNBA215'] = {numero_fmnba215}

    # Vérifier le motif de début de groupe
    elif 'Load Module Information' in ligne:
        # Initialiser un nouveau groupe
        infos['Load Module Information'] = []

    # Ajouter les lignes au groupe en cours (en excluant celles spécifiées)
    else:
        infos['Load Module Information'].append(ligne)

    return infos

# Ouvrir le fichier en mode lecture
with open('./data/vlm.txt', 'r') as fichier:
    # Initialiser une liste de dictionnaire pour stocker chaque groupe de lignes associées à un même module 
    groupes = []
    # le nombre total de groupes
    nb_groupes = 0
    # le nombre total de lignes comportant le motif d'ouverture de groupe 'Load Module Information'
    nb_lignes_module = 0
    # Compteur - le nombre total de lignes comportant le motif de fermeture de groupe 'FMNBA215'
    nb_lignes_fmnba215 = 0

    # Parcourir chaque ligne du fichier
    for numero_ligne, ligne in enumerate(fichier, start=1):
        # Ignorer les lignes vides et les lignes composées uniquement d'espaces
        if not ligne.strip():
            continue
        # Ignorer les lignes contenant certains motifs
        elif re.search(r'\$\$FILEM|IBM File Manager for z/OS|Attributes|Name      Type Address Size|--------- ----', ligne):
            continue

        # Traiter la ligne
        infos = traiter_ligne(ligne)

        # Ajouter les informations extraites à la liste des groupes
        groupes.append(infos)
        nb_groupes += 1  # Incrémenter le nombre de groupes

        # Incrémenter le nombre de lignes 'Load Module Information' et 'FMNBA215'
        if 'Load Module Information' in infos:
            nb_lignes_module += 1
        if 'FMNBA215' in infos:
            nb_lignes_fmnba215 += 1

# Imprimer les compteurs finaux pour déboguer
print(f"Nombre total de groupes : {nb_groupes}")
print(f"Nombre total de lignes 'Load Module Information' : {nb_lignes_module}")
print(f"Nombre total de lignes 'FMNBA215' : {nb_lignes_fmnba215}")
