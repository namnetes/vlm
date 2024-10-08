# Importations de modules locaux
from error_handler import ErrorHandler
from csv_writer import write_loadlibs_to_csv
from structures import Loadlibs, Loadlib, Module
from utils import (
    should_ignore_line,
    is_module_not_processing,
    is_module_processing,
    is_loadlib_not_processing,
    is_loadlib_processing,
    get_new_loadlib,
    get_new_module,
)


def update_progress(line_counter, total_lines, verbose, last_percent_displayed):
    if verbose:
        percent = (line_counter / total_lines) * 100
        current_percent = int(percent // 5) * 5  # On garde les multiples de 5
        if current_percent > last_percent_displayed:
            print(f"\rProcessing of input file in progres: {current_percent}%", end="")
            return current_percent
    return last_percent_displayed


def process_file(input_file, output_file, csv_separator, log_file, verbose):
    error_handler = ErrorHandler(log_file)

    loadlibs_collection: Loadlibs = Loadlibs()

    # Log uniquement si le mode verbeux est activé
    if verbose:
        error_handler.log_info(
            f"loadlibs_collection id is {hex(id(loadlibs_collection))}"
        )

    current_loadlib: Loadlib = None
    current_module: Module = None
    line_counter = 0

    total_lines = sum(
        1 for _ in open(input_file, "r", encoding="latin-1")
    )  # Compter les lignes du fichier
    last_percent_displayed = (
        -10
    )  # Pour suivre la dernière tranche de progression affichée

    try:
        with open(input_file, "r", encoding="latin-1") as file, open(
            output_file, "w", encoding="utf-8"
        ) as outfile:
            for line in file:
                line_counter += 1
                line = line[1:]  # Supprimer le caractère de contrôle ASA
                line = line.strip()  # Supprimer les espaces superflus

                last_percent_displayed = update_progress(
                    line_counter, total_lines, verbose, last_percent_displayed
                )

                if should_ignore_line(line):
                    continue

                if line.startswith("$$FILEM VLM DSNIN="):
                    # Début d'une nouvelle section Loadlib
                    if is_module_processing(
                        error_handler, current_module, line_counter
                    ):
                        exit()

                    if is_loadlib_processing(
                        error_handler, current_loadlib, line_counter
                    ):
                        exit()

                    # Acquisition d'une nouvelle instance de loadlib
                    current_loadlib = get_new_loadlib(line)

                    if verbose:
                        error_handler.log_info(
                            f"(lc={line_counter}) New current loadlib is {current_loadlib.loadlib_name}."
                        )
                        error_handler.log_info(
                            f"(lc={line_counter}) Id of the new current loadlib instance is {hex(id(current_loadlib))}."
                        )
                    continue

                if line.startswith(("FMNBE329", "FMNBB437")):
                    # Fin de section Loadlib
                    if is_loadlib_not_processing(
                        error_handler, current_loadlib, line_counter
                    ):
                        exit()

                    if is_module_processing(
                        error_handler, current_module, line_counter
                    ):
                        exit()

                    if verbose:
                        error_handler.log_info(
                            f"(lc={line_counter}) {current_loadlib.loadlib_name} added to loadlib_collection."
                        )
                        error_handler.log_info(
                            f"(lc={line_counter}) Id {hex(id(current_loadlib))} added to {hex(id(loadlibs_collection))}."
                        )
                    loadlibs_collection.add_loadlib(current_loadlib)
                    current_loadlib = None  # Réinitialiser l'instance
                    continue

                if line.startswith("FMNBA215"):
                    # Fin de la section module
                    if is_module_not_processing(
                        error_handler, current_module, line_counter
                    ):
                        exit()

                    if current_module is not None:
                        if verbose:
                            error_handler.log_info(
                                f"(lc={line_counter}) {current_module.info.module_name} added to {current_loadlib.loadlib_name}."
                            )
                            error_handler.log_info(
                                f"(lc={line_counter}) Id {hex(id(current_module))} added to {hex(id(current_loadlib))}."
                            )
                        current_loadlib.add_module(current_module)
                        current_module = None
                    continue

                if line.startswith("Load Module Information"):
                    # Début d'une nouvelle section module

                    if is_module_processing(
                        error_handler, current_module, line_counter
                    ):
                        exit()

                    # Acquisition d'une nouvelle instance de module
                    current_module = get_new_module(line_counter)

                    if verbose:
                        error_handler.log_info(
                            f"(lc={line_counter}) Id of the new current module instance is {hex(id(current_module))}."
                        )
                        error_handler.log_info(
                            f"(lc={line_counter}) Id of the new current module.info instance is {hex(id(current_module.info))}."
                        )
                        error_handler.log_info(
                            f"(lc={line_counter}) Id of the new current module.CSECT instance is {hex(id(current_module.CSECT))}."
                        )
                    continue
                elif line.startswith("Load Library"):
                    current_module.info.set_library_name(line)
                    continue
                elif line.startswith("Load Module"):
                    current_module.info.set_module_name(line)
                    continue
                elif line.startswith("Linked on"):
                    current_module.info.set_linked_on(line)
                    continue
                elif line.startswith("EPA"):
                    current_module.info.set_epa(line)
                    continue

            # La fin du fichier a traité a été détecté
            if is_module_processing(error_handler, current_module, line_counter):
                exit()

            if is_loadlib_processing(error_handler, current_loadlib, line_counter):
                exit()

            # Ecrire le résultat dans le fichier en sortie
            # print(loadlibs_collection)
            write_loadlibs_to_csv(loadlibs_collection, outfile)

    except FileNotFoundError:
        print(f"Error: Cannot open input file '{input_file}'")
    finally:
        if verbose:
            print()  # Retour à la ligne après la barre de progression
