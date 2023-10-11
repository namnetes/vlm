import re

regex_ignore = {
    'regex1': r'^\s*\$\$FILEM',         
    'regex2': r'^\sIBM File Manager',
    'regex3': r'^\sLoad Module Information',
    'regex4': r'^FMNBA215\s\d+\sControl sections processed$',
    'regex5': r'^FMNBB437\s\d+\smember(s) read$',
    'regex6': r'^FMNBE329 The PDS contains no members.$',
}

rx_dict = {
    'libname': re.compile(
        r"^(?P<libname>(0|1| )"
        r"[ ]+Load[ ]+Library[ ]+"
        r"[a-zA-Z#$@]"
        r"[a-zA-Z0-9#$@-]{0,7}"
        r"(?:.([a-zA-Z#$@])([a-zA-Z0-9#$@-]{0,7})){0,4}"
        r"(?:.([a-zA-Z#$@])([a-zA-Z0-9#$@-]{0,4}))?)$",
        re.VERBOSE),
    'module': re.compile(
        r"^(?P<module>(0|1| )"
        r"[ ]+Load[ ]+Module[ ]+"
        r"[a-zA-Z#$@]"
        r"[a-zA-Z0-9#$@-]{0,7}"
        r"$)",
        re.VERBOSE),
    'linked': re.compile(r"^(?P<module>(0|1| )[ ]+Linked[ ]+on[ ]+.*$)",re.VERBOSE),
}

def _parse_line(line: str) -> tuple:
    """
    Parsing en utilisant des expressions régulières.

    Args:
        line (str): La ligne de texte à analyser.

    Returns:
        tuple: La clé correspondante à la première expression régulière
        trouvée et l'objet de correspondance. Si aucune correspondance
        n'est trouvée, renvoie 'None' pour les deux éléments.
    """

    for regex_key, regex_pattern in regex_ignore.items():
         if re.match(regex_pattern, line):
              print(f"Ligne matchée : {line.strip()}")
              print(f"Regex correspondante : {regex_key}")

    if re.match(r'^\s*\$\$FILEM', line):
        return None, None

    for key, rx in rx_dict.items():
        match = rx.search(line)
        if match:
            return key, match
    return None, None

