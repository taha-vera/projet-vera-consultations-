#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GET /api/cle_publique interdit au navigateur de garder l'URL (audit 2, N10).

CONSTAT. static/vote.html appelle GET /api/cle_publique?departement=<groupe> a
chaque ouverture de lien. nginx pose `Cache-Control: no-cache`, qui oblige a
revalider mais autorise le STOCKAGE : le cache HTTP du navigateur garde l'URL, donc
le nom du groupe, et l'heure. Sur un appareil administre par l'employeur, c'est la
trace qu'on est alle jusqu'a la demande de signature. L'application ajoute
`Cache-Control: no-store`, y compris sur les refus (la requete et son URL sont les
memes). nginx n'est pas touche : son en-tete s'AJOUTE a celui de l'application.

CE QUE CE TEST VERIFIE (reponses reelles, TestClient)
  1. 200 (groupe declare) : Cache-Control contient no-store ;
  2. 404 (groupe inconnu)   : idem ;
  3. les autres routes publiques de lecture n'en dependent pas : /api/question
     n'est pas modifiee (pas de nom de groupe dans son URL).
"""

import os
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_nostore_")
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

MDP = "motdepasse_test_nostore"
os.environ["VERA_ADMIN_USER"] = "rh_nostore"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


G = "GroupeNoStore"
client = TestClient(api.app, base_url="https://testserver")
client.post("/api/rh/connexion", json={"identifiant": "rh_nostore", "mot_de_passe": MDP})
client.post("/api/rh/question", json={"intitule": "Question de test, cache ?"})
assert client.post("/api/rh/declarer_groupes",
                   json={"groupes": [G], "effectifs": {G: 50}}).status_code == 200

r = client.get("/api/cle_publique", params={"departement": G})
verifier(r.status_code == 200 and "no-store" in r.headers.get("cache-control", ""),
         "1. 200 : Cache-Control contient no-store",
         f"{r.status_code} {r.headers.get('cache-control')!r}")
r = client.get("/api/cle_publique", params={"departement": "GroupeQuiNExistePas"})
verifier(r.status_code == 404 and "no-store" in r.headers.get("cache-control", ""),
         "2. 404 (groupe inconnu) : Cache-Control contient no-store aussi",
         f"{r.status_code} {r.headers.get('cache-control')!r}")
r = client.get("/api/question")
verifier("no-store" not in r.headers.get("cache-control", ""),
         "3. /api/question (aucun nom de groupe dans l'URL) n'est pas alourdie",
         f"{r.headers.get('cache-control')!r}")

client.post("/api/rh/cloturer", json={})
print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : l'URL de /api/cle_publique n'est pas stockee par le navigateur.")
sys.exit(0)
