# Conteneurisation — Linux

Cas de référence : Docker Engine natif en `linux/amd64` (ou `linux/arm64`
sur un hôte ARM). Aucune émulation nécessaire.

## 1. Prérequis

| Outil | Rôle |
|---|---|
| [Docker Engine](https://docs.docker.com/engine/install/) | construire et exécuter le conteneur |

## 2. Construire l'image

Depuis la racine du dépôt :

```bash
make docker-build
# équivalent : docker build -t vlm-pipeline .
```

```bash
docker images vlm-pipeline
```

## 3. Préparer le volume `datas/`

Le répertoire `datas/` du dépôt sert de volume — il doit déjà contenir le
rapport brut `vlm.xml` (voir `config.toml` → `[settings] vlm_input`) :

```bash
ls datas/vlm.xml
```

## 4. Lancer le pipeline

```bash
# Pipeline complet (étapes 1 à 4)
make docker-run ARGS=run

# Sous-ensemble d'étapes (alias acceptés : clean|copt|json|extract)
make docker-run ARGS="run STEPS=2-4"
make docker-run ARGS="run STEPS=extract"
```

Équivalent `docker run` direct (ce que fait `make docker-run` en
coulisses) :

```bash
docker run --rm -v "$(pwd)/datas:/app/datas" vlm-pipeline run
docker run --rm -v "$(pwd)/datas:/app/datas" vlm-pipeline run STEPS=2-4
```

Les fichiers produits (`clean_vlm.xml`, `vlm.json`, `copt/copt.csv`,
`copt/loadlibs/**`, `pipeline.log`...) apparaissent directement dans
`./datas/` sur l'hôte.

## 5. Exporter en CSV

```bash
make docker-run ARGS=query
make docker-run ARGS="query QUERY_MODE=-p"
make docker-run ARGS="query QUERY_MODE=-c QUERY_OUTPUT=datas/compilers.csv QUERY_DATE=2026/01/01"
```

## 6. Journal et niveau de log

Ces deux cibles ont besoin d'options `docker run` supplémentaires (montage
de `config.toml`, mode interactif) que le `DOCKER_RUN_OPTS` par défaut de
`make docker-run` ne fournit pas — on les surcharge donc explicitement :

```bash
# Changer le niveau de log dans config.toml (relit par le prochain `run`)
make docker-run ARGS="log-level LOG_LEVEL=DEBUG" \
    DOCKER_RUN_OPTS='--rm -v "$(CURDIR)/datas:/app/datas" -v "$(CURDIR)/config.toml:/app/config.toml"'

# Consulter datas/pipeline.log avec less (terminal interactif)
make docker-run ARGS=log DOCKER_RUN_OPTS='--rm -it -v "$(CURDIR)/datas:/app/datas"'
```

Équivalent `docker run` direct :

```bash
docker run --rm -v "$(pwd)/datas:/app/datas" -v "$(pwd)/config.toml:/app/config.toml" \
    vlm-pipeline log-level LOG_LEVEL=DEBUG

docker run --rm -it -v "$(pwd)/datas:/app/datas" vlm-pipeline log
```

!!! note "`log-level` modifie `config.toml`"
    Cette cible utilise `sed -i` sur `config.toml`. Comme ce fichier n'est
    **pas** dans le volume `datas/` par défaut, il faut le monter
    explicitement (second `-v` ci-dessus) pour que la modification soit
    persistée sur l'hôte. `make log` nécessite `-it` (terminal interactif)
    car `less` est un programme interactif.

## 7. Nettoyage des fichiers générés

```bash
make docker-run ARGS=clean
# équivalent : docker run --rm -v "$(pwd)/datas:/app/datas" vlm-pipeline clean
```

`make clean` ne supprime jamais `datas/vlm.xml` ni le répertoire
`datas/copt/` lui-même — voir [Le Makefile](../dev/makefile.md#7-nettoyage--make-clean).

## 8. Build multi-arch (optionnel)

`make docker-build` (équivalent `docker build -t vlm-pipeline .`) ne
produit qu'**une seule image**, pour `linux/amd64`, depuis un poste Linux
x86_64 (voir [Vue d'ensemble §5](index.md#5-construire-limage)).

Pour produire une image **pour une autre architecture** (ex. `linux/arm64`
pour macOS ou `linux/s390x` pour la zCX), suivez le pas-à-pas
[Cross-build (autres architectures)](cross_build.md#3-parcours-a--depuis-linux-x86_64).
