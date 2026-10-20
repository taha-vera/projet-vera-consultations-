#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La page de vote n'accepte QUE la cle publiee pour le groupe du lien.

CONSTAT (audit externe du 19/10/2026, F3). Le client verifiait que la cle
recue « figure dans la liste » des cles publiees. Un operateur actif pouvait
donc repondre, pour un lien d'« Atelier », avec la cle -- reelle, publiee -- de
« Direction ». L'agregat etant identique pour tous, les controles passaient ;
seule cette personne signait sous une cle que personne d'autre dans son groupe
n'avait recue, ce qui la designait au depot. Aucune segmentation des liens
n'etait necessaire.

CE QUE CE TEST VERIFIE
  1. la fonction pure cleAppartientAuGroupe() de static/vote.html, EXECUTEE
     sous node : bonne cle du bon groupe -> vrai ; cle d'un autre groupe (le cas
     de l'attaque) -> faux ; groupe absent de la liste -> faux ; liste vide ou
     invalide -> faux ; groupe vide ou non texte -> faux ;
  2. le chemin de vote APPELLE cette fonction (et non l'ancien « some(...) » qui
     acceptait n'importe quelle cle de la liste).

EXIGE node. Sans lui le test s'arrete avec IGNORE, comme test_syntaxe_js.
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


node = shutil.which("node")
if not node:
    print("IGNORE : node est absent.")
    raise SystemExit(2)

html = (RACINE / "static" / "vote.html").read_text(encoding="utf-8")
m = re.search(r"function cleAppartientAuGroupe\(.*?\n  \}\n", html, re.S)
verifier(m is not None, "0. cleAppartientAuGroupe() est retrouvee dans vote.html")

if m:
    source = m.group(0)
    A = {"departement": "Atelier", "cle_publique_hex": "aa11"}
    D = {"departement": "Direction", "cle_publique_hex": "dd22"}
    cas = [
        ("1a. bonne cle du bon groupe", [A, D], "Atelier", "aa11", True),
        ("1b. CLE D'UN AUTRE GROUPE (l'attaque F3)", [A, D], "Atelier", "dd22", False),
        ("1c. cle inconnue", [A, D], "Atelier", "ff99", False),
        ("1d. groupe absent de la liste", [A, D], "Bureau", "aa11", False),
        ("1e. liste vide", [], "Atelier", "aa11", False),
        ("1f. liste invalide (null)", None, "Atelier", "aa11", False),
        ("1g. groupe vide", [A, D], "", "aa11", False),
        ("1h. groupe non texte", [A, D], None, "aa11", False),
        ("1i. entree nulle dans la liste", [None, A], "Atelier", "aa11", True),
    ]
    script = source + "\nconst cas = " + json.dumps(
        [[c[1], c[2], c[3]] for c in cas]) + ";\n" + \
        "console.log(JSON.stringify(cas.map(c => cleAppartientAuGroupe(...c))));\n"
    r = subprocess.run([node, "-e", script], capture_output=True, text=True)
    verifier(r.returncode == 0, "1. la fonction s'execute sous node", r.stderr[:200])
    if r.returncode == 0:
        resultats = json.loads(r.stdout.strip().splitlines()[-1])
        for (libelle, _l, _g, _k, attendu), obtenu in zip(cas, resultats):
            verifier(obtenu is attendu, libelle,
                     f"attendu {attendu}, obtenu {obtenu}")

verifier("cleAppartientAuGroupe(eng.cles, departementVote, cle_publique_hex)" in html,
         "2a. le chemin de vote appelle cleAppartientAuGroupe(...) avec le groupe du lien")
verifier("eng.cles.some(c => c.cle_publique_hex === cle_publique_hex)" not in html,
         "2b. l'ancien controle « figure dans la liste » a disparu")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : seule la cle publiee pour le groupe du lien est acceptee.")
sys.exit(0)
