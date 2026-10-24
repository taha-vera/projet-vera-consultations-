#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La date d'ouverture des votes doit laisser du temps avant l'expiration des cles.

CONSTAT (audit externe du 24/10/2026, N1, reproduit). Les sept jours de vie des
cles partent de la declaration des groupes. La date d'ouverture n'avait pas de
borne haute : question -> declaration (J0) -> ouverture fixee a J+8 -> 200 ->
liens generes -> 200. A J+7 la cle privee est detruite, avant J+8 tout depot
recoit 425. Personne ne pouvait voter, et rien ne l'avait signale. Plus courant :
une ouverture a J+5 ne laisse que deux jours de collecte.

CE QUE CE TEST VERIFIE (chemin HTTP reel)
  1. AVANT la declaration des groupes (aucune cle) : une date a +8 jours est
     refusee (422), une date a +3 jours moins une marge est acceptee ;
  2. APRES la declaration : la borne suit l'echeance REELLE des cles (horloge
     des cles avancee de deux jours -> la borne recule de deux jours) ;
  3. le refus est un 422 qui dit la fenetre et ne modifie rien : la date
     precedente est conservee ;
  4. une cle presque expiree (moins de 72 h) : aucune date n'est utile, le
     message dit de cloturer ;
  5. la borne ne gene pas l'usage normal : une date a +2 secondes, utilisee par
     tous les autres tests, reste acceptee.
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_bornee_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

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
    print("IGNORE : fastapi.testclient indisponible.")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_test_bornee"
os.environ["VERA_ADMIN_USER"] = "rh_bornee"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402
import vera_signature_manager as sm  # noqa: E402

# L'ecart minimal d'une heure n'est pas l'objet : on le neutralise pour que la
# seule borne testee soit la borne haute.
api.ECART_MINIMAL_OUVERTURE_SECONDES = 0
J = 24 * 3600
H = 3600
G = "GroupeBornee"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")
client.post("/api/rh/connexion", json={"identifiant": "rh_bornee", "mot_de_passe": MDP})
client.post("/api/rh/question", json={"intitule": "Question de test, bornee ?"})


def fixer(delta_secondes):
    return client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + delta_secondes})


# --- 1. avant la declaration : pas de cles, borne theorique ---------------
r = fixer(8 * J)
verifier(r.status_code == 422, "1a. sans cles, une ouverture a +8 jours est refusee (422)",
         f"recu {r.status_code} : {r.text[:200]}")
verifier(persistance.charger_ouverture_depots() is None,
         "1b. et rien n'est enregistre")
r = fixer(5 * J)
verifier(r.status_code == 422, "1c. une ouverture a +5 jours (2 jours de collecte) est refusee",
         f"recu {r.status_code}")
verifier("72" in r.text, "1d. le message dit la duree de collecte exigee", r.text[:200])
r = fixer(4 * J - 1 * H)
verifier(r.status_code == 200, "1e. une ouverture a +3 jours 23 h (>= 72 h de collecte) est acceptee",
         f"recu {r.status_code} : {r.text[:200]}")

# --- 2. apres la declaration : la borne suit l'echeance reelle -----------
assert client.post("/api/rh/declarer_groupes",
                   json={"groupes": [G], "effectifs": {G: 50}}).status_code == 200
g = api.gestionnaire_signature
r = fixer(4 * J - 1 * H)
verifier(r.status_code == 200, "2a. apres declaration, +3 j 23 h reste acceptee",
         f"recu {r.status_code} : {r.text[:200]}")
ouverture_avant = persistance.charger_ouverture_depots()

ts_reel = g._ouverture_ts
g._ouverture_ts = ts_reel - 2 * J            # les cles ont deja deux jours
r = fixer(4 * J - 1 * H)
verifier(r.status_code == 422,
         "2b. cles vieilles de 2 jours : la meme date (+3 j 23 h) est maintenant refusee",
         f"recu {r.status_code} : {r.text[:200]}")
verifier(persistance.charger_ouverture_depots() == ouverture_avant,
         "3. le refus laisse la date precedente intacte")
r = fixer(2 * J - 1 * H)
verifier(r.status_code == 200,
         "2c. mais +1 j 23 h (expiration dans ~5 j, soit >= 72 h de collecte) est acceptee",
         f"recu {r.status_code} : {r.text[:200]}")

# --- 4. cles presque expirees : plus aucune date utile -------------------
g._ouverture_ts = ts_reel - (sm.DUREE_VIE_CLE_SECONDES - 10 * H)   # reste 10 h
r = fixer(1 * H)
verifier(r.status_code == 422 and "cloturez" in r.text,
         "4. a moins de 72 h de l'expiration, aucune date n'est utile : le message dit de cloturer",
         f"recu {r.status_code} : {r.text[:200]}")

# --- 5. l'usage normal des autres tests ----------------------------------
g._ouverture_ts = ts_reel
r = fixer(2)
verifier(r.status_code == 200, "5. une ouverture a +2 secondes reste acceptee (cles neuves)",
         f"recu {r.status_code}")

g._ouverture_ts = ts_reel
client.post("/api/rh/cloturer", json={})

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la date d'ouverture est bornee par l'expiration des cles.")
sys.exit(0)
