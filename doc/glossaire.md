# Glossaire métier — projet VLM z/OS

Ce glossaire s'applique à toute la documentation du projet.
Les termes ci-dessous ne doivent **jamais être traduits** en français.

## Plateforme IBM Z

| Terme | Définition |
|-------|------------|
| **IBM Z** | Famille de serveurs mainframe IBM (anciennement zSeries, System z). Désignation courte : *Z* ou *z*. |
| **Mainframe** | Terme générique désignant les grands systèmes IBM à haute disponibilité. Synonyme courant d'IBM Z dans ce projet. |
| **z/OS** | Système d'exploitation 64 bits d'IBM pour les serveurs Z. Versions courantes dans ce projet : z/OS 2.5 et z/OS 3.1/3.2. |
| **z/OS 2.5** | Dernière release de la branche z/OS V2 (support jusqu'en 2027). Référence fréquente dans les environnements de production existants. |
| **z/OS 3.1 / 3.2** | Branches actives de z/OS V3 introduisant le support natif de containers Linux (zCX) et des améliorations LE. |
| **zCX** | *z/OS Container Extensions* — fonctionnalité z/OS permettant d'exécuter des containers Linux (Docker) directement sur un LPAR z/OS, sans VM intermédiaire. |
| **LPAR** | *Logical Partition* — partition logique d'un serveur IBM Z, équivalent d'une VM au niveau hardware. |
| **USS** | *Unix System Services* — sous-système z/OS fournissant un environnement POSIX (shell, utilitaires Unix) au-dessus de z/OS. Utilise l'encodage IBM-1047, à distinguer de l'environnement MVS classique (IBM-1147). |
| **z/OS Container Platform** | Offre IBM permettant de déployer et orchestrer des containers Linux sur IBM Z via Kubernetes (Red Hat OpenShift), en complément ou à la place de zCX. Vise les workloads cloud-native nécessitant une intégration forte avec les applications mainframe. |
| **z/OS Connect** | Middleware IBM exposant des services z/OS (CICS, IMS, DB2, fichiers VSAM…) sous forme d'API REST ou OpenAPI, consommables par des applications distribuées ou cloud. Permet l'intégration entre le mainframe et les architectures microservices. |

## Outils IBM

| Terme | Définition |
|-------|------------|
| **IBM File Manager** | Outil IBM de la suite z/OS Tools permettant de visualiser et manipuler des fichiers z/OS (VSAM, séquentiels, PDS…). La fonction **VLM** (View Load Module) analyse les loadlibs. |
| **VLM** | *View Load Module* — fonction IBM File Manager qui analyse le contenu des loadlibs z/OS et produit un rapport XML décrivant chaque module et ses CSECTs. |
| **LE** | *Language Environment* — environnement d'exécution commun à tous les langages HLL IBM (COBOL, PL/I, C/C++) sur z/OS. Fournit des services runtime partagés. |
| **APF** | *Authorized Program Facility* — mécanisme z/OS autorisant les programmes à exécuter des instructions privilégiées (accès système). |

## Structures de chargement

| Terme | Définition |
|-------|------------|
| **Loadlib** | *Load Library* — bibliothèque PDS ou PDSE z/OS contenant des modules exécutables. Identifiée par un nom de dataset qualifié (ex. `EXPL.BIB.CHMD.LODLIB`). |
| **Loadmod** | *Load Module* — programme exécutable stocké dans une loadlib. Correspond à un membre du PDS/PDSE. Contient une ou plusieurs CSECTs. |
| **Load Module** | Synonyme de Loadmod. Terme IBM officiel. |
| **CSECT** | *Control Section* — unité de compilation élémentaire à l'intérieur d'un loadmod. Produite par un compilateur COBOL, PL/I ou C/C++. |
| **PDS** | *Partitioned Data Set* — bibliothèque z/OS à capacité fixe. Chaque entrée est appelée *membre*. Utilisée pour les programmes (loadlibs), JCL, sources, procédures. |
| **PDSE** | *Partitioned Data Set Extended* — version étendue du PDS, à capacité dynamique et accès partagé. Recommandée pour les nouvelles loadlibs. |
| **EPA** | *Entry Point Address* — adresse du point d'entrée du loadmod. |
| **SSI** | *System Status Index* — identifiant de version/statut du loadmod sur z/OS. |
| **AC** | *Authorization Code* — indicateur de niveau d'autorisation APF du loadmod (0 = non-autorisé, 1 = autorisé). |
| **AMODE** | *Addressing Mode* — mode d'adressage du loadmod (24, 31 ou 64 bits), déterminant la taille des adresses qu'il peut référencer. |
| **RMODE** | *Residency Mode* — mode de résidence mémoire du loadmod (`24` ou `ANY`), indiquant s'il doit résider sous la ligne des 16 Mo. Champ JSON `RMODE` produit par `build_json.py` à partir de l'attribut XML `ARMODE` ; apparaît aussi comme option COPT (`RMODE(ANY)`). |
| **TTR** | Adresse physique relative (Track, Record) d'un membre dans un PDS. |
| **ASA** | *American National Standard Carriage Control Characters* — caractères de contrôle imprimante présents dans les rapports mainframe bruts, supprimés à l'étape 1 du pipeline. |

## Datasets z/OS

| Terme | Définition |
|-------|------------|
| **Dataset séquentiel** | Fichier z/OS dont les enregistrements sont lus du début à la fin, sans accès direct. Équivalent d'un fichier plat Unix. Utilisé pour les rapports, journaux, fichiers d'entrée/sortie de batch. Extension DSORG=PS. |
| **VSAM** | *Virtual Storage Access Method* — méthode d'accès IBM pour fichiers à organisation indexée (KSDS), relative (RRDS) ou séquentielle (ESDS). Utilisée pour les fichiers de référence et bases de données applicatives z/OS. IBM File Manager sait les lire et les afficher. |
| **GDG** | *Generation Data Group* — groupe de datasets versionnés automatiquement par z/OS. Chaque génération est numérotée (G0001V00, G0002V00…). Utilisé pour la gestion des fichiers historiques et des sauvegardes en batch. Le nom relatif `(0)` désigne la génération courante, `(-1)` la précédente. |
| **RECFM** | *Record Format* — format des enregistrements d'un dataset : `F` (fixe), `V` (variable), `U` (indéfini), `FB` (fixe bloqué), `VB` (variable bloqué). Détermine comment z/OS lit et écrit les enregistrements. |
| **LRECL** | *Logical Record Length* — longueur en octets d'un enregistrement logique. Pour RECFM=FB, c'est la taille fixe de chaque enregistrement. Pour RECFM=VB, c'est la longueur maximale. |
| **BLKSIZE** | *Block Size* — taille en octets d'un bloc physique sur disque. Un bloc contient un ou plusieurs enregistrements logiques. Un BLKSIZE bien choisi optimise les E/S disque. Peut être laissé à 0 pour que z/OS le calcule automatiquement (recommandé). |
| **EBCDIC** | *Extended Binary Coded Decimal Interchange Code* — encodage de caractères propriétaire IBM, natif sur z/OS. Variantes courantes : IBM-1147 en environnement MVS, IBM-1047 en USS. Les rapports mainframe bruts sont produits dans cet encodage. |
| **ISO-8859-1** | Encodage Latin-1 utilisé pour les rapports mainframe transcodés depuis l'EBCDIC (IBM-1147/IBM-1047) avant traitement par le pipeline Python. Valeur par défaut de l'option `-e`/`--encoding` de `clean_report.py` et `build_json.py`. |

## Environnement z/OS

| Terme | Définition |
|-------|------------|
| **JCL** | *Job Control Language* — langage de scripts z/OS permettant de soumettre des travaux (jobs) en batch. Un JCL décrit les étapes (`EXEC`), les datasets d'entrée/sortie (`DD`), et les paramètres d'exécution. Fichier texte stocké dans un PDS. |
| **SYSOUT** | Instruction `DD SYSOUT=*` dans un JCL — redirige la sortie d'un programme (messages, rapports) vers le spooler JES2/JES3, consultable via SDSF ou un outil équivalent. SYSOUT=A désigne l'imprimante par défaut. |
| **Programme BATCH** | Programme z/OS exécuté de façon asynchrone, soumis via un JCL et traité par le sous-système JES. N'a pas d'interface utilisateur interactive. Lit des fichiers en entrée, écrit des fichiers en sortie. Typiquement COBOL, PL/I ou Assembler. |
| **Programme TP** | *Transaction Processing* — programme z/OS exécuté sous le contrôle d'un moniteur transactionnel (CICS, IMS/TM). Déclenché par une requête utilisateur (terminal 3270, appel API). Doit être court, rapide et réentrant. Peut appeler des programmes BATCH via LINK ou XCTL. |
| **Panel ISPF** | *Interactive System Productivity Facility* — interface utilisateur en mode texte (écran 3270) de z/OS. Un panel est un écran ISPF défini par des macros, utilisé pour naviguer dans les datasets, éditer des membres PDS, soumettre des JCL. IBM File Manager est une application ISPF. |
| **TWS / OPC** | *Tivoli Workload Scheduler* (anciennement *Operations Planning and Control*) — ordonnanceur de travaux IBM pour z/OS. Planifie et enchaîne automatiquement les jobs JCL selon des calendriers, dépendances inter-jobs et conditions de déclenchement. OPC est le nom historique (z/OS), TWS le nom actuel de la suite (inclut aussi les agents distribués). Utilisé dans les environnements de production pour orchestrer les traitements batch nuit, semaine, fin de mois. |

## Options de compilation

| Terme | Définition |
|-------|------------|
| **COPT** | *Compilation Options* — options du compilateur IBM (COBOL, C/C++, PL/I) enregistrées dans chaque CSECT au moment de la compilation. |
| **LEINFO** | Pseudo-token COPT contenant des métadonnées internes au Language Environment IBM. Ce n'est **pas** une vraie option compilateur — traité séparément par `reformat_copt.py`. |
| **SMFNO** | Token COPT indiquant le numéro SMF (*System Management Facilities*) associé à la compilation — métadonnée interne au même titre que `LEINFO`. |
| **Copt@Val** | Format interne XML des options compilateur avant normalisation par `reformat_copt.py`. |
| **placeholder** | Mode de traitement LEINFO par défaut : remplace la valeur par `LEINFO=(N)` et sauvegarde les originaux dans `copt_ignored.txt`. |

## Termes du pipeline

| Terme | Définition |
|-------|------------|
| **Identify** | Code package extrait de l'attribut `Identify` d'une CSECT — troisième segment du chemin `partie1/partie2/DYxxnnnnnn`. Absent ou invalide → `null` dans le JSON. |
| **FMNBA001** | Message de démarrage émis par IBM File Manager en début de rapport VLM. Ligne de bruit ignorée à l'étape 1. |
| **FMNBA010** | Message de fin émis par IBM File Manager en fin de rapport VLM. Ligne de bruit ignorée à l'étape 1. |
| **FMNBB437** | Message informatif indiquant le nombre de membres lus dans la loadlib : `FMNBB437 N member(s) read`. Utilisé par `clean_report.py` pour alimenter l'attribut `memberCount`. |
| **FMNBE329** | Message indiquant que le PDS ne contient aucun membre : `The PDS contains no members`. Génère un bloc `<vlm>` vide avec `memberCount=0`. |
| **FMNBF427** | Message d'erreur critique IBM File Manager : loadlib inaccessible ou échec d'ouverture (`OPEN failed`). Provoque l'arrêt immédiat du pipeline avec code de sortie 1. |
| **ThreadSafe** | Flag booléen dérivé des patterns de nom de CSECT — indique si le loadmod est thread-safe. |
| **CICS** | *Customer Information Control System* — middleware transaction IBM. Flag `CICS=true` si une CSECT porte un nom caractéristique CICS. |
| **DB2** | Système de gestion de bases de données relationnelles IBM sur z/OS. Flag `DB2=true` si une CSECT porte un nom caractéristique DB2. |
| **WMQ** | *WebSphere MQ* (alias IBM MQ) — middleware de messagerie IBM. Flag `WMQ=true` si une CSECT porte un nom caractéristique MQ. |
