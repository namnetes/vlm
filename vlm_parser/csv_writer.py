# Importations de bibliothèques standard
import csv  # par exemple, si vous utilisez le module csv

# Importations de modules locaux
from structures import Loadlibs, Loadlib, Module, ModuleInfo


def write_loadlibs_to_csv(listof_all_modules, loadlibs_collection: Loadlibs, outfile):
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
            "Line Counter",
            "Is CICS",
            "Is_DB2",
            "Is_MQ",
            "Stub",
            "Module Name",
            "Linked Date",
            "Linked Time",
            "EPA",
            "Size",
            "TTR",
            "SSI",
            "AMODE",
            "RMODE",
            "CSECT_Name",
            "CSECT_Address",
            "CSECT_Size",
            "CSECT_Amode",
            "CSECT_Rmode",
            "CSECT_Compiler_1",
            "CSECT_Compiler_2",
            "CSECT_Linked",
            "Appel Static LCL",
            "Appel Stub Appicatif",
        ]
    )

    # Parcourir chaque Loadlib dans la collection
    loadlib: Loadlib = None
    for loadlib in loadlibs_collection.loadlibs:
        # Écrire les informations de la Loadlib
        if len(loadlib.loadlib_modules) > 0:
            module: Module = None
            for module in loadlib.loadlib_modules:
                # Écrire les informations du module
                module_info: ModuleInfo = module.info
                flag_cics = "CICS" if module.CICS else ""
                flag_db2 = "DB2" if module.DB2 else ""
                flag_mq = "WMQ" if module.DB2 else ""

                appel_static = False
                for csect in module.CSECT:
                    appel_static = "Non"
                    if csect.csect_name != module_info.module_name:
                        if csect.csect_name in listof_all_modules:
                            appel_static = "Oui"

                    stub_applicatif = False
                    if (
                        module.Stub
                        and csect.csect_name == module_info.module_name
                        and csect.csect_linked == module_info.linked_date
                    ):
                        stub_applicatif = True

                    # if module_info:
                    csv_writer.writerow(
                        [
                            loadlib.loadlib_name,
                            module.line_counter,
                            flag_cics,
                            flag_db2,
                            flag_mq,
                            str(module.Stub),
                            module_info.module_name,
                            module_info.linked_date,
                            module_info.linked_time,
                            module_info.epa,
                            module_info.size,
                            module_info.ttr,
                            module_info.ssi,
                            module_info.amode,
                            module_info.rmode,
                            csect.csect_name,
                            csect.csect_address,
                            csect.csect_size,
                            csect.csect_amode,
                            csect.csect_rmode,
                            csect.csect_comp1,
                            csect.csect_comp2,
                            csect.csect_linked,
                            appel_static,
                            str(stub_applicatif),
                        ]
                    )
        else:
            # Si aucune info, on écrit une ligne vide pour le module
            csv_writer.writerow([loadlib.loadlib_name] + [""] * 24)
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
