import sys
import time
import io
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, List, Union, Dict, Set


def read_file(
    infile: Union[io.TextIOWrapper, None], filepath: str, encoding: str
) -> Tuple[Union[io.TextIOWrapper, None], str, int, int, Optional[int], str]:
    """
    Lit par appel successif le contenu d'un fichier texte par bloc de lignes.

    La fin d'un bloc est marquée par une ligne normalisée qui commence par la
    chaîne de caractères "FMNBB437" ou "FMNBE329".

    Dès que la fin du fichier est atteinte, le fichier est fermé.

    Ouvre le fichier lors du premier appel.

    Remarques:
    - Les caractères de fin de ligne '\n' peuvent apparaître à n'importe quel
    endroit dans le segment XML, scindant ainsi une balise XML en deux parties.
    Ce phénomène peut compliquer la recherche de sous-chaînes de caractères
    réparties sur deux lignes distinctes. Par exemple, cela peut poser des
    problèmes pour trouver du texte dans des valeurs d'attributs entourées de
    guillemets doubles.
    - IBM utilise historiquement des caractères ASA dans ses fichiers pouvant
    être imprimés. La première colonne du fichier leur est réservée et doit
    donc être ignorée:
        Exemple de caractères ASA courants :
            ' ' (espace) : Saut de ligne simple.
            '0' : Saut de ligne double.
            '-' : Saut de ligne triple.
            '+' : Aucune action (impression immédiate).
            '1' : Éjection de page.

    Args:
        infile (Union[io.TextIOWrapper, None]) : Objet de fichier texte ouvert,
        ou None si premier appel.
        filepath (str) : Chemin vers le fichier à lire.
        encoding (str) : Encodage utilisé pour lire le fichier.

    Returns:
        Tuple[Union[io.TextIOWrapper, None], str, int, int] : Tuple contenant :
        - L'objet de fichier texte (ou None si fermé).
        - Le bloc de lignes lu en tant que chaîne de caractères.
        - Le numéro de ligne où la balise de début <vlm> a été trouvée.
        - Le numéro de ligne où la balise de fin </vlm> a été trouvée.
        - Le nombre de load modules présents dans la loadlib, ou None si le
        code message n'était pas celui attendu !
        - Le nom de loadlib

    Raises:
        FileNotFoundError :
        - Si le fichier spécifié par 'filepath' est introuvable.
        UnicodeDecodeError :
        - Si l'encodage spécifié n'est pas valide pour le fichier.
        Exception :
        - Pour capturer toutes les autres erreurs inattendues.
    """
    lines: List[str] = []
    line: str = ""
    line_count: int = 0
    xml_start: int = 0
    xml_end: int = 0
    modules_count: Optional[int] = None
    loadlib_name: str = ""

    excludes: Set[str] = {
        "IBM File",
        "FMNBA001",
        "FMNBA010",
        "DEFAULT SET",
        "PRINTOUT=",
        "PRINTLEN=",
        "PAGESIZE=",
        "PRTTRANS=",
        "SMFNO=",
        "TEMP UNIT=",
        "PERM UNIT=",
        "TRACECLS=",
        "$$FILEM",
    }

    try:
        if infile is None:
            infile = open(filepath, "r", encoding=encoding)

        while True:
            line = infile.readline()
            if not line:  # Fin du fichier atteinte!
                break

            line_count += 1

            # Ignorer le premier caractère qui est réservé a un caractère ASA
            line = line[1:]

            if line.startswith("$$FILEM VLM DSNIN="):
                loadlib_name = line.split("=")[1].rstrip(",\n")
                continue
            # Cette ligne indique la fin du bloc de lignes et, par conséquent,
            # interrompt la lecture jusqu'au prochain appel. C'est aussi elle
            # qui précise le nombre de load modules présents dans la loadlib.
            elif any(line.startswith(prefix) for prefix in ["FMNBB437", "FMNBE329"]):
                modules_count = process_fmnb_message(line)
                break

            # Exclure certaines lignes dont les lignes vides
            if not line.strip() or any(line.startswith(prefix) for prefix in excludes):
                continue

            # si la ligne contenant la balise de début <vlm> ou de fin </vlm>
            if xml_start == 0 and line.startswith("<vlm>"):
                xml_start = line_count
            elif xml_end == 0 and line.startswith("</vlm>"):
                xml_end = line_count

            # Ajouter la ligne aux résultats à retourner
            lines.append(line)

        if not line:  # Si fin de fichier atteinte
            infile.close()
            infile = None

    except FileNotFoundError:
        print(f"Erreur : fichier '{filepath}' introuvable.")
        raise
    except UnicodeDecodeError:
        print(
            f"Erreur : encodage '{encoding}' non valide pour le fichier '{filepath}'."
        )
        raise
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")
        raise

    if modules_count is None and xml_start > 0:
        if infile is not None and not infile.closed:
            infile.close()
            infile = None
        print(
            "Erreur : Alors qu'un xml existe, aucune ligne avec le code message "
            "'FMNBB437' ou 'FMNBE329' n'a été trouvée. Elle était attendue "
            "immédiatement après la balise fermante </vlm>."
        )

    return infile, "\n".join(lines), xml_start, xml_end, modules_count, loadlib_name


def process_fmnb_message(fmnb_line: str) -> Optional[int]:
    """
    Cette fonction traite une ligne de message générée par File Manager et
    retourne le nombre de load modules présents dans la loadlib ou indique
    que la loadlib ne contient aucun membre.

    Messages standardisés attendus :
    - 'FMNBB437 xxx Member(s) Read' : où `xxx` indique le nombre de load
      modules présents dans la loadlib_name.
    - 'FMNBE329 The PDS Contains No Members.' : indique que la loadlib_name ne
      contient aucun membre.

    Args:
        fmnb_line (str): Ligne de message FMNB à analyser.

    Returns:
        Optional[int]: Nombre de load modules si le message est 'FMNBB437',
        0 si le message est 'FMNBE329', ou None si le message n'est pas
        reconnu.

    Raises:
        ValueError: Si le format du message FMNB est incorrect.
    """
    # Récupère le premier mot de la ligne
    msg_code: str = fmnb_line.split()[0] if fmnb_line else ""

    # Liste des codes de messages standardisés attendus.
    known_messages: list[str] = ["FMNBB437", "FMNBE329"]

    # Si le code message n'est pas connu...
    if msg_code not in known_messages:
        return None

    # Retourne le nombre de modules indiqué par le mot suivant le code message
    # si celui-ci est "FMNBB437", sinon retourne 0.
    return int(fmnb_line.split()[1]) if msg_code == "FMNBB437" else 0


def log_current_xml(xml: str, logfile: str):
    """
    Écrit le contenu XML fourni dans un fichier log spécifié.

    Cette fonction ouvre le fichier de log en mode écriture, écrit le
    contenu XML fourni dans ce fichier et ferme le fichier.

    Args:
        xml (str): Chaîne de caractères contenant le contenu XML à écrire
        dans le fichier de journal.
        logfile (str): Chemin du fichier log où le contenu XML sera écrit.

    Remarques:
        Si le fichier de journal spécifié par `logfile` n'existe pas, il
        sera créé. Si le fichier existe déjà, son contenu sera écrasé.
    """
    with open(logfile, "w") as file:
        file.write(xml)


def sanitize_xml(xml: str) -> str:
    """
    Échappe les caractères spéciaux dans une chaîne XML tout en conservant les
    guillemets doubles non échappés à l'intérieur des valeurs d'attributs.

    Cette fonction parcourt chaque caractère de la chaîne XML d'entrée et
    remplace les caractères spéciaux par leurs entités XML correspondantes.
    Elle conserve les guillemets doubles intacts lorsqu'ils se trouvent dans
    des valeurs d'attributs, ce qui permet de préserver la validité des
    attributs XML. Les remplacements sont effectués uniquement pour les
    caractères compris entre deux guillemets doubles.

    Caractères remplacés :
    - '&'  -> '&amp;'
    - '<'  -> '&lt;'
    - '>'  -> '&gt;'
    - '"'  -> '&quot;'
    - "'"  -> '&apos;'

    Remarques:
        La méthode `append` de la liste `escaped_xml` ajoute un élément à
        la fin de la liste. Ainsi, `escaped_xml.append(escape_map[char])`
        ajoute la valeur échappée correspondante du caractère spécial `char`
        à la liste `escaped_xml`. Par exemple, si `char` est '&', la valeur
        échappée `&amp;` est ajoutée à la liste.

        Le dictionnaire `escape_map` est utilisé pour associer chaque
        caractère spécial à son entité XML correspondante. Lorsqu'un
        caractère est trouvé dans le dictionnaire `escape_map`, la valeur
        associée (par exemple, `&amp;` pour `&`) est ajoutée à la liste
        `escaped_xml`. Cela garantit que chaque occurrence de ce caractère
        est remplacée correctement dans le texte échappé.

        Un dictionnaire est une collection de paires clé-valeur. Dans ce
        contexte, escape_map[char] renvoie la valeur associée à la clé
        'char'.

    Args:
        xml (str): Chaîne de caractères contenant le XML à assainir.

    Returns:
        str: Chaîne XML avec les caractères spéciaux échappés.

    """
    escape_map: dict[str, str] = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;",
    }

    in_quotes: bool = False
    escaped_xml: List = []

    for char in xml:
        if char == '"':
            in_quotes = not in_quotes
            escaped_xml.append(char)
        elif in_quotes and char in escape_map:
            escaped_xml.append(escape_map[char])
        else:
            escaped_xml.append(char)

    return "".join(escaped_xml)


def parse_xml(xml_content: str) -> ET.Element:
    """
    Parse le contenu XML et retourne l'élément racine.

    Cette fonction utilise la méthode `fromstring` du module
    `xml.etree.ElementTree` pour parser une chaîne de caractères contenant
    du XML et retourne l'élément racine de la structure XML résultante.

    Args:
        xml_content (str): Chaîne de caractères contenant le contenu XML
        à parser.

    Returns:
        xml.etree.ElementTree.Element: Élément racine de la structure
        XML parsée.

    Raises:
        xml.etree.ElementTree.ParseError: Si le contenu XML fourni
        n'est pas bien formé.

    Remarques:
        La fonction `fromstring` lève une exception
        `xml.etree.ElementTree.ParseError` si le contenu XML n'est pas
        bien formé. Il est donc important de gérer cette exception lors
        de l'appel à `parse_xml`.
    """
    return ET.fromstring(xml_content)


def process_xml(root: ET.Element, xml_start: int, loadlib_name: str) -> int:
    """
    Traite les éléments 'Loadmod' et 'CSECT' présents dans le contenu XML.

    Cette fonction parcourt les éléments 'Loadmod' du contenu XML et traite
    chaque 'CSECT' qui compose le 'Loadmod'. Les informations extraites sont
    utilisées pour générer une sortie CSV.

    La balise <Loadmod> est parente de la balise <CSECT> et contient tous les
    attributs du load module. La balise <CSECT> est parente de la balise
    <Copt> et renferme tous les attributs de la CSECT. La balise <Copt>
    contient toutes les options de compilation de la CSECT sous forme
    d'attributs. Il n'y a généralement pas d'options de compilation indiquées
    pour les modules assembleur, PL/I ou PL/X d'IBM.

    Args:
        root (xml.etree.ElementTree.Element): Élément racine du contenu XML.
        xml_start (int): Numéro de la ligne où commence le contenu XML.
        loadlib_name (str): Nom de la loadlib.

    Returns:
        int: Le nombre de load modules traités.

    Remarques:
        - La fonction `extract_loadmod_attributes` est utilisée pour extraire
        les attributs de chaque 'Loadmod'.
        - La fonction `extract_csect_attributes` est utilisée pour extraire
        les attributs de chaque 'CSECT'.
        - Les stubs sont déterminés à l'aide de la fonction `determine_stubs`.
        - Les lignes résultantes sont stockées dans `csv_output` et intégrées
        avec des flag de stubs à l'aide de la fonction `integrate_stub_flags`.
        - Chaque ligne résultante est convertie en chaîne CSV et imprimée.
    """
    for idx, loadmod in enumerate(root.findall("Loadmod")):
        # Déclaration de la variable csv_output qui contiendra les données
        # formatées pour une sortie CSV. Cette liste sera une liste de listes,
        # où chaque sous-liste représente une ligne du fichier CSV.

        # Type de la variable csv_output :
        # List[List[Union[str, Dict[bool, str]]]]
        #  - La liste externe (List[...]) contient plusieurs lignes du CSV.
        #  - Chaque ligne est elle-même une liste (List[...]) de différentes
        #    valeurs.
        #  - Les valeurs dans chaque ligne peuvent être de deux types
        #    différents :
        #    1. str : Une chaîne de caractères, représentant typiquement un
        #       attribut ou une valeur textuelle.
        #    2. Dict[bool, str] : Un dictionnaire dont les clés sont de type
        #       booléen et les valeurs de type chaîne de caractères. Ce
        #       dictionnaire est utilisé pour représenter des paires
        #       clé-valeur spécifiques où la clé est un booléen et la valeur
        #       est une chaîne.

        csv_output: List[List[Union[str, Dict[bool, str]]]] = []

        # Recherche les attributs du LOAD MODULE.
        line_module: list[str] = extract_loadmod_attributes(loadmod)

        # Recherche en boucle les attributs de chaque CSECT qui composent le
        # load module.
        for csect in loadmod.findall("CSECT"):
            if csect.attrib.get("Type") != "SD":
                continue

            # Recehrche les attributs de la CSECT
            line_csect: List[str] = extract_csect_attributes(csect)
            csect_name: str = line_csect[0]
            stubs: Dict[str, bool] = determine_stubs(csect_name)

            # Définit la ligne.
            row: List[Union[str, Dict[bool, str]]] = []
            row.append(stubs)
            row.append(str(xml_start))
            row.append(str(idx + 1))
            row.append(loadlib_name)
            row.extend(line_module)
            row.extend(line_csect)

            # Ajoute la ligne à la liste résultat.
            csv_output.append(row)

        # Il faut intégrer/propager la notion de stub au load module
        csv_output = integrate_stub_flags(csv_output)

        # A ffichage du résultat sur la sortie standard
        for rowline in csv_output:
            csv_string = ";".join(rowline)
            print(csv_string)

    return idx + 1


def extract_loadmod_attributes(loadmod: ET.Element) -> List[str]:
    """
    Extrait les attributs d'une balise 'Loadmod'.

    Cette fonction parcourt les attributs d'un élément 'Loadmod' et extrait
    les valeurs associées. Chaque balise 'Loadmod' correspond à un load
    module présent dans la `loadlib`.

    Args:
        loadmod (xml.etree.ElementTree.Element): Élément 'Loadmod' contenant
        les attributs à extraire.

    Returns:
        List[str]: Liste des valeurs d'attributs extraites de l'élément
        'Loadmod'.

    Remarques:
        Les attributs extraits incluent :
        - "Name": Nom du load module.
        - "Linkedon": Date de linkedit du load module.
        - "Linkedat": Heure de linkedit du load module.
        - "EPA": Adresse d'entrée du load module.
        - "MSize": Taille du load module.
        - "TTR": Référence de piste/cylindre du load module.
        - "SSI": Identifiant système du load module.
        - "AC": Code d'autorisation du load module.
        - "AM": (AMODE) Mode d'adresse du load module.
        - "RM": (RMODE) Mode de réinstallation en mémoire du load module.
        - "RENT": Indicateur de réentrance du load module.
        - "REUS": Indicateur de réutilisation du load module.
    """
    return [
        loadmod.attrib.get("Name", ""),
        loadmod.attrib.get("Linkedon", ""),
        loadmod.attrib.get("Linkedat", ""),
        loadmod.attrib.get("EPA", ""),
        loadmod.attrib.get("MSize", ""),
        loadmod.attrib.get("TTR", ""),
        loadmod.attrib.get("SSI", ""),
        loadmod.attrib.get("AC", ""),
        loadmod.attrib.get("AM", ""),
        loadmod.attrib.get("RM", ""),
        loadmod.attrib.get("RENT", ""),
        loadmod.attrib.get("REUS", ""),
    ]


def extract_csect_attributes(csect: ET.Element) -> List[str]:
    """
    Extrait les attributs d'une balise 'CSECT'.

    Cette fonction parcourt les attributs d'un élément 'CSECT' et extrait les
    valeurs associées. Chaque balise 'CSECT' correspond à une section de
    code (CSECT) qui compose le load module.

    Args:
        csect (xml.etree.ElementTree.Element): Élément 'CSECT' contenant les
        attributs à extraire.

    Returns:
        List[str]: Liste des valeurs d'attributs formatées en CSV.

    Remarques:
        - La balise 'Identify' est utilisée pour extraire le package ChangeMan
          C'est le dernier segment de sa valeur (séparé par '/').
        - La balise 'Copt' contient les options de compilation de la CSECT
          sous forme d'attributs. Ces options sont stockées dans une liste.
        - Les attributs extraits incluent :
            - "Name": Nom de la CSECT.
            - "Address": Adresse de la CSECT.
            - "Size": Taille de la CSECT.
            - "ARMode": (AMODE) Mode d'adressage de la CSECT.
            - "Compiler1": Compilateur utilisé pour générer la CSECT.
            - "Date": Date de compilation de la CSECT.
            - Package : Paquetage de la CSECT.
            - Options: Nombre d'options de compilation de la CSECT.
    """
    package: str = "None"
    identify: ET.Element = csect.find("Identify")
    if identify is not None:
        i: list = identify.attrib.get("Val").split("/")
        package = i[-1]

    copt: ET.Element = csect.find("Copt")
    options: list[str] = []
    if copt is not None:
        options = copt.attrib.get("Val").split()

    return [
        csect.attrib.get("Name", ""),
        csect.attrib.get("Address", ""),
        csect.attrib.get("Size", ""),
        csect.attrib.get("ARMode", ""),
        csect.attrib.get("Compiler1", ""),
        csect.attrib.get("Date", ""),
        package,
        str(len(options)),
    ]


def determine_stubs(csect_name: str) -> Dict[str, bool]:
    """
    Détermine si le nom de la CSECT correspond à un STUB CICS, DB2 ou WMQ.

    Cette fonction vérifie si le nom de la CSECT fourni correspond à un
    STUB CICS, DB2 ou WMQ. Elle retourne un dictionnaire indiquant
    la présence de chaque type de STUB.

    Args:
        csect_name (str): Nom de la section à vérifier.

    Returns:
        Dict[str, bool]: Dictionnaire avec des indicateurs pour CICS, DB2
        et WMQ.

    Remarques:
    Pour ce qui concerne CICS et WMQ, le terme "stub" est tout à fait
    approprié. En revanche, pour DB2, il serait plus précis de parler d’un
    module d’interface. Que les puristes me pardonnent cette simplification.
    """
    # Dictionnaire des STUBS avec des ensembles pour chaque type de STUB
    STUBS = {
        "CICS": {"DFHECI"},
        "DB2": {"DSNCLI", "DSNELI", "DSNULI"},
        "WMQ": {
            "CSQBSTUB",
            "CSQBRRSI",
            "CSQBRSTB",
            "CSQCSTUB",
            "CSQQSTUB",
            "CSQXSTUB",
            "CSQASTUB",
        },
    }

    # Initialisation du dictionnaire de résultats avec des valeurs booléennes
    return {
        "CICS": csect_name in STUBS["CICS"],
        "DB2": csect_name in STUBS["DB2"],
        "WMQ": csect_name in STUBS["WMQ"],
    }

    # Analyse de la compréhension de dictionnaire utilisée dans le return :
    #
    # Étape 1 : STUBS.items() retourne les paires clé-valeur de STUBS
    # - Chaque paire contient :
    #   - Une clé (par ex. : "CICS", "DB2", "WMQ").
    #   - Un ensemble (set) contenant les modules associés (par ex. :
    #     {"DFHECI"}, {"DSNCLI", "DSNELI", "DSNULI"}, etc.).
    #
    # Étape 2 : La boucle for key, modules in STUBS.items()
    # - Cette boucle parcourt chaque paire clé-valeur dans STUBS :
    #   - `key` correspond à la clé (par ex. : "CICS").
    #   - `modules` correspond à l'ensemble des modules associés à cette clé.
    #
    # Étape 3 : La vérification csect_name in modules
    # - Pour chaque clé, on vérifie si la variable `csect_name` (une chaîne
    #   de caractères) appartient à l'ensemble `modules`.
    # - Résultat :
    #   - Si `csect_name` est dans `modules`, le résultat est `True`.
    #   - Sinon, le résultat est `False`.
    #
    # Étape 4 : Création du dictionnaire de sortie
    # - Pour chaque clé, on associe le résultat de la vérification comme
    #   valeur :
    #   Exemple avec csect_name = "DFHECI" :
    #   {
    #     "CICS": True,  # "DFHECI" est dans l'ensemble associé à "CICS".
    #     "DB2": False,  # "DFHECI" n'est pas dans l'ensemble associé à "DB2".
    #     "WMQ": False,  # "DFHECI" n'est pas dans l'ensemble associé à "WMQ".
    #   }
    return {key: csect_name in modules for key, modules in STUBS.items()}


def integrate_stub_flags(
    csv_output: List[List[Union[str, Dict[bool, str]]]]
) -> List[List[Union[str, Dict[bool, str]]]]:
    """
    Integre les indicateurs de stubs CICS, DB2 et WMQ dans les lignes CSV.

    Cette fonction reformate `csv_output`, une liste structurée pour
    représenter les informations d'un load module.

    Les informations sont divisées en deux catégories :
    1. générales pour le module
    2. spécifiques pour chaque CSECT.

    Args:
        csv_output (List[List[Union[str, Dict[bool, str]]]]): Liste des
        lignes CSV à reformater.

    Returns:
        List[List[Union[str, Dict[bool, str]]]]: Liste reformattée des
        lignes CSV.

    Remarques:
    - `csv_output` est une liste où chaque élément est une sous-liste.
    - Chaque sous-liste contient des informations générales du module
      et des informations spécifiques au CSECT correspondant.
    - Un dictionnaire Python est ajouté au début de chaque sous-liste
      pour indiquer si la CSECT correspond à un stub CICS, DB2 ou WMQ.
    - Cette notion de stub est applicable globalement au load module et
      doit-être intégrée aux données globales du module.
    - Le dictionnaire est remplacé par trois chaînes de caractères
      ("CICS", "DB2" ou "WMQ") si l'état booléen est True, ou par des
      chaînes vides si l'état est False.
    - Les indicateurs de stubs sont insérés juste avant les éléments
      CSECT dans l'ordre CICS, DB2 et WMQ.
    """

    cics_flag: str = ""
    db2_flag: str = ""
    wmq_flag: str = ""
    stubs: Dict[str, bool] = {}

    for row in csv_output:
        stubs = row[0]
        del row[0]
        if isinstance(stubs, dict):
            cics_flag = "CICS" if cics_flag or stubs["CICS"] else cics_flag
            db2_flag = "DB2" if db2_flag or stubs["DB2"] else db2_flag
            wmq_flag = "WMQ" if wmq_flag or stubs["WMQ"] else wmq_flag

    # Les indicateurs de stubs sont insérés juste avant les éléments CSECT
    # dans l'ordre CICS, DB2 et WMQ.
    for row in csv_output:
        row.insert(14, wmq_flag)
        row.insert(14, db2_flag)
        row.insert(14, cics_flag)

    return csv_output


def main(filepath: str, encoding: str):
    """
    Lit le fichier en entrée, remplace les caractères,
    extrait et parse le contenu XML, puis traite chacune des balises.

    Args:
        filepath str : le fichier à traiter
        encoding str : l'encodage a utiliser pour lire le fichier à traiter
    """
    infile: io.TextIOWrapper = None
    xml: str = ""
    xml_start: int = 0
    xml_end: int = 0
    modules_count: int = 0
    loadlib_name: str = ""

    infile, xml, xml_start, xml_end, modules_count, loadlib_name = read_file(
        infile, filepath, encoding
    )

    while infile:
        if modules_count > 0:
            # Enregistrer l'XML dans un fichier, principalement pour faciliter le
            # débogage en cas d'anomalies comme celle-ci."
            # --------------------------------------------------------------------
            # Traceback (most recent call last):
            #   File "/home/dagoba/workspaces/vlm/vlm.py", line 472, in <module>
            #     main()
            #   File "/home/dagoba/workspaces/vlm/vlm.py", line 460, in main
            #     root: ET.Element = parse_xml(xml)
            #                        ^^^^^^^^^^^^^^
            #   File "/home/dagoba/workspaces/vlm/vlm.py", line 180, in parse_xml
            #     return ET.fromstring(xml_content)
            #            ^^^^^^^^^^^^^^^^^^^^^^^^^^
            #   File "/usr/lib/python3.12/xml/etree/ElementTree.py", line 1335, in
            #      XML parser.feed(text)
            # xml.etree.ElementTree.ParseError: not well-formed (invalid token):
            # line 7010, column 123
            # ----------------------------------------------------------------------
            log_current_xml(xml, "datas/current_xml.log")

            # En XML, certains caractères spéciaux doivent être échappés pour être
            # bien formés.
            xml = sanitize_xml(xml)
            log_current_xml(xml, "datas/current_xml_escaped.log")

            # print(
            #     f"L'xml n° {idx+1} à été détectée à la ligne {xml_start} "
            #     f"et il correspond à la loadlib_name {loadlib_name} "
            #     f"de {modules_count} load modules"
            # )
            # if xml_start is not None:
            root: ET.Element = parse_xml(xml)
            modules_processed = process_xml(root, xml_start, loadlib_name)
            if modules_count != modules_processed:
                print(
                    f"Erreur: {modules_processed} load modules traités pour "
                    f"{modules_count} annoncé(s).\n"
                    f"XML s'étendant de la ligne {xml_start} à {xml_end}, "
                    f"pour {loadlib_name}."
                )

        # lecture du bloc de lignes suivant s'il existe
        infile, xml, xml_start, xml_end, modules_count, loadlib_name = read_file(
            infile, filepath, encoding
        )


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python vlm.py <filepath>")
        print(" <filepath> \t nom du fichier des VLM File Manager à traiter")
        sys.exit(1)

    encoding: str = "latin-1"
    filename: str = sys.argv[1]

    start_time = time.time()

    main(filename, encoding)

    end_time = time.time()
    print(f"Le temps d'exécution est de {end_time - start_time} secondes")
