#!/usr/bin/env python3
"""Garde : l'epsilon annonce, le budget et l'echelle du bruit ne peuvent pas
diverger sans qu'un test echoue (audit du 15/11/2026, constat E).

Trois valeurs devaient rester coherentes, et rien ne les liait :
  - EPSILON_PAR_PUBLICATION (API) : ce que le budget compte par publication ;
  - le budget total autorise par groupe (API) : une seule publication ;
  - DELTA_INT / SCALE (vera_dp_noise) : l'epsilon que le bruit tient reellement.

Changer SCALE sans toucher a EPSILON_PAR_PUBLICATION aurait fausse le budget en
silence : la comptabilite aurait annonce 0,5 pour un bruit qui en tient un autre.
Ce test relie les trois, et echoue des qu'elles different.
"""
import math
import os
import pathlib
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_eps_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")
os.environ.setdefault("VERA_ADMIN_USER", "rh_eps")
import vera_admin_auth as auth  # noqa: E402
os.environ.setdefault("VERA_ADMIN_HASH", auth.generer_empreinte("motdepasse_eps_test"))

try:
    import vera_dp_noise as bruit
    import vera_consultation_api as api
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


epsilon_bruit = bruit.DELTA_INT / bruit.SCALE
epsilon_api = api.EPSILON_PAR_PUBLICATION
total_budget = api.budget_epsilon._epsilon_total_autorise

verifier(math.isclose(epsilon_bruit, epsilon_api, rel_tol=1e-12),
         "l'epsilon tenu par le bruit (DELTA_INT / SCALE) egale EPSILON_PAR_PUBLICATION",
         f"bruit : {epsilon_bruit} ; API : {epsilon_api}")
verifier(math.isclose(total_budget, epsilon_api, rel_tol=1e-12),
         "le budget total par groupe egale EPSILON_PAR_PUBLICATION (une seule publication)",
         f"budget : {total_budget} ; par publication : {epsilon_api}")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : epsilon annonce, budget et echelle du bruit sont lies.")
sys.exit(0)
