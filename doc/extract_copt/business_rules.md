# Règles métier — `extract_copt.py`

> **Rôle du script :** lire le fichier JSON VLM produit par `build_json.py`,
> extraire les options de compilation (COPT) de chaque CSECT et produire deux
> types de sortie : un fichier CSV récapitulatif et un fichier texte détaillé
> par CSECT.

---

## Sommaire

1. [Contexte et glossaire](#1-contexte-et-glossaire)
2. [Vue d'ensemble du traitement](#2-vue-densemble-du-traitement)
3. [Format du fichier d'entrée](#3-format-du-fichier-dentrée)
4. [Format des fichiers de sortie](#4-format-des-fichiers-de-sortie)
5. [Règles d'extraction et de formatage](#5-règles-dextraction-et-de-formatage)
6. [Gestion des erreurs et codes de sortie](#6-gestion-des-erreurs-et-codes-de-sortie)
7. [Exemples concrets](#7-exemples-concrets)

---

## 1. Contexte et glossaire

| Terme        | Définition                                                                                                                       |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| **VLM**      | _View Load Module_ — fonction d'IBM File Manager permettant d'analyser le contenu des load modules d'une bibliothèque z/OS. Le fichier JSON produit par le pipeline à partir de cette sortie est l'entrée de ce script. |
| **Loadlib**  | PDS (_Partitioned Dataset_) contenant des Load Modules (modules exécutables). Ex. : `SYS1.LINKLIB`.                             |
| **Loadmod**  | Module exécutable contenu dans une loadlib.                                                                                      |
| **CSECT**    | _Control Section_ — sous-partie d'un programme COBOL compilé. Un loadmod peut contenir plusieurs CSECTs.                        |
| **COPT**     | _Compilation OPTions_ — liste des options passées au compilateur IBM COBOL 6.5 lors de la compilation d'un CSECT.               |
| **Préfixe**  | Indicateur `"1"` ou `"0"` placé en première colonne du CSV : `"1"` si le CSECT est le module principal (même nom), `"0"` sinon. |
| **CSV**      | Fichier texte à colonnes séparées par `;` — format exploitable par un tableur ou un script.                                     |
| **CSECT principal** | CSECT dont le nom est identique à celui du loadmod qui le contient. En IBM COBOL, c'est le programme lui-même.         |
| **CSECT secondaire** | CSECT dont le nom diffère du loadmod : stubs DB2 (`DSNCLI`, `DSNELI`), stub CICS (`DFHECI`), sous-programmes liés, etc. |

---

## 2. Vue d'ensemble du traitement

```
Lire les arguments (-f fichier_json, -o fichier_csv)
    │
    ▼
[1] Valider le fichier d'entrée (doit exister)
    │
    ▼
[2] Valider le fichier de sortie (ne doit PAS déjà exister)
    │
    ▼
[3] Valider le répertoire de sortie (doit exister et être inscriptible)
    │
    ▼
[4] Charger le JSON en mémoire
    │
    ▼
[5] Pour chaque Loadlib → Loadmod → CSECT :
    │   La CSECT a-t-elle des options COPT ?  ──► NON → Ignorer (passer à la suivante)
    │   OUI
    │   ├── Calculer le préfixe ("1" si CSECT principal, "0" sinon)
    │   ├── Écrire une ligne dans le CSV récapitulatif
    │   └── Créer le fichier texte détaillé pour ce CSECT
    ▼
[6] Afficher le bilan (nombre de CSECTs traités)
```

---

## 3. Format du fichier d'entrée

- **Type :** JSON produit par `build_json.py`.
- **Encodage :** UTF-8.
- **Structure :** tableau de Loadlibs. Chaque Loadlib contient une liste de
  Loadmods, chacun contenant une liste de CSECTs.

Fragment JSON d'entrée :

```json
[
  {
    "Loadlib": "MY.LOAD.LIB",
    "MemberCount": 3,
    "Loadmods": [
      {
        "Name": "MYPGM",
        "Linkedon": "2025/06/01",
        "CSECTs": [
          {
            "Name": "MYPGM",
            "Compiler1": "COBOL",
            "Copt": ["RENT", "NOOPT", "CSECT(CODE,ACCPRINT)"]
          },
          {
            "Name": "DFHECI",
            "Compiler1": "COBOL",
            "Copt": []
          },
          {
            "Name": "DSNCLIMYMOD",
            "Compiler1": "COBOL",
            "Copt": ["RENT", "OPT(FULL)"]
          }
        ]
      }
    ]
  }
]
```

> **Seuls les CSECTs dont le champ `Copt` est présent et non vide sont traités.**
> Dans l'exemple ci-dessus, `DFHECI` (liste vide) sera ignoré.

---

## 4. Format des fichiers de sortie

### 4.1 Fichier CSV récapitulatif

- **Encodage :** UTF-8, délimiteur `;`, une ligne par CSECT traité.
- **Pas d'en-tête** : la première ligne contient déjà des données.
- **Format de chaque ligne :**

```
<préfixe>;<loadlib>;<load_name>;<csect_name>;<compilateur>;<nb_options>
```

| Colonne      | Type   | Description                                                                 |
| ------------ | ------ | --------------------------------------------------------------------------- |
| `préfixe`    | `str`  | `"1"` si csect_name == load_name (CSECT principal), `"0"` sinon.           |
| `loadlib`    | `str`  | Nom de la bibliothèque de chargement (ex. `MY.LOAD.LIB`).                  |
| `load_name`  | `str`  | Nom du module de chargement (ex. `MYPGM`).                                  |
| `csect_name` | `str`  | Nom de la section compilée (ex. `MYPGM`, `DSNCLIMYMOD`).                   |
| `compilateur`| `str`  | Identifiant du compilateur (ex. `COBOL`).                                   |
| `nb_options` | `int`  | Nombre total d'options de compilation dans la liste `Copt`.                 |

### 4.2 Fichiers texte détaillés par CSECT

Pour chaque CSECT traité, un fichier texte est créé sous le chemin :

```
<répertoire_sortie>/loadlibs/<loadlib>/<load_name>_<csect_name>_<compiler_short>.txt
```

- **Encodage :** UTF-8.
- **Contenu :** une option de compilation par ligne.
- **Répertoires créés automatiquement** si absents (`mkdir -p`).
- `<compiler_short>` est le code abrégé du compilateur issu du dictionnaire
  `COMPILERS` (voir §5.6). Si le compilateur n'est pas reconnu, la valeur
  `unknown` est utilisée.

Exemple de chemin :
```
datas/copt/loadlibs/MY.LOAD.LIB/MYPGM_DSNCLIMYMOD_cbv63.txt
```

---

## 5. Règles d'extraction et de formatage

### 5.1 Filtrage des CSECTs sans options COPT

**Règle :** un CSECT est ignoré si son champ `Copt` est absent **ou** si la liste
est vide.

> **Pourquoi ?** Un loadmod peut contenir des dizaines de CSECTs (stubs système,
> modules liés statiquement) dont beaucoup n'ont pas été compilés avec COBOL ou
> dont les options ne sont pas disponibles. Les ignorer évite de polluer le CSV
> avec des lignes vides ou sans valeur métier.

```python
# src/extract_copt.py — dans iter_csect_copt()
copt = csect.get("Copt")
# `not copt` est True pour None (clé absente) ET pour [] (liste vide).
if not copt:
    continue
```

---

### 5.2 Calcul du préfixe

**Règle :** le préfixe vaut `"1"` si le nom du CSECT est exactement identique au
nom du loadmod qui le contient, `"0"` dans tous les autres cas.

> **Pourquoi ?** En IBM Enterprise COBOL, le programme principal porte le même
> nom que le module de chargement. Les CSECTs secondaires (stubs DB2, CICS,
> sous-programmes inclus à la link-edit) ont des noms différents. Ce préfixe
> permet de filtrer rapidement les lignes du programme principal dans un
> tableur, sans avoir à comparer les deux colonnes manuellement.

```python
# src/extract_copt.py — dans iter_csect_copt()
prefix = "1" if load_name == csect_name else "0"
```

Exemples :

| `load_name` | `csect_name`  | `préfixe` | Interprétation           |
| ----------- | ------------- | --------- | ------------------------ |
| `MYPGM`     | `MYPGM`       | `"1"`     | CSECT principal          |
| `MYPGM`     | `DFHECI`      | `"0"`     | Stub CICS                |
| `MYPGM`     | `DSNCLIMYMOD` | `"0"`     | Stub DB2                 |
| `MYPGM`     | `CEEUOPT`     | `"0"`     | Module options LE        |

---

### 5.3 Comptage des options dans le CSV

**Règle :** la dernière colonne du CSV contient le **nombre d'options** de la
liste `Copt`, pas les options elles-mêmes. Les options détaillées sont dans le
fichier texte individuel (§4.2).

> **Pourquoi séparer le récapitulatif du détail ?** Le CSV récapitulatif permet
> une analyse rapide en tableur (tri, filtre, pivot). Le fichier texte détaillé
> permet d'accéder aux options précises d'un CSECT particulier sans ouvrir un
> JSON volumineux.

```python
# src/extract_copt.py — dans write_csv()
f.write(
    f"{prefix};{loadlib};{load_name};"
    f"{csect_name};{compiler};{len(copt)}\n"
)
```

---

### 5.4 Création des fichiers texte détaillés

**Règle :** pour chaque CSECT traité, un fichier texte est créé avec une option
par ligne. Le chemin du fichier encode la loadlib, les noms de module/CSECT et
le code abrégé du compilateur pour permettre une recherche directe.

**Règle de nommage :** `<load_name>_<csect_name>_<compiler_short>.txt`

> **Pourquoi inclure `<compiler_short>` ?** Un même CSECT compilé avec deux
> versions différentes du compilateur (ex. migration `cbv42` → `cbv63`) aurait
> sinon le même nom de fichier. Le suffixe du compilateur garantit l'unicité.
>
> **Pourquoi `<load_name>_<csect_name>` ?** Plusieurs loadmods d'une même loadlib
> peuvent contenir un CSECT de même nom (ex. `CEEUOPT` est présent dans presque
> tous les modules COBOL). Le préfixe `<load_name>_` garantit l'unicité au sein
> d'un répertoire loadlib.

```python
# src/extract_copt.py — dans write_csv()
# Résolution du code abrégé depuis COMPILERS (COBOL, C/C++, PL/I).
compiler_short = COMPILERS.get(compiler, "unknown")
if compiler_short == "unknown":
    LOGGER.warning(
        "Compilateur inconnu pour %s/%s/%s", loadlib, load_name, csect_name
    )
# Chemin : <basedir>/loadlibs/<loadlib>/<load_name>_<csect_name>_<compiler_short>.txt
output_file = (
    basedir / "loadlibs" / loadlib
    / f"{load_name}_{csect_name}_{compiler_short}.txt"
)
generate_copt_file(output_file, copt)
```

```python
# src/extract_copt.py — generate_copt_file()
def generate_copt_file(output_file: Path, compiler_options: list[str]) -> None:
    # parents=True : crée tous les sous-répertoires manquants (mkdir -p).
    # exist_ok=True : ne lève pas d'erreur si le répertoire existe déjà.
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open(mode="w", encoding="utf-8") as f:
        for option in compiler_options:
            f.write(f"{option}\n")
```

---

### 5.5 Protection contre l'écrasement du fichier de sortie

**Règle :** si le fichier CSV de sortie existe déjà, le script **s'arrête
immédiatement** avec le code `2` sans écrire quoi que ce soit.

> **Pourquoi ?** Cette protection évite d'écraser accidentellement un fichier
> de résultats produit lors d'un run précédent. Pour ré-exécuter le script sur
> le même fichier de sortie, il faut d'abord supprimer l'ancien fichier
> manuellement (ou utiliser `pipeline.py` qui le supprime automatiquement).

```python
# src/extract_copt.py — dans main()
if output_path.exists():
    LOGGER.error("Le fichier de sortie '%s' existe déjà.", output_path)
    sys.exit(2)
```

---

### 5.6 Résolution du compilateur

**Règle :** le champ `Compiler1` de chaque CSECT (chaîne brute issue du JSON)
est traduit en un code abrégé court via le dictionnaire `COMPILERS`. Ce code
est utilisé uniquement pour nommer les fichiers texte détaillés (§4.2).

| Famille | Clé exacte dans `Compiler1`           | Code court  |
| ------- | ------------------------------------- | ----------- |
| COBOL   | `"COBOL/370 for MVS V1R1"`            | `c370v11`   |
| COBOL   | `"COBOL/370 for MVS V1R2"`            | `c370v12`   |
| COBOL   | `"COBOL for OS/390 & VM V2R1"`        | `cos390v21` |
| COBOL   | `"COBOL for OS/390 & VM V2R2"`        | `cos390v22` |
| COBOL   | `"Enterpr.COBOL for z/OS V3R1"`       | `cbv31`     |
| COBOL   | `"Enterpr.COBOL for z/OS V3R2"`       | `cbv32`     |
| COBOL   | `"Enterpr.COBOL for z/OS V3R3"`       | `cbv33`     |
| COBOL   | `"Enterpr.COBOL for z/OS V3R4"`       | `cbv34`     |
| COBOL   | `"Enterpr.COBOL for z/OS V4R1"`       | `cbv41`     |
| COBOL   | `"Enterpr.COBOL for z/OS V4R2"`       | `cbv42`     |
| COBOL   | `"Enterpr.COBOL for z/OS V6R3"`       | `cbv63`     |
| COBOL   | `"OS/VS COBOL V1R2"`                  | `osvsv12`   |
| COBOL   | `"OS/VS COBOL V2R0"`                  | `osvsv20`   |
| COBOL   | `"OS/VS COBOL z/OS"`                  | `osvszos`   |
| COBOL   | `"VS COBOL II V1R2"`                  | `vsc2v12`   |
| COBOL   | `"VS COBOL II V1R3"`                  | `vsc2v13`   |
| COBOL   | `"VS COBOL II V1R4"`                  | `vsc2v14`   |
| C/C++   | `"C/C++ for z/OS V2R1"`               | `cppz21`    |
| C/C++   | `"C/C++ for z/OS V2R2"`               | `cppz22`    |
| C/C++   | `"C/C++ for z/OS V2R3"`               | `cppz23`    |
| C/C++   | `"C/C++ for z/OS V2R4"`               | `cppz24`    |
| C/C++   | `"C/C++ OS/390 R4 V2R0"`              | `cpp390v20` |
| C/C++   | `"C/C++ OS/390 R4 V2R4"`              | `cpp390v24` |
| C/C++   | `"C/C++ OS/390 R4 V2R6"`              | `cpp390v26` |
| C/C++   | `"C/C++ OS/390 R4 V2R9"`              | `cpp390v29` |
| C/C++   | `"C/C++ z/OS R5 V1R0"`               | `cppz10`    |
| C/C++   | `"C/C++ z/OS R5 V1R1"`               | `cppz11`    |
| C/C++   | `"C/C++ z/OS R5 V1R2"`               | `cppz12`    |
| C/C++   | `"C/C++ z/OS R5 V1R3"`               | `cppz13`    |
| C/C++   | `"C/C++ z/OS R5 V1R6"`               | `cppz16`    |
| C/C++   | `"C/C++ z/OS R5 V1R7"`               | `cppz17`    |
| C/C++   | `"C/C++ z/OS R5 V1R8"`               | `cppz18`    |
| C/C++   | `"C/C++ z/OS R5 V1R9"`               | `cppz19`    |
| PL/I    | `"Enterpr. PL/I for z/OS V3R1"`       | `pliv31`    |

> **Les clés sont les valeurs exactes du champ `Compiler1` dans le JSON** tel
> que produit par `build_json.py`. Pour identifier la bonne clé à ajouter,
> inspecter la valeur `Compiler1` dans `datas/vlm.json`.

**Compilateur inconnu :** si la valeur `Compiler1` ne figure pas dans
`COMPILERS`, le code `unknown` est utilisé comme suffixe et un avertissement
(`WARNING`) est émis dans les logs. Le fichier est tout de même créé
(ex. `MYPGM_MYPGM_unknown.txt`).

```python
# src/extract_copt.py — dictionnaire COMPILERS (34 entrées)
COMPILERS = {
    # --- COBOL (17 entrées) ---
    "COBOL/370 for MVS V1R1":       "c370v11",
    "COBOL/370 for MVS V1R2":       "c370v12",
    "COBOL for OS/390 & VM V2R1":   "cos390v21",
    # ...
    "Enterpr.COBOL for z/OS V6R3":  "cbv63",
    # --- C/C++ (16 entrées) ---
    "C/C++ for z/OS V2R1":          "cppz21",
    # ...
    "C/C++ z/OS R5 V1R9":           "cppz19",
    # --- PL/I (1 entrée) ---
    "Enterpr. PL/I for z/OS V3R1":  "pliv31",
}
```

---

### 5.7 Parcours en mémoire avec un générateur

**Règle :** la hiérarchie JSON est parcourue avec un **générateur** Python
(`yield`). Les lignes sont produites et écrites une par une, sans stocker
l'ensemble en mémoire.

> **Pourquoi un générateur ?** Un fichier VLM peut contenir des milliers de
> loadmods et des dizaines de milliers de CSECTs. Construire une liste complète
> avant d'écrire la première ligne consommerait de la mémoire inutilement. Le
> générateur maintient une empreinte mémoire constante quelle que soit la taille
> du JSON.

```python
# src/extract_copt.py — iter_csect_copt() est un générateur
yield prefix, loadlib, load_name, csect_name, compiler, copt

# Appelé directement dans write_csv() sans liste intermédiaire :
count = write_csv(iter_csect_copt(data), output_path)
```

---

## 6. Gestion des erreurs et codes de sortie

### 6.1 Validation des chemins avant traitement

Avant tout traitement, le script effectue quatre vérifications sur les chemins :

| Vérification                                          | Condition d'échec                  | Code de sortie |
| ----------------------------------------------------- | ---------------------------------- | -------------- |
| Le fichier JSON d'entrée existe                       | Fichier absent                     | `2`            |
| Le fichier CSV de sortie n'existe pas                 | Fichier déjà présent               | `2`            |
| Le répertoire de sortie existe                        | Répertoire parent absent           | `2`            |
| Le répertoire de sortie est accessible en écriture    | Pas de droits d'écriture           | `2`            |

> La vérification des droits d'écriture se fait par la création puis la
> suppression immédiate d'un fichier temporaire `.__vlm_write_test__`.

```python
# src/extract_copt.py — dans main()
if not input_path.is_file():
    LOGGER.error("Le fichier d'entrée '%s' n'existe pas.", input_path)
    sys.exit(2)

if output_path.exists():
    LOGGER.error("Le fichier de sortie '%s' existe déjà.", output_path)
    sys.exit(2)

output_dir = output_path.parent
if not output_dir.is_dir():
    LOGGER.error("Le répertoire de sortie '%s' n'existe pas.", output_dir)
    sys.exit(2)
try:
    testfile = output_dir / ".__vlm_write_test__"
    testfile.touch()
    testfile.unlink()
except OSError:
    LOGGER.error(
        "Le répertoire de sortie '%s' n'est pas accessible en écriture.",
        output_dir,
    )
    sys.exit(2)
```

### 6.2 Erreurs de lecture JSON

| Condition                     | Code de sortie | Message de log                          |
| ----------------------------- | -------------- | --------------------------------------- |
| Fichier JSON introuvable      | `2`            | `Fichier '%s' introuvable.`             |
| Accès refusé en lecture       | `2`            | `Accès refusé en lecture sur '%s'.`     |
| Contenu non JSON valide       | `3`            | `'%s' n'est pas un JSON valide : %s`    |
| Erreur I/O inattendue         | `10`           | `Erreur I/O lors de la lecture de '%s'` |

### 6.3 Erreurs d'écriture

Toute erreur système survenant pendant l'écriture du CSV ou la création des
fichiers détail (disque plein, droits révoqués en cours d'écriture, etc.) est
capturée par un `except OSError` et déclenche une sortie avec le code `10`.

```python
# src/extract_copt.py — dans write_csv()
except OSError as exc:
    LOGGER.error("Erreur I/O lors de l'écriture de '%s' : %s", output_path, exc)
    sys.exit(10)
```

### 6.4 Tableau récapitulatif des codes de sortie

| Code | Signification                                                                              |
| ---- | ------------------------------------------------------------------------------------------ |
| `0`  | Succès — le fichier CSV et les fichiers détail ont été produits correctement.              |
| `2`  | Erreur fichier/répertoire — fichier absent, fichier de sortie déjà existant, ou répertoire non accessible. |
| `3`  | Erreur de parsing — le fichier d'entrée n'est pas du JSON valide.                         |
| `10` | Erreur E/S — erreur de lecture ou d'écriture lors du traitement.                          |

---

## 7. Exemples concrets

### 7.1 Exemple d'entrée JSON (simplifié)

```json
[
  {
    "Loadlib": "MY.LOAD.LIB",
    "MemberCount": 2,
    "Loadmods": [
      {
        "Name": "MYPGM",
        "CSECTs": [
          {
            "Name": "MYPGM",
            "Compiler1": "COBOL",
            "Copt": ["RENT", "NOOPT", "CSECT(CODE,ACCPRINT)"]
          },
          {
            "Name": "DFHECI",
            "Compiler1": "COBOL",
            "Copt": []
          },
          {
            "Name": "DSNCLIMYMOD",
            "Compiler1": "COBOL",
            "Copt": ["RENT", "OPT(FULL)"]
          }
        ]
      }
    ]
  }
]
```

### 7.2 Fichier CSV récapitulatif correspondant

```
1;MY.LOAD.LIB;MYPGM;MYPGM;COBOL;3
0;MY.LOAD.LIB;MYPGM;DSNCLIMYMOD;COBOL;2
```

> `DFHECI` est absent : sa liste `Copt` est vide, il est ignoré.

Détail colonne par colonne pour la première ligne :

| `préfixe` | `loadlib`    | `load_name` | `csect_name` | `compilateur` | `nb_options` |
| --------- | ------------ | ----------- | ------------ | ------------- | ------------ |
| `1`       | `MY.LOAD.LIB`| `MYPGM`     | `MYPGM`      | `COBOL`       | `3`          |

Le préfixe est `"1"` car `load_name == csect_name` (`MYPGM == MYPGM`).

---

### 7.3 Fichiers texte détaillés créés

> Les noms de fichiers incluent le code abrégé du compilateur. Ici `COBOL`
> correspond à `"Enterpr.COBOL for z/OS V6R3"` → code `cbv63`.

**`datas/copt/loadlibs/MY.LOAD.LIB/MYPGM_MYPGM_cbv63.txt`**

```
RENT
NOOPT
CSECT(CODE,ACCPRINT)
```

**`datas/copt/loadlibs/MY.LOAD.LIB/MYPGM_DSNCLIMYMOD_cbv63.txt`**

```
RENT
OPT(FULL)
```

---

### 7.4 Arborescence des fichiers de sortie

En supposant un appel :
```bash
python extract_copt.py -f datas/vlm.json -o datas/copt/copt.csv
```

La structure créée est :

```
datas/copt/
├── copt.csv                                  ← Récapitulatif CSV
└── loadlibs/
    ├── MY.LOAD.LIB/
    │   ├── MYPGM_MYPGM_cbv63.txt             ← Options de MYPGM/MYPGM (COBOL V6R3)
    │   └── MYPGM_DSNCLIMYMOD_cbv63.txt       ← Options de MYPGM/DSNCLIMYMOD
    └── OTHER.LOAD.LIB/
        └── OTHERPGM_OTHERPGM_cbv63.txt
```

> Si le compilateur est inconnu (absent du dictionnaire `COMPILERS`), le fichier
> serait nommé `MYPGM_MYPGM_unknown.txt` et un `WARNING` serait émis dans les logs.

---

### 7.5 Cas particulier : CSECT sans champ `Copt`

Si un CSECT ne possède pas du tout la clé `Copt` dans le JSON (par exemple un
CSECT assembleur sans informations de compilation) :

```json
{
  "Name": "ASMSTUB",
  "Compiler1": "ASM"
}
```

→ `csect.get("Copt")` retourne `None` → `not copt` est `True` → **ignoré**.

---

### 7.6 Cas particulier : loadlib ou nom manquant dans le JSON

Si un nœud de la hiérarchie JSON est incomplet (clé absente), les champs
correspondants sont remplacés par une chaîne vide `""` grâce au pattern
`lib.get("Loadlib") or ""`.

```json
{
  "MemberCount": 1,
  "Loadmods": [...]
}
```

→ `loadlib = ""` → la ligne CSV aura une deuxième colonne vide, et le fichier
détail sera créé sous `loadlibs//MYPGM_MYPGM.txt`.

> **Note :** cette situation ne devrait pas se produire avec un JSON produit par
> `build_json.py` dans des conditions normales.
