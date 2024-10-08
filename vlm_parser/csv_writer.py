# Importations de bibliothèques standard
import csv  # par exemple, si vous utilisez le module csv

# Importations de modules locaux
from structures import Loadlibs


def write_loadlibs_to_csv(loadlibs_collection: Loadlibs, outfile):
    """
    Écrit les données de la collection de Loadlibs dans un fichier CSV.

    Args:
        loadlibs_collection (Loadlibs): La collection de Loadlibs à écrire.
        outfile (TextIO): Le fichier de sortie ouvert pour écrire le CSV.
    """
    # Créer un écrivain CSV
    csv_writer = csv.writer(outfile, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # Écrire l'en-tête (vous pouvez modifier les noms des colonnes selon vos besoins)
    csv_writer.writerow(
        [
            "Loadlib Name",
            "Module Line Counter",
            "Module Name",
            "Linked Date",
            "Linked Time",
            "EPA",
            "Size",
            "TTR",
            "SSI",
            "AMODE",
            "RMODE",
        ]
    )

    # Parcourir chaque Loadlib dans la collection
    for loadlib in loadlibs_collection.loadlibs:
        # Écrire les informations de la Loadlib
        if len(loadlib.loadlib_modules) > 0:
            for module in loadlib.loadlib_modules:
                # Écrire les informations du module
                module_info = module.info
                if module_info:
                    csv_writer.writerow(
                        [
                            loadlib.loadlib_name,
                            module.line_counter,
                            module_info.module_name,
                            module_info.linked_date,
                            module_info.linked_time,
                            module_info.epa,
                            module_info.size,
                            module_info.ttr,
                            module_info.ssi,
                            module_info.amode,
                            module_info.rmode,
                        ]
                    )
        else:
            # Si aucune info, on écrit une ligne vide pour le module
            csv_writer.writerow([loadlib.loadlib_name] + [""] * 10)
            # csv_writer.writerow(
            #     [
            #         loadlib.loadlib_name,
            #         "",
            #         "",
            #         "",
            #         "",
            #         "",
            #         "",
            #         "",
            #         "",
            #         "",
            #         "",
            #     ]
            # )
