#! /home/galan/Workspace/py/vlm/.venv/bin/python
# -*- coding: utf-8 *-*

# Lecture du fichier texte
with open('vlm.csv', 'r', encoding='utf-8') as file:
    lines = file.readlines()

# Initialisation d'un dictionnaire pour stocker les lignes en fonction de la première colonne
grouped_lines = {}

# Parcours des lignes
for line in lines:
    # Séparation des colonnes en utilisant le point-virgule comme délimiteur
    columns = line.strip().split(';')
    
    # Récupération de la première colonne (module) et de la onzième colonne (csect)
    key = columns[0]
    csect = columns[10]
    
    # Vérifie si la clé (key) n'est pas déjà présente dans le dictionnaire. Si non, crée une
    # nouvelle entrée dans le dictionnaire avec la clé key et une liste vide comme valeur.
    # Ajoute le couple (ligne, csect) à la liste associée à la clé key.
    if key not in grouped_lines:
        grouped_lines[key] = []
    grouped_lines[key].append((line, csect))

# Ici parcours du dictionnaire quand tout le fichier a été traité.
# Recherche des correspondances entre les groupes de module (key)

iteration_counter = 0
# 1 clé contient une liste de couple ( ligne et csect )
for key, lines in grouped_lines.items():
    
    # donc 1 couple contient sa ligne et sa csect
    for line, csect in lines:
        # Vérification si la onzième colonne correspond à la première colonne d'un autre groupe
        if csect in grouped_lines and key != csect:
            iteration_counter += 1
            print(f'{line}',end='')
            # print(f'{iteration_counter};{line}',end='')
            #print(f'{iteration_counter};{grouped_lines[csect][0][0]}',end='')