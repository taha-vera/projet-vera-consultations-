#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deux mutants survivants de l'audit du 24/10/2026 (N4), maintenant tues.

1. LA SECONDE PUBLICATION RENVOIE LE RESULTAT FIGE. Mutant : supprimer le
   court-circuit « deja publie » de _publier_departement. Sans danger pour
   l'anonymat (le budget epuise et la cle primaire de resultats_publies
   refusaient le second tirage), mais la seconde publication renvoyait alors un
   refus 409 au lieu du resultat fige, et aucun test ne le voyait. Re-tirer
   serait pire : moyenner N tirages annulerait le bruit.
     a. POST /api/rh/publier deux fois : 200 puis 200 ;
     b. les deux resultats sont IDENTIQUES (octet pour octet) ;
     c. une seule publication est decomptee dans le budget.

2. persister_jeton_autorisation LEVE sur collision (A10). Mutant : le remettre
   en ON CONFLICT DO NOTHING. L'ancienne fonction ignorait en silence une
   empreinte deja presente et rendait un succes : un lien de plus sans ligne a
   lui, ou partage avec un autre.
     a. le meme jeton enregistre deux fois leve CollisionJetonErreur ;
     b. une seule ligne existe pour lui ensuite.
"""

import os
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_figee_")
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

MDP = "motdepasse_test_figee"
os.environ["VERA_ADMIN_USER"] = "rh_figee"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


G = "GroupeFige"
client = TestClient(api.app, base_url="https://testserver")
client.post("/api/rh/connexion", json={"identifiant": "rh_figee", "mot_de_passe": MDP})
client.post("/api/rh/question", json={"intitule": "Question de test, figee ?"})
assert client.post("/api/rh/declarer_groupes",
                   json={"groupes": [G], "effectifs": {G: 50}}).status_code == 200

# --- 1. double publication ---------------------------------------------------
api.K_MIN = 3                                   # le test n'attend pas 240 votes
with api.verrou:
    api.effectif_par_departement[G] = 5
    api.compteurs_par_departement[G] = {"oui": 3, "non": 2, "abstention": 0}
r1 = client.post("/api/rh/publier", json={"departement": G})
r2 = client.post("/api/rh/publier", json={"departement": G})
verifier(r1.status_code == 200 and r2.status_code == 200,
         "1a. deux POST /api/rh/publier : 200 puis 200 (pas de refus a la seconde)",
         f"{r1.status_code} {r1.text[:100]} / {r2.status_code} {r2.text[:150]}")
verifier(r1.status_code == 200 and r1.json().get("resultats_bruits") == r2.json().get("resultats_bruits"),
         "1b. le second resultat est IDENTIQUE au premier (resultat fige, pas de nouveau tirage)",
         f"{r1.text[:150]} / {r2.text[:150]}")
verifier(api.budget_epsilon.etat(G)["nombre_publications"] == 1,
         "1c. une seule publication est decomptee dans le budget",
         str(api.budget_epsilon.etat(G)))

# --- 2. collision dans persister_jeton_autorisation (A10) --------------------
jeton = "jeton_de_test_collision_" + "x" * 24
persistance.persister_jeton_autorisation(jeton, G)
try:
    persistance.persister_jeton_autorisation(jeton, G)
    leve = False
except persistance.CollisionJetonErreur:
    leve = True
verifier(leve, "2a. le meme jeton enregistre deux fois leve CollisionJetonErreur (pas de succes silencieux)")
lignes = persistance.compter_jetons_par_departement().get(G, 0)
verifier(lignes == 1, "2b. une seule ligne existe pour ce jeton", f"{lignes} ligne(s)")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : publication figee et collision de jeton gardees.")
sys.exit(0)
