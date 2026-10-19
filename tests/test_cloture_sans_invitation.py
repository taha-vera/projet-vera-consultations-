#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La cloture doit fonctionner meme si AUCUNE invitation n'a ete generee.

CONSTAT (17/10/2026, test reel sur le serveur). Un organisateur declare ses
groupes, puis -- avant d'avoir genere le moindre lien -- veut tout annuler pour
recommencer (faute de frappe dans un nom de groupe, erreur de perimetre).
L'ecran le lui promet : « Cette declaration est definitive [...] il faudrait
cloturer et recommencer. » Or la garde anti-double-cloture ne regardait que les
EFFECTIFS et les INVITATIONS : sans ni l'un ni l'autre, elle repondait
`rien_a_cloturer` et ne faisait RIEN. La question restait figee, la liste de
groupes restait figee, les cles restaient en base jusqu'a leur expiration (7
jours). Aucune issue cote interface.

Pas de fuite de donnees (il n'y avait aucune reponse) mais une impasse : le
seul geste annonce pour recommencer ne marchait pas.

CE QUE CE TEST VERIFIE
  1. groupes declares, zero invitation -> la cloture s'EXECUTE (pas de
     `rien_a_cloturer`), la liste de groupes et la question disparaissent ;
  2. le groupe est inscrit a l'historique des consultations closes ;
  3. un second appel -- double clic, reponse perdue -- repond
     `rien_a_cloturer` (la garde de double-cloture reste intacte) ;
  4. un etat reellement vide repond `rien_a_cloturer` d'emblee.

EXIGE le module Rust compile (l'API refuse de demarrer sans lui), comme
tests/test_parcours_http.py.
"""

import os
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db",
                                                 prefix="vera_cloture_")
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
    print("  cd vera_blind_sig && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 "
          "maturin develop --release")
    raise SystemExit(2)

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("IGNORE : fastapi.testclient indisponible (httpx manquant ?).")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_test_cloture"
os.environ["VERA_ADMIN_USER"] = "rh_cloture"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

GROUPE = "GroupeSansInvitation"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")
r = client.post("/api/rh/connexion",
                json={"identifiant": "rh_cloture", "mot_de_passe": MDP})
verifier(r.status_code == 200, "0. connexion RH", f"recu {r.status_code}")

# --- 4. Etat reellement vide : rien a cloturer, d'emblee ------------------

r = client.post("/api/rh/cloturer", json={})
verifier(r.status_code == 200 and r.json().get("statut") == "rien_a_cloturer",
         "4. etat reellement vide -> rien_a_cloturer",
         f"recu {r.status_code} : {r.text[:150]}")

# --- 1. Groupes declares, aucune invitation -------------------------------

r = client.post("/api/rh/question",
                json={"intitule": "Question de test de cloture ?"})
verifier(r.status_code == 200, "1a. question definie",
         f"recu {r.status_code} : {r.text[:150]}")

r = client.post("/api/rh/declarer_groupes", json={"groupes": [GROUPE], "effectifs": {GROUPE: 5}})
verifier(r.status_code == 200, "1b. groupes declares",
         f"recu {r.status_code} : {r.text[:150]}")

verifier(persistance.charger_groupes_declares() == [GROUPE],
         "1c. precondition : la liste de groupes est bien figee")
verifier(not persistance.compter_jetons_par_departement(),
         "1d. precondition : aucune invitation generee")

r = client.post("/api/rh/cloturer", json={})
corps = r.json() if r.status_code == 200 else {}
verifier(r.status_code == 200, "1e. cloture acceptee",
         f"recu {r.status_code} : {r.text[:150]}")
verifier(corps.get("statut") != "rien_a_cloturer",
         "1f. la cloture S'EXECUTE (elle repondait « rien a cloturer »)",
         f"reponse : {str(corps)[:150]}")
verifier(persistance.charger_groupes_declares() is None,
         "1g. la liste de groupes est effacee : on peut recommencer")
verifier(persistance.charger_question() is None,
         "1h. la question est effacee : elle n'est plus figee")

# --- 2. Historique --------------------------------------------------------

verifier(persistance.compter_consultations_recentes(GROUPE) == 1,
         "2. le groupe est inscrit a l'historique des consultations closes",
         f"compte = {persistance.compter_consultations_recentes(GROUPE)}")

# --- 3. Double cloture : la garde reste intacte ---------------------------

r = client.post("/api/rh/cloturer", json={})
verifier(r.status_code == 200 and r.json().get("statut") == "rien_a_cloturer",
         "3. second appel -> rien_a_cloturer (garde de double-cloture)",
         f"recu {r.status_code} : {r.text[:150]}")
verifier(persistance.compter_consultations_recentes(GROUPE) == 1,
         "3b. le second appel n'a pas dedouble l'historique")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la cloture fonctionne meme sans invitation, et reste idempotente.")
sys.exit(0)
