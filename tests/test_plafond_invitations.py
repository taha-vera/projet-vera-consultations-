#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le nombre de liens generes ne peut pas depasser l'effectif declare (D4).

CONSTAT (audit cible du 10/2026). /api/rh/generer_autorisations bornait chaque
APPEL a 1000 liens, mais rien ne bornait le CUMUL : un clic en double, un
script fautif ou une session volee pouvait produire plus de jetons que de
membres -- et chaque jeton est une voix. Le serveur ne connait pas les membres
(c'est ce qui protege leur anonymat) ; il ne peut donc pas verifier un chiffre,
mais il peut exiger qu'on le donne AVANT, le figer, et le faire respecter.

CE QUE CE TEST VERIFIE
  1. declarer des groupes SANS effectifs est refuse (422) ;
  2. un effectif manquant, en trop, nul, negatif, ou qui n'est pas un entier
     strict (chaine, booleen, flottant) est refuse, et rien n'est ecrit ;
  3. une declaration valide fige les effectifs avec les groupes ; l'API les
     rend, et signale un groupe sous K_MIN ;
  4. generer jusqu'au plafond reussit, exactement ; le lot qui le franchirait
     est refuse (409) SANS rien creer, meme d'un seul jeton ;
  5. le plafond est CUMULE : plusieurs lots successifs, et le restant est
     renvoye ;
  6. DEUX APPELS SIMULTANES ne passent pas ensemble le plafond (la verification
     est dans la transaction d'insertion, pas avant) ;
  7. les plafonds sont propres a chaque groupe ;
  8. la cloture efface les plafonds avec le reste : on peut recommencer ;
  9. une consultation declaree AVANT D4 (aucun plafond en base) garde
     l'ancien comportement : on ne peut pas inventer un chiffre.

EXIGE le module Rust compile (l'API refuse de demarrer sans lui), comme
tests/test_parcours_http.py.
"""

import os
import pathlib
import sys
import threading

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db",
                                                 prefix="vera_plafond_")
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

MDP = "motdepasse_test_plafond"
os.environ["VERA_ADMIN_USER"] = "rh_plafond"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

A, B = "Atelier", "Bureau"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


def gen(client, groupe, quantite):
    return client.post("/api/rh/generer_autorisations",
                       json={"departement": groupe, "quantite": quantite})


def nb(groupe):
    return persistance.compter_jetons_par_departement().get(groupe, 0)


client = TestClient(api.app, base_url="https://testserver")
r = client.post("/api/rh/connexion",
                json={"identifiant": "rh_plafond", "mot_de_passe": MDP})
verifier(r.status_code == 200, "0. connexion RH", f"recu {r.status_code}")

r = client.post("/api/rh/question", json={"intitule": "Question de test ?"})
verifier(r.status_code == 200, "0b. question definie", f"recu {r.status_code}")

# --- 1 & 2. Declarations refusees ------------------------------------------

print("\nDeclarations refusees")
refus = [
    ("1. sans effectifs du tout", {"groupes": [A, B]}),
    ("2a. effectif manquant pour un groupe",
     {"groupes": [A, B], "effectifs": {A: 10}}),
    ("2b. effectif donne pour un groupe non declare",
     {"groupes": [A], "effectifs": {A: 10, B: 10}}),
    ("2c. effectif nul", {"groupes": [A], "effectifs": {A: 0}}),
    ("2d. effectif negatif", {"groupes": [A], "effectifs": {A: -5}}),
    ("2e. effectif en chaine", {"groupes": [A], "effectifs": {A: "10"}}),
    ("2f. effectif booleen", {"groupes": [A], "effectifs": {A: True}}),
    ("2g. effectif flottant", {"groupes": [A], "effectifs": {A: 10.5}}),
    ("2h. effectif absurde (> 1 000 000)",
     {"groupes": [A], "effectifs": {A: 10_000_000}}),
]
for libelle, corps in refus:
    r = client.post("/api/rh/declarer_groupes", json=corps)
    verifier(r.status_code == 422,
             libelle + " -> 422", f"recu {r.status_code} : {r.text[:120]}")
verifier(persistance.charger_groupes_declares() is None,
         "2i. aucune de ces tentatives n'a rien ecrit",
         f"groupes = {persistance.charger_groupes_declares()}")

# --- 3. Declaration valide -------------------------------------------------

print("\nDeclaration valide")
r = client.post("/api/rh/declarer_groupes",
                json={"groupes": [A, B], "effectifs": {A: 5, B: 300}})
corps = r.json() if r.status_code == 200 else {}
verifier(r.status_code == 200, "3a. declaration acceptee",
         f"recu {r.status_code} : {r.text[:150]}")
verifier(corps.get("effectifs") == {A: 5, B: 300},
         "3b. la reponse rend les effectifs figes", str(corps.get("effectifs")))
verifier(any(A in w for w in corps.get("avertissements_effectif", [])),
         "3c. un groupe sous K_MIN est signale AVANT l'envoi des liens",
         str(corps.get("avertissements_effectif")))
verifier(not any(B in w for w in corps.get("avertissements_effectif", [])),
         "3d. un groupe au-dessus de K_MIN n'est pas signale")
verifier(persistance.charger_plafonds_invitations() == {A: 5, B: 300},
         "3e. les plafonds sont en base, figes avec les groupes")
r = client.get("/api/rh/groupes_declares")
verifier(r.status_code == 200 and r.json().get("effectifs") == {A: 5, B: 300},
         "3f. /groupes_declares rend les effectifs", r.text[:150])

# --- 4 & 5. Plafond cumule -------------------------------------------------

print("\nPlafond cumule")
r = gen(client, A, 3)
verifier(r.status_code == 200 and r.json().get("restant") == 2
         and r.json().get("plafond") == 5,
         "5a. premier lot de 3 : accepte, il en reste 2", r.text[:150])
r = gen(client, A, 3)
verifier(r.status_code == 409, "4a. un lot de 3 de plus franchirait 5 -> 409",
         f"recu {r.status_code} : {r.text[:150]}")
verifier(nb(A) == 3, "4b. le lot refuse n'a cree AUCUN jeton (pas de lot partiel)",
         f"jetons = {nb(A)}")
verifier("2" in r.text and "5" in r.text,
         "4c. le message dit combien il en reste et sur combien", r.text[:200])
r = gen(client, A, 2)
verifier(r.status_code == 200 and r.json().get("restant") == 0 and nb(A) == 5,
         "4d. generer exactement jusqu'au plafond reussit",
         f"recu {r.status_code} : {r.text[:150]}")
r = gen(client, A, 1)
verifier(r.status_code == 409 and nb(A) == 5,
         "4e. un seul jeton de plus est refuse, plafond atteint",
         f"recu {r.status_code}, jetons = {nb(A)}")

# --- 7. Plafonds propres a chaque groupe -----------------------------------

r = gen(client, B, 10)
verifier(r.status_code == 200 and nb(B) == 10,
         "7. le plafond atteint pour un groupe ne bloque pas l'autre",
         f"recu {r.status_code} : {r.text[:150]}")

# --- 6. Concurrence --------------------------------------------------------

print("\nConcurrence")
# B : 10 generes sur 300. Dix appels simultanes de 40 : un seul tour de 40 ne
# passerait pas 300, mais dix tours font 400. Au plus 7 peuvent aboutir.
statuts = []
verrou_liste = threading.Lock()


def appel():
    c = TestClient(api.app, base_url="https://testserver")
    c.cookies.update(client.cookies)
    r = gen(c, B, 40)
    with verrou_liste:
        statuts.append(r.status_code)


fils = [threading.Thread(target=appel) for _ in range(10)]
for f in fils:
    f.start()
for f in fils:
    f.join()
verifier(nb(B) <= 300,
         "6a. dix appels simultanes ne depassent JAMAIS le plafond",
         f"jetons = {nb(B)} sur 300")
verifier(nb(B) == 10 + 40 * statuts.count(200),
         "6b. chaque appel accepte a cree son lot entier, chaque refus aucun",
         f"jetons = {nb(B)}, statuts = {sorted(statuts)}")
verifier(set(statuts) <= {200, 409},
         "6c. aucun appel n'a plante (que des 200 ou 409)",
         f"statuts = {sorted(statuts)}")

# --- 8. Cloture ------------------------------------------------------------

print("\nCloture")
r = client.post("/api/rh/cloturer", json={})
verifier(r.status_code == 200, "8a. cloture acceptee", f"recu {r.status_code}")
verifier(persistance.charger_plafonds_invitations() is None,
         "8b. les plafonds sont effaces avec le reste",
         str(persistance.charger_plafonds_invitations()))
verifier(persistance.charger_groupes_declares() is None,
         "8c. la liste de groupes est effacee")

# --- 9. Consultation declaree avant D4 -------------------------------------

print("\nConsultation sans plafond en base (declaree avant D4)")
r = client.post("/api/rh/question", json={"intitule": "Question ancienne ?"})
ancien = "GroupeAncien"
api.gestionnaire_signature.cle_publique(ancien)
verifier(persistance.persister_groupes_declares([ancien]) is True,
         "9a. precondition : groupes declares sans plafond")
verifier(persistance.charger_plafonds_invitations() is None,
         "9b. precondition : aucun plafond en base")
r = gen(client, ancien, 50)
verifier(r.status_code == 200 and r.json().get("plafond") is None
         and r.json().get("restant") is None,
         "9c. l'ancien comportement est conserve : pas de plafond invente",
         f"recu {r.status_code} : {r.text[:150]}")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : le nombre de liens ne peut pas depasser l'effectif declare.")
sys.exit(0)
