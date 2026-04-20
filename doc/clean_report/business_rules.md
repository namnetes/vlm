# Règles métier — `clean_report.py`

> **Rôle du script :** transformer un rapport brut émis par IBM File Manager
> (mainframe z/OS) en un fichier XML propre et bien formé, exploitable par
> les étapes suivantes du pipeline VLM.

---

## Sommaire

1. [Contexte et glossaire](#1-contexte-et-glossaire)
2. [Vue d'ensemble du traitement](#2-vue-densemble-du-traitement)
3. [Format du fichier d'entrée](#3-format-du-fichier-dentrée)
4. [Format du fichier de sortie](#4-format-du-fichier-de-sortie)
5. [Règles de traitement ligne par ligne](#5-règles-de-traitement-ligne-par-ligne)
6. [Enrichissement des balises XML](#6-enrichissement-des-balises-xml)
7. [Gestion des erreurs et codes de sortie](#7-gestion-des-erreurs-et-codes-de-sortie)
8. [Exemples concrets](#8-exemples-concrets)

---

## 1. Contexte et glossaire

| Terme            | Définition                                                                                                                                      |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **VLM**          | _View Load Module_ — fonction d'IBM File Manager permettant d'analyser le contenu des load modules d'une bibliothèque z/OS. Le rapport brut produit par cette fonction (vlm.xml) est l'entrée de ce script. |
| **Loadlib**      | Bibliothèque de chargement (un répertoire de programmes sur le mainframe).                                                                      |
| **Loadmod**      | Module de chargement (un programme).                                                                                                            |
| **CSECT**        | _Control Section_ — sous-partie d'un programme (équivalent d'un module ou d'une fonction).                                                      |
| **DSN**          | _Data Set Name_ — nom d'une ressource sur le mainframe (équivalent d'un chemin de fichier).                                                     |
| **ASA**          | Caractère de contrôle imprimante hérité du mainframe, placé en **première colonne** de chaque ligne. Les valeurs possibles sont : ` ` (normal), `0` (saut de ligne), `1` (saut de page), `-` (retour arrière). Ce caractère n'a aucun intérêt dans un XML. |
| **PDS**          | _Partitioned Data Set_ — fichier partitionné mainframe (comparable à un répertoire).                                                            |
| **File Manager** | Utilitaire IBM qui génère le rapport VLM brut en entrée.                                                                                        |
| **FMNBXXX**      | Codes de message émis par File Manager (ex. `FMNBF427` = erreur critique).                                                                      |

---

## 2. Vue d'ensemble du traitement

Le script lit le rapport **ligne par ligne** et applique les règles dans cet
ordre strict pour chaque ligne :

```
Lire une ligne
    │
    ▼
[1] Supprimer le caractère ASA (1er caractère)
    │
    ▼
[2] La ligne est-elle du "bruit" technique ?  ──► OUI → Ignorer, passer à la ligne suivante
    │ NON
    ▼
[3] Contient-elle DSNIN= ?  ──► OUI → Mémoriser le nom de la loadlib, ignorer la ligne
    │ NON
    ▼
[4] Contient-elle FMNBF427 ?  ──► OUI → Arrêt immédiat (erreur critique, code 1)
    │ NON
    ▼
[5] Contient-elle FMNBE329 ?  ──► OUI → Écrire un bloc <vlm> vide (memberCount=0)
    │ NON
    ▼
[6] Commence-t-elle par <vlm> ?  ──► OUI → Réécrire avec l'attribut loadlib
    │ NON
    ▼
[7] Commence-t-elle par </vlm> ?  ──► OUI → Lire la ligne suivante pour extraire
    │                                         memberCount, injecter <memberCount/> avant </vlm>
    │ NON
    ▼
[8] Écrire la ligne telle quelle dans le fichier de sortie
```

---

## 2b. Paramètres de la ligne de commande

| Paramètre        | Obligatoire | Valeur par défaut  | Description                                  |
| ---------------- | ----------- | ------------------ | -------------------------------------------- |
| `-f` / `--file`  | non         | `vlm.xml`          | Chemin du rapport VLM brut en entrée         |
| `-o` / `--output`| non         | `clean_vlm.xml`    | Chemin du fichier XML de sortie              |
| `-e` / `--encoding` | non      | `iso8859-1`        | Encodage du fichier source (mainframe)       |

> L'encodage `iso8859-1` (aussi appelé Latin-1) est l'encodage standard des
> fichiers mainframe IBM z/OS en Europe occidentale. Il doit correspondre à
> l'encodage réel du rapport VLM brut.

---

## 3. Format du fichier d'entrée

- **Encodage :** ISO-8859-1 par défaut (paramétrable via `-e`).
- **Structure :** mélange hétérogène de lignes de texte brut (messages File
  Manager) et de fragments XML. Ce n'est pas un XML valide à ce stade.
- **Caractère ASA :** chaque ligne commence par un caractère de contrôle
  imprimante (`0`, `1`, `-` ou espace). Ce caractère n'a aucune signification
  métier et doit être retiré avant tout traitement.

---

## 4. Format du fichier de sortie

- **Encodage :** UTF-8 (toujours, indépendamment de l'encodage source).
- **Structure XML bien formée :**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
  <vlm loadlib="NOM.DE.LA.LOADLIB">
    ...contenu des membres...
    <memberCount value="42"/>
  </vlm>
  <vlm loadlib="AUTRE.LOADLIB">
    <memberCount value="0"/>
  </vlm>
</root>
```

- La balise `<root>` encapsule tous les blocs `<vlm>`.
- Chaque bloc `<vlm>` porte l'attribut `loadlib` et se termine par
  `<memberCount value="N"/>` juste avant la balise fermante `</vlm>`.

---

## 5. Règles de traitement ligne par ligne

### 5.1 Suppression du caractère ASA

**Règle :** le premier caractère de chaque ligne est systématiquement supprimé,
puis les espaces en début et fin de ligne sont retirés.

> **Pourquoi ?** Les rapports mainframe réservent la colonne 1 à un code
> imprimante hérité de l'époque des imprimantes à aiguilles. Ce caractère est
> toujours présent mais sans valeur pour notre traitement.

```python
# src/clean_report.py — strip_asa_char()
def strip_asa_char(line: str) -> str:
    return line[1:].strip()

# Appelé pour chaque ligne dans convert_report()
for line in f_in:
    line_str = strip_asa_char(line)
```

---

### 5.2 Filtrage du bruit technique

**Règle :** une ligne est ignorée si elle est vide **ou** si elle commence par
l'un des préfixes suivants :

| Préfixe       | Description                               |
| ------------- | ----------------------------------------- |
| `IBM File`    | En-tête de bannière File Manager          |
| `FMNBA001`    | Message d'initialisation                  |
| `FMNBA010`    | Message de configuration                  |
| `DEFAULT SET` | Paramètre de configuration                |
| `PRINTOUT=`   | Paramètre d'impression                    |
| `PRINTLEN=`   | Paramètre de longueur d'impression        |
| `PAGESIZE=`   | Paramètre de taille de page               |
| `PRTTRANS=`   | Paramètre de translation d'impression     |
| `SMFNO=`      | Numéro SMF (System Management Facilities) |
| `TEMP UNIT=`  | Unité temporaire                          |
| `PERM UNIT=`  | Unité permanente                          |
| `TRACECLS=`   | Classe de trace                           |
| `$$FILEM`     | En-tête de section File Manager           |

**Exception importante :** la ligne commençant par `$$FILEM VLM` n'est **pas**
ignorée. Elle annonce un bloc VLM et contient des informations utiles (notamment
le paramètre `DSNIN=` décrit ci-après).

```python
# src/clean_report.py — constante + is_noise_line()
_NOISE_PREFIXES: frozenset[str] = frozenset(
    {
        "IBM File", "FMNBA001", "FMNBA010", "DEFAULT SET",
        "PRINTOUT=", "PRINTLEN=", "PAGESIZE=", "PRTTRANS=",
        "SMFNO=", "TEMP UNIT=", "PERM UNIT=", "TRACECLS=",
        "$$FILEM",
    }
)

def is_noise_line(line: str) -> bool:
    if not line:
        return True
    if line.startswith("$$FILEM VLM"):   # exception : ligne utile
        return False
    return any(line.startswith(prefix) for prefix in _NOISE_PREFIXES)

# Appelé dans convert_report()
if is_noise_line(line_str):
    continue
```

---

### 5.3 Extraction du nom de la loadlib (DSNIN=)

**Règle :** si une ligne (après suppression du bruit) contient le motif
`DSNIN=VALEUR`, la valeur est extraite et mémorisée comme nom de la loadlib
courante.

- La valeur peut se terminer par une virgule (`,`) qui est retirée.
- La ligne elle-même n'est **pas** écrite dans le fichier de sortie.
- La valeur mémorisée sera injectée comme attribut `loadlib` dans la prochaine
  balise `<vlm>` rencontrée.

> **Exemple :** `DSNIN=MY.LOAD.LIB,` → loadlib mémorisée = `MY.LOAD.LIB`

```python
# src/clean_report.py — regex + extraction dans convert_report()
_RE_DSN: re.Pattern[str] = re.compile(r"DSNIN=([\w\.]+)")

# Dans convert_report() :
dsn_match = _RE_DSN.search(line_str)
if dsn_match:
    current_loadlib = dsn_match.group(1).rstrip(",")
    LOGGER.debug("Loadlib détectée : %s", current_loadlib)
    continue                          # ligne non écrite en sortie
```

---

## 6. Enrichissement des balises XML

### 6.1 Transformation de la balise ouvrante `<vlm>`

**Règle :** la balise `<vlm>` brute est remplacée par `<vlm loadlib="VALEUR">`
où `VALEUR` est le nom de la loadlib mémorisé à l'étape précédente.

```
Entrée  :  <vlm>
Sortie  :  <vlm loadlib="MY.LOAD.LIB">
```

```python
# src/clean_report.py — dans convert_report()
if line_str.startswith("<vlm>"):
    f_out.write(f'<vlm loadlib="{current_loadlib}">\n')
```

---

### 6.2 Injection de `<memberCount>` — cas standard

**Règle :** lorsque la balise `</vlm>` est détectée, le script lit
**immédiatement la ligne suivante** pour y chercher le message
`FMNBB437 N member(s) read`.

- Si le message est trouvé, `N` est extrait.
- Si la ligne suivante ne contient pas ce message, le compteur vaut `0`.
- La balise `<memberCount value="N"/>` est insérée **juste avant** `</vlm>`.

```xml
<!-- Résultat dans le fichier de sortie -->
    <memberCount value="42"/>
</vlm>
```

> **Pourquoi lire la ligne suivante ?** File Manager place ce message de
> comptage _après_ la balise fermante `</vlm>`. Le script consomme cette ligne
> hors du flux principal pour ne pas l'écrire dans le XML.

```python
# src/clean_report.py — read_member_count() + usage dans convert_report()
_RE_COUNT: re.Pattern[str] = re.compile(r"FMNBB437\s+(\d+)\s+member\(s\) read")

def read_member_count(f_in: Iterator[str]) -> int:
    next_line = next(f_in, None)
    if next_line is None:
        return 0
    match = _RE_COUNT.search(strip_asa_char(next_line))
    return int(match.group(1)) if match else 0

# Dans convert_report() :
else:
    if line_str.startswith("</vlm>"):
        member_count = read_member_count(f_in)
        f_out.write(f'<memberCount value="{member_count}"/>')
    f_out.write(line_str + "\n")
```

---

### 6.3 Cas de bibliothèque vide (`FMNBE329`)

**Règle :** si le message `FMNBE329 The PDS contains no members` est détecté,
la bibliothèque ne contient aucun programme. Le script génère alors un bloc
XML minimal avec `memberCount` à zéro, **sans attendre** de balise `<vlm>` ni
`</vlm>` dans le flux :

```xml
<vlm loadlib="MY.EMPTY.LIB">
  <memberCount value="0"/>
</vlm>
```

```python
# src/clean_report.py — regex + traitement dans convert_report()
_RE_EMPTY: re.Pattern[str] = re.compile(
    r"FMNBE329\s+The PDS contains no members"
)

# Dans convert_report() :
if _RE_EMPTY.search(line_str):
    LOGGER.debug("Bibliothèque vide : %s (memberCount=0)", current_loadlib)
    f_out.write(f'<vlm loadlib="{current_loadlib}">\n')
    f_out.write('  <memberCount value="0"/>\n')
    f_out.write("</vlm>\n")
    continue
```

---

## 7. Gestion des erreurs et codes de sortie

### 7.1 Erreur critique mainframe — FMNBF427

**Règle :** si le message `FMNBF427` est détecté dans le flux, il signale une
erreur grave côté mainframe (ex. : problème d'accès à la ressource). Le script
**s'arrête immédiatement** sans produire de fichier de sortie.

- Code de sortie : **`1`** (erreur métier)
- Le message d'erreur associé est enregistré dans les logs.

```python
# src/clean_report.py — regex + traitement dans convert_report()
_RE_ERROR: re.Pattern[str] = re.compile(r"FMNBF427\s+(.*)")

# Dans convert_report() :
error_match = _RE_ERROR.search(line_str)
if error_match:
    LOGGER.error("Erreur métier FMNBF427 : %s", error_match.group(1))
    sys.exit(1)
```

---

### 7.2 Validation des chemins avant traitement

Avant de commencer la lecture du rapport, le script vérifie :

| Vérification                                       | Condition d'échec        | Code de sortie |
| -------------------------------------------------- | ------------------------ | -------------- |
| Le fichier d'entrée existe                         | Fichier absent           | `10`           |
| Le répertoire de sortie existe                     | Répertoire parent absent | `2`            |
| Le répertoire de sortie est accessible en écriture | Pas de droits d'écriture | `2`            |

> La vérification des droits d'écriture se fait par une tentative de création
> d'un fichier temporaire (`./__vlm_write_test__`) immédiatement supprimé.

```python
# src/clean_report.py — validate_input_file() + validate_output_dir()
def validate_input_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Fichier d'entrée introuvable : '{path}'")

def validate_output_dir(path: Path) -> None:
    output_dir = path.parent if path.parent != Path("") else Path(".")
    if not output_dir.is_dir():
        raise NotADirectoryError(
            f"Répertoire de sortie introuvable : '{output_dir}'"
        )
    test_file = output_dir / ".__vlm_write_test__"
    try:
        test_file.touch()
        test_file.unlink()
    except OSError as exc:
        raise PermissionError(
            f"Répertoire de sortie non accessible en écriture : '{output_dir}'"
        ) from exc

# Appelées dans main() avant convert_report() :
validate_input_file(input_path)
validate_output_dir(output_path)
```

---

### 7.3 Tableau récapitulatif des codes de sortie

| Code | Signification                                                                          |
| ---- | -------------------------------------------------------------------------------------- |
| `0`  | Succès — le fichier XML de sortie a été produit correctement.                          |
| `1`  | Erreur métier — message `FMNBF427` détecté dans le rapport.                            |
| `2`  | Erreur fichier/répertoire — répertoire de sortie absent ou non accessible en écriture. |
| `10` | Erreur E/S — fichier d'entrée introuvable ou erreur de lecture/écriture.               |

```python
# src/clean_report.py — gestion des codes de sortie dans main()
try:
    validate_input_file(input_path)    # FileNotFoundError → exit 10
    validate_output_dir(output_path)   # NotADirectoryError / PermissionError → exit 2
    convert_report(input_path, output_path, args.encoding)  # FMNBF427 → exit 1
except FileNotFoundError as exc:
    LOGGER.error("%s", exc)
    sys.exit(10)
except (NotADirectoryError, PermissionError) as exc:
    LOGGER.error("%s", exc)
    sys.exit(2)
except IOError as exc:
    LOGGER.error("Erreur E/S : %s", exc)
    sys.exit(10)
# Succès implicite → code 0
```

---

## 8. Exemples concrets

### 8.1 Exemple de flux d'entrée (simplifié)

```
 IBM File Manager for z/OS
 FMNBA001  Version 15.1.10
 DEFAULT SET  FILEMAN
 PRINTOUT=SYSOUT
 $$FILEM VLM   DSNIN=MY.LOAD.LIB,
0<vlm>
0  <loadmod name="MYPGM">
0    <csect name="MYPGM"/>
0  </loadmod>
0</vlm>
 FMNBB437    2 member(s) read
```

> Note : le premier caractère de chaque ligne (`espace`, `0`) est le caractère
> ASA.

### 8.2 Fichier XML de sortie correspondant

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
<vlm loadlib="MY.LOAD.LIB">
  <loadmod name="MYPGM">
    <csect name="MYPGM"/>
  </loadmod>
<memberCount value="2"/></vlm>
</root>
```

### 8.3 Exemple avec bibliothèque vide

Flux d'entrée :

```
 $$FILEM VLM   DSNIN=MY.EMPTY.LIB,
 FMNBE329  The PDS contains no members
```

Sortie XML :

```xml
<vlm loadlib="MY.EMPTY.LIB">
  <memberCount value="0"/>
</vlm>
```

### 8.4 Exemple avec erreur critique

Flux d'entrée :

```
 FMNBF427  OPEN failed for DSNIN=MY.MISSING.LIB
```

Résultat : arrêt immédiat, **aucun fichier de sortie**, code de retour `1`.
