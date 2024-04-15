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
        self.file = FileHandler.open_file(self.filename)  # Open the file
        self.loadlib_name = ''              # Name of the loadlib being processed
        self.previous_loadlib_name = ''     # Name of the previous loadlib 
        self.loadlib_lines = ()             # Tuple containing the lines of a loadlib
        self.modules = 0                    # Number of modules declared in the FMNBB437 message

    def ignore_line(self, line):
        return (not line.strip() or
                line.startswith("IBM File Manager for z/OS") or
                (line.startswith("$$FILEM") and 
                 not line.startswith("$$FILEM VLM DSNIN=")) or
                line.startswith("--------- ---- -------"))

    def __iter__(self):
        for line in self.file:
            line = line[1:]                 # Always remove the ASA character

            if self.ignore_line(line):
                continue
            
            if line.startswith("$$FILEM VLM DSNIN="):
                self.loadlib_name = line.split("=")[1].split(",")[0]
                if self.loadlib_lines:      # If loadlib_lines is not empty
                    raise SectionError(
                        f'Missing end of loadlib section (FMNBB437 or FMNBE329).\n'
                        f'Current loadlib is {self.loadlib_name}.\n'
                        f'Previous encountered loadlib is {self.previous_loadlib_name}.'
                    )

                self.loadlib_lines = (line,)
            
            elif line.startswith("FMNBB437"):
                if not self.loadlib_lines:  # If loadlib_lines is not empty
                    raise SectionError(
                        f'Missing section identification for loadlib ($$FILEM VLM DSNIN).\n'
                        f'Current loadlib is {self.loadlib_name}.\n'
                        f'Previous encountered loadlib is {self.previous_loadlib_name}.'
                    )
                
                self.modules = int(line.split()[1])
                self.loadlib_lines += (line,)
                self.previous_loadlib_name = self.loadlib_name
                yield (self.modules, self.loadlib_lines)
                self.loadlib_lines = ()
            
            elif line.startswith("FMNBE329"):
                if not self.loadlib_lines:  # If loadlib_lines is not empty
                    raise SectionError(
                        f'Missing section identification for loadlib ($$FILEM VLM DSNIN).\n'
                        f'Current loadlib is {self.loadlib_name}.\n'
                        f'Previous encountered loadlib is {self.previous_loadlib_name}.'
                    )
                
                self.loadlib_lines += (line,)
                self.previous_loadlib_name = self.loadlib_name
                yield (0, self.loadlib_lines)
                self.loadlib_lines = ()
            
            else:
                self.loadlib_lines += (line,)

        FileHandler.close_file(self.file)   # Close the file
