#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GET /api/rh/resultats ne publie rien -- verifie PAR LA ROUTE (audit A2).

POURQUOI CE TEST S'AJOUTE A tests/test_lecture_ne_publie_pas.py

Ce dernier (Porte 20) n'importe que `vera_epsilon_budget` : il verifie qu'une
LECTURE DU BUDGET ne le consomme pas, jamais que la ROUTE ne publie pas.
L'audit externe du 20/10/2026 (A2) a remis dans GET /api/rh/resultats l'appel
a `_publier_departement` -- la regression du 31/07, ou un tableau de bord
ouvert figeait le resultat sur les 240 premiers votants, declenchable par un
lien piege (GET + cookie SameSite=Lax). Suite complete sur ce mutant : 49 reussis,
0 echec. Cette regression passait la CI.

CE QU'IL FAIT, EN HTTP
  1. trois votants votent pour de vrai (signature aveugle, depot) ; K_MIN est
     abaisse a 3 DANS CE PROCESSUS pour ne pas avoir a deposer 240 votes : seule
     la logique de la route compte ici, pas la valeur du seuil ;
  2. GET /api/rh/resultats, trois fois : publiable mais NON publie, aucun
     budget epsilon consomme, aucun resultat fige en base ;
  3. CONTROLE POSITIF : POST /api/rh/publier publie bien, avec la meme
     installation. Sans lui, « rien n'est publie » pourrait etre vrai parce que
     le test n'atteint jamais le cas ou la publication serait possible ;
  4. un GET apres publication relit le resultat fige, sans en recalculer un.
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_lecture_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

try:
    import vera_blind_sig as vbs
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)
if not callable(getattr(vbs, "generer_cles", None)):
    print("IGNORE : module Rust non compile.")
    raise SystemExit(2)
try:
    from fastapi.testclient import TestClient
except ImportError:
    print("IGNORE : fastapi.testclient indisponible.")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_lecture_http"
os.environ["VERA_ADMIN_USER"] = "rh_lecture"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

if hasattr(api, "ECART_MINIMAL_OUVERTURE_SECONDES"):
    api.ECART_MINIMAL_OUVERTURE_SECONDES = 0

NB_VOTANTS = 3
api.K_MIN = NB_VOTANTS          # voir l'en-tete : seule la logique de la route compte
GROUPE = "LectureHTTP"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")
assert client.post("/api/rh/connexion",
                   json={"identifiant": "rh_lecture", "mot_de_passe": MDP}).status_code == 200
assert client.post("/api/rh/question", json={"intitule": "Question de test, lecture seule ?"}).status_code == 200
r = client.post("/api/rh/declarer_groupes", json={"groupes": [GROUPE], "effectifs": {GROUPE: 5}})
assert r.status_code == 200, r.text
assert client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + 2}).status_code == 200
r = client.post("/api/rh/generer_autorisations", json={"departement": GROUPE, "quantite": NB_VOTANTS})
assert r.status_code == 200, r.text
jetons = [a["jeton"] for a in r.json()["autorisations"]]
time.sleep(2.3)
pub = bytes.fromhex(client.get("/api/cle_publique", params={"departement": GROUPE}).json()["cle_publique_hex"])

for i, jeton in enumerate(jetons):
    message = os.urandom(32)
    aveugle, secret, rnd = vbs.aveugler_message(list(pub), list(message))
    r = client.post("/api/signer_aveugle", json={
        "jeton_autorisation": jeton, "message_aveugle_hex": bytes(aveugle).hex()})
    assert r.status_code == 200, r.text
    sig = bytes(vbs.finaliser_signature(
        list(pub), list(message), list(aveugle), list(secret),
        list(bytes.fromhex(r.json()["signature_aveugle_hex"])), list(rnd)))
    r = client.post("/api/repondre", json={
        "K_hex": bytes(message).hex(), "randomizer_hex": bytes(rnd).hex(),
        "signature_hex": sig.hex(), "reponse": "oui" if i % 2 == 0 else "non",
        "departement": GROUPE, "pad": "x" * 100})
    assert r.status_code == 200, r.text

verifier(api.effectif_par_departement.get(GROUPE) == NB_VOTANTS,
         "1. trois votes reellement deposes par la route",
         f"effectif = {api.effectif_par_departement.get(GROUPE)}")

# --- 2. la lecture ne publie pas -----------------------------------------
lectures = [client.get("/api/rh/resultats") for _ in range(3)]
verifier(all(l.status_code == 200 for l in lectures),
         "2a. GET /api/rh/resultats repond", str([l.status_code for l in lectures]))
entrees = [l.json().get("resultats", l.json()).get(GROUPE, {}) if l.status_code == 200 else {}
           for l in lectures]
verifier(all(e.get("publiable") is True and e.get("publie") is False for e in entrees),
         "2b. le groupe est publiable mais NON publie, a chaque lecture",
         str(entrees))
verifier(api.budget_epsilon.etat(GROUPE)["nombre_publications"] == 0,
         "2c. aucun budget epsilon consomme par la lecture",
         str(api.budget_epsilon.etat(GROUPE)))
verifier(persistance.charger_resultat_publie(GROUPE) is None,
         "2d. aucun resultat fige en base par la lecture")

# --- 3. controle positif : la meme installation sait publier --------------
r = client.post("/api/rh/publier", json={"departement": GROUPE})
verifier(r.status_code == 200,
         "3a. POST /api/rh/publier publie bien (le test peut donc detecter une publication)",
         f"recu {r.status_code} : {r.text[:200]}")
verifier(api.budget_epsilon.etat(GROUPE)["nombre_publications"] == 1,
         "3b. la publication consomme bien UNE fois le budget",
         str(api.budget_epsilon.etat(GROUPE)))
fige = persistance.charger_resultat_publie(GROUPE)
verifier(fige is not None, "3c. le resultat est fige en base apres publication")

# --- 4. un GET apres publication relit, ne recalcule pas -----------------
r = client.get("/api/rh/resultats")
verifier(r.status_code == 200 and api.budget_epsilon.etat(GROUPE)["nombre_publications"] == 1
         and persistance.charger_resultat_publie(GROUPE) == fige,
         "4. un GET apres publication ne republie rien et ne change pas le resultat fige")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la lecture des resultats ne publie rien, verifie par la route.")
sys.exit(0)
