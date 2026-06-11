# Conteneurisation — IBM Z / zCX — Déploiement

!!! warning "Procédure non testée sur une zCX réelle"
    Les commandes `docker` (build, save, load, run) sont standards et
    valables sur toute zCX. Les étapes de **transfert réseau** (SFTP,
    registre interne) dépendent en revanche de la configuration de chaque
    site et doivent être adaptées avec l'équipe systèmes.

## 1. Construire l'image pour `s390x`

Deux options, selon la disponibilité d'une machine s390x native.

### Option A — cross-build depuis Linux/macOS (émulation QEMU)

```bash
# Une seule fois : enregistre les binfmt QEMU
docker run --privileged --rm tonistiigi/binfmt --install all

docker buildx build --platform linux/s390x -t vlm-pipeline:s390x --load .
```

Cette approche a été validée sur ce projet (build + `python --version` +
`xml.etree.ElementTree` + `tomllib` fonctionnels sous émulation). Le build
est plus lent que natif mais produit une image utilisable.

### Option B — build natif sur la zCX

Si l'appliance zCX dispose elle-même de Docker (c'est le cas par
construction) et d'un accès au code source (transféré via SFTP, voir §3),
l'image peut être construite directement dedans :

```bash
docker build -t vlm-pipeline:s390x .
```

Aucune émulation requise — le résultat est identique, potentiellement plus
rapide.

## 2. Exporter / transférer l'image (Option A)

Si l'image est construite hors de la zCX, elle doit être transférée comme
fichier :

```bash
# Sur la machine de build
docker save vlm-pipeline:s390x | gzip > vlm-pipeline-s390x.tar.gz
```

Transférer `vlm-pipeline-s390x.tar.gz` vers le système de fichiers Linux de
l'appliance zCX (SFTP/SCP, **mode binaire**), puis sur la zCX :

```bash
gunzip -c vlm-pipeline-s390x.tar.gz | docker load
docker images   # vérifier que vlm-pipeline:s390x apparaît
```

!!! note "Registre interne (alternative)"
    Si le site dispose d'un registre Docker interne accessible depuis la
    zCX, préférer `docker push` / `docker pull` à l'export/import manuel —
    plus simple à reproduire et à automatiser.

## 3. Transférer le fichier d'entrée `vlm.xml`

Le rapport VLM brut (encodage `iso8859-1`, voir `config.toml`) doit être
déposé dans le répertoire qui servira de volume, par exemple :

```bash
mkdir -p ~/vlm/datas
# Transfert SFTP/SCP en mode binaire vers ~/vlm/datas/vlm.xml
```

!!! warning "Transfert binaire obligatoire"
    `vlm.xml` est en encodage mainframe `iso8859-1`. Un transfert FTP/SFTP
    en mode **texte** (ASCII) corromprait l'encodage — toujours utiliser le
    mode **binaire** (`bin` en FTP, comportement par défaut en SFTP/SCP).

## 4. Lancer le pipeline

Identique aux autres plateformes — voir [Vue d'ensemble §3](index.md#3-piloter-le-makefile-depuis-lextérieur-du-conteneur) :

```bash
docker run --rm -v ~/vlm/datas:/app/datas vlm-pipeline:s390x run
docker run --rm -v ~/vlm/datas:/app/datas vlm-pipeline:s390x query QUERY_MODE=-p
```

Les fichiers produits (`vlm.json`, `copt/copt.csv`, ...) se retrouvent dans
`~/vlm/datas/` sur le système de fichiers de l'appliance zCX, d'où ils
peuvent être récupérés (SFTP/SCP) vers z/OS UNIX System Services ou un poste
de travail.

## 5. Points ouverts à valider sur site

- **Réseau** : accès de la zCX à un registre interne, ou procédure de
  transfert de fichiers validée par l'équipe réseau/sécurité.
- **Dimensionnement** : capacité disque de l'appliance pour `datas/`
  (rapports volumineux → fichiers intermédiaires + JSON + CSV peuvent
  représenter plusieurs fois la taille du `vlm.xml` d'origine).
- **Automatisation** : si le pipeline doit tourner régulièrement, envisager
  un script shell (cron sur l'appliance, ou job z/OS déclenchant un
  `ssh ... docker run ...`) plutôt qu'une exécution manuelle.
