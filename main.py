# -*- coding: utf-8 -*-
from vlm.loadlibs_parser import LoadlibsParser, SectionError
import logging
import os
import sys

def configure_logging():
    logging.basicConfig(filename='./vlm.log', 
                        level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    
    configure_logging()
    logging.info(f'Beginning of processing of {os.path.abspath(sys.argv[0])}')
    logging.info(f'Current directory: {os.getcwd()}')

    try:
        filename = "./data/vlm.txt"
        loadlibs_parser = LoadlibsParser(filename)

        for number_of_modules, loadlib_lines in loadlibs_parser:
            loadlib_name = loadlib_lines[0].split('=')[1].split(',')[0]
            message = f'{loadlib_name}'
            message = f'Nombre de modules {str(number_of_modules).rjust(3)} '
            message += f'Nombre de lignes par loadlib {str(len(loadlib_lines)).rjust(4)}'
            logging.info(message)
            
    except (FileNotFoundError, 
            PermissionError, 
            IsADirectoryError, 
            IOError, 
            UnicodeDecodeError) as e:
        logging.error(f'{e}')
        print(e)
        sys.exit(1)
        
    except SectionError as se:
        logging.error(f'{e}')
        print(se)
        sys.exit(1)

if __name__ == "__main__":
    main()
