# -*- coding: utf-8 -*-

from vlm.utils.file_handler import FileHandler

class LoadlibsParser:
    def __init__(self, filename):
        self.filename = filename
        self.file = FileHandler.open_file(self.filename)  # Ouverture du fichier
        self.number_of_modules = 0
        self.loadlib_name = ()   # nom de la loadlib en cours de traitement
        self.loadlib_lines = ()  # Initialisation du tuple

    def ignore_line(self, line):
        return (not line.strip() or
                line.startswith("IBM File Manager for z/OS") or
                line.startswith("$$FILEM") and not line.startswith("$$FILEM VLM DSNIN=") or
                line.startswith("--------- ---- -------"))

    def __iter__(self):
        encountered_dsnin = False  # Variable pour suivre si on a rencontré "$$FILEM VLM DSNIN="
        encountered_fmnbb = False  # Variable pour suivre si on a rencontré "FMNBB437" ou "FMNBE329"

        def check_error():
            if encountered_dsnin and not encountered_fmnbb:
                raise Exception("Erreur: Deux lignes $$FILEM VLM DSNIN= rencontrées sans FMNBB437 ou FMNBE329.")

        for line in self.file:
            line = line[1:]  # Supprimmer systématiquement le caractères ASA

            if self.ignore_line(line):
                continue

            if line.startswith("$$FILEM VLM DSNIN="):
                self.loadlib_name = line.split("=")[1].split(",")[0]
                if self.loadlib_lines:  # Si loadlib_lines n'est pas vide
                    yield (self.number_of_modules, self.loadlib_lines)
                self.loadlib_lines = (line,)
            elif line.startswith("FMNBB437"):
                self.number_of_modules = int(line.split()[2])
                self.loadlib_lines += (line,)
                yield (self.number_of_modules, self.loadlib_lines)
                self.loadlib_lines = ()
            elif line.startswith("FMNBE329"):
                self.loadlib_lines += (line,)
                yield (0, self.loadlib_lines)
                self.loadlib_lines = ()
            else:
                self.loadlib_lines += (line,)

        FileHandler.close_file(self.file)  # Fermeture du fichier
