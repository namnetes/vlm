# Importations de bibliothèques standard
import re


class ModuleInfo:
    """
    Cette classe définit les attributs descriptifs d'un module, tels
    qu'extraits par la fonction VLM d'IBM File Manager. Elle modélise un
    module générique, indépendamment du langage (COBOL, ASSEMBLEUR, C,
    PLI, PLX, etc.), et regroupe ses caractéristiques essentielles. Ces
    informations sont utilisées dans la classe `Module`, en complément de
    `ModuleCsect`, pour représenter un module d'un PDS de Loadlib.

    La classe inclut un motif regex (`PATTERN`) permettant d'extraire des
    informations clés : nom du module, taille, TTR, SSI (optionnel), AC,
    AM, RM, directement à partir des lignes de sortie du VLM.
    """

    PATTERN = re.compile(
        r"""
        EPA\s+        # Correspond à "EPA" suivi d'un ou plusieurs espaces
        (\S+)         # Capturer le nom du module
        \s+Size\s+    # Correspond à "Size"
        (\S+)         # Capturer la taille
        \s+TTR\s+     # Correspond à "TTR"
        (\S+)         # Capturer la valeur TTR
        \s+SSI\s*     # Correspond à "SSI"
        (\S*)         # Capturer la valeur SSI (peut être vide)
        \s+AC\s+      # Correspond à "AC"
        (\S+)         # Capturer la valeur AC
        \s+AM\s+      # Correspond à "AM"
        (\S+)         # Capturer la valeur AMode
        \s+RM\s+      # Correspond à "RM"
        (\S+)         # Capturer la valeur RMode
    """,
        re.VERBOSE,
    )

    def __init__(self):
        self.library_name: str = ""
        self.module_name: str = ""
        self.linked_date: str = ""
        self.linked_time: str = ""
        self.epa: str = ""
        self.size: str = ""
        self.ttr: str = ""
        self.ssi: str = ""
        self.amode: str = ""
        self.rmode: str = ""

    def set_library_name(self, line):
        self.library_name = line.split()[2].strip()

    def set_module_name(self, line):
        self.module_name = line.split()[2].strip()

    def set_linked_on(self, line):
        self.linked_date = line.split()[2].strip()
        self.linked_time = line.split()[4].strip()

    def set_epa(self, line):
        """
        Traite la ligne EPA contenant plusieurs champs.
        """
        match = re.match(ModuleInfo.PATTERN, line)
        if match:
            self.epa = match.group(1)
            self.size = match.group(2)
            self.ttr = match.group(3)
            self.ssi = match.group(4) or ""
            self.ac = match.group(5) or ""
            self.amode = match.group(6)
            self.rmode = match.group(7)
        else:
            self.epa = "error"
            self.size = "error"
            self.ttr = "error"
            self.ssi = "error"
            self.ac = "error"
            self.amode = "error"
            self.rmode = "error"

    def __str__(self) -> str:
        """
        Retourne une représentation sous forme de chaîne de caractères des
        attributs du module pour un usage destiné à l'affichage.

        Cette méthode renvoie les informations du module au format CSV, où
        les différents attributs sont séparés par des points-virgules.
        """

        return (
            f"{self.module_name};"
            f"{self.linked_date};"
            f"{self.linked_time};"
            f"{self.epa};"
            f"{self.size};"
            f"{self.ttr};"
            f"{self.ssi};"
            f"{self.amode};"
            f"{self.rmode}"
        )


class ModuleCsect:
    """
    Cette classe définit les attributs du tableau des CSECT composant un
    module, tels qu'extraits par la fonction VLM d'IBM File Manager. À
    l'instar de la classe `ModuleInfo`, elle modélise des informations sur
    un module générique, indépendamment du langage (COBOL, ASSEMBLEUR, C,
    PLI, PLX, etc.). Ces données sont utilisées dans la classe `Module`,
    en complément de `ModuleInfo`, pour représenter un module contenu dans
    un PDS de type Loadlib.
    """

    def __init__(self):
        self.csect_name: str = ""
        self.csect_address: str = ""
        self.csect_size: str = ""
        self.csect_amode: str = ""
        self.csect_rmode: str = ""
        self.csect_comp1: str = ""
        self.csect_comp2: str = ""
        self.csect_linked: str = ""

    def __str__(self) -> str:
        """
        Retourne une représentation sous forme de chaîne de caractères des
        attributs d'une CSECT pour un usage destiné à l'affichage.

        Cette méthode renvoie les informations de la CSECT au format CSV, où
        les différents attributs sont séparés par des points-virgules.
        """

        return (
            f"{self.csect_name};"
            f"{self.csect_address};"
            f"{self.csect_size};"
            f"{self.csect_amode};"
            f"{self.csect_rmode};"
            f"{self.csect_comp1};"
            f"{self.csect_comp2};"
            f"{self.csect_linked}"
        )


class Module:
    """
    La classe `Module` représente un module générique extrait d'un PDS de
    type Loadlib, indépendamment du langage (COBOL, ASSEMBLEUR, C, PLI,
    PLX, etc.). Elle regroupe les informations détaillées sur le module,
    telles qu'extraites par la fonction VLM d'IBM File Manager.

    Cette classe utilise les informations modélisées par les classes
    `ModuleInfo` et `ModuleCsect`, qui décrivent respectivement les
    métadonnées du module et des CSECT qui le composent.

    Elle permet de rassembler ces éléments et de fournir une vue complète
    d'un module au sein d'un PDS de Loadlib. Les données recueillies sont
    ensuite utilisées pour des analyses ou pour générer des fichiers de
    sortie comme un fichier CSV.
    """

    def __init__(self):
        self.line_counter = 0  # A des fins de debugging
        self.info: ModuleInfo = None
        self.CSECT: list[ModuleCsect] = []

    def __str__(self) -> str:
        """
        Retourne une représentation sous forme de chaîne de caractères des
        informations du module, incluant les détails du module et de ses
        CSECT.

        Cette méthode renvoie la représentation des classes `ModuleInfo`
        et `ModuleCsect` associées au module. Elle compile ainsi les
        informations collectées par les méthodes `__str__` de ces deux
        classes. Si aucune information n'est disponible pour le module,
        la méthode renvoie la chaîne `No module information is available.`
        """

        if self.info:
            return f"{self.line_counter};{self.info}"
        else:
            return "No module information is available."


class Loadlib:
    """
    La classe `Loadlib` constitue une représentation d'un PDS de Loadlib,
    dans lequel sont stockés plusieurs modules. Elle permet de gérer les
    modules présents, d'extraire des informations pertinentes les concernant
    et de fournir une représentation structurée de l'ensemble.
    """

    def __init__(self, loadlib_name: str = ""):
        self.loadlib_name: str = loadlib_name
        self.loadlib_modules: list[Module] = []

    def add_module(self, module: Module) -> None:
        """Cette méthode ajoute un module à la liste des modules."""
        self.loadlib_modules.append(module)

    def __str__(self) -> str:
        """
        Retourne une représentation structurée de la Loadlib sous forme de
        chaîne de caractères.

        Cette méthode génère une sortie détaillée pour chaque module dans
        la Loadlib, affichant :
        - Le nom de la Loadlib
        - Le nombre de modules contenus dans la loadlib
        - Les informations générales du module
        - Pour chaque module, les informations de chaque CSECT sont ajoutées

        Ainsi, pour une Loadlib comportant trois modules, dont les CSECT
        respectives se comptent à 13, 25 et 31, l'affichage total se composera
        de 31 + 25 + 13 lignes, soit 69 lignes au total.

        La sortie est formatée en CSV, où chaque ligne représente soit
        les informations d'un module, soit celles de ses CSECT. Ainsi,
        vous aurez une ligne pour chaque CSECT, permettant de visualiser
        facilement la hiérarchie des modules et des CSECT qui les
        composent.
        """

        # Initialiser une liste vide pour les lignes de sortie
        output_lines = []

        if not self.loadlib_modules:
            line = f"{self.loadlib_name}{';' * 10}"
            output_lines = [line]
        else:
            # Parcourir chaque module dans self.loadlib_modules
            for module in self.loadlib_modules:
                # Créer une chaîne de caractères formatée pour chaque module
                line = f"{self.loadlib_name};{str(module)}"
                # Ajouter cette ligne à la liste output_lines
                output_lines.append(line)

        return "\n".join(output_lines)


class Loadlibs:
    """
    La classe `Loadlibs` représente une collection de PDS de Loadlib, chacune
    contenant de zéro à n modules.
    """

    def __init__(self):
        self.loadlibs: list[Loadlib] = []

    def add_loadlib(self, loadlib: Loadlib) -> None:
        """Ajouter un PDS de Loadlib à la collection."""
        self.loadlibs.append(loadlib)

    def __str__(self) -> str:
        """
        Retourne une représentation sous forme de chaîne de caractères du
        contenu de chaque PDS de Loadlib de la collection.
        """

        # Partie pour les loadlibs présents
        loadlibs_str = ""
        for loadlib in self.loadlibs:
            loadlibs_str += str(loadlib) + "\n"

        # Retirer le dernier retour à la ligne si nécessaire
        loadlibs_str = loadlibs_str.rstrip()

        # Construire la chaîne finale seulement si nécessaire
        return f"{loadlibs_str}"
