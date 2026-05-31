#!/usr/bin/env bash
# =============================================================================
# export_csv.sh — Extraction de données VLM vers CSV
# =============================================================================
#
# VLM = View Load Module — fonction d'IBM File Manager qui analyse les load
# modules d'une bibliothèque z/OS. Le JSON produit par le pipeline à partir
# de cette sortie est la source de ce script.
#
# Lit le fichier JSON VLM produit par build_json.py et produit un fichier CSV
# (délimiteur ';') selon un mode d'extraction choisi par l'utilisateur.
#
# Trois modes d'extraction disponibles :
#   --global   : une ligne par CSECT avec l'ensemble de ses métadonnées.
#   --options  : une ligne par module avec ses options de compilation (Copt),
#                CSECT principal uniquement.
#   --compiler : une ligne par module avec son compilateur utilisé,
#                CSECT principal uniquement.
#
# Un filtre de date optionnel (-d) permet de ne retenir que les modules
# liés (Linkedon) à partir d'une date donnée (format yyyy/mm/dd).
#
# Dépendances externes requises :
#   jq   : outil en ligne de commande pour interroger et transformer du JSON.
#          Vérifier son installation avec : jq --version
#   awk  : outil Unix standard de traitement de texte en colonnes.
#          Présent par défaut sur tout système Linux/macOS.
#
# Usage :
#   bash script/export_csv.sh -i datas/vlm.json -o datas/output.csv -g
#   bash script/export_csv.sh -i datas/vlm.json -o datas/output.csv -p
#   bash script/export_csv.sh -i datas/vlm.json -o datas/output.csv -c
#   bash script/export_csv.sh -i datas/vlm.json -o datas/output.csv -g \
#        -d 2025/01/01
#
# Variable d'environnement optionnelle :
#   VLM_DATA_DIR : répertoire de base pour les chemins relatifs.
#                  Si non définie, les chemins sont relatifs au répertoire
#                  courant du terminal.
# =============================================================================

# Protection contre les erreurs silencieuses :
#   -e : quitte immédiatement si une commande retourne un code d'erreur non nul.
#   -u : toute variable non définie utilisée dans le script déclenche une erreur.
#        Cela évite des bugs discrets causés par des fautes de frappe de noms
#        de variables (ex. $OUTUT au lieu de $OUTPUT).
#   -o pipefail : si une commande dans un pipe échoue (ex. jq | awk), le code
#        d'erreur global du pipe est celui de la commande fautive, pas de la
#        dernière. Sans cela, un échec de jq serait masqué si awk réussit.
set -euo pipefail


# =============================================================================
# Variables globales — valeurs par défaut
# =============================================================================
# Ces variables sont déclarées ici pour donner un aperçu des paramètres du
# script. Elles seront écrasées par les arguments passés sur la ligne de
# commande (fonction parse_args).

# Chemin du fichier CSV de sortie (modifiable via -o).
OUTPUT="query_output.csv"

# Mode d'extraction : "global", "options" ou "compiler" (modifiable via -g/-p/-c).
MODE="global"

# Chemin du fichier JSON d'entrée (modifiable via -i).
INPUT_JSON="vlm.json"

# Date minimale de link-edit au format yyyy/mm/dd (modifiable via -d).
# Chaîne vide = pas de filtre de date appliqué.
MIN_LINKEDIT_DATE=""

# Répertoire de base pour les chemins relatifs.
# La syntaxe ${VAR:-valeur_par_défaut} retourne $VLM_DATA_DIR si la variable
# est définie et non vide, sinon retourne la valeur par défaut (ici "").
# Cela permet d'utiliser la variable sans déclencher l'erreur de -u si elle
# n'est pas exportée dans l'environnement.
DATA_DIR="${VLM_DATA_DIR:-}"


# =============================================================================
# show_help — affiche l'aide et la liste des options disponibles
# =============================================================================
show_help() {
    # $0 contient le nom du script tel qu'il a été invoqué (ex. ./export_csv.sh).
    # L'utiliser dans le message d'aide rend celui-ci exact si le script est
    # renommé ou lancé depuis un autre répertoire.
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -h, --help           Afficher cette aide"
    echo "  -i, --input FILE     Fichier JSON en entrée (défaut: vlm.json)"
    echo "  -o, --output FILE    Fichier CSV en sortie (défaut: query_output.csv)"
    echo "  -d, --date DATE      Ne garder que les modules liés à partir de DATE" \
         "(format yyyy/mm/dd)"
    echo "  -g, --global         Extraire toutes les données (mode par défaut)"
    echo "  -p, --options        Extraire les options de compilation (Copt)"
    echo "  -c, --compiler       Extraire le compilateur par module/loadlib"
    echo ""
    echo "Variables d'environnement :"
    echo "  VLM_DATA_DIR  Répertoire de base pour les chemins relatifs" \
         "d'entrée/sortie"
}


# =============================================================================
# resolve_paths_from_env — préfixe les chemins relatifs avec VLM_DATA_DIR
# =============================================================================
resolve_paths_from_env() {
    # Si VLM_DATA_DIR n'est pas définie, il n'y a rien à faire.
    # [ -z "$DATA_DIR" ] est vraie si la chaîne est vide ("").
    if [ -z "$DATA_DIR" ]; then
        return 0
    fi

    # [ -d "$DATA_DIR" ] est vraie si le chemin existe ET est un répertoire.
    # Le ! inverse la condition : on entre dans le if si le répertoire N'EXISTE PAS.
    if [ ! -d "$DATA_DIR" ]; then
        # >&2 redirige ce message vers la sortie d'erreur standard (stderr).
        # Bonne pratique : les messages d'erreur vont sur stderr, pas sur stdout,
        # afin de ne pas polluer une éventuelle capture de la sortie normale.
        echo "Error: VLM_DATA_DIR '$DATA_DIR' does not exist" \
             "or is not a directory." >&2
        exit 1
    fi

    # [[ "$INPUT_JSON" != /* ]] : teste si le chemin ne commence PAS par '/'.
    # En Bash, [[ ]] est une version étendue de [ ] qui supporte les motifs
    # glob (*, ?, [...]). '/*' signifie "commence par /", ce qui caractérise
    # un chemin absolu sous Linux. Si le chemin est relatif, on le préfixe.
    if [[ "$INPUT_JSON" != /* ]]; then
        INPUT_JSON="$DATA_DIR/$INPUT_JSON"
    fi

    if [[ "$OUTPUT" != /* ]]; then
        OUTPUT="$DATA_DIR/$OUTPUT"
    fi
}


# =============================================================================
# parse_args — analyse les arguments de la ligne de commande
# =============================================================================
parse_args() {
    # "$@" représente l'ensemble des arguments passés à la fonction, dans
    # l'ordre, chacun dans une entrée séparée (les espaces internes sont
    # préservés). Ici, main() passe les arguments du script à parse_args.
    #
    # La boucle while continue tant qu'il reste au moins un argument.
    # "$#" donne le nombre d'arguments restants.
    while [ "$#" -gt 0 ]; do
        # case "$1" in ... esac : compare la valeur du premier argument courant
        # ($1) avec plusieurs motifs. C'est l'équivalent d'un switch/case en
        # Python ou en C. Le ;; termine chaque branche.
        case "$1" in

            # --- Aide ---------------------------------------------------------
            -h|--help)
                show_help
                exit 0
                ;;

            # --- Fichier de sortie --------------------------------------------
            -o|--output)
                # Validation que l'argument suivant ($2) est bien présent et
                # qu'il ne ressemble pas lui-même à une option (ne commence pas
                # par -). Sans cette vérification, un oubli comme :
                #   ./export_csv.sh -o -g
                # utiliserait "-g" comme nom de fichier, ce qui est un bug.
                #
                # "$#" -lt 2 : moins de 2 arguments restants (donc pas de $2).
                # -z "$2"    : $2 est une chaîne vide.
                # "$2" == -* : $2 commence par - (ce serait une autre option).
                if [ "$#" -lt 2 ] || [ -z "$2" ] || [[ "$2" == -* ]]; then
                    echo "Error: -o|--output requires a filename argument." >&2
                    exit 1
                fi
                OUTPUT="$2"
                # shift 2 : décale la liste des arguments vers la gauche de 2
                # positions. $1 (l'option -o) et $2 (la valeur) sont consommés.
                # Après shift 2, l'ancien $3 devient le nouveau $1.
                shift 2
                ;;

            # --- Fichier d'entrée ---------------------------------------------
            -i|--input)
                if [ "$#" -lt 2 ] || [ -z "$2" ] || [[ "$2" == -* ]]; then
                    echo "Error: -i|--input requires a filename argument." >&2
                    exit 1
                fi
                INPUT_JSON="$2"
                shift 2
                ;;

            # --- Filtre de date -----------------------------------------------
            -d|--date)
                if [ "$#" -lt 2 ] || [ -z "$2" ] || [[ "$2" == -* ]]; then
                    echo "Error: -d|--date requires a date argument." >&2
                    exit 1
                fi

                # Validation du format de date avec une expression régulière.
                # [[ "$2" =~ pattern ]] : vérifie si $2 correspond au motif regex.
                # ^          : début de chaîne.
                # [0-9]{4}   : exactement 4 chiffres (année).
                # /          : un slash littéral.
                # [0-9]{2}   : exactement 2 chiffres (mois).
                # /          : un slash littéral.
                # [0-9]{2}   : exactement 2 chiffres (jour).
                # $          : fin de chaîne.
                # Le ! inverse la condition : on entre dans le if si la date
                # NE correspond PAS au format attendu.
                if ! [[ "$2" =~ ^[0-9]{4}/[0-9]{2}/[0-9]{2}$ ]]; then
                    echo "Error: date format must be yyyy/mm/dd" >&2
                    exit 1
                fi

                # Découpe la date "yyyy/mm/dd" en trois variables.
                # IFS='/' : positionne temporairement le séparateur de champs sur '/'.
                # read -r : assigne chaque champ à year, month, day (-r désactive
                #           l'interprétation des backslashs, bonne pratique systématique).
                # <<< "$2" : here-string — transmet $2 directement sur l'entrée
                #            standard de read, sans créer de sous-processus.
                IFS='/' read -r year month day <<< "$2"

                # Validation numérique du mois (01–12) et du jour (01–31).
                # (( expression )) : évalue une expression arithmétique entière.
                # 10#$month : force l'interprétation en base 10.
                # Sans le préfixe 10#, Bash interpréterait "08" et "09" comme
                # des octaux invalides (les octaux ne contiennent que 0-7),
                # ce qui provoquerait une erreur avec set -e.
                if (( 10#$month < 1 || 10#$month > 12 )); then
                    echo "Error: month must be between 01 and 12" >&2
                    exit 1
                fi
                if (( 10#$day < 1 || 10#$day > 31 )); then
                    echo "Error: day must be between 01 and 31" >&2
                    exit 1
                fi

                MIN_LINKEDIT_DATE="$2"
                shift 2
                ;;

            # --- Modes d'extraction -------------------------------------------
            -g|--global)
                MODE="global"
                # shift (sans argument) : décale d'une seule position.
                # On consomme uniquement le flag courant ($1) car il n'a pas de
                # valeur associée (contrairement à -o ou -i).
                shift
                ;;

            -p|--options)
                MODE="options"
                shift
                ;;

            -c|--compiler)
                MODE="compiler"
                shift
                ;;

            # --- Option inconnue ----------------------------------------------
            *)
                # Le motif * est le joker : il correspond à n'importe quelle
                # valeur non reconnue par les branches précédentes.
                echo "Error: unknown option '$1'" >&2
                show_help
                exit 1
                ;;
        esac
    done
}


# =============================================================================
# validate_inputs — vérifie que les prérequis sont satisfaits avant traitement
# =============================================================================
validate_inputs() {
    # [ ! -f "$INPUT_JSON" ] : -f teste si le chemin existe ET est un fichier
    # ordinaire (pas un répertoire, ni un lien symbolique brisé).
    if [ ! -f "$INPUT_JSON" ]; then
        echo "Error: input file '$INPUT_JSON' not found." >&2
        exit 1
    fi

    # dirname -- "$OUTPUT" : retourne le répertoire parent du chemin de sortie.
    # Le -- évite que les chemins commençant par - soient interprétés comme des
    # options de dirname. Exemples :
    #   "datas/output.csv"    → "datas"
    #   "output.csv"          → "."
    #   "/tmp/out/result.csv" → "/tmp/out"
    output_dir="$(dirname -- "$OUTPUT")"

    # Si le répertoire de sortie n'existe pas, on tente de le créer.
    if [ ! -d "$output_dir" ]; then
        # mkdir -p : crée le répertoire ET tous ses parents manquants (comme
        # "mkdir -p datas/subdir/subsubdir" créerait les 3 niveaux d'un coup).
        # -- : protège contre les noms de répertoires commençant par -.
        # || { ... } : si mkdir échoue, exécuter le bloc entre accolades.
        # Sans || {}, set -e arrêterait le script mais sans message d'erreur
        # explicite pour l'utilisateur.
        mkdir -p -- "$output_dir" || {
            echo "Error: unable to create output directory '$output_dir'." >&2
            exit 1
        }
    fi

    # Vérification que jq est installé et accessible dans le PATH.
    # command -v jq : affiche le chemin absolu de jq si trouvé, ne retourne
    # rien sinon. C'est la méthode recommandée pour tester la présence d'une
    # commande (préférable à "which", qui n'est pas portable).
    # >/dev/null 2>&1 : redirige stdout ET stderr vers /dev/null pour supprimer
    # tout affichage (on ne veut que le code de retour, pas le chemin affiché).
    if ! command -v jq >/dev/null 2>&1; then
        echo "Error: jq is not installed (or not in PATH)." >&2
        exit 1
    fi
}


# =============================================================================
# prepare_output_file — supprime le fichier de sortie existant s'il y en a un
# =============================================================================
prepare_output_file() {
    # rm -f -- "$OUTPUT" : supprime le fichier de sortie sans erreur si absent.
    #   -f (force) : ne produit PAS d'erreur si le fichier n'existe pas.
    #                Sans -f, rm échouerait si le fichier est absent, et set -e
    #                arrêterait le script.
    #   -- : protège les noms de fichiers commençant par un tiret.
    # 2>/dev/null : redirige les messages d'erreur système vers /dev/null
    #               (ex: "permission denied"), les rendant invisibles.
    # || true : si rm retourne malgré tout un code d'erreur non nul (cas rare
    #           avec set -e), "true" retourne toujours 0 pour ne pas interrompre
    #           le script. C'est une protection supplémentaire pour set -e.
    rm -f -- "$OUTPUT" 2>/dev/null || true
}


# =============================================================================
# run_global_mode — extrait toutes les métadonnées CSECT
# =============================================================================
# Format de sortie (une ligne par CSECT) :
#   loadlib;load_name;linkedon;csect_name;compiler;ThreadSafe=bool;CICS=bool;
#   DB2=bool;WMQ=bool;identify
# =============================================================================
run_global_mode() {
    # -------------------------------------------------------------------------
    # Présentation de jq
    # -------------------------------------------------------------------------
    # jq est un processeur JSON en ligne de commande. Il accepte un filtre
    # (programme jq) et un fichier JSON, et produit une sortie transformée.
    # Analogie : jq est à JSON ce que sed/awk est au texte.
    #
    # Options utilisées :
    #   -r (raw output) : affiche les chaînes de caractères sans guillemets.
    #                     Sans -r, "MYPGM" serait affiché avec les guillemets.
    #   --arg nom valeur : injecte une variable shell dans le filtre jq sous
    #                     forme de variable jq ($nom). Ici, $MIN_LINKEDIT_DATE
    #                     devient accessible dans le filtre jq sous le nom
    #                     $min_date. Cela évite les injections de code (problème
    #                     similaire aux injections SQL) car la valeur est
    #                     transmise proprement, pas interpolée dans la chaîne.
    # -------------------------------------------------------------------------
    #
    # Décryptage du filtre jq ligne par ligne :
    #
    #   .[]
    #     Le JSON d'entrée est un tableau [ {...}, {...}, ... ].
    #     .[] itère sur chaque élément du tableau (une Loadlib à la fois).
    #     Équivalent Python : "for item in data:"
    #
    #   | .Loadlib as $lib
    #     Le | (pipe jq) passe le résultat de l'expression précédente à la
    #     suivante, comme le pipe Unix | mais à l'intérieur de jq.
    #     ".Loadlib as $lib" stocke la valeur du champ Loadlib dans la variable
    #     $lib pour pouvoir la réutiliser plus loin (car une fois qu'on itère
    #     sur les Loadmods, le contexte courant change et .Loadlib n'est plus
    #     accessible directement).
    #
    #   | .Loadmods[] as $lm
    #     .Loadmods[] itère sur chaque élément du tableau Loadmods.
    #     Chaque élément est stocké dans $lm.
    #     L'effet combiné de .[] au début et de .Loadmods[] ici produit le
    #     produit cartésien : chaque loadlib × chaque loadmod.
    #
    #   | select($min_date == "" or ($lm.Linkedon >= $min_date))
    #     select(condition) : ne laisse passer que les éléments pour lesquels
    #     la condition est vraie (filtre).
    #     - Si $min_date est vide : la condition est toujours vraie (pas de filtre).
    #     - Sinon : ne garde que les loadmods dont Linkedon >= $min_date.
    #     La comparaison >= est LEXICOGRAPHIQUE (alphabétique) en jq. Cela
    #     fonctionne correctement pour les dates au format yyyy/mm/dd car l'année
    #     est en premier : "2025/06/01" > "2025/01/15" (comme un tri alphabétique).
    #
    #   | $lm.CSECTs[] as $csect
    #     Itère sur chaque CSECT du loadmod courant. L'effet combiné des trois
    #     itérateurs (.[], .Loadmods[], .CSECTs[]) produit une ligne pour chaque
    #     triplet (loadlib, loadmod, csect).
    #
    #   | "\($lib);" + "\($lm.Name);" + ...
    #     Construction de la ligne CSV par interpolation de chaîne.
    #     \(expression) dans une chaîne jq évalue l'expression et insère le
    #     résultat (similaire à f"{variable}" en Python ou "${variable}" en Bash).
    #     Les chaînes sont concaténées avec l'opérateur +.
    #     Chaque champ est suivi de ; (le délimiteur CSV du projet).
    # -------------------------------------------------------------------------
    jq -r --arg min_date "$MIN_LINKEDIT_DATE" '
        .[]
        | .Loadlib as $lib
        | .Loadmods[] as $lm
        | select($min_date == "" or ($lm.Linkedon >= $min_date))
        | $lm.CSECTs[] as $csect
        | "\($lib);"
        +"\($lm.Name);"
        +"\($lm.Linkedon);"
        +"\($csect.Name);"
        +"\($csect.Compiler1);"
        +"ThreadSafe=\($csect.ThreadSafe);"
        +"CICS=\($csect.CICS);"
        +"DB2=\($csect.DB2);"
        +"WMQ=\($csect.WMQ);"
        +"\($csect.Identify // "")"
    ' "$INPUT_JSON" > "$OUTPUT"
    # > "$OUTPUT" : redirige toute la sortie de jq vers le fichier CSV.
    # Si le fichier n'existe pas, il est créé. S'il existe, il est écrasé
    # (ce qui est sûr ici car prepare_output_file l'a déjà supprimé).

    # [ -n "$MIN_LINKEDIT_DATE" ] : -n teste si la chaîne est NON vide.
    # && : exécute la commande suivante seulement si la précédente réussit.
    # Affiche un rappel du filtre de date uniquement s'il est actif.
    [ -n "$MIN_LINKEDIT_DATE" ] && echo "Date filter: >= $MIN_LINKEDIT_DATE"
    echo "Global mode: all data collected per load and loadlib."
    echo "Output file: $OUTPUT created."
}


# =============================================================================
# run_options_mode — extrait les options de compilation du CSECT principal
# =============================================================================
# Format de sortie (une ligne par module) :
#   loadlib;load_name;linkedon;compiler;OPT1;OPT2;OPT3;...
#
# Seul le CSECT principal (même nom que le module) est retenu.
# Les options sont triées par ordre alphabétique.
# =============================================================================
run_options_mode() {
    # Explication des opérateurs jq supplémentaires par rapport au mode global :
    #
    #   | select($lm.Name == $csect.Name)
    #     Filtre supplémentaire : ne conserve que le CSECT dont le nom est
    #     IDENTIQUE à celui du loadmod. En IBM COBOL, ce CSECT est le programme
    #     principal. Les CSECTs secondaires (stubs DB2, CICS, sous-programmes)
    #     ont des noms différents et sont ainsi exclus.
    #
    #   | select((($csect.Copt // []) | length) > 0)
    #     Double filtre sur la liste Copt :
    #     - $csect.Copt // [] : opérateur // (alternative en jq, similaire à
    #       l'opérateur "or" de null-coalescing). Si Copt est null ou absent,
    #       retourne [] (tableau vide) plutôt que null. Cela évite une erreur
    #       sur la suite du filtre.
    #     - | length : retourne le nombre d'éléments du tableau.
    #     - > 0 : ne garder que les modules ayant au moins une option Copt.
    #       Les modules sans options compilées (stubs assembleur, etc.) sont exclus.
    #
    #   ($csect.Copt | sort | join(";"))
    #     Traitement de la liste des options :
    #     - sort : trie les éléments du tableau dans l'ordre lexicographique
    #       (alphabétique). Résultat stable et reproductible quel que soit
    #       l'ordre original dans le JSON.
    #     - join(";") : concatène tous les éléments avec ; comme séparateur.
    #       Exemple : ["RENT","NOOPT","OPT(FULL)"] → "NOOPT;OPT(FULL);RENT"
    #       Chaque option devient ainsi sa propre colonne CSV.
    jq -r --arg min_date "$MIN_LINKEDIT_DATE" '
        .[]
        | .Loadlib as $lib
        | .Loadmods[] as $lm
        | select($min_date == "" or ($lm.Linkedon >= $min_date))
        | $lm.CSECTs[] as $csect
        | select($lm.Name == $csect.Name)
        | select((($csect.Copt // []) | length) > 0)
        | "\($lib);"
        +"\($lm.Name);"
        +"\($lm.Linkedon);"
        +"\($csect.Compiler1);"
        +($csect.Copt | sort | join(";"))
    ' "$INPUT_JSON" > "$OUTPUT"

    [ -n "$MIN_LINKEDIT_DATE" ] && echo "Date filter: >= $MIN_LINKEDIT_DATE"
    echo "Options mode: compilation options collected per load and loadlib."
    echo "Output file: $OUTPUT created."
}


# =============================================================================
# run_compiler_mode — extrait le compilateur utilisé par module/loadlib
# =============================================================================
# Format de sortie (une ligne par module, CSECT principal uniquement) :
#   loadlib;load_name;linkedon;csect_name;compiler
# =============================================================================
run_compiler_mode() {
    # select($lm.Name == $csect.Name) : même filtre que dans run_options_mode.
    # Ne retient que le CSECT dont le nom est identique à celui du module
    # (le CSECT principal). Les stubs DB2, CICS et autres CSECTs secondaires
    # ont des noms différents et sont ainsi exclus.
    jq -r --arg min_date "$MIN_LINKEDIT_DATE" '
        .[]
        | .Loadlib as $lib
        | .Loadmods[] as $lm
        | select($min_date == "" or ($lm.Linkedon >= $min_date))
        | $lm.CSECTs[] as $csect
        | select($lm.Name == $csect.Name)
        | "\($lib);"
        +"\($lm.Name);"
        +"\($lm.Linkedon);"
        +"\($csect.Name);"
        +"\($csect.Compiler1)"
    ' "$INPUT_JSON" > "$OUTPUT"

    [ -n "$MIN_LINKEDIT_DATE" ] && echo "Date filter: >= $MIN_LINKEDIT_DATE"
    echo "Compiler mode: compilers collected (primary CSECT only)."
    echo "Output file: $OUTPUT created."
}


# =============================================================================
# dispatch_mode — aiguille vers la fonction de traitement selon le mode choisi
# =============================================================================
dispatch_mode() {
    # Ce case joue le rôle de table de dispatch : il mappe chaque valeur
    # possible de MODE vers la fonction correspondante. Centraliser ce choix
    # dans une fonction dédiée évite de disperser la logique conditionnelle
    # dans main() et facilite l'ajout d'un nouveau mode à l'avenir.
    case "$MODE" in
        global)
            run_global_mode
            ;;
        options)
            run_options_mode
            ;;
        compiler)
            run_compiler_mode
            ;;
        *)
            # Cette branche ne devrait jamais être atteinte en utilisation
            # normale : parse_args ne positionne MODE qu'à des valeurs connues.
            # Elle constitue un filet de sécurité en cas de bug interne.
            echo "Error: unsupported mode '$MODE'." >&2
            exit 1
            ;;
    esac
}


# =============================================================================
# main — point d'entrée et orchestrateur du script
# =============================================================================
main() {
    # main() orchestre l'exécution dans un ordre précis et immuable :
    # 1. parse_args  : décoder les options de la ligne de commande.
    # 2. resolve_paths_from_env : préfixer les chemins relatifs si VLM_DATA_DIR
    #                 est défini (après parse_args pour que les chemins fournis
    #                 par l'utilisateur soient déjà connus).
    # 3. validate_inputs : vérifier que les prérequis sont satisfaits (fichier
    #                 d'entrée existant, répertoire de sortie accessible, jq
    #                 disponible). Cette étape doit être effectuée APRÈS la
    #                 résolution des chemins.
    # 4. prepare_output_file : supprimer l'éventuel fichier de sortie existant
    #                 pour repartir d'un fichier vide.
    # 5. dispatch_mode : lancer la fonction de traitement correspondant au mode.
    parse_args "$@"
    resolve_paths_from_env
    validate_inputs
    prepare_output_file
    dispatch_mode
}

# Appel de main avec tous les arguments du script.
# "$@" préserve chaque argument comme une unité distincte, même s'il contient
# des espaces internes (ex. un nom de fichier avec un espace).
# Sans guillemets (juste $@), les espaces casseraient les arguments en plusieurs
# morceaux, causant des bugs difficiles à diagnostiquer.
main "$@"
