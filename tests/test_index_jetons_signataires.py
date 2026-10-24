#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'index des jetons ayant signe reste exact, et jeton_a_deja_signe est O(1).

CONSTAT (audit externe du 24/10/2026, N8). jeton_a_deja_signe parcourait tout
le cache des signatures de l'heure : un jeton libre le parcourait en entier, un
jeton utilise s'arretait a sa position. Mesure en processus avec 1500 signatures :
36 microsecondes d'ecart entre jeton utilise et libre, et une duree qui croissait
avec le RANG de signature du jeton (de 104 a 234 microsecondes). La reponse
trahissait donc non seulement la participation, mais l'ordre des signatures.

Le correctif remplace le parcours par un index (jeton -> nombre d'entrees). Un
index peut diverger du cache qu'il double : ce test verifie qu'il suit exactement
les ajouts, les remplacements, l'expiration et la cloture.

CE QU'IL VERIFIE
  1. apres une signature, jeton_a_deja_signe est vrai pour ce jeton seulement ;
  2. deux messages pour un meme jeton : l'index le garde tant que l'un des deux
     vit, et le perd quand le dernier expire ;
  3. enregistrer deux fois le MEME couple n'enfle pas l'index (un remplacement
     n'est pas un ajout) ;
  4. l'expiration d'un jeton ne retire que lui ;
  5. vider_signatures_emises (cloture) vide cache ET index ;
  6. jeton_a_deja_signe ne parcourt pas le cache : on remplace le cache par un
     dictionnaire qui interdit toute iteration, l'appel doit quand meme aboutir.
"""

import os
import pathlib
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_index_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

import vera_persistance as p  # noqa: E402

p.initialiser()
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


horloge = {"t": 1000.0}
p._horloge_cache = lambda: horloge["t"]
RET = p.RETENTION_SIGNATURES_SECONDES
p.vider_signatures_emises()

JA, JB, JC = "jeton_a" * 8, "jeton_b" * 8, "jeton_c" * 8
M1, M2 = "message_1" * 6, "message_2" * 6

# 1. un jeton qui a signe est connu, les autres non.
p.enregistrer_signature_emise(JA, M1, "aa" * 10, "G")
verifier(p.jeton_a_deja_signe(JA), "1a. le jeton qui a signe est connu")
verifier(not p.jeton_a_deja_signe(JB), "1b. un autre jeton ne l'est pas")

# 3. enregistrer deux fois le meme couple n'enfle pas l'index.
p.enregistrer_signature_emise(JA, M1, "aa" * 10, "G")
verifier(p._jetons_signataires.get(JA) == 1,
         "3. le meme couple enregistre deux fois compte pour une entree",
         str(p._jetons_signataires.get(JA)))

# 2. deux messages pour un meme jeton.
horloge["t"] += 10
p.enregistrer_signature_emise(JA, M2, "bb" * 10, "G")
verifier(p._jetons_signataires.get(JA) == 2, "2a. deux messages : l'index compte deux entrees")
# le 1er message expire (inscrit a t=1000, renouvele a t=1000 par le 2e appel), le 2e vit encore
horloge["t"] = 1000.0 + RET + 5          # M1 (t=1000) expire ; M2 (t=1010) encore valide
verifier(p.jeton_a_deja_signe(JA), "2b. l'un des messages vit encore : le jeton reste connu")
horloge["t"] = 1010.0 + RET + 5          # M2 expire a son tour
verifier(not p.jeton_a_deja_signe(JA), "2c. le dernier message expire : le jeton est oublie")
verifier(JA not in p._jetons_signataires, "2d. et l'index n'en garde aucune trace")

# 4. l'expiration d'un jeton ne retire que lui.
horloge["t"] = 5000.0
p.enregistrer_signature_emise(JB, M1, "cc" * 10, "G")
horloge["t"] = 5000.0 + RET - 10
p.enregistrer_signature_emise(JC, M1, "dd" * 10, "G")
horloge["t"] = 5000.0 + RET + 1          # JB expire, JC non
verifier(not p.jeton_a_deja_signe(JB) and p.jeton_a_deja_signe(JC),
         "4. JB expire, JC reste")

# 5. la cloture vide cache et index.
p.vider_signatures_emises()
verifier(not p._signatures_emises and not p._jetons_signataires and not p.jeton_a_deja_signe(JC),
         "5. vider_signatures_emises vide le cache ET l'index")

# 6. aucun parcours du cache.
horloge["t"] = 9000.0
p.enregistrer_signature_emise(JA, M1, "ee" * 10, "G")


class SansIteration(dict):
    def __iter__(self):
        raise AssertionError("jeton_a_deja_signe a parcouru le cache")

    def items(self):
        # la purge a besoin d'items() ; elle est autorisee, pas le parcours de
        # recherche par iteration directe
        return super().items()


copie = SansIteration(p._signatures_emises)
original = p._signatures_emises
p._signatures_emises = copie
try:
    try:
        reponse = p.jeton_a_deja_signe(JA)
        verifier(reponse is True, "6. jeton_a_deja_signe aboutit sans iterer le cache")
    except AssertionError as e:
        verifier(False, "6. jeton_a_deja_signe aboutit sans iterer le cache", str(e))
finally:
    p._signatures_emises = original

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : l'index des jetons ayant signe reste exact.")
sys.exit(0)
