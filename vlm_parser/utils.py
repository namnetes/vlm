# Importations de bibliothèques standard
import re

# Importations de modules locaux
from structures import Loadlib, Module, ModuleInfo, ModuleCsect


def is_blank_line(line):
    return not line.strip()


def should_ignore_line(line):
    if is_blank_line(line):
        return True

    if line.startswith("IBM File Manager for z/OS"):
        return True

    if line.startswith("---------"):
        return True

    if line.startswith("$$FILEM") and not line.startswith("$$FILEM VLM DSNIN"):
        return True

    if line.startswith("Attributes"):
        return True

    return False


def get_loadlib_name(line: str) -> str:
    """
    Extrait le nom de la Loadlib de la chaîne de caractères passée
    en paramètre.

    Cette méthode analyse la chaîne fournie pour extraire la sous-chaîne
    située entre le symbole '=' de 'DSNIN=' et la fin de la chaîne,
    marquée soit par une virgule, soit par un espace, soit par la fin de
    la chaîne. Elle renvoie le nom extrait.

    Args:
        line (str): La ligne de texte à analyser.

    Returns:
        str: Le nom de la bibliothèque extrait de la ligne.
    """

    start_index = line.find("=") + 1
    end_index = len(line)

    for delimiter in [",", " "]:
        temp_index = line.find(delimiter, start_index)
        if temp_index != -1 and temp_index < end_index:
            end_index = temp_index

    return line[start_index:end_index].strip()


def get_new_loadlib(line) -> Loadlib:
    """
    Retourne une instance d'une nouvelle loadlib dont le nom est initialisé
    """
    current_loadlib = Loadlib()
    current_loadlib.loadlib_name = get_loadlib_name(line)
    return current_loadlib


def get_new_module(line_counter) -> Module:
    """
    Retourne une instance d'un nouveau module
    """
    current_module = Module()
    current_module.info = ModuleInfo()
    current_module.CSECT = None
    current_module.line_counter = line_counter
    return current_module


def is_CSECT_name(line):

    # Séparer la chaîne en mots
    mots = line.split()

    # Vérifier qu'il y a au moins quatre mots
    if len(mots) < 4:
        return None

    premier_mot = mots[0]
    second_mot = mots[1]
    troisieme_mot = mots[2]
    quatrieme_mot = mots[3]

    # Vérifier si le second mot est exactement 'FD'
    if second_mot != "SD":
        return None

    # Vérifier que les 3e et 4e mots sont des chaînes hexadécimales de 7 caractères
    if re.fullmatch(r"[0-9A-Fa-f]{7}", troisieme_mot) and re.fullmatch(
        r"[0-9A-Fa-f]{7}", quatrieme_mot
    ):
        return premier_mot

    return None
