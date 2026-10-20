#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La page de vote ne doit JAMAIS afficher « enregistre » sur un refus de voix.

CONSTAT (audit externe du 19/10/2026, F1). Le serveur refusait les voix
deposees apres la publication du resultat avec un 409 « Votre voix n'a PAS ete
enregistree ». Mais la page de vote traite tout 409 comme « deja vote, votre
voix EST comptee » et affichait « Reponse enregistree -- elle a rejoint celles
des autres participants », en posant le marqueur local qui interdit de
reessayer. Le refus explicite etait annule cote client : toute voix deposee
apres la publication disparaissait sans que personne le sache.

CE QUE CE TEST VERIFIE (sur le source de static/vote.html et de l'API)
  1. dans deposerVote(), la branche 410 existe, affiche une ERREUR, et n'appelle
     NI showSuccess() NI marquerVoteLocal() ;
  2. la branche 409 reste un succes (rejeu du meme K : la voix EST comptee) ;
  3. cote serveur, aucun refus « PAS ete enregistree » ne part en 409 : il
     partirait dans la branche « succes » du client.
Le comportement HTTP du refus est exerce par tests/test_parcours_http.py (6b).
"""

import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


html = (RACINE / "static" / "vote.html").read_text(encoding="utf-8")
debut = html.find("async function deposerVote")
fin = html.find("catch (err)", debut)
corps = html[debut:fin] if debut != -1 and fin != -1 else ""
verifier(bool(corps), "0. deposerVote() est retrouvee dans vote.html")


def branche(statut):
    """Texte de la branche `if (rVote.status === <statut>) { ... }`."""
    m = re.search(r"if \(rVote\.status === %d\) \{" % statut, corps)
    if not m:
        return None
    i, profondeur = m.end(), 1
    while i < len(corps) and profondeur:
        profondeur += {"{": 1, "}": -1}.get(corps[i], 0)
        i += 1
    return corps[m.end():i - 1]


b410 = branche(410)
verifier(b410 is not None, "1a. une branche 410 existe dans deposerVote()")
if b410 is not None:
    verifier("showError(" in b410, "1b. la branche 410 affiche une erreur")
    verifier("showSuccess" not in b410,
             "1c. la branche 410 n'affiche JAMAIS le succes")
    verifier("marquerVoteLocal" not in b410,
             "1d. la branche 410 ne pose pas le marqueur « a vote »",
             "il interdirait toute nouvelle tentative")
    verifier("PAS" in b410 and "enregistrée" in b410,
             "1e. le message dit que la voix n'a PAS ete enregistree")

b409 = branche(409)
verifier(b409 is not None and "showSuccess" in b409,
         "2. la branche 409 reste un succes (rejeu : la voix EST comptee)")

api = (RACINE / "vera_consultation_api.py").read_text(encoding="utf-8")
fautifs = []
for m in re.finditer(r"status_code=409,\s*detail=(?P<d>(?:\"[^\"]*\"\s*)+)", api):
    texte = re.sub(r"\"\s*\"", "", m.group("d"))
    if "PAS ete enregistree" in texte or "NON enregistre" in texte:
        fautifs.append(texte[:80])
verifier(not fautifs,
         "3. aucun refus « voix PAS enregistree » ne part en 409 cote serveur",
         "\n      ".join(fautifs))

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : un refus de voix ne s'affiche jamais comme un succes.")
sys.exit(0)
