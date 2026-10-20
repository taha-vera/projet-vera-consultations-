#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Une cloture intercalee pendant la generation ne laisse aucun jeton orphelin.

CONSTAT (audit externe du 19/10/2026, F8). generer_autorisations verifie que le
groupe est declare, puis que ses cles existent, HORS verrou ; l'insertion des
jetons ne revoyait rien. Une cloture intercalee entre les deux produisait 200 et
N liens, alors que la consultation n'existait plus : question_active vide, N
jetons en base. Consequences, dans la consultation SUIVANTE : le compteur
d'invitations publie affichait N avant toute generation (faussant le controle du
tiers qui atteste l'effectif), le plafond etait amputé d'autant, et les anciens
liens -- que le transporteur a pu garder -- restaient des credentials valides.

CE QUE CE TEST VERIFIE
  1. une cloture executee ENTRE les controles de l'API et l'insertion (entrelacement
     force) -> la generation est refusee (409) et RIEN n'est ecrit ;
  2. aucun jeton ne reste en base, et le compteur d'invitations de la consultation
     suivante part de zero ;
  3. sans cloture, la meme generation reussit (le controle ne refuse pas a tort) ;
  4. le plafond lu est celui de la declaration EN COURS, pas celui d'une
     declaration precedente.

EXIGE le module Rust compile (l'API refuse de demarrer sans lui).
"""

import os
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db",
                                                 prefix="vera_course_")
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

MDP = "motdepasse_test_course"
os.environ["VERA_ADMIN_USER"] = "rh_course"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

GROUPE = "GroupeCourse"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")
r = client.post("/api/rh/connexion",
                json={"identifiant": "rh_course", "mot_de_passe": MDP})
verifier(r.status_code == 200, "0. connexion RH", f"recu {r.status_code}")


def preparer(effectif):
    client.post("/api/rh/question", json={"intitule": "Question de test ?"})
    return client.post("/api/rh/declarer_groupes",
                       json={"groupes": [GROUPE], "effectifs": {GROUPE: effectif}})


def generer(n):
    return client.post("/api/rh/generer_autorisations",
                       json={"departement": GROUPE, "quantite": n})


# --- 3. Sans cloture : la generation reussit ------------------------------

verifier(preparer(100).status_code == 200, "3a. consultation preparee")
r = generer(5)
verifier(r.status_code == 200, "3b. sans cloture, la generation reussit",
         f"recu {r.status_code} : {r.text[:120]}")
client.post("/api/rh/cloturer", json={})

# --- 1 & 2. Cloture intercalee --------------------------------------------

verifier(preparer(100).status_code == 200, "1a. consultation preparee de nouveau")

lot_reel = persistance.persister_jetons_autorisation_lot


def lot_apres_cloture(*args, **kwargs):
    """Entrelacement force : la cloture passe APRES les controles de l'API,
    AVANT l'insertion -- le moment que la course visait."""
    rc = client.post("/api/rh/cloturer", json={})
    assert rc.status_code == 200, rc.text
    return lot_reel(*args, **kwargs)


api.persistance.persister_jetons_autorisation_lot = lot_apres_cloture
try:
    r = generer(50)
finally:
    api.persistance.persister_jetons_autorisation_lot = lot_reel

verifier(r.status_code == 409,
         "1b. generation refusee quand la cloture s'est intercalee (F8)",
         f"recu {r.status_code} : {r.text[:120]} -- 50 liens renvoyes pour "
         "une consultation qui n'existe plus")
verifier("Aucun lien" in r.text, "1c. le message dit qu'aucun lien n'a ete cree",
         r.text[:150])
verifier(persistance.compter_jetons_par_departement() == {},
         "2a. AUCUN jeton orphelin en base",
         str(persistance.compter_jetons_par_departement()))
verifier(persistance.charger_groupes_declares() is None,
         "2b. la cloture a bien eu lieu (rien de declare)")

# --- 2c & 4. La consultation suivante part de zero, avec SON plafond ------

verifier(preparer(7).status_code == 200, "2c. consultation suivante declaree (7)")
verifier(persistance.compter_jetons_par_departement() == {},
         "2d. son compteur d'invitations part de zero")
r = generer(7)
verifier(r.status_code == 200 and r.json().get("plafond") == 7
         and r.json().get("restant") == 0,
         "4a. le plafond appliqué est celui de la declaration EN COURS (7)",
         f"recu {r.status_code} : {r.text[:120]}")
verifier(generer(1).status_code == 409, "4b. et il est tenu")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : une cloture intercalee ne laisse aucun jeton orphelin.")
sys.exit(0)
