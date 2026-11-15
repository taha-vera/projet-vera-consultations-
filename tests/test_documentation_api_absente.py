#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'API ne publie ni son schema ni sa documentation interactive (audit d'exposition, 15/11/2026).

CONSTAT. Interrogees en ligne depuis le serveur, /openapi.json, /docs, /redoc et
/docs/oauth2-redirect repondaient 200 : FastAPI les publie par defaut. Le schema listait
toutes les routes, celles de l'administration comprises. Rien de secret (le depot est
public), mais une surface que personne n'avait decidee.

CE QUE CE TEST VERIFIE (reponses reelles, TestClient)
  1. les quatre chemins ci-dessus repondent 404 ;
  2. les routes elles-memes sont toujours la : /api/health repond 200, et une route
     d'administration refuse sans session (401) au lieu de disparaitre (404) -- on a
     retire la DESCRIPTION des routes, pas les routes.
"""

import os
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_nodocs_")
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

os.environ["VERA_ADMIN_USER"] = "rh_nodocs"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte("motdepasse_test_nodocs")

import vera_consultation_api as api  # noqa: E402

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


client = TestClient(api.app, base_url="https://testserver")

for chemin in ("/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"):
    r = client.get(chemin)
    verifier(r.status_code == 404, f"1. {chemin} : 404 (aucune description de l'API en ligne)",
             f"{r.status_code}, {len(r.text)} octets")

r = client.get("/api/health")
verifier(r.status_code == 200, "2a. /api/health repond toujours 200", f"{r.status_code}")
r = client.get("/api/rh/resultats")
verifier(r.status_code == 401,
         "2b. une route d'administration existe toujours : 401 sans session (pas 404)",
         f"{r.status_code}")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : le schema et la documentation interactive de l'API ne sont pas publies.")
sys.exit(0)
