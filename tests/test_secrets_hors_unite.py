#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les trois secrets ne sont pas dans l'unite systemd (F6).

CONSTAT (audit externe du 19/10/2026, F6). VERA_DB_KEY, VERA_ADMIN_HASH et
VERA_SECRET_CREATION_COMPTE vivaient en `Environment=` dans l'unite : lisibles
en clair par `systemctl cat` et `systemctl show`, donc par toute sortie de
diagnostic collee quelque part -- le chemin par lequel des secrets avaient fuite
le 31/07/2026. Ils sont desormais dans /etc/vera/vera.env (root, 600).

GARDE STRUCTURELLE sur le depot (elle ne voit pas le serveur ; c'est le role de
infra/verifier_deploiement.sh, controles 3b et 3c). Elle echoue si :
  1. le modele d'unite porte de nouveau un de ces secrets en Environment= ;
  2. le modele d'unite ne reference pas /etc/vera/vera.env ;
  3. infra/vera.env.exemple n'a pas exactement les trois noms, ou porte autre
     chose que « CHANGER_MOI » comme valeur (une vraie valeur commitee) ;
  4. un document d'exploitation demande encore de poser un secret dans l'unite
     (`Environment="VERA_DB_KEY=...`).
"""

import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
SECRETS = {"VERA_DB_KEY", "VERA_ADMIN_HASH", "VERA_SECRET_CREATION_COMPTE"}
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


unite = (RACINE / "infra" / "vera-consultation.service").read_text(encoding="utf-8")
code = "\n".join(l for l in unite.splitlines() if not l.lstrip().startswith("#"))

dans_unite = sorted(n for n in SECRETS
                    if re.search(r'^Environment="?' + n + r"=", code, re.M))
verifier(not dans_unite, "1. aucun secret en Environment= dans le modele d'unite",
         "présents : " + ", ".join(dans_unite))
verifier(re.search(r"^EnvironmentFile=/etc/vera/vera\.env\s*$", code, re.M) is not None,
         "2. le modele d'unite lit /etc/vera/vera.env")

exemple = (RACINE / "infra" / "vera.env.exemple").read_text(encoding="utf-8")
paires = re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", exemple, re.M)
verifier({n for n, _ in paires} == SECRETS and len(paires) == 3,
         "3a. vera.env.exemple porte exactement les trois noms de secrets",
         str(sorted(n for n, _ in paires)))
verifier(all(v == "CHANGER_MOI" for _, v in paires),
         "3b. et aucune valeur reelle (que « CHANGER_MOI »)")

for nom in ("PROCEDURE_REPRISE_VERA.md", "README.md", "GUIDE_DEPLOIEMENT.md"):
    f = RACINE / nom
    if not f.exists():
        continue
    t = f.read_text(encoding="utf-8")
    fautifs = re.findall(r'Environment="(?:' + "|".join(SECRETS) + r")=", t)
    verifier(not fautifs,
             f"4. {nom} ne demande plus de poser un secret dans l'unite",
             str(fautifs))

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : les secrets ne sont pas dans l'unite.")
sys.exit(0)
