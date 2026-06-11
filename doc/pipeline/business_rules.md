# Règles métier — `pipeline.py`

> **Rôle du script :** orchestrer les quatre étapes de la chaîne de traitement
> VLM en séquence. Chaque étape doit réussir avant que la suivante ne démarre.
> En cas d'échec d'une étape, le pipeline s'arrête immédiatement et propage le
> code d'erreur de l'étape fautive.

---

## Sommaire

1. [Contexte et glossaire](#1-contexte-et-glossaire)
2. [Vue d'ensemble du traitement](#2-vue-densemble-du-traitement)
3. [Configuration via `config.toml`](#3-configuration-via-configtoml)
4. [Fichiers du pipeline](#4-fichiers-du-pipeline)
5. [Règles d'orchestration](#5-règles-dorchestration)
6. [Gestion des erreurs et codes de sortie](#6-gestion-des-erreurs-et-codes-de-sortie)
7. [Exemples concrets](#7-exemples-concrets)

---

## 1. Contexte et glossaire

| Terme              | Définition                                                                                                                                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **VLM**            | _View Load Module_ — fonction d'IBM File Manager permettant d'analyser le contenu des load modules d'une bibliothèque z/OS. Le rapport produit (vlm.xml) est la matière première de toute la chaîne. |
| **Pipeline**       | Enchaînement ordonné d'étapes de traitement, chaque étape consommant la sortie de la précédente.                                                                                                     |
| **Orchestrateur**  | Script dont le seul rôle est de lancer d'autres scripts dans le bon ordre et de vérifier leur succès.                                                                                                |
| **subprocess**     | Module Python standard permettant de lancer un programme externe (ici un autre script Python) depuis un script Python.                                                                               |
| **code de retour** | Entier renvoyé par un programme à son processus parent à la fin de son exécution : `0` = succès, tout autre valeur = erreur.                                                                         |
| **config.toml**    | Fichier de configuration TOML à la racine du projet. Contient les chemins des fichiers d'entrée/sortie utilisateur.                                                                                  |
| **LEINFO**         | Pseudo-option de compilation IBM LE — mode `placeholder` utilisé par défaut dans le pipeline.                                                                                                        |

---

## 2. Vue d'ensemble du traitement

Le pipeline exécute quatre étapes dans un ordre fixe et strict :

```
Lire config.toml (chemins configurables)
    │
    ▼
[1] clean_report.py
    Entrée  : fichier VLM brut ISO-8859-1 (vlm_input)
    Sortie  : clean_vlm.xml (UTF-8, XML bien formé)
    Échec ? ──► Arrêt immédiat, propagation du code d'erreur
    │
    ▼
[2] reformat_copt.py
    Entrée  : clean_vlm.xml
    Sortie  : clean_vlm_copt.xml + copt_ignored.txt
    Échec ? ──► Arrêt immédiat, propagation du code d'erreur
    │
    ▼
[3] build_json.py
    Entrée  : clean_vlm_copt.xml
    Sortie  : vlm.json (final_json)
    Échec ? ──► Arrêt immédiat, propagation du code d'erreur
    │
    ▼
[4] extract_copt.py
    Pré-requis : supprimer copt.csv s'il existe déjà
    Entrée  : vlm.json
    Sortie  : copt.csv + fichiers .txt par CSECT
    Échec ? ──► Arrêt immédiat, propagation du code d'erreur
    │
    ▼
Afficher le bilan (chemins des fichiers produits)
```

---

## 3. Configuration via `config.toml`

Le pipeline lit trois chemins dans la section `[settings]` de `config.toml`.
Ces chemins sont **relatifs à la racine du projet**.

| Clé TOML     | Description                                             | Exemple de valeur       |
| ------------ | ------------------------------------------------------- | ----------------------- |
| `vlm_input`  | Rapport VLM en entrée                                   | `"datas/vlm.xml"`       |
| `final_json` | Fichier JSON final produit par `build_json.py`          | `"datas/vlm.json"`      |
| `copt_csv`   | Fichier CSV récapitulatif produit par `extract_copt.py` | `"datas/copt/copt.csv"` |

```toml
# config.toml (section settings)
[settings]
vlm_input  = "datas/vlm.xml"
final_json = "datas/vlm.json"
copt_csv   = "datas/copt/copt.csv"
```

```python
# src/pipeline.py — lecture de la configuration
_config = load_config()
_settings = _config.get("settings", {})

VLM_INPUT  = PROJECT_ROOT / _settings["vlm_input"]
FINAL_JSON = PROJECT_ROOT / _settings["final_json"]
COPT_CSV   = PROJECT_ROOT / _settings["copt_csv"]
```

> **Pourquoi utiliser `config.toml` ?** Les chemins des fichiers d'entrée/sortie
> utilisateur sont susceptibles de changer d'un environnement à l'autre. Les
> centraliser dans un seul fichier de configuration évite de modifier le code
> source pour chaque nouvel environnement.

---

## 4. Fichiers du pipeline

### 4.1 Fichier d'entrée (configurable)

| Fichier     | Source        | Description                                           |
| ----------- | ------------- | ----------------------------------------------------- |
| `vlm_input` | `config.toml` | Rapport VLM généré par IBM File Manager (ISO-8859-1). |

### 4.2 Fichiers intermédiaires (câblés dans le code)

Ces chemins ne sont pas exposés dans `config.toml` car ils sont internes au
pipeline et n'ont pas vocation à être modifiés par l'utilisateur.

| Fichier                    | Produit par        | Consommé par             |
| -------------------------- | ------------------ | ------------------------ |
| `datas/clean_vlm.xml`      | `clean_report.py`  | `reformat_copt.py`       |
| `datas/clean_vlm_copt.xml` | `reformat_copt.py` | `build_json.py`          |
| `datas/copt_ignored.txt`   | `reformat_copt.py` | _(consultation humaine)_ |

```python
# src/pipeline.py — câblage interne
CLEAN_XML    = PROJECT_ROOT / "datas/clean_vlm.xml"
COPT_XML     = PROJECT_ROOT / "datas/clean_vlm_copt.xml"
COPT_IGNORED = PROJECT_ROOT / "datas/copt_ignored.txt"
```

### 4.3 Fichiers de sortie (configurables)

| Fichier      | Produit par       | Description                                             |
| ------------ | ----------------- | ------------------------------------------------------- |
| `final_json` | `build_json.py`   | JSON structuré exploitable par `jq` ou `export_csv.sh`. |
| `copt_csv`   | `extract_copt.py` | CSV récapitulatif des options COPT par CSECT.           |

---

## 5. Règles d'orchestration

### 5.1 Exécution séquentielle et propagation d'erreur

**Règle :** chaque étape est lancée avec `subprocess.run()`. Si le code de
retour est différent de `0`, le pipeline s'arrête immédiatement et retourne
ce même code d'erreur à son processus parent.

> **Pourquoi s'arrêter à la première erreur ?** Les étapes sont dépendantes :
> `reformat_copt.py` ne peut pas fonctionner si `clean_report.py` n'a pas
> produit un XML valide. Continuer malgré une erreur ne ferait que produire
> des fichiers corrompus ou vides aux étapes suivantes.

```python
# src/pipeline.py — run_step() factorise le pattern pour chaque étape
# cmd      : commande complète sous forme de liste (sys.executable + args)
# step_num : numéro affiché dans les messages
# label    : nom du script affiché en cas d'erreur
def run_step(cmd: list[str], step_num: int, label: str) -> None:
    ret = subprocess.run(cmd)
    if ret.returncode != 0:
        LOGGER.error(
            "Échec de l'étape %d (%s) — code de retour %d.",
            step_num, label, ret.returncode,
        )
        print(f"Erreur lors de l'étape {step_num} ({label})")
        sys.exit(ret.returncode)
    LOGGER.info("Étape %d (%s) terminée avec succès.", step_num, label)
```

### 5.2 Invocation avec le même interpréteur Python

**Règle :** chaque sous-script est lancé avec `sys.executable` (l'interpréteur
Python actuel) plutôt qu'avec la commande `python` ou `python3`.

> **Pourquoi `sys.executable` ?** Sur un système avec plusieurs environnements
> Python (virtualenvs, `uv`, conda…), `python` peut pointer vers un
> interpréteur différent de celui qui exécute `pipeline.py`. `sys.executable`
> garantit que le même interpréteur — et donc les mêmes bibliothèques installées
> — est utilisé pour toutes les étapes.

```python
# src/pipeline.py
subprocess.run([sys.executable, str(SRC_DIR / "clean_report.py"), ...])
#               ↑ chemin absolu de l'interpréteur Python courant
```

### 5.3 Suppression préalable du fichier CSV de sortie (étape 4)

**Règle :** avant de lancer `extract_copt.py`, le pipeline supprime le fichier
`copt_csv` s'il existe déjà.

> **Pourquoi ?** `extract_copt.py` refuse d'écraser un fichier de sortie
> existant (protection anti-perte de données, voir son propre `business_rules.md`).
> Le pipeline contourne cette protection de façon intentionnelle et contrôlée :
> lors d'une ré-exécution du pipeline complet, le fichier CSV de la dernière
> exécution est de toute façon périmé.

```python
# src/pipeline.py — pré-traitement de l'étape 4
if COPT_CSV.exists():
    LOGGER.debug("Suppression du fichier COPT CSV existant : '%s'.", COPT_CSV)
    COPT_CSV.unlink()
```

### 5.4 Options passées à chaque sous-script

Le tableau ci-dessous récapitule les arguments transmis à chaque étape :

| Étape | Script             | Arguments clés                                                                    |
| ----- | ------------------ | --------------------------------------------------------------------------------- |
| 1     | `clean_report.py`  | `-f vlm_input -o clean_vlm.xml -e iso8859-1`                                      |
| 2     | `reformat_copt.py` | `-f clean_vlm.xml -o clean_vlm_copt.xml -e utf-8 --ignored-file copt_ignored.txt` |
| 3     | `build_json.py`    | `-f clean_vlm_copt.xml -o final_json -e utf-8`                                    |
| 4     | `extract_copt.py`  | `-f final_json -o copt_csv`                                                       |

> **Note :** `reformat_copt.py` est appelé sans `--leinfo-mode` ; le mode par
> défaut `placeholder` s'applique (voir `reformat_copt/business_rules.md` §6.3).

### 5.5 Exécution partielle (sous-ensemble d'étapes)

**Règle :** le pipeline accepte un argument positionnel optionnel pour exécuter
uniquement certaines étapes. Sans argument, toutes les étapes sont exécutées.

```bash
python src/pipeline.py             # Toutes les étapes (1→4)
python src/pipeline.py 3           # Étape 3 uniquement
python src/pipeline.py 2-4         # Étapes 2, 3 et 4
python src/pipeline.py extract     # Étape 4 (par alias)
python src/pipeline.py copt-json   # Étapes 2 et 3 (par alias)
```

**Alias disponibles :**

| Alias     | Étape | Script             |
| --------- | ----- | ------------------ |
| `clean`   | 1     | `clean_report.py`  |
| `copt`    | 2     | `reformat_copt.py` |
| `json`    | 3     | `build_json.py`    |
| `extract` | 4     | `extract_copt.py`  |

> **Pré-requis pour une exécution partielle :** si vous exécutez l'étape N sans
> avoir exécuté l'étape N-1, le fichier intermédiaire attendu en entrée doit
> déjà exister sur le disque. Sinon le sous-script retourne le code `2`
> (fichier introuvable) et le pipeline s'arrête.
>
> Exemple : `pipeline.py 3` requiert que `datas/clean_vlm_copt.xml` existe
> (produit par l'étape 2).

**L'affichage s'adapte** au nombre d'étapes sélectionnées :

```
[1/2] Conversion XML → JSON...   ← sur 2 étapes au lieu de 4
[2/2] Extraction des options COPT par CSECT...
```

```python
# src/pipeline.py — parse_steps() gère N, N-M, alias et alias-alias
parse_steps("3")          # → [3]
parse_steps("2-4")        # → [2, 3, 4]
parse_steps("extract")    # → [4]
parse_steps("copt-json")  # → [2, 3]
```

---

### 5.6 Pas de parallélisme

**Règle :** les étapes sont exécutées **strictement l'une après l'autre**. Aucune
étape n'est lancée en arrière-plan ou en parallèle.

> **Pourquoi ?** Les étapes sont liées par des dépendances de données : la sortie
> de l'étape N est l'entrée de l'étape N+1. Un traitement parallèle n'est pas
> possible sans refactoriser complètement la chaîne.

---

## 6. Gestion des erreurs et codes de sortie

### 6.1 Aucune validation des chemins dans le pipeline lui-même

Le pipeline ne vérifie pas lui-même l'existence des fichiers d'entrée ou la
disponibilité des répertoires de sortie. Cette responsabilité est déléguée à
chaque sous-script, qui effectue ses propres vérifications et retourne un code
d'erreur explicite.

> **Pourquoi déléguer ?** Chaque script est conçu pour fonctionner de façon
> autonome (en dehors du pipeline). Centraliser les validations dans le pipeline
> serait redondant et créerait un risque de désynchronisation si les règles de
> validation d'un script évoluent.

### 6.2 Codes de sortie propagés

Le pipeline propage tel quel le code de retour du sous-script en échec :

| Code renvoyé | Signification probable (dépend du script en échec)                 |
| ------------ | ------------------------------------------------------------------ |
| `0`          | Toutes les étapes ont réussi.                                      |
| `1`          | Erreur métier détectée par `clean_report.py` (message `FMNBF427`). |
| `2`          | Erreur fichier/répertoire dans l'une des étapes.                   |
| `3`          | Erreur de parsing XML ou JSON dans l'une des étapes.               |
| `10`         | Erreur E/S (lecture ou écriture) dans l'une des étapes.            |

> Le message affiché sur le terminal (`Erreur lors de l'étape N (script.py)`)
> identifie quelle étape a échoué. Le code exact et le message détaillé sont
> disponibles dans `logs/pipeline.log`.

### 6.3 Tableau récapitulatif

| Code | Signification                                             |
| ---- | --------------------------------------------------------- |
| `0`  | Succès — les quatre étapes se sont terminées sans erreur. |
| `≠0` | Échec — code hérité du sous-script défaillant.            |

---

## 7. Exemples concrets

### 7.1 Exécution réussie

```bash
$ python src/pipeline.py
[1/4] Nettoyage du rapport VLM...
[2/4] Reformatage des balises Copt...
[3/4] Conversion XML → JSON...
[4/4] Extraction des options COPT par CSECT...
Pipeline terminé avec succès !
Fichier JSON final : /home/user/vlm/datas/vlm.json
Fichier COPT CSV  : /home/user/vlm/datas/copt/copt.csv
```

Entrées dans `logs/pipeline.log` (niveaux INFO) :

```
2025-06-01 10:00:00 | INFO     | pipeline     | Démarrage du pipeline : entrée='...' ...
2025-06-01 10:00:00 | INFO     | pipeline     | [1/4] Nettoyage du rapport VLM : '...' → '...'
2025-06-01 10:00:02 | INFO     | clean_report | Début du traitement : '...' → '...'
2025-06-01 10:00:05 | INFO     | clean_report | Terminé : 1247 lignes écrites dans '...'
2025-06-01 10:00:05 | INFO     | pipeline     | Étape 1 terminée avec succès.
...
2025-06-01 10:00:30 | INFO     | pipeline     | Pipeline terminé avec succès.
```

> Chaque message est identifiable par la colonne `%(name)s` du format de log :
> `pipeline` pour les messages du pipeline lui-même, `clean_report`,
> `reformat_copt`, `build_json`, `extract_copt` pour ceux des sous-scripts.

---

### 7.2 Échec à l'étape 1 (fichier d'entrée absent)

```bash
$ python src/pipeline.py
[1/4] Nettoyage du rapport VLM...
Erreur lors de l'étape 1 (clean_report.py)
$ echo $?
2
```

Entrée dans `logs/pipeline.log` :

```
2025-06-01 10:00:00 | ERROR    | clean_report | Le fichier d'entrée '...' n'existe pas.
2025-06-01 10:00:00 | ERROR    | pipeline     | Échec de l'étape 1 (clean_report.py) — code de retour 2.
```

---

### 7.3 Échec à l'étape 1 (erreur métier mainframe FMNBF427)

```bash
$ python src/pipeline.py
[1/4] Nettoyage du rapport VLM...
Erreur lors de l'étape 1 (clean_report.py)
$ echo $?
1
```

Entrée dans `logs/pipeline.log` :

```
2025-06-01 10:00:02 | ERROR    | clean_report | Erreur métier FMNBF427 : OPEN failed for DSNIN=MY.LIB
2025-06-01 10:00:02 | ERROR    | pipeline     | Échec de l'étape 1 (clean_report.py) — code de retour 1.
```

---

### 7.4 Ré-exécution du pipeline sur un répertoire déjà peuplé

Lors d'une seconde exécution sur un répertoire contenant déjà `copt.csv` :

```
2025-06-01 11:00:05 | DEBUG    | pipeline     | Suppression du fichier COPT CSV existant : '...copt.csv'.
```

Le fichier est supprimé silencieusement, puis `extract_copt.py` repart de zéro.
Les étapes 1 à 3 écrasent leurs fichiers intermédiaires sans restriction
(contrairement à `extract_copt.py`, les scripts `clean_report.py`,
`reformat_copt.py` et `build_json.py` **acceptent** d'écraser leurs fichiers
de sortie existants).
