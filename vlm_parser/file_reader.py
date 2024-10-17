# Importations de modules locaux
from error_handler import ErrorHandler
from csv_writer import write_loadlibs_to_csv
from structures import Loadlibs, Loadlib, Module, ModuleCsect
from utils import should_ignore_line, get_new_loadlib, get_new_module, is_CSECT_name


def log_missing_loadlib(error_handler, line_counter):
    error_handler.log_error("End of loadlib section detected.")
    error_handler.log_error(f"Line number read from the input file is {line_counter}.")
    error_handler.log_error("No loadlib is currently being processed.")
    exit()


def log_missing_module(error_handler, line_counter, current_module):
    error_handler.log_error("End of loadlib section detected.")
    error_handler.log_error(
        f"Module {current_module.info.module_name} is currently being processed."
    )
    error_handler.log_error(f"Id Module is {hex(id(current_module))}.")
    exit()


def log_new_section_while_processing(
    error_handler, line_counter, current_object, obj_type
):
    error_handler.log_error(f"New {obj_type} section detected.")
    error_handler.log_error(f"Line number read from the input file is {line_counter}.")
    error_handler.log_error(
        f"{obj_type} {current_object} is currently being processed."
    )
    exit()


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
    current_csect: ModuleCsect = None
    line_counter = 0
    all_modules = set()

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

                # ================== Fin de section Loadlib ==================
                if line.startswith(("FMNBE329", "FMNBB437")):

                    # Erreur détectée
                    if current_loadlib is None:
                        log_missing_loadlib(error_handler, line_counter)
                        exit()

                    if current_module is not None:
                        log_missing_module(error_handler, line_counter, current_module)
                        exit()

                    # Aucune erreur détectée
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

                # ================== Fin de section Module ==================
                if line.startswith("FMNBA215"):

                    # Erreur détectéee
                    if current_module is None:
                        log_missing_module(error_handler, line_counter, current_module)
                        exit()

                    if current_module.CSECT is None:
                        error_handler.log_error("End of module section detected.")
                        error_handler.log_error(
                            f"Module name is {current_module.info.module_name}"
                        )
                        error_handler.log_error(
                            f"Line number read from the input file is {line_counter}."
                        )
                        error_handler.log_error(
                            "No CSECT is currently being processed."
                        )
                        exit()

                    # Aucune erreur détectée
                    if verbose:
                        error_handler.log_info(
                            f"(lc={line_counter}) Module {current_module.info.module_name} added to {current_loadlib.loadlib_name}."
                        )
                        error_handler.log_info(
                            f"(lc={line_counter}) Id {hex(id(current_module))} added to {hex(id(current_loadlib))}."
                        )
                        error_handler.log_info(
                            f"(lc={line_counter}) Id {hex(id(current_module.info))} of the module info."
                        )
                        error_handler.log_info(
                            f"(lc={line_counter}) Id {hex(id(current_module.CSECT))} of the module CSECT."
                        )
                    current_loadlib.add_module(current_module)
                    current_module = None

                    continue

                # =========== Début d'une nouvelle section Loadlib ===========
                if line.startswith("$$FILEM VLM DSNIN="):

                    # Erreur détectée
                    if current_loadlib is not None:
                        log_new_section_while_processing(
                            error_handler,
                            line_counter,
                            current_loadlib.loadlib_name,
                            "loadlib",
                        )
                        exit()

                    if current_module is not None:
                        log_missing_module(error_handler, line_counter, current_module)
                        exit()

                    # Aucune erreur détectée
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

                # ============ Début d'une nouvelle section Module ============
                if line.startswith("Load Module Information"):

                    # Erreur détectée
                    if current_module is not None:
                        log_new_section_while_processing(
                            error_handler,
                            line_counter,
                            current_module.info.module_name,
                            "module",
                        )
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

                    # Stub CICS, MQ + Interface DB2
                    stub_sets = [
                        current_module.STUB_CICS,
                        current_module.STUB_DB2,
                        current_module.STUB_MQ,
                    ]

                    # Le nom du module correspond-il à un des deux Stubs ou à l'interface DB2 ?
                    current_module.Stub = any(
                        current_module.info.module_name in stub_set
                        for stub_set in stub_sets
                    )

                    # Si current_module.Stub est toujours False, ajoutez le module
                    if not current_module.Stub:
                        all_modules.add(current_module.info.module_name)
                        continue

                elif line.startswith("Linked on"):
                    current_module.info.set_linked_on(line)
                    continue
                elif line.startswith("EPA"):
                    current_module.info.set_epa(line)
                    continue

                # ========= Début d'une nouvelle section table CSECT =========
                if line.startswith("Name      Type"):

                    # Erreur Détectée
                    if current_module is None:
                        error_handler.log_error("New CSECT section detected.")
                        error_handler.log_error(
                            f"Line number read from the input file is {line_counter}."
                        )
                        error_handler.log_error(
                            "No module is currently being processed."
                        )
                        exit()

                    # Aucune erreur détectée
                    current_module.CSECT = []
                    continue

                # ========= Ligne de CSECT =========
                csect_name = is_CSECT_name(line)
                if csect_name is not None:
                    if not current_module.CICS:
                        current_module.CICS = csect_name in current_module.STUB_CICS

                    if not current_module.DB2:
                        current_module.DB2 = csect_name in current_module.STUB_DB2

                    if not current_module:
                        current_module.MQ = csect_name in current_module.STUB_MQ

                    current_csect = ModuleCsect()
                    current_csect.set_csect_data(csect_name, line)
                    current_module.CSECT.append(current_csect)
                    current_csect = None

            # ================== Fin du fichier en entrée ==================
            if current_loadlib is not None:
                error_handler.log_error("New loadlib section detected.")
                error_handler.log_error(
                    f"Line number read from the input file is {line_counter}."
                )
                error_handler.log_error(
                    f"loadlib {current_loadlib.loadlib_name} is currently being processed."
                )
                exit()

            if current_module is not None:
                error_handler.log_error("End of loadlib section detected.")
                error_handler.log_error(
                    f"Module {current_module.info.module_name} is currently being processed."
                )
                error_handler.log_error(f"Id Module is {hex(id(current_module))}.")
                exit()

            # ========= Ecrire le résultat dans le fichier de sortie =========
            # print(loadlibs_collection)
            write_loadlibs_to_csv(all_modules, loadlibs_collection, outfile)

    except FileNotFoundError:
        print(f"Error: Cannot open input file '{input_file}'")
    finally:
        if verbose:
            print()  # Retour à la ligne après la barre de progression
