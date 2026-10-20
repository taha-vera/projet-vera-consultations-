#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La question se fige a la declaration des groupes, et ne se rouvre pas.

CONSTATS (audit externe du 19/10/2026).
  F2. Le gel de la question ne se lisait que sur l'horloge des cles. Apres
      l'expiration des cles (7 jours) puis un redemarrage du processus, cette
      horloge repond « rien » : la question redevenait modifiable alors que les
      votes et le resultat publie portaient sur l'ancienne. Des reponses
      recueillies sur Q1 se retrouvaient a cote de Q2.
  F7. Fixer la date d'ouverture AVANT la question cree la ligne avec un intitule
      VIDE ; le garde de D3 testait `is None` et laissait passer '' : les groupes
      se declaraient, la question restait vide, puis se figeait ainsi.

CE QUE CE TEST VERIFIE
  1. ouverture fixee, question jamais definie -> declarer les groupes refuse (409) ;
  2. la question reste modifiable AVANT la declaration des groupes ;
  3. apres la declaration, redefinir la question est refuse (409) ;
  4. MEME apres « expiration des cles + redemarrage » (horloge des cles qui
     repond rien), redefinir la question reste refuse : le gel se lit dans la base ;
  5. la question n'a pas change pendant ces tentatives ;
  6. apres la cloture, on peut a nouveau definir une question.

EXIGE le module Rust compile (l'API refuse de demarrer sans lui).
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db",
                                                 prefix="vera_question_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS",
                      os.environ["VERA_DB_PATH"] + ".lock")

try:
    import vera_blind_sig as vbs
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)

if not callable(getattr(vbs, "generer_cles", None)):
    print("IGNORE : le module Rust n'est pas compile.")
    raise SystemExit(2)

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("IGNORE : fastapi.testclient indisponible (httpx manquant ?).")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_test_question"
os.environ["VERA_ADMIN_USER"] = "rh_question"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

GROUPE = "GroupeQuestion"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")
r = client.post("/api/rh/connexion",
                json={"identifiant": "rh_question", "mot_de_passe": MDP})
verifier(r.status_code == 200, "0. connexion RH", f"recu {r.status_code}")


def poser_question(texte):
    return client.post("/api/rh/question", json={"intitule": texte})


def declarer():
    return client.post("/api/rh/declarer_groupes",
                       json={"groupes": [GROUPE], "effectifs": {GROUPE: 300}})


# --- 1. Ouverture fixee d'abord : la question est VIDE ---------------------

r = client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + 3600})
verifier(r.status_code == 200, "1a. ouverture fixee avant la question",
         f"recu {r.status_code} : {r.text[:120]}")
verifier(persistance.charger_question() == "",
         "1b. precondition : la ligne existe avec un intitule VIDE",
         repr(persistance.charger_question()))
r = declarer()
verifier(r.status_code == 409,
         "1c. declarer les groupes SANS question est refuse (F7)",
         f"recu {r.status_code} -- la question se figeait vide")
verifier(persistance.charger_groupes_declares() is None,
         "1d. rien n'a ete ecrit par cette tentative")

# --- 2. Modifiable avant la declaration -----------------------------------

verifier(poser_question("Question Q1 ?").status_code == 200,
         "2a. la question se definit")
verifier(poser_question("Question Q1 bis ?").status_code == 200,
         "2b. elle reste modifiable AVANT la declaration des groupes")

# --- 3. Figee apres la declaration ----------------------------------------

r = declarer()
verifier(r.status_code == 200, "3a. groupes declares",
         f"recu {r.status_code} : {r.text[:120]}")
verifier(poser_question("Question Q2 ?").status_code == 409,
         "3b. apres la declaration, redefinir la question est refuse")

# --- 4. Expiration des cles + redemarrage ---------------------------------
# Apres expiration puis redemarrage, l'horloge des cles ne repond plus rien.
# Les groupes declares, eux, sont en base et survivent.

reel = api.gestionnaire_signature.temps_restant_secondes
api.gestionnaire_signature.temps_restant_secondes = lambda: None
try:
    r = poser_question("Question Q2 ?")
finally:
    api.gestionnaire_signature.temps_restant_secondes = reel
verifier(r.status_code == 409,
         "4. horloge des cles muette (expiration + redemarrage) : toujours refuse (F2)",
         f"recu {r.status_code} -- la question se rouvrait a cote du resultat")
verifier(persistance.charger_question() == "Question Q1 bis ?",
         "5. la question n'a pas change pendant ces tentatives",
         repr(persistance.charger_question()))

# --- 6. Cloture : on peut recommencer -------------------------------------

r = client.post("/api/rh/cloturer", json={})
verifier(r.status_code == 200, "6a. cloture acceptee", f"recu {r.status_code}")
verifier(poser_question("Question Q3 ?").status_code == 200,
         "6b. apres la cloture, une nouvelle question se definit")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la question se fige a la declaration des groupes et ne se rouvre pas.")
sys.exit(0)
