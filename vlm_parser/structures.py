# Importations de bibliothèques standard
import re


class ModuleCsect:
    """
    Cette classe définit les attributs du tableau des CSECT composant un
    module, tels qu'extraits par la fonction VLM d'IBM File Manager. À
    l'instar de la classe `ModuleInfo`, elle modélise des informations sur
    un module générique, indépendamment du langage (COBOL, ASSEMBLEUR, C,
    PLI, PLX, etc.). Ces données sont utilisées dans la classe `Module`,
    en complément de `ModuleInfo`, pour représenter un module contenu dans
    un PDS de type Loadlib.

    Voici la convention de nommage des symboles de CSECT définie par HLASM.

    Caractères autorisés :
    - Alphanumériques : Lettres de A à Z (sans distinction
      majuscules/minuscules) et chiffres de 0 à 9.
    - Caractères spéciaux : $, #, @ et _ (trait de soulignement).

    Longueur maximale :
    - 63 caractères si l'option GOFF est spécifiée.
    - 8 caractères si l'option GOFF n'est pas spécifiée.

    Premier caractère : Doit être une lettre.
    Espaces : Non autorisés.
    Données double octet : Non autorisées.

    Les symboles CSECT sont des symboles externes, ce qui signifie qu'ils
    sont visibles et utilisables par d'autres modules assemblés séparément.

    Lors de l'édition des liens, les symboles CSECT sont utilisés pour
    relier les différentes sections de code et former un programme
    exécutable.
    """

    def __init__(self):
        self.csect_name = str("")
        self.csect_address = str("")
        self.csect_size = str("")
        self.csect_amode = str("")
        self.csect_rmode = str("")
        self.csect_comp1 = str("")
        self.csect_comp2 = str("")
        self.csect_linked = str("")

    def set_csect_data(self, csect_name, line):
        for attr in vars(self):  # Tous les attributs = "Error"
            setattr(self, attr, "error")

        self.csect_name = csect_name

        words = line.split()
        if len(words) >= 3:
            self.csect_address = words[2]

        if len(words) >= 4:
            self.csect_size = words[3]

        if len(words) >= 5:
            armode = words[5].split("/")
            if len(armode) >= 1:
                self.csect_amode = armode[0]

            if len(armode) == 2:
                self.csect_rmode = armode[1]

        self.csect_comp1 = line[56 : 56 + 28].strip() if len(line) >= 56 else ""
        self.csect_comp2 = line[85 : 85 + 28].strip() if len(line) >= 85 else ""
        self.csect_linked = line[114 : 114 + 10].strip() if len(line) >= 114 else ""


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
        self.library_name = str("")
        self.module_name = str("")
        self.linked_date = str("")
        self.linked_time = str("")
        self.epa = str("")
        self.size = str("")
        self.ttr = str("")
        self.ssi = str("")
        self.ac = str("")
        self.amode = str("")
        self.rmode = str("")

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

    STUB_CICS = {"DFHECI"}
    STUB_DB2 = {"DSNCLI", "DSNELI", "DSNULI"}
    STUB_MQ = {
        "CSQBSTUB",
        "CSQBRRSI",
        "CSQBRSTB",
        "CSQCSTUB",
        "CSQQSTUB",
        "CSQXSTUB",
        "CSQASTUB",
    }

    def __init__(self):
        self.line_counter = 0  # A des fins de debugging
        self.DB2 = False  # Indicateur Module DB2
        self.CICS = False  # Indicateur Module CICS
        self.MQ = False  # Indicateur Module MQ
        self.Stub = False  # Indicateur d'un stub CICS, MQ ou une interface DB2
        self.info: ModuleInfo = None
        self.CSECT: list[ModuleCsect] = None

    def add_csect(self, csect: ModuleCsect) -> None:
        """Cette méthode ajoute une CSECT à la liste des CSECT."""
        self.CSECT.append(csect)
        self.CSECT_number = len(self.CSECT)


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
