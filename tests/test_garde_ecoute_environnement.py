#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La garde « uvicorn n'ecoute que sur la boucle locale » voit aussi l'environnement.

CONSTAT (audit du 20/10/2026, A5, reproduit). uvicorn lit ses options dans
l'environnement (prefixe UVICORN_). Avec UVICORN_HOST=0.0.0.0 le service
demarrait et annoncait « running on http://0.0.0.0:8098 » : la garde ne
regardait que sys.argv, donc nginx etait contourne (journaux, debit, CSP).

CE QUE CE TEST VERIFIE (appel direct de la garde, environnement et argv simules)
  1. UVICORN_HOST=0.0.0.0 est refuse ;
  2. UVICORN_HOST=127.0.0.1 et l'absence de variable sont acceptes ;
  3. --host 0.0.0.0 reste refuse, et --host 127.0.0.1 l'emporte sur
     UVICORN_HOST=0.0.0.0 (la ligne de commande prime, comme dans uvicorn) ;
  4. un descripteur herite (UVICORN_FD ou --fd) est refuse ;
  5. VERA_ECOUTE_PUBLIQUE=1 permet toujours de passer outre, volontairement ;
  6. gunicorn (audit du 24/10/2026, N12) : -b / --bind / --bind= et
     GUNICORN_CMD_ARGS vers une adresse non locale sont refuses ; 127.0.0.1,
     [::1], localhost et unix:... sont acceptes.
"""

import os
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_ecoute_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

import vera_admin_auth as auth  # noqa: E402

os.environ["VERA_ADMIN_USER"] = "rh_ecoute"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte("motdepasse_test_ecoute")

try:
    import vera_consultation_api as api  # noqa: E402
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)

VARIABLES = ("UVICORN_HOST", "UVICORN_FD", "VERA_ECOUTE_PUBLIQUE", "GUNICORN_CMD_ARGS")
argv_origine = list(sys.argv)
echecs = []


def verifier(condition, message):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message)
        print(f"  ECHEC  {message}")


def refuse(env=None, argv=None):
    """True si la garde leve RuntimeError dans cet environnement."""
    for v in VARIABLES:
        os.environ.pop(v, None)
    os.environ.update(env or {})
    sys.argv = ["uvicorn"] + list(argv or [])
    try:
        api._verifier_ecoute_loopback()
        return False
    except RuntimeError:
        return True
    finally:
        sys.argv = argv_origine
        for v in VARIABLES:
            os.environ.pop(v, None)


verifier(refuse({"UVICORN_HOST": "0.0.0.0"}),
         "1. UVICORN_HOST=0.0.0.0 est refuse")
verifier(not refuse({"UVICORN_HOST": "127.0.0.1"}),
         "2a. UVICORN_HOST=127.0.0.1 est accepte")
verifier(not refuse(),
         "2b. sans hote (ni option ni variable), rien a signaler")
verifier(refuse(argv=["--host", "0.0.0.0"]),
         "3a. --host 0.0.0.0 reste refuse")
verifier(not refuse({"UVICORN_HOST": "0.0.0.0"}, ["--host=127.0.0.1"]),
         "3b. la ligne de commande 127.0.0.1 prime sur l'environnement 0.0.0.0")
verifier(refuse({"UVICORN_HOST": "127.0.0.1"}, ["--host=0.0.0.0"]),
         "3c. et l'inverse : --host 0.0.0.0 prime sur UVICORN_HOST=127.0.0.1")
verifier(refuse({"UVICORN_FD": "3"}),
         "4a. UVICORN_FD est refuse (adresse non verifiable)")
verifier(refuse(argv=["--fd", "3"]),
         "4b. --fd est refuse")
verifier(not refuse({"UVICORN_HOST": "0.0.0.0", "VERA_ECOUTE_PUBLIQUE": "1"}),
         "5. VERA_ECOUTE_PUBLIQUE=1 permet de passer outre")

for libelle, argv, env in (
    ("-b 0.0.0.0:8001", ["-b", "0.0.0.0:8001"], None),
    ("--bind 0.0.0.0:8001", ["--bind", "0.0.0.0:8001"], None),
    ("--bind=0.0.0.0:8001", ["--bind=0.0.0.0:8001"], None),
    ("-b0.0.0.0:8001", ["-b0.0.0.0:8001"], None),
    ("--bind :8001 (toutes interfaces)", ["--bind", ":8001"], None),
    ("--bind [::]:8001", ["--bind", "[::]:8001"], None),
    ("GUNICORN_CMD_ARGS=--bind 0.0.0.0:8001", [], {"GUNICORN_CMD_ARGS": "--bind 0.0.0.0:8001"}),
):
    verifier(refuse(env, argv), f"6a. gunicorn {libelle} est refuse")
for libelle, argv, env in (
    ("-b 127.0.0.1:8001", ["-b", "127.0.0.1:8001"], None),
    ("--bind=localhost:8001", ["--bind=localhost:8001"], None),
    ("--bind [::1]:8001", ["--bind", "[::1]:8001"], None),
    ("--bind unix:/run/vera.sock", ["--bind", "unix:/run/vera.sock"], None),
    ("GUNICORN_CMD_ARGS=--bind 127.0.0.1:8001", [], {"GUNICORN_CMD_ARGS": "--bind 127.0.0.1:8001"}),
):
    verifier(not refuse(env, argv), f"6b. gunicorn {libelle} est accepte")
verifier(not refuse({"GUNICORN_CMD_ARGS": "--bind 0.0.0.0:8001", "VERA_ECOUTE_PUBLIQUE": "1"}),
         "6c. VERA_ECOUTE_PUBLIQUE=1 passe outre aussi pour gunicorn")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la garde d'ecoute voit l'environnement et la ligne de commande.")
sys.exit(0)
