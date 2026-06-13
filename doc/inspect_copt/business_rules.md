# Règles métier — `inspect_copt.py`

> **Rôle du script :** afficher le contenu brut de chaque balise `<Copt>`
> d'un fichier XML VLM. Outil de débogage utilisé pour comparer les valeurs
> d'options de compilation avant et après le traitement par `reformat_copt.py`.

---

## Sommaire

1. [Contexte et usage](#1-contexte-et-usage)
2. [Arguments de la ligne de commande](#2-arguments-de-la-ligne-de-commande)
3. [Comportement](#3-comportement)
4. [Codes de sortie](#4-codes-de-sortie)
5. [Exemples](#5-exemples)

---

## 1. Contexte et usage

`inspect_copt.py` est un **utilitaire de diagnostic**, indépendant du
pipeline principal. Il n'écrit aucun fichier : il lit un XML VLM et affiche
sur la sortie standard la valeur de l'attribut `Val` de chaque balise
`<Copt>`, numérotée à partir de 1.

**Cas d'utilisation typiques :**

- Vérifier qu'une valeur COPT particulière est bien présente dans le XML
  d'entrée avant de lancer `reformat_copt.py`.
- Comparer les valeurs brutes (`clean_vlm.xml`) et normalisées
  (`clean_vlm_copt.xml`) pour valider le reformatage.
- Identifier les valeurs `Compiler1` inconnues qui produiraient un
  fichier `_unknown.txt` dans `extract_copt.py`.

```bash
# Inspecter le XML brut (avant reformatage)
uv run src/inspect_copt.py -f datas/clean_vlm.xml  # (1)!

# Inspecter le XML normalisé (après reformatage)
uv run src/inspect_copt.py -f datas/clean_vlm_copt.xml  # (2)!
```

1. Affiche toutes les balises `<Copt>` du fichier brut — utile pour vérifier
   ce qu'IBM File Manager a produit.
2. Affiche les mêmes balises après normalisation — permet de comparer avec (1).

---

## 2. Arguments de la ligne de commande

| Option | Forme courte | Obligatoire | Défaut                  | Description                       |
| ------ | ------------ | ----------- | ----------------------- | --------------------------------- |
| `--file`     | `-f` | Non | `datas/clean_vlm.xml`   | Fichier XML en entrée.            |
| `--encoding` | `-e` | Non | `utf-8`                 | Encodage du fichier XML.          |

```bash
uv run src/inspect_copt.py --help
```

---

## 3. Comportement

### 3.1 Chargement du XML

Le fichier XML est chargé en mémoire dans son intégralité avec
`xml.etree.ElementTree`. L'encodage passé en argument force la lecture
(utile si le XML ne déclare pas son encodage en en-tête).

### 3.2 Recherche des balises `<Copt>`

La recherche utilise le sélecteur XPath `.//Copt`, qui trouve tous les
éléments `<Copt>` quelle que soit leur profondeur dans l'arbre XML
(balises imbriquées sous `<root>`, `<vlm>`, `<Loadmod>`, etc.).

### 3.3 Affichage

Chaque balise trouvée est affichée sur une ligne sous la forme :

```
[N] <valeur de l'attribut Val>
```

- `N` commence à `1`.
- Si l'attribut `Val` est absent sur une balise, une chaîne vide est affichée.
- Si aucune balise `<Copt>` n'est trouvée, le message
  `Aucune balise Copt trouvée.` est affiché.

---

## 4. Codes de sortie

| Code | Signification                                           |
| ---- | ------------------------------------------------------- |
| `0`  | Succès — affichage terminé normalement.                 |
| `2`  | Erreur fichier — le fichier XML n'existe pas.           |
| `3`  | Erreur XML — le fichier n'est pas un XML valide.        |

---

## 5. Exemples

### 5.1 Inspection basique

```bash
uv run src/inspect_copt.py -f datas/clean_vlm.xml
```

Sortie (extrait) :

```
[1] RENT NOOPT APOST NOSEQ SOURCE LIB MAP XREF LIST OFFSET NOADV
[2] RENT OPT(FULL) APOST NOSEQ NOADV
[3] LEINFO=(VERSION(1) MODULE(MONPGM) DATE(20240101) TIME(120000))
[4]
```

- La ligne `[4]` correspond à une balise `<Copt Val=""/>` (valeur vide).

### 5.2 Comparaison avant / après reformatage

```bash
# Avant reformatage (valeurs brutes)
uv run src/inspect_copt.py -f datas/clean_vlm.xml > /tmp/avant.txt

# Après reformatage
uv run src/inspect_copt.py -f datas/clean_vlm_copt.xml > /tmp/apres.txt

# Différences
diff /tmp/avant.txt /tmp/apres.txt
```

### 5.3 Fichier absent

```bash
uv run src/inspect_copt.py -f datas/inexistant.xml
# Erreur : le fichier 'datas/inexistant.xml' n'existe pas.
# Code de sortie : 2
```
