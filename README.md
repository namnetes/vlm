# Structure du projet

```
test_date/
│
├── vlm.log
│
vlm_parser/
│
├── __init__.py
├── args_handler.py
├── csv_writer.py
├── error_handling.py
├── file_reader.py
├── main.py
├── structures.py
└── utils.py
launch.json
```

## Description
VLM est un utilitaire en ligne de commande conçu pour analyser et traiter les fichiers générés par l'analyse VLM effectuée avec IBM File Manager.

## Installation
Pour installer my_parser, clonez ce dépôt et installez les dépendances :

```bash
git clone [URL non valide supprimée]
cd my_parser
pip install -r requirements.txt
```

## Utilisation

Pour exécuter le script `vlm_parser`, utilisez la commande suivante dans votre terminal :

```bash
vlm_parser --input_file mon_fichier.dat --output_file resultat.csv
```

Options

    -f, --input_file:
    Spécifie le fichier d'entrée à traiter. Cet argument est requis.

    -o, --output_file:
    Spécifie le fichier de sortie où les résultats seront écrits. Cet argument est requis.

    --sep:
    Définit le séparateur de champ du fichier CSV. Vous pouvez choisir entre "," et ";". La valeur par défaut est ";".

    -l, --log_file:
    Indique le nom du fichier de log. Par défaut, un nom basé sur la date et l'heure actuelles sera utilisé, sous la forme vlm_YYYYMMDD_HHMMSS.log.

    -q, --quiet:
    Active le mode silencieux (quiet). Par défaut, ce mode est activé. Utilisez -q pour supprimer les messages de sortie.


## Structure du Fichier des VLM à Traiter

Ci-dessous, vous trouverez la structure du fichier résultant de l'analyse de plusieurs LOADLIB sur IBM Mainframe, réalisée par la fonction VLM (View Load Module) d'IBM File Manager.

**Détails de la Structure :**

- **Section LOADLIB :**
    - **Nom de la LOADLIB :** Une chaîne représentant le nom de la LOADLIB (par exemple, "EXPL.BIB.CHME.YA0.LODLIB").
    
    - **Informations sur le Module Exécutable (répétables) :**
        - **Nom du Module :** Une chaîne désignant le nom du module (par exemple, "CCBD01").
        - **Horodatage de Lien :** Date et heure indiquant le moment où le module a été lié.
        - **Éditeur de Liens :** Chaîne représentant le programme d'édition de liens utilisé (par exemple, "PROGRAM BINDER 5695-PMB V1R3").
        - **EPA (Adresse d'Entrée du Programme) :** Valeur hexadécimale indiquant l'adresse d'entrée du programme.
        - **Taille du Module :** Valeur décimale exprimant la taille du module.
        - **TTR (Clé de Table de Traduction) :** Valeur hexadécimale représentant la clé de table de traduction.
        - **SSI :** Valeur hexadécimale.
        - **AC :** Valeur hexadécimale.
        - **AM :** Valeur hexadécimale.
        - **RM :** Valeur hexadécimale.
        
    - **Table des CSECT (Sections de Contrôle) :**
        - **Entrées de la Table des CSECT (répétables) :**
            - **Nom :** Chaîne représentant le nom de la section de contrôle (par exemple, "CCBD01").
            - **Type :** Chaîne représentant le type de section de contrôle (par exemple, "SD").
            - **Adresse :** Valeur hexadécimale représentant l'adresse de début de la section de contrôle.
            - **Taille :** Valeur hexadécimale représentant la taille de la section de contrôle.
            - **Classe :** Chaîne représentant la classe de la section de contrôle (par exemple, "B_TEXT").
            - **A/RMODE :** Chaîne indiquant le mode adresse/relocalisation (par exemple, "MIN/ANY").
            - **Compilateur 1 :** Chaîne désignant le premier compilateur utilisé (le cas échéant).
            - **Compilateur 2 :** Chaîne désignant le deuxième compilateur utilisé (le cas échéant).
            - **Date :** Date représentant la date de compilation de la section de contrôle.

        - La fin de la table des CSECT est indiquée par une ligne spécifique précisant le nombre de CSECT traitées, formatée comme suit : &laquo;`FMNBA215 xxx Control sections processed.` où `xxx` représente un nombre variant de 0 à n, reflétant le total des sections de contrôle traitées.

    - La fin de la section LOADLIB est marquée par une ligne spécifique indiquant le nombre de membres de PDS contenus, formatée comme suit : « `FMNBB437 xxx member(s) read.` » où `xxx` représente un nombre variant de 1 à n, indiquant le total de membres de PDS dans la LOADLIB.

    - La fin de la section LOADLIB peut également être signalée par une ligne spécifique indiquant l'absence de membres dans le PDS, formatée comme suit : « `FMNBE329 The PDS contains no members.` »


