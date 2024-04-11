# -*- coding: utf-8 -*-
from vlm.loadlibs_parser import LoadlibsParser
import os
import sys

def main():
    print(f'Current directory: {os.getcwd()}')

    try:
        filename = "./vlm.txt"
        loadlibs_parser = LoadlibsParser(filename)
    except Exception as e:
        print("An error occurred during opening the VLM file:", e)
        sys.exit(1)

    for number_of_modules, loadlib_lines in loadlibs_parser:
        print("Nombre de modules:", number_of_modules)
        print(len(loadlib_lines))
        #for line in loadlib_lines:
        #    print(line)

if __name__ == "__main__":
    main()
