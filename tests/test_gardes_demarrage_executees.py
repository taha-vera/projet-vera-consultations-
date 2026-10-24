#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les gardes de demarrage sont EXECUTEES : importer le module les declenche vraiment.

CONSTAT (audit externe du 24/10/2026, N4). Mutant survivant : supprimer
_verifier_worker_unique() laissait la suite verte, parce que la garde n°4 de
test_non_regression_correctifs.py cherchait seulement les mots « sys.argv » et
« --workers » dans le source, que les commentaires contiennent deja. Une garde
textuelle qui ne garde rien. Meme remarque pour l'appel de la garde d'ecoute :
test_garde_ecoute_environnement.py appelle la fonction, pas l'import.

CE QUE FAIT CE TEST : il lance un VRAI interpreteur qui importe le module comme
le fait uvicorn, avec la ligne de commande et l'environnement simules, et lit
le code de sortie et le message.
  1. `--workers 2`, `--workers=2`, `-w 2` et WEB_CONCURRENCY=3 : le demarrage est
     refuse, avec le message qui parle de workers ;
  2. `--workers 1` et l'absence d'option : le module s'importe (temoin : sans lui
     un refus pourrait venir d'une autre cause) ;
  3. --host 0.0.0.0 et UVICORN_HOST=0.0.0.0 : refus, message qui parle de l'hote ;
  4. VERA_ECOUTE_PUBLIQUE=1 : l'import reussit malgre --host 0.0.0.0.
Une suppression de l'appel de l'une ou l'autre garde fait echouer ce test.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import vera_admin_auth as auth  # noqa: E402

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


def importer(argv_extra, env_extra=None):
    """Importe le module dans un interpreteur neuf. Renvoie (code, sortie d'erreur)."""
    base = tempfile.mktemp(suffix=".db", prefix="vera_gardes_")
    env = {k: v for k, v in os.environ.items()
           if k not in ("WEB_CONCURRENCY", "UVICORN_HOST", "UVICORN_FD", "VERA_ECOUTE_PUBLIQUE")}
    env.update({
        "VERA_DB_PATH": base,
        "VERA_DB_KEY": "0" * 64,
        "VERA_VERROU_PROCESSUS": base + ".lock",
        "VERA_ADMIN_USER": "rh_gardes",
        "VERA_ADMIN_HASH": auth.generer_empreinte("motdepasse_test_gardes"),
        "PYTHONPATH": str(RACINE),
    })
    env.update(env_extra or {})
    code = ("import sys; sys.argv = ['uvicorn', 'vera_consultation_api:app'] + "
            + repr(argv_extra) + "; import vera_consultation_api")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(RACINE), env=env,
                       capture_output=True, text=True, timeout=120)
    for suffixe in ("", "-journal", ".lock"):
        try:
            os.unlink(base + suffixe)
        except OSError:
            pass
    return r.returncode, r.stderr


# Temoin d'abord : sans lui, un « refus » pourrait venir d'une autre cause.
code, err = importer([])
verifier(code == 0, "0. sans option, le module s'importe (temoin)", err[-400:])
if code != 0:
    print("\nECHEC : le temoin n'importe pas, les autres cas ne prouveraient rien.")
    sys.exit(1)

code, err = importer(["--workers", "1"])
verifier(code == 0, "2a. --workers 1 est accepte", err[-300:])

for libelle, argv, env in (
    ("--workers 2", ["--workers", "2"], None),
    ("--workers=2", ["--workers=2"], None),
    ("-w 2", ["-w", "2"], None),
    ("WEB_CONCURRENCY=3", [], {"WEB_CONCURRENCY": "3"}),
):
    code, err = importer(argv, env)
    verifier(code != 0 and "workers" in err and "REFUSE DE DEMARRER" in err,
             f"1. {libelle} : demarrage refuse, message sur les workers",
             f"code {code}, fin de stderr : {err[-300:]}")

for libelle, argv, env in (
    ("--host 0.0.0.0", ["--host", "0.0.0.0"], None),
    ("UVICORN_HOST=0.0.0.0", [], {"UVICORN_HOST": "0.0.0.0"}),
):
    code, err = importer(argv, env)
    verifier(code != 0 and "REFUS" in err and "0.0.0.0" in err,
             f"3. {libelle} : demarrage refuse, message sur l'hote",
             f"code {code}, fin de stderr : {err[-300:]}")

code, err = importer(["--host", "0.0.0.0"], {"VERA_ECOUTE_PUBLIQUE": "1"})
verifier(code == 0, "4. VERA_ECOUTE_PUBLIQUE=1 : l'import reussit malgre --host 0.0.0.0", err[-300:])

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : les deux gardes de demarrage sont executees a l'import.")
sys.exit(0)
