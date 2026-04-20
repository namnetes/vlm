# Guide — `export_csv.sh`

> **Rôle :** lire le fichier JSON produit par `build_json.py` et extraire
> des données vers un fichier CSV (délimiteur `;`).

---

## Sommaire

1. [Rôle du script](#1-rôle-du-script)
2. [Prérequis](#2-prérequis)
3. [Utilisation rapide](#3-utilisation-rapide)
4. [Les trois modes d'extraction](#4-les-trois-modes-dextraction)
5. [Filtre de date](#5-filtre-de-date)
6. [Variable d'environnement VLM_DATA_DIR](#6-variable-denvironnement-vlm_data_dir)
7. [Format des fichiers de sortie](#7-format-des-fichiers-de-sortie)
8. [jq — Guide complet pour débutants](#8-jq--guide-complet-pour-débutants)
9. [Codes de sortie et dépannage](#9-codes-de-sortie-et-dépannage)

---

## 1. Rôle du script

`export_csv.sh` lit le fichier JSON produit par `build_json.py`.

Il extrait des données et les écrit dans un fichier CSV.

Le délimiteur CSV est le point-virgule (`;`).

Trois modes d'extraction sont disponibles :

| Mode | Option | Contenu |
|---|---|---|
| Global | `-g` | Une ligne par CSECT avec toutes ses métadonnées |
| Options | `-p` | Une ligne par module avec ses options de compilation |
| Compilateur | `-c` | Une ligne par module avec son compilateur |

---

## 2. Prérequis

Le script nécessite deux outils :

| Outil | Rôle | Vérification |
|---|---|---|
| `jq` | Interroger le fichier JSON | `jq --version` |
| `awk` | Traitement de texte | `awk --version` |

`awk` est présent par défaut sur tous les systèmes Linux et macOS.

`jq` doit être installé manuellement.

**Installer jq sur Ubuntu / Debian :**

```bash
sudo apt update && sudo apt install -y jq
```

**Vérifier l'installation :**

```bash
jq --version
# → jq-1.7.1  (ou version supérieure)
```

---

## 3. Utilisation rapide

### 3.1 Syntaxe

```bash
bash script/export_csv.sh -i FICHIER_JSON -o FICHIER_CSV MODE [OPTIONS]
```

### 3.2 Exemples

```bash
# Mode global : toutes les métadonnées de chaque CSECT
bash script/export_csv.sh \
    -i datas/vlm.json -o datas/export_global.csv -g

# Mode options : les options de compilation par module
bash script/export_csv.sh \
    -i datas/vlm.json -o datas/export_options.csv -p

# Mode compilateur : le compilateur utilisé par module
bash script/export_csv.sh \
    -i datas/vlm.json -o datas/export_compilers.csv -c

# Avec filtre de date : modules liés à partir du 01/01/2025 uniquement
bash script/export_csv.sh \
    -i datas/vlm.json -o datas/export.csv -g -d 2025/01/01

# Afficher l'aide
bash script/export_csv.sh --help
```

### 3.3 Options disponibles

| Option | Forme longue | Valeur | Description |
|---|---|---|---|
| `-i` | `--input` | fichier | Fichier JSON d'entrée (défaut : `vlm.json`) |
| `-o` | `--output` | fichier | Fichier CSV de sortie (défaut : `query_output.csv`) |
| `-g` | `--global` | — | Mode global |
| `-p` | `--options` | — | Mode options de compilation |
| `-c` | `--compiler` | — | Mode compilateur |
| `-d` | `--date` | `yyyy/mm/dd` | Ne garder que les modules liés à partir de cette date |
| `-h` | `--help` | — | Afficher l'aide |

---

## 4. Les trois modes d'extraction

### 4.1 Mode global (`-g`)

Ce mode extrait **toutes les métadonnées** de chaque CSECT.

Une ligne est produite par CSECT.

**Colonnes de sortie :**

| N° | Nom | Exemple | Description |
|---|---|---|---|
| 1 | `loadlib` | `MY.LOAD.LIB` | PDS contenant des Load Modules |
| 2 | `load_name` | `MYPGM` | Module exécutable (Load Module) |
| 3 | `linkedon` | `2025/06/01` | Date de link-edit |
| 4 | `csect_name` | `MYPGM` | Nom de la section compilée |
| 5 | `compiler` | `Enterpr.COBOL for z/OS V6R3` | Compilateur utilisé |
| 6 | `ThreadSafe` | `ThreadSafe=false` | Module thread-safe ? |
| 7 | `CICS` | `CICS=false` | Utilise CICS ? |
| 8 | `DB2` | `DB2=false` | Utilise DB2 ? |
| 9 | `WMQ` | `WMQ=false` | Utilise WebSphere MQ ? |
| 10 | `identify` | `DY012345678` | Identifiant de package (vide si absent) |

**Exemple de sortie :**

```
MY.LOAD.LIB;MYPGM;2025/06/01;MYPGM;Enterpr.COBOL for z/OS V6R3;ThreadSafe=false;CICS=false;DB2=false;WMQ=false;DY012345678
```

---

### 4.2 Mode options (`-p`)

Ce mode extrait les **options de compilation** de chaque module.

Seul le **CSECT principal** est retenu.

!!! note "CSECT principal"
    Le CSECT principal est celui dont le nom est identique au nom du module.
    En IBM COBOL, c'est le programme lui-même.
    Les stubs DB2 (`DSNCLI`), CICS (`DFHECI`) et autres sont exclus.

Les options sont triées par ordre alphabétique.

Chaque option occupe sa propre colonne dans le CSV.

**Colonnes de sortie :**

| N° | Nom | Exemple | Description |
|---|---|---|---|
| 1 | `loadlib` | `MY.LOAD.LIB` | PDS contenant des Load Modules |
| 2 | `load_name` | `MYPGM` | Module exécutable (Load Module) |
| 3 | `linkedon` | `2025/06/01` | Date de link-edit |
| 4 | `compiler` | `Enterpr.COBOL for z/OS V6R3` | Compilateur |
| 5+ | options | `NOOPT;RENT;...` | Une option par colonne, triées alphabétiquement |

**Exemple de sortie :**

```
MY.LOAD.LIB;MYPGM;2025/06/01;Enterpr.COBOL for z/OS V6R3;NOOPT;RENT;RMODE(ANY)
```

---

### 4.3 Mode compilateur (`-c`)

Ce mode extrait le **compilateur utilisé** par chaque module.

Seul le **CSECT principal** est retenu (même règle que le mode options).

**Colonnes de sortie :**

| N° | Nom | Exemple | Description |
|---|---|---|---|
| 1 | `loadlib` | `MY.LOAD.LIB` | PDS contenant des Load Modules |
| 2 | `load_name` | `MYPGM` | Module exécutable (Load Module) |
| 3 | `linkedon` | `2025/06/01` | Date de link-edit |
| 4 | `csect_name` | `MYPGM` | Nom du CSECT principal |
| 5 | `compiler` | `Enterpr.COBOL for z/OS V6R3` | Compilateur utilisé |

**Exemple de sortie :**

```
MY.LOAD.LIB;MYPGM;2025/06/01;MYPGM;Enterpr.COBOL for z/OS V6R3
```

---

## 5. Filtre de date

L'option `-d yyyy/mm/dd` retient **uniquement** les modules dont la date de
link-edit (`Linkedon`) est **supérieure ou égale** à la date indiquée.

```bash
# Modules liés à partir du 1er janvier 2025
bash script/export_csv.sh \
    -i datas/vlm.json -o datas/export.csv -g -d 2025/01/01
```

**Format obligatoire :** `yyyy/mm/dd`

| Exemple | Valide ? |
|---|---|
| `2025/01/01` | ✓ |
| `2024/12/31` | ✓ |
| `01/01/2025` | ✗ jour et année inversés |
| `2025-01-01` | ✗ tirets non acceptés |
| `2025/1/1` | ✗ mois et jour sur 1 chiffre |

!!! info "Pourquoi la comparaison alphabétique fonctionne pour les dates ?"
    Les dates sont au format `aaaa/mm/jj`.
    L'année est en premier, puis le mois, puis le jour.
    Ce format permet un tri alphabétique équivalent au tri chronologique.
    Exemple : `"2025/06/01" > "2025/01/15"` est vrai dans les deux cas.

---

## 6. Variable d'environnement `VLM_DATA_DIR`

Si la variable `VLM_DATA_DIR` est définie, les chemins relatifs sont
automatiquement préfixés par cette valeur.

```bash
# Définir le répertoire de base
export VLM_DATA_DIR=/home/user/vlm/datas

# Ces deux commandes sont alors équivalentes
bash script/export_csv.sh -i vlm.json -o output.csv -g
bash script/export_csv.sh \
    -i /home/user/vlm/datas/vlm.json \
    -o /home/user/vlm/datas/output.csv -g
```

Les chemins absolus (commençant par `/`) ne sont pas modifiés.

---

## 7. Format des fichiers de sortie

- **Encodage :** UTF-8
- **Délimiteur :** `;` (point-virgule)
- **Sans en-tête :** la première ligne contient déjà des données

**Ouvrir dans LibreOffice Calc :**

1. Menu Fichier → Ouvrir → sélectionner le fichier `.csv`
2. Choisir `;` comme séparateur de colonnes
3. Choisir l'encodage `UTF-8`

**Ouvrir dans Microsoft Excel :**

1. Onglet Données → Depuis un fichier texte/CSV
2. Choisir `;` comme délimiteur
3. Choisir l'encodage `65001 : Unicode (UTF-8)`

---

## 8. `jq` — Guide complet pour débutants

Cette section explique `jq` depuis zéro.

Elle utilise le fichier JSON VLM comme support tout au long des exemples.

### 8.1 Qu'est-ce que JSON ?

JSON est un format de fichier texte.

Il stocke des données structurées avec des clés et des valeurs.

Voici un extrait simplifié du fichier JSON utilisé par ce script :

```json
[
  {
    "Loadlib": "MY.LOAD.LIB",
    "MemberCount": 2,
    "Loadmods": [
      {
        "Name": "MYPGM",
        "Linkedon": "2025/06/01",
        "CSECTs": [
          {
            "Name": "MYPGM",
            "Compiler1": "Enterpr.COBOL for z/OS V6R3",
            "ThreadSafe": false,
            "CICS": false,
            "DB2": false,
            "WMQ": false,
            "Identify": "DY012345678",
            "Copt": ["RENT", "NOOPT", "RMODE(ANY)"]
          }
        ]
      }
    ]
  }
]
```

Les accolades `{}` contiennent un **objet** (ensemble de clés/valeurs).

Les crochets `[]` contiennent un **tableau** (liste ordonnée d'éléments).

On peut imbriquer des objets dans des objets et des tableaux dans des tableaux.

---

### 8.2 Qu'est-ce que `jq` ?

`jq` est un outil en ligne de commande.

Il lit un fichier JSON et le transforme selon un **filtre**.

Un filtre est un programme jq. Il est écrit entre apostrophes `'...'`.

**Analogie :** `jq` est à JSON ce que `grep` ou `awk` est au texte brut.

**Syntaxe de base :**

```bash
jq 'FILTRE' fichier.json
```

---

### 8.3 Premier contact

**Afficher le fichier entier (formaté et coloré) :**

```bash
jq '.' datas/vlm.json
```

Le filtre `.` (un simple point) signifie "retourne la valeur courante telle quelle".

Sans `jq`, le JSON est stocké sur une seule ligne illisible.

`jq '.'` le formate proprement avec indentation et couleurs.

---

### 8.4 L'option `-r` (raw output)

Par défaut, `jq` affiche les chaînes de caractères **avec des guillemets** :

```bash
jq '.[0].Loadlib' datas/vlm.json
# → "MY.LOAD.LIB"   ← les guillemets sont là
```

Avec l'option `-r`, les guillemets sont supprimés :

```bash
jq -r '.[0].Loadlib' datas/vlm.json
# → MY.LOAD.LIB     ← sans guillemets
```

Dans un fichier CSV, on ne veut pas de guillemets dans les valeurs.

Ce script utilise toujours `-r`.

---

### 8.5 Accéder à un champ : `.nomDuChamp`

`.nomDuChamp` lit la valeur associée à une clé dans un objet.

```bash
# Loadlib du premier élément du tableau
jq -r '.[0].Loadlib' datas/vlm.json
# → MY.LOAD.LIB

# Nombre de membres du premier élément
jq '.[0].MemberCount' datas/vlm.json
# → 2
```

On peut enchaîner les accès pour descendre dans la hiérarchie :

```bash
# Nom du premier module de la première loadlib
jq -r '.[0].Loadmods[0].Name' datas/vlm.json
# → MYPGM
```

Si le champ n'existe pas, `jq` retourne `null`.

---

### 8.6 Parcourir un tableau : `.[]`

`.[]` itère sur **chaque élément** d'un tableau.

`jq` produit un résultat par élément.

```bash
# Nom de toutes les loadlibs
jq -r '.[].Loadlib' datas/vlm.json
# → MY.LOAD.LIB
#    OTHER.LIB
#    ...
```

On peut enchaîner les itérations pour descendre dans plusieurs niveaux :

```bash
# Noms de tous les modules (toutes loadlibs confondues)
jq -r '.[].Loadmods[].Name' datas/vlm.json
```

---

### 8.7 Le pipe `|`

Le `|` (pipe jq) passe le résultat de gauche vers le filtre de droite.

C'est le même concept que le pipe Unix `|` dans un terminal.

```bash
# Ces deux commandes donnent le même résultat
jq -r '.[].Loadlib' datas/vlm.json
jq -r '.[] | .Loadlib' datas/vlm.json
```

Le pipe est utile pour les filtres complexes car il améliore la lisibilité.

**Analogie Python :**

```python
for lib in data:                    # .[]
    for lm in lib["Loadmods"]:      # | .Loadmods[]
        print(lm["Name"])           # | .Name
```

**Équivalent jq :**

```bash
jq -r '.[] | .Loadmods[] | .Name' datas/vlm.json
```

---

### 8.8 Filtrer avec `select(condition)`

`select(condition)` ne laisse passer que les éléments qui satisfont la condition.

Les autres sont silencieusement ignorés.

```bash
# Modules liés à partir du 2025/01/01
jq -r '.[] | .Loadmods[] | select(.Linkedon >= "2025/01/01") | .Name' \
   datas/vlm.json
```

**Opérateurs de comparaison :**

| Opérateur | Signification | Exemple |
|---|---|---|
| `==` | Égal à | `select(.Name == "MYPGM")` |
| `!=` | Différent de | `select(.Name != "CEEUOPT")` |
| `>=` | Supérieur ou égal | `select(.Linkedon >= "2025/01/01")` |
| `>` | Strictement supérieur | `select(.MemberCount > 0)` |
| `<=` | Inférieur ou égal | `select(.MemberCount <= 10)` |
| `<` | Strictement inférieur | `select(.MemberCount < 5)` |

**Opérateurs logiques :**

| Opérateur | Signification | Exemple |
|---|---|---|
| `and` | Les deux conditions sont vraies | `select(.CICS == true and .DB2 == true)` |
| `or` | Au moins une condition est vraie | `select(.CICS == true or .WMQ == true)` |
| `not` | Inverse la condition | `select(.ThreadSafe == true \| not)` |

**Exemple :** modules CICS liés après 2025/01/01 :

```bash
jq -r '
  .[] | .Loadmods[] as $lm
  | $lm.CSECTs[]
  | select($lm.Linkedon >= "2025/01/01" and .CICS == true)
  | .Name
' datas/vlm.json
```

---

### 8.9 Stocker une valeur : `expression as $variable`

Quand on itère dans un tableau, le "contexte courant" change.

Après `.Loadmods[]`, on est dans un module. La loadlib n'est plus accessible directement.

`expression as $variable` sauvegarde une valeur pour la réutiliser plus tard.

Les variables jq commencent toujours par `$`.

```bash
jq -r '
  .[]
  | .Loadlib as $lib        # on sauvegarde la loadlib
  | .Loadmods[] as $lm      # on descend dans les modules
  | "\($lib) — \($lm.Name)" # on peut encore utiliser $lib ici
' datas/vlm.json
# → MY.LOAD.LIB — MYPGM
#    MY.LOAD.LIB — OTHERPGM
#    ...
```

Sans `as $lib`, la valeur de `Loadlib` serait perdue dès qu'on entre dans `.Loadmods[]`.

La variable reste disponible à tous les niveaux d'imbrication qui suivent sa déclaration.

---

### 8.10 Valeur par défaut si absent : `expression // valeur`

En JSON, `null` signifie "absent" ou "pas de valeur".

Si un champ n'existe pas dans un objet, jq retourne `null`.

L'opérateur `//` fournit une valeur de remplacement si l'expression est `null`.

```bash
# Si Identify est null ou absent → afficher "" à la place
jq -r '.[0].Loadmods[0].CSECTs[0] | (.Identify // "")' datas/vlm.json
# → DY012345678  si présent
# → ""           si absent ou null
```

**Analogie Python :**

```python
value = csect.get("Identify") or ""
```

Dans ce script, `// ""` est utilisé pour le champ `Identify`.

Ce champ n'est pas toujours présent dans le JSON.

Sans `// ""`, le mot `null` apparaîtrait littéralement dans le CSV.

---

### 8.11 Trier un tableau : `sort`

`sort` trie les éléments d'un tableau dans l'ordre alphabétique.

```bash
# Options de compilation, triées
jq '.[0].Loadmods[0].CSECTs[0].Copt | sort' datas/vlm.json
# → ["NOOPT", "RENT", "RMODE(ANY)"]
```

Le tri est stable et reproductible. Le résultat est identique à chaque exécution.

---

### 8.12 Assembler un tableau en chaîne : `join(séparateur)`

`join(sep)` concatène tous les éléments d'un tableau avec un séparateur.

```bash
jq -r '.[0].Loadmods[0].CSECTs[0].Copt | sort | join(";")' datas/vlm.json
# → NOOPT;RENT;RMODE(ANY)
```

En combinant `sort` et `join(";")`, chaque option devient une colonne CSV.

---

### 8.13 Compter les éléments : `length`

`length` retourne le nombre d'éléments d'un tableau.

```bash
jq '.[0].Loadmods[0].CSECTs[0].Copt | length' datas/vlm.json
# → 3
```

Dans ce script, `length > 0` filtre les modules sans option de compilation.

Explication du filtre complet utilisé dans le script :

```jq
select((($csect.Copt // []) | length) > 0)
```

Décomposé étape par étape :

| Étape | Expression | Résultat si Copt = `["RENT","NOOPT"]` | Résultat si Copt absent |
|---|---|---|---|
| 1 | `$csect.Copt // []` | `["RENT","NOOPT"]` | `[]` |
| 2 | `\| length` | `2` | `0` |
| 3 | `> 0` | `true` → élément conservé | `false` → élément ignoré |

---

### 8.14 Interpolation de chaîne : `"\(expression)"`

Dans une chaîne jq, `\(expression)` insère la valeur d'une expression.

C'est l'équivalent des f-strings de Python : `f"{variable}"`.

```bash
jq -r '.[] | "Loadlib: \(.Loadlib), membres: \(.MemberCount)"' datas/vlm.json
# → Loadlib: MY.LOAD.LIB, membres: 2
```

Plusieurs expressions peuvent être concaténées avec `+` :

```bash
jq -r '.[] | "\(.Loadlib);" + "\(.MemberCount)"' datas/vlm.json
# → MY.LOAD.LIB;2
```

---

### 8.15 Injecter une variable shell : `--arg nom valeur`

Il ne faut **pas** insérer directement une variable shell dans un filtre jq.

**Méthode dangereuse — à ne jamais faire :**

```bash
date="2025/01/01"
# ← risqué : si $date contient des " ou des \, le filtre est cassé
jq ".[] | select(.Linkedon >= \"$date\")" datas/vlm.json
```

**Méthode sûre : `--arg nom valeur`**

```bash
date="2025/01/01"
jq --arg min_date "$date" \
   '.[] | select(.Linkedon >= $min_date)' \
   datas/vlm.json
```

`--arg min_date "$date"` crée une variable jq `$min_date`.

La valeur est transmise proprement, sans être interprétée comme du code jq.

C'est l'équivalent des paramètres préparés en SQL pour éviter les injections.

---

### 8.16 Récapitulatif des opérateurs jq

| Opérateur | Exemple | Signification |
|---|---|---|
| `.` | `.` | Valeur courante (retourne tout) |
| `.champ` | `.Loadlib` | Accès à un champ d'objet |
| `.[]` | `.Loadmods[]` | Itère sur chaque élément d'un tableau |
| `\|` | `.[] \| .Name` | Passe le résultat au filtre suivant |
| `select(c)` | `select(.Linkedon >= "2025/01/01")` | Filtre : garde si condition vraie |
| `expr as $v` | `.Loadlib as $lib` | Sauvegarde une valeur dans une variable |
| `//` | `.Identify // ""` | Valeur par défaut si null ou absent |
| `sort` | `.Copt \| sort` | Trie un tableau alphabétiquement |
| `join(s)` | `.Copt \| join(";")` | Concatène un tableau avec un séparateur |
| `length` | `.Copt \| length` | Nombre d'éléments d'un tableau |
| `\(expr)` | `"\(.Name);"` | Insère une valeur dans une chaîne |
| `--arg n v` | `--arg d "$DATE"` | Injecte une variable shell dans jq |

---

### 8.17 Décryptage du filtre du mode global

Voici le filtre jq complet du mode global, commenté ligne par ligne :

```jq
.[]
| .Loadlib as $lib
| .Loadmods[] as $lm
| select($min_date == "" or ($lm.Linkedon >= $min_date))
| $lm.CSECTs[] as $csect
| "\($lib);"
+ "\($lm.Name);"
+ "\($lm.Linkedon);"
+ "\($csect.Name);"
+ "\($csect.Compiler1);"
+ "ThreadSafe=\($csect.ThreadSafe);"
+ "CICS=\($csect.CICS);"
+ "DB2=\($csect.DB2);"
+ "WMQ=\($csect.WMQ);"
+ "\($csect.Identify // "")"
```

| Ligne | Ce que ça fait |
|---|---|
| `.[]` | Pour chaque loadlib dans le tableau racine |
| `\| .Loadlib as $lib` | Sauvegarder le nom de la loadlib dans `$lib` |
| `\| .Loadmods[] as $lm` | Pour chaque module, sauvegarder dans `$lm` |
| `\| select(...)` | Ignorer les modules trop anciens si `-d` est actif |
| `\| $lm.CSECTs[] as $csect` | Pour chaque CSECT, sauvegarder dans `$csect` |
| `\| "\($lib);"` | Commencer la ligne CSV avec la loadlib |
| `+ "\($lm.Name);"` | Ajouter le nom du module |
| `+ "\($lm.Linkedon);"` | Ajouter la date de link-edit |
| `+ "\($csect.Name);"` | Ajouter le nom du CSECT |
| `+ "\($csect.Compiler1);"` | Ajouter le compilateur |
| `+ "ThreadSafe=\(...)"` | Ajouter les indicateurs middleware |
| `+ "\($csect.Identify // "")"` | Ajouter l'identifiant (vide si absent) |

**Pourquoi `$lib` et pas `.Loadlib` à la fin ?**

À la ligne `| $lm.CSECTs[] as $csect`, le contexte courant est un CSECT.

`.Loadlib` ne correspond plus à rien dans un CSECT.

Mais `$lib` a été sauvegardé avant de descendre dans la hiérarchie. Il reste accessible.

---

## 9. Codes de sortie et dépannage

### 9.1 Codes de sortie

| Code | Signification |
|---|---|
| `0` | Succès — le fichier CSV a été produit |
| `1` | Erreur — argument invalide, prérequis manquant ou fichier introuvable |

### 9.2 Messages d'erreur courants

**`Error: input file 'vlm.json' not found.`**

Le fichier JSON n'existe pas au chemin indiqué.

```bash
# Vérifier que le fichier existe
ls -la datas/vlm.json

# Relancer avec le bon chemin
bash script/export_csv.sh -i datas/vlm.json -o datas/output.csv -g
```

---

**`Error: jq is not installed (or not in PATH).`**

`jq` n'est pas installé sur ce système.

```bash
sudo apt install -y jq
jq --version  # vérifier
```

---

**`Error: date format must be yyyy/mm/dd`**

La date est dans un format incorrect.

```bash
# Correct
bash script/export_csv.sh ... -d 2025/06/01

# Incorrect
bash script/export_csv.sh ... -d 01/06/2025   # ← ordre inversé
bash script/export_csv.sh ... -d 2025-06-01   # ← tirets non acceptés
```

---

**`Error: unknown option '-x'`**

L'option n'est pas reconnue.

```bash
bash script/export_csv.sh --help
```

---

**Le fichier CSV est vide**

Si aucune ligne ne correspond aux critères, le fichier est créé mais vide.

Avec un filtre de date `-d`, vérifiez que la date choisie n'est pas trop récente :

```bash
# Voir les dates présentes dans le JSON
jq -r '.[].Loadmods[].Linkedon' datas/vlm.json | sort -u
```
