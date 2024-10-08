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
    current_module.CSECT = ModuleCsect()
    current_module.line_counter = line_counter
    return current_module


def is_loadlib_not_processing(
    error_handler, current_loadlib: Loadlib, line_counter: int
) -> bool:

    if current_loadlib is None:
        error_handler.log_error("End of loadlib section detected.")
        error_handler.log_error(
            f"Line number read from the input file is {line_counter}."
        )
        error_handler.log_error(f"No loadlib is currently being processed.")
        return True  # True pour indiquer qu'une erreur a été détectée
    return False  # Aucun problème détecté


def is_module_not_processing(
    error_handler, current_module: Module, line_counter: int
) -> bool:

    if current_module is None:
        error_handler.log_error("End of module section detected.")
        error_handler.log_error(
            f"Line number read from the input file is {line_counter}."
        )
        error_handler.log_error(f"No module is currently being processed.")
        return True  # True pour indiquer qu'une erreur a été détectée
    return False  # Aucun problème détecté


def is_module_processing(
    error_handler, current_module: Module, line_counter: int
) -> bool:

    if current_module is not None:
        error_handler.log_error("New loadlib section detected.")
        error_handler.log_error(
            f"Line number read from the input file is {line_counter}."
        )
        error_handler.log_error(
            f"Module {current_module.info.module_name} is currently being processed."
        )
        error_handler.log_error(f"Id Module is {hex(id(current_module))}.")
        error_handler.log_error(f"Id ModuleInfo is {hex(id(current_module.info))}.")
        error_handler.log_error(f"Id ModuleCSECT is {hex(id(current_module.CSECT))}.")
        return True  # True pour indiquer qu'une erreur a été détectée
    return False  # Aucun problème détecté


def is_loadlib_processing(
    error_handler, current_loadlib: Loadlib, line_counter: int
) -> bool:

    if current_loadlib is not None:
        error_handler.log_error("New loaddlib section detected.")
        error_handler.log_error(
            f"line number read from the input file is {line_counter}."
        )
        error_handler.log_error(
            f"Loadlib {current_loadlib.loadlib_name} is currently being processed."
        )
        error_handler.log_error(f"Id loadlib is {hex(id(current_loadlib))}.")
        return True  # True pour indiquer qu'une erreur a été détectée
    return False  # Aucun problème détecté
