#!/usr/bin/env python3
"""Garde : un meme jeton ne declenche qu'UNE operation de cle privee, meme sous
requetes simultanees (audit du 15/11/2026, constat 6).

Avant le verrou par jeton, N requetes simultanees sur un meme jeton, avec N
messages aveugles differents, passaient toutes le controle « jeton libre », et
faisaient toutes une operation de cle privee : une seule signature etait livree,
mais N calculs etaient executes, et les perdants recevaient leur 403 APRES le
calcul (duree mesurable). Mesure : 24 requetes -> 24 operations.

Ce test compte les operations de cle privee reellement demandees au gestionnaire
de signature. Il verifie :
  1. N requetes simultanees, meme jeton, messages differents : exactement une
     reponse 200, N-1 reponses 403, et UNE seule operation de cle privee ;
  2. une requete ulterieure sur ce jeton est refusee sans aucun calcul ;
  3. le rejeu identique (meme jeton, meme message) retrouve sa signature : le
     verrou ne casse pas l'idempotence ;
  4. des jetons DIFFERENTS en parallele sont tous signes (le verrou ne bloque pas
     le service).

La signature est ralentie de 50 ms dans le test : une vraie signature RSA-2048
dure quelques millisecondes, et on veut une fenetre de course large pour que le
defaut, s'il revient, ne passe pas inapercu par chance.
"""
import os
import pathlib
import sys
import tempfile
import threading
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_conc_")
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

MDP = "motdepasse_concurrence"
os.environ["VERA_ADMIN_USER"] = "rh_conc"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402

if hasattr(api, "ECART_MINIMAL_OUVERTURE_SECONDES"):
    api.ECART_MINIMAL_OUVERTURE_SECONDES = 0

GROUPE = "Concurrence"
NB_REQUETES = 24
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")
r = client.post("/api/rh/connexion", json={"identifiant": "rh_conc", "mot_de_passe": MDP})
assert r.status_code == 200, r.text
assert client.post("/api/rh/question", json={"intitule": "Question de test, concurrence ?"}).status_code == 200
assert client.post("/api/rh/declarer_groupes", json={"groupes": [GROUPE], "effectifs": {GROUPE: 10}}).status_code == 200
assert client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + 2}).status_code == 200
r = client.post("/api/rh/generer_autorisations", json={"departement": GROUPE, "quantite": 5})
assert r.status_code == 200, r.text
jetons = [a["jeton"] for a in r.json()["autorisations"]]
time.sleep(2.3)

pub = bytes.fromhex(client.get("/api/cle_publique", params={"departement": GROUPE}).json()["cle_publique_hex"])

# Espion : compte les operations de cle privee demandees au gestionnaire.
compteur = {"n": 0}
verrou_compteur = threading.Lock()
_signer_reel = api.gestionnaire_signature.signer_message_aveugle


def _espion(departement, message):
    with verrou_compteur:
        compteur["n"] += 1
    time.sleep(0.05)
    return _signer_reel(departement, message)


api.gestionnaire_signature.signer_message_aveugle = _espion


def aveugle_neuf():
    aveugle, _, _ = vbs.aveugler_message(list(pub), list(os.urandom(32)))
    return bytes(aveugle).hex()


def demander(jeton, hexa):
    return client.post("/api/signer_aveugle",
                       json={"jeton_autorisation": jeton, "message_aveugle_hex": hexa})


# ---- 1. Course : meme jeton, messages differents -------------------------------
print("1. Requetes simultanees sur un meme jeton")
jeton = jetons[0]
messages = [aveugle_neuf() for _ in range(NB_REQUETES)]
codes = [None] * NB_REQUETES
barriere = threading.Barrier(NB_REQUETES)


def appel(i):
    barriere.wait()
    codes[i] = demander(jeton, messages[i]).status_code


fils = [threading.Thread(target=appel, args=(i,)) for i in range(NB_REQUETES)]
[f.start() for f in fils]
[f.join() for f in fils]
verifier(codes.count(200) == 1,
         f"exactement une signature livree ({NB_REQUETES} requetes)",
         f"statuts : { {k: codes.count(k) for k in sorted(set(codes))} }")
verifier(codes.count(403) == NB_REQUETES - 1,
         "toutes les autres requetes recoivent 403",
         f"statuts : { {k: codes.count(k) for k in sorted(set(codes))} }")
verifier(compteur["n"] == 1,
         "UNE seule operation de cle privee pour ce jeton",
         f"{compteur['n']} operations executees (avant le verrou : {NB_REQUETES})")

# ---- 2. Refus sequentiel : avant tout calcul -----------------------------------
print("2. Requete ulterieure sur le jeton consomme")
avant = compteur["n"]
r = demander(jeton, aveugle_neuf())
verifier(r.status_code == 403, "refusee en 403")
verifier(compteur["n"] == avant, "refusee SANS aucune operation de cle privee",
         f"{compteur['n'] - avant} operation(s) ajoutee(s)")

# ---- 3. Rejeu identique : l'idempotence survit ---------------------------------
print("3. Rejeu identique (meme jeton, meme message)")
jeton2 = jetons[1]
m = aveugle_neuf()
r1 = demander(jeton2, m)
avant = compteur["n"]
r2 = demander(jeton2, m)
verifier(r1.status_code == 200 and r2.status_code == 200, "les deux appels reussissent",
         f"{r1.status_code} puis {r2.status_code}")
verifier(r1.json().get("signature_aveugle_hex") == r2.json().get("signature_aveugle_hex"),
         "la meme signature est renvoyee")
verifier(compteur["n"] == avant, "le rejeu ne refait aucun calcul")

# ---- 4. Jetons differents en parallele : tous signes ---------------------------
print("4. Jetons differents, en parallele")
autres = jetons[2:5]
codes4 = [None] * len(autres)


def appel4(i):
    codes4[i] = demander(autres[i], aveugle_neuf()).status_code


fils = [threading.Thread(target=appel4, args=(i,)) for i in range(len(autres))]
[f.start() for f in fils]
[f.join() for f in fils]
verifier(codes4 == [200] * len(autres), "chaque jeton distinct obtient sa signature",
         f"statuts : {codes4}")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : un jeton = une operation de cle privee, meme en concurrence ; idempotence et parallelisme intacts.")
sys.exit(0)
