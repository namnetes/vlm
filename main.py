# -*- coding: utf-8 -*-
from vlm.loadlibs_parser import LoadlibsParser, SectionError
import os
import sys

def main():
    
    print(f'Current directory: {os.getcwd()}')

    try:
        filename = "./data/vlm.txt"
        loadlibs_parser = LoadlibsParser(filename)

        for number_of_modules, loadlib_lines in loadlibs_parser:
            print("Nombre de modules:", number_of_modules)
            print(len(loadlib_lines))

    except (FileNotFoundError, 
            PermissionError, 
            IsADirectoryError, 
            IOError, 
            UnicodeDecodeError) as e:
        print(e)
        sys.exit(1)
        
    except SectionError as se:
        print(se)
        sys.exit(1)

if __name__ == "__main__":
    main()
