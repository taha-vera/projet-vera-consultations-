#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La date d'ouverture des votes est obligatoire avant tout lien (audit A4).

CONSTAT (audit externe du 20/10/2026, A4). Rien n'exigeait de date avant de generer
ou d'envoyer les liens ; « maintenant + 1 seconde » etait accepte ; et sans date
fixee, les votes etaient acceptes des la reception. Or la date est la seule chose
qui separe l'ORDRE DES ENVOIS de l'ORDRE DES VOTES : sans elle, l'ordre des votes
reproduit l'ordre dans lequel l'organisateur a envoye ses invitations, ce qui
suffit a attribuer des reponses dans un petit groupe. La protection dependait du
bon vouloir de celui contre qui elle protege en partie.

DECISION DU MAINTENEUR (22/10/2026) : date OBLIGATOIRE avant de generer des liens,
au moins une heure dans le futur au moment ou on la fixe ; un lien de
REMPLACEMENT reste possible apres l'ouverture (un membre qui a perdu le sien doit
pouvoir voter).

CE QUE CE TEST VERIFIE, PAR LES ROUTES (l'ecart minimal de production n'est PAS
neutralise ici)
  1. sans date : generer des liens est refuse (409) et AUCUN lien n'est cree ;
  2. date a maintenant + 1 s, puis + 30 min : refusee (422) ;
  3. date a + 2 h : acceptee, et la generation passe ;
  4. apres l'ouverture, un lien de remplacement se genere encore ;
  5. une date deja passee ne peut plus etre modifiee (409), comme avant.
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_ouverture_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("IGNORE : fastapi.testclient indisponible.")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_ouverture"
os.environ["VERA_ADMIN_USER"] = "rh_ouverture"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

G = "GroupeOuverture"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


verifier(api.ECART_MINIMAL_OUVERTURE_SECONDES >= 3600,
         "0. l'ecart minimal de production est d'au moins une heure",
         str(api.ECART_MINIMAL_OUVERTURE_SECONDES))

client = TestClient(api.app, base_url="https://testserver")
assert client.post("/api/rh/connexion",
                   json={"identifiant": "rh_ouverture", "mot_de_passe": MDP}).status_code == 200
assert client.post("/api/rh/question", json={"intitule": "Question de test ?"}).status_code == 200
assert client.post("/api/rh/declarer_groupes",
                   json={"groupes": [G], "effectifs": {G: 50}}).status_code == 200


def generer(n=2):
    return client.post("/api/rh/generer_autorisations", json={"departement": G, "quantite": n})


def nb():
    return persistance.compter_jetons_par_departement().get(G, 0)


# --- 1. sans date : refuse, rien n'est cree ---------------------------------
r = generer()
verifier(r.status_code == 409 and "date d'ouverture" in r.text,
         "1a. sans date d'ouverture, generer des liens est refuse (409)",
         f"recu {r.status_code} : {r.text[:150]}")
verifier(nb() == 0, "1b. ... et aucun lien n'a ete cree", f"{nb()} jeton(s)")
verifier("Aucun lien n'a ete cree" in r.text, "1c. ... le message le dit")

# --- 2. date trop proche ----------------------------------------------------
for libelle, delta in (("maintenant + 1 s", 1), ("maintenant + 30 min", 1800)):
    r = client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + delta})
    verifier(r.status_code == 422,
             f"2. date a {libelle} : refusee (422)", f"recu {r.status_code} : {r.text[:150]}")
verifier(persistance.charger_ouverture_depots() is None,
         "2b. ... et rien n'a ete enregistre")

# --- 3. date valide, puis generation ----------------------------------------
r = client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + 7200})
verifier(r.status_code == 200, "3a. date a + 2 h : acceptee", f"recu {r.status_code} : {r.text[:150]}")
r = generer(3)
verifier(r.status_code == 200 and nb() == 3,
         "3b. avec une date, la generation passe", f"recu {r.status_code} : {r.text[:150]}")

# --- 4. apres l'ouverture, un lien de remplacement reste possible -----------
persistance.persister_ouverture_depots(time.time() - 10)    # l'ouverture est passee
r = generer(1)
verifier(r.status_code == 200 and nb() == 4,
         "4. apres l'ouverture, un lien de remplacement se genere encore",
         f"recu {r.status_code} : {r.text[:150]}")

# --- 5. une date passee ne se modifie plus ----------------------------------
r = client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + 7200})
verifier(r.status_code == 409,
         "5. une fois les votes ouverts, la date ne peut plus etre modifiee (409)",
         f"recu {r.status_code}")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la date d'ouverture est obligatoire avant tout lien, et ne peut pas etre posee pour la forme.")
sys.exit(0)
