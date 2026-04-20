# VLM

Pipeline de traitement d'un rapport VLM (XML) vers un format interrogeable.

## Enchainnement logique

1. Traiter le fichier XML brut avec [src/clean_report.py](src/clean_report.py).
2. Traiter le XML nettoye produit avec [src/build_json.py](src/build_json.py).
3. Interroger le JSON final avec [script/export_csv.sh](script/export_csv.sh).

En resume:

XML brut -> XML nettoye -> JSON -> CSV requetable

## Prerequis

- Python 3
- jq (necessaire pour [script/export_csv.sh](script/export_csv.sh))

## Utilisation

### 1) Nettoyage du XML

Commande:

```bash
python src/clean_report.py -f datas/vlm.xml -o datas/clean_vlm.xml -e iso8859-1
```

Resultat attendu:
√
- [datas/clean_vlm.xml](datas/clean_vlm.xml)

### 2) Conversion XML -> JSON

Commande:

```bash
python src/build_json.py -f datas/clean_vlm.xml -o datas/vlm.json -e utf-8
```

Resultat attendu:

- [datas/vlm.json](datas/vlm.json)

### 3) Requetes JSON avec le script Bash

Mode global:

```bash
bash script/export_csv.sh -i datas/vlm.json -o datas/query_output.csv -g
```

Mode options de compilation:

```bash
bash script/export_csv.sh -i datas/vlm.json -o datas/query_output.csv -p
```

Mode compilateur principal:

```bash
bash script/export_csv.sh -i datas/vlm.json -o datas/query_output.csv -c
```

Filtre date optionnel (format yyyy/mm/dd):

```bash
bash script/export_csv.sh -i datas/vlm.json -o datas/query_output.csv -g -d 2026/01/01
```

Resultat attendu:

- [datas/query_output.csv](datas/query_output.csv)

## Fichiers principaux

- [src/clean_report.py](src/clean_report.py): nettoyage du rapport XML brut
- [src/build_json.py](src/build_json.py): conversion XML nettoye vers JSON
- [script/export_csv.sh](script/export_csv.sh): extraction/requetes sur le JSON
