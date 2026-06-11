# Conteneurisation — macOS (Apple Silicon)

Cas visé : Mac Apple Silicon (M4) avec **Docker Desktop**. L'image
`python:3.12-alpine` étant disponible en `linux/arm64/v8`, le conteneur
tourne **nativement** dans la VM Linux de Docker Desktop — aucune émulation
Rosetta n'est nécessaire.

## 1. Prérequis

| Outil | Rôle |
|---|---|
| [Docker Desktop pour Mac (Apple Silicon)](https://docs.docker.com/desktop/install/mac-install/) | moteur Docker + VM Linux ARM64 |

## 2. Construire et exécuter

Les commandes sont **identiques à Linux** — voir la
[page Linux](linux.md) pour le détail des cibles (`run`, `query`,
`log-level`, `log`, `clean`).

```bash
docker build -t vlm-pipeline .
docker run --rm -v "$(pwd)/datas:/app/datas" vlm-pipeline run
```

`docker build` produit ici une image `linux/arm64/v8` par défaut — c'est le
comportement voulu (build natif, pas d'émulation).

## 3. Spécificités macOS

### Performance des volumes (bind mounts)

Docker Desktop sur Apple Silicon utilise **VirtioFS** par défaut depuis la
version 4.6, ce qui rend les bind mounts (`-v "$(pwd)/datas:/app/datas"`)
nettement plus rapides que l'ancien `osxfs`. Aucune option supplémentaire
(`:cached`, `:delegated`) n'est nécessaire ni recommandée.

!!! tip "Vérifier que VirtioFS est actif"
    Docker Desktop → *Settings* → *General* → *Virtual Machine Options* →
    *VirtioFS* doit être sélectionné (réglage par défaut sur les
    installations récentes).

### Mémoire allouée à la VM

Le pipeline charge le rapport VLM XML en mémoire (`xml.etree`). Pour de gros
rapports, vérifier que la VM Docker Desktop dispose d'assez de RAM :
*Settings* → *Resources* → *Memory*.

### `make log` et terminal interactif

Comme sur Linux, `make log` (qui ouvre `less`) nécessite `-it` :

```bash
docker run --rm -it -v "$(pwd)/datas:/app/datas" vlm-pipeline log
```

## 4. Build multi-arch depuis macOS

`make docker-build` (équivalent `docker build -t vlm-pipeline .`) ne
produit qu'**une seule image**, pour `linux/arm64`, construite nativement
sur ce Mac (voir [Vue d'ensemble §5](index.md#5-construire-limage)).

Pour produire une image **pour une autre architecture** (ex. `linux/amd64`
pour un poste Linux ou `linux/s390x` pour la zCX), suivez le pas-à-pas
[Cross-build (autres architectures)](cross_build.md#4-parcours-b--depuis-macos-apple-silicon-m4) —
Docker Desktop embarque déjà les binfmts QEMU nécessaires, aucune
installation supplémentaire n'est requise.
