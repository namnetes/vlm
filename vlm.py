import re
import parseline as pl

data = []
with open('vlm.txt', 'r') as file_object:
    line = file_object.readline()

    while line:
        if line[0] in ['0', '1']:                # suppression du caractère ASA
            line = ' ' + line[1:]

        if line.strip():                         # la ligne lue n'est pas vide
            key, match = pl._parse_line(line)

            if key == 'libname':
                library = match.group('libname').split()[-1]
                print(library)

            if key == 'module':
                module = match.group('module').split()[-1]
                print(module)

#            if key == 'linked':
                #linked_date = match.group('linked')
#                print(match.group('linked'))

        line = file_object.readline()
