# Guide jq

> `jq` est l'outil en ligne de commande utilisé par `export_csv.sh` pour
> interroger le fichier JSON VLM. Ce guide explique ses concepts depuis zéro,
> en utilisant les données VLM comme support d'exemples.

---

## 1. Qu'est-ce que JSON ?

JSON est un format de fichier texte pour stocker des données structurées.

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

### 1.1 Des tableaux dans des tableaux

C'est le point le plus important à comprendre avant de lire la suite : dans
le fichier `vlm.json`, **un tableau peut contenir des objets qui contiennent
eux-mêmes un tableau**, et ainsi de suite sur plusieurs niveaux. L'extrait
ci-dessus contient **quatre tableaux imbriqués** :

| Niveau | Clé / position    | Type      | Contenu                                  |
|--------|-------------------|-----------|---------------------------------------------|
| 1      | racine `[ ... ]`  | tableau   | une entrée par **Loadlib**                 |
| 2      | `"Loadmods"`      | tableau   | une entrée par **Loadmod** (module)        |
| 3      | `"CSECTs"`        | tableau   | une entrée par **CSECT** (section compilée)|
| 4      | `"Copt"`          | tableau   | une chaîne par **option de compilation**   |

Entre chaque tableau se trouve un **objet** (`{ ... }`) qui porte les
métadonnées de ce niveau (`Loadlib`, `Name`, `Compiler1`, etc.) **et** la clé
qui contient le tableau du niveau suivant. C'est cette alternance
`tableau → objet → tableau → objet → ...` qui explique pourquoi, plus loin
dans ce guide, on enchaîne plusieurs `.[]` à la suite (un par niveau de
tableau à traverser).

---

## 2. Qu'est-ce que `jq` ?

`jq` est un outil en ligne de commande qui lit un fichier JSON et le transforme
selon un **filtre** — un petit programme écrit entre apostrophes `'...'`.

**Analogie :** `jq` est à JSON ce que `grep` ou `awk` est au texte brut.

**Syntaxe de base :**

```bash
jq 'FILTRE' fichier.json
```

---

## 3. Premier contact

**Afficher le fichier entier (formaté et coloré) :**

```bash
jq '.' datas/vlm.json
```

Le filtre `.` (un simple point) signifie "retourne la valeur courante telle quelle".

Sans `jq`, le JSON est stocké sur une seule ligne illisible.
`jq '.'` le formate proprement avec indentation et couleurs.

---

## 4. L'option `-r` (raw output)

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
`export_csv.sh` utilise toujours `-r`.

---

## 5. Accéder à un champ : `.nomDuChamp`

`.nomDuChamp` lit la valeur associée à une clé dans un objet.

```bash
jq -r '.[0].Loadlib' datas/vlm.json
# → MY.LOAD.LIB

jq -r '.[0].Loadmods[0].Name' datas/vlm.json
# → MYPGM
```

Si le champ n'existe pas, `jq` retourne `null`.

---

## 6. Parcourir un tableau : `.[]`

`.[]` itère sur **chaque élément** d'un tableau et produit un résultat par élément.

```bash
# Nom de toutes les loadlibs
jq -r '.[].Loadlib' datas/vlm.json
```

Ici, `.[]` parcourt le tableau racine (niveau 1) et `.Loadlib` lit un champ
de chaque objet Loadlib obtenu — un seul niveau de tableau est traversé.

### 6.1 Traverser un deuxième niveau de tableau

Pour lister les modules, il faut descendre d'un niveau supplémentaire :
`Loadmods` est **lui-même un tableau** (niveau 2, voir §1.1), donc `.[]` seul
ne suffit pas.

```bash
# .[] entre dans le tableau racine, .Loadmods accède au champ
jq '.[].Loadmods' datas/vlm.json
# → renvoie un tableau de Loadmods par Loadlib, ex. [ {...}, {...} ]
#   (toujours un tableau, pas encore un module individuel)
```

Il faut un **second `.[]`** pour entrer dans ce tableau et obtenir un Loadmod
à la fois :

```bash
# Noms de tous les modules (toutes loadlibs confondues)
jq -r '.[].Loadmods[].Name' datas/vlm.json
```

**Règle pratique :** chaque `[]` correspond à un niveau de tableau du §1.1.
Pour atteindre `Copt` (niveau 4), il faudrait donc trois `.[]` :
`.[].Loadmods[].CSECTs[].Copt`.

---

## 7. Le pipe `|`

Le `|` passe le résultat de gauche vers le filtre de droite — même concept
que le pipe Unix `|` dans un terminal.

```bash
# Ces deux commandes donnent le même résultat
jq -r '.[].Loadlib' datas/vlm.json
jq -r '.[] | .Loadlib' datas/vlm.json
```

**Analogie Python / jq :**

```python
# Python
for lib in data:               # .[]
    for lm in lib["Loadmods"]: # | .Loadmods[]
        print(lm["Name"])      # | .Name
```

```bash
# jq équivalent
jq -r '.[] | .Loadmods[] | .Name' datas/vlm.json
```

---

## 8. Filtrer avec `select(condition)`

`select(condition)` ne laisse passer que les éléments qui satisfont la condition.

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

**Opérateurs logiques :**

| Opérateur | Signification | Exemple |
|---|---|---|
| `and` | Les deux conditions sont vraies | `select(.CICS == true and .DB2 == true)` |
| `or` | Au moins une condition est vraie | `select(.CICS == true or .WMQ == true)` |

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

## 9. Stocker une valeur : `expression as $variable`

Quand on descend dans la hiérarchie, le "contexte courant" change.
Après `.Loadmods[]`, on est dans un module : la loadlib n'est plus accessible
directement. `expression as $variable` sauvegarde une valeur pour la réutiliser.

```bash
jq -r '
  .[]
  | .Loadlib as $lib        # on sauvegarde la loadlib
  | .Loadmods[] as $lm      # on descend dans les modules
  | "\($lib) — \($lm.Name)" # $lib est encore accessible ici
' datas/vlm.json
# → MY.LOAD.LIB — MYPGM
```

---

## 10. Valeur par défaut si absent : `expression // valeur`

Si un champ n'existe pas, `jq` retourne `null`. L'opérateur `//` fournit
une valeur de remplacement.

```bash
jq -r '.[0].Loadmods[0].CSECTs[0] | (.Identify // "")' datas/vlm.json
# → DY012345678  si présent
# → ""           si absent ou null
```

**Analogie Python :**

```python
value = csect.get("Identify") or ""
```

Sans `// ""`, le mot `null` apparaîtrait littéralement dans le CSV.

---

## 11. Trier un tableau : `sort`

```bash
jq '.[0].Loadmods[0].CSECTs[0].Copt | sort' datas/vlm.json
# → ["NOOPT", "RENT", "RMODE(ANY)"]
```

Le tri est alphabétique, stable et reproductible.

---

## 12. Assembler un tableau en chaîne : `join(séparateur)`

```bash
jq -r '.[0].Loadmods[0].CSECTs[0].Copt | sort | join(";")' datas/vlm.json
# → NOOPT;RENT;RMODE(ANY)
```

En combinant `sort` et `join(";")`, chaque option devient une colonne CSV.

---

## 13. Compter les éléments : `length`

```bash
jq '.[0].Loadmods[0].CSECTs[0].Copt | length' datas/vlm.json
# → 3
```

Dans ce script, `length > 0` filtre les modules sans option de compilation.
Décomposé étape par étape :

| Étape | Expression | Résultat si Copt = `["RENT","NOOPT"]` | Résultat si Copt absent |
|---|---|---|---|
| 1 | `$csect.Copt // []` | `["RENT","NOOPT"]` | `[]` |
| 2 | `\| length` | `2` | `0` |
| 3 | `> 0` | `true` → conservé | `false` → ignoré |

---

## 14. Interpolation de chaîne : `"\(expression)"`

Dans une chaîne jq, `\(expression)` insère la valeur d'une expression.
C'est l'équivalent des f-strings Python : `f"{variable}"`.

```bash
jq -r '.[] | "\(.Loadlib);\(.MemberCount)"' datas/vlm.json
# → MY.LOAD.LIB;2
```

---

## 15. Injecter une variable shell : `--arg nom valeur`

Il ne faut **pas** insérer directement une variable shell dans un filtre jq.

```bash
# ← DANGEREUX : si $date contient des " ou des \, le filtre est cassé
jq ".[] | select(.Linkedon >= \"$date\")" datas/vlm.json
```

**Méthode sûre : `--arg nom valeur`**

```bash
jq --arg min_date "$date" \
   '.[] | select(.Linkedon >= $min_date)' \
   datas/vlm.json
```

`--arg min_date "$date"` crée une variable jq `$min_date`.
La valeur est transmise proprement — équivalent des paramètres préparés en SQL.

---

## 16. Récapitulatif des opérateurs

| Opérateur | Exemple | Signification |
|---|---|---|
| `.` | `.` | Valeur courante |
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

## 17. Pour aller plus loin

Ce guide couvre les concepts jq de base, indépendamment de tout script.

Pour voir comment ces concepts s'assemblent dans les filtres réels utilisés
par `export_csv.sh` (modes `-g`, `-p`, `-c`), consultez la page dédiée :

**→ [Décryptage des filtres](filtres.md)**
