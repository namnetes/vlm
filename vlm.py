#! /home/galan/workspace/vlm/venv/bin/python
# -*- coding: utf-8 *-*

import argparse
import time

i = 0
start = time.time() # enregistre le temps au début

with open('vlm.txt', 'r') as file:
    for line in file:
        i+=1

end = time.time() # enregistre le temps de fin
print(f"Temps d'exécution est {end - start}")
print(f"{i} enregistrements lus")
