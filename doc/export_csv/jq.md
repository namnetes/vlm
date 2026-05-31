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

# Noms de tous les modules (toutes loadlibs confondues)
jq -r '.[].Loadmods[].Name' datas/vlm.json
```

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

## 17. Mise en pratique — décryptage du filtre du mode global

Voici le filtre jq complet utilisé par `export_csv.sh` en mode global (`-g`),
commenté ligne par ligne :

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
Mais `$lib` a été sauvegardé avant de descendre — il reste accessible.
