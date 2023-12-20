#! /home/galan/Workspace/py/vlm/.venv/bin/python
# -*- coding: utf-8 *-*

import re

# Ouvrir le fichier en mode lecture
with open('./data/vlm.txt', 'r') as fichier:
    
    # Initialiser une liste de dictionnaire pour stocker chaque groupe de lignes associées à un même module 
    groupes = []
    # Initialiser un dictionnaire qui contiendra les lignes du groupe courant
    groupe_courant = None
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
        # Ignorer les lignes contenant '$$FILEM'
        elif '$$FILEM' in ligne:
            continue
        # Ignorer les lignes contenant 'IBM File Manager for z/OS'
        elif 'IBM File Manager for z/OS' in ligne:
            continue
        # Ignorer les lignes contenant 'Attributes'
        elif 'Attributes'  in ligne:
            continue
        # Ignorer les lignes contenant 'Name Type Address Size'
        elif 'Name      Type Address Size' in ligne:
            continue
        # Ignorer les lignes contenant '--------- ----'
        elif '--------- ----' in ligne:
            continue

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
            groupe_courant['FMNBA215'] = {numero_fmnba215}
            
            # Ajouter le groupe à la liste
            groupes.append(groupe_courant)
            nb_groupes += 1  # Incrémenter le nombre de groupes
            
            # Réinitialiser le dictionnaire qui contiend les lignes du groupe courant
            groupe_courant = None
            
            # Incrémenter le nombre de lignes 'FMNBA215'
            nb_lignes_fmnba215 += 1
        else:
            # Vérifier le motif de début de groupe
            if 'Load Module Information' in ligne:
                # Si un groupe est en cours, l'ajouter à la liste
                if groupe_courant:
                    groupes.append(groupe_courant)
                    nb_groupes += 1  # Incrémenter le nombre de groupes

                # Incrémenter le nombre de lignes 'Load Module Information'
                nb_lignes_module += 1

                # Initialiser un nouveau groupe
                groupe_courant = {'Load Module Information': []}
                
            # Ajouter les lignes au groupe en cours (en excluant celles spécifiées)
            elif groupe_courant is not None:
                groupe_courant['Load Module Information'].append(ligne)

# Imprimer les compteurs finaux pour déboguer
print(f"Nombre total de groupes : {nb_groupes}")
print(f"Nombre total de lignes 'Load Module Information' : {nb_lignes_module}")
print(f"Nombre total de lignes 'FMNBA215' : {nb_lignes_fmnba215}")
