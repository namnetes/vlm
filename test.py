import re


# Fonction pour remplacer les caractères '&' dans les sous-chaînes entourées de doubles guillemets
def remplacer_et(chaine):

    # Expression régulière pour trouver les sous-chaînes entourées de
    # doubles guillemets
    #
    # **r** :
    #     C'est un préfixe utilisé en Python pour indiquer que la chaîne qui
    #     suit est une chaîne brute ("raw string"). Cela signifie que les
    #     caractères spéciaux comme les barres obliques inverses ( \ ) sont
    #     traités littéralement et non comme des caractères d'échappement.
    #     Par exemple, `\n` est interprété comme une nouvelle ligne, mais
    #     `r"\n"` est interprété comme une barre oblique inverse suivie de
    #     la lettre "n".
    #
    # **"** :
    #     Ce guillemet signifie que nous cherchons une sous-chaîne qui
    #     commence par un double guillemet.
    #
    # **[ ]** :
    #     Les crochets définissent une classe de caractères, ce qui signifie
    #     que nous cherchons à faire correspondre un seul caractère qui se
    #     trouve à l'intérieur des crochets.
    #
    # **[^]** :
    #     Le symbole `^` à l'intérieur des crochets signifie une négation.
    #     Donc, `[^"]` signifie "tout caractère qui n'est pas un double
    #     guillemet".
    #
    # **[^"]*** :
    #     Le symbole `*` signifie "zéro ou plusieurs occurrences" du caractère
    #     précédant. Ainsi, `[^"]*` signifie "zéro ou plusieurs caractères
    #     qui ne sont pas des doubles guillemets". En d'autres termes, cela
    #     correspond à toute séquence de caractères (y compris une séquence
    #     vide) qui n'inclut pas de double guillemet.
    #
    # **"** :
    #     Ce guillemet signifie que nous cherchons une sous-chaîne qui se
    #     termine par un double guillemet.

    # Expression régulière pour trouver les sous-chaînes entourées de doubles guillemets
    sous_chaines = re.findall(r'"[^"]*"', chaine)

    for sous_chaine in sous_chaines:
        # Remplacer les caractères '&' par un autre caractère (par exemple, '#')
        nouvelle_sous_chaine = sous_chaine.replace("&", "#")
        # Remplacer la sous-chaîne originale par la nouvelle sous-chaîne dans la chaîne principale
        chaine = chaine.replace(sous_chaine, nouvelle_sous_chaine)

    return chaine


def remplacer_et2(chaine):
    caracteres_speciaux_xml = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;",
    }
    sous_chaines = re.findall(r'"[^"]*"', chaine)

    for sous_chaine in sous_chaines:
        # Enlever les guillemets pour traiter uniquement le contenu
        contenu = sous_chaine[1:-1]
        # Remplacer chaque caractère spécial par son échappement
        # nouvelle_sous_chaine = contenu.replace("&", "#")
        for char, echappement in caracteres_speciaux_xml.items():
            nouvelle_sous_chaine = contenu.replace(char, echappement)
        # Remplacer la sous-chaîne originale par la nouvelle sous-chaîne dans la chaîne principale
        nouvelle_sous_chaine = f'"{nouvelle_sous_chaine}"'
        chaine = chaine.replace(sous_chaine, nouvelle_sous_chaine)

    return chaine


import re

# Chaîne de caractères fournie
chaine = (
    r'<Loadmod Name="A8BDP2P" '
    r'Linke<do>n="2011/09/13" '
    r'Link\'edat="15:47:58" '
    r'Linked\'by="PROGRAM-&\'&\'5695-PMB-V1R1" '
    r'EP&A="000000" '
    r'MSize="00054B8" '
    r'TTR="000112" '
    r'SSI="613F&729F" '
    r'AC="00" '
    r'AM=" 31" '
    r'RM="ANY" '
    r'RENT="1" '
    r'REUS="1">'
)


def remplacer_non_affichables(chaine):
    sous_chaines = re.findall(r'"[^"]*"', chaine)

    for sous_chaine in sous_chaines:
        # Enlever les guillemets pour traiter uniquement le contenu
        contenu = sous_chaine[1:-1]
        # Remplacer les caractères non affichables par des espaces
        nouvelle_contenu = re.sub(r"[^\x20-\x7E]", " ", contenu)
        # Ajouter les guillemets autour du nouveau contenu échappé
        nouvelle_sous_chaine = f'"{nouvelle_contenu}"'
        # Remplacer la sous-chaîne originale par la nouvelle sous-chaîne dans la chaîne principale
        chaine = chaine.replace(sous_chaine, nouvelle_sous_chaine)

    return chaine


chaine = (
    r'<Loadmod Name="A8BDP2P" '
    r'Linke<do>n="2011/09/13" '
    r'Link\'edat="15:47:58" '
    r'Linked\'by="PROGRAM-&\'&\'5695-PMB-V1R1" '
    r'EP&A="000000" '
    r'MSize="00054B8" '
    r'TTR="000112" '
    r'SSI="613F&729F" '
    r'AC="00" '
    r'AM=" 31" '
    r'RM="ANY" '
    r'RENT="1" '
    r'REUS="1">'
)

print("-" * 40)
print("Avant")
[print(e) for e in chaine.split()]
print("-" * 40)
print("Après")
# Utiliser la fonction pour remplacer les caractères '&'
newstring = remplacer_et2(chaine)
[print(e) for e in newstring.split()]
