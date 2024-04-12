# -*- coding: utf-8 -*-
from vlm.utils.file_handler import FileHandler
class SectionError(Exception):
    """Exception raised for errors related to sections in the file."""
    def __init__(self, section_name):
        self.section_name = section_name
        super().__init__(section_name)
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
                (line.startswith("$$FILEM") and 
                 not line.startswith("$$FILEM VLM DSNIN=")) or
                line.startswith("--------- ---- -------"))

    def __iter__(self):
        for line in self.file:
            line = line[1:]  # Supprimer systématiquement le caractère ASA

            if self.ignore_line(line):
                continue
            
            if line.startswith("$$FILEM VLM DSNIN="):
                self.loadlib_name = line.split("=")[1].split(",")[0]
                if self.loadlib_lines:  # Si loadlib_lines n'est pas vide
                    raise SectionError(
                        f'Missing end section identification for loadlib '
                        f'(FMNBB437 or FMNBE329).\nLast encountered start '
                        f'section identification for loadlib: {self.loadlib_name}.'
                    )

                    # yield (self.number_of_modules, self.loadlib_lines)
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
