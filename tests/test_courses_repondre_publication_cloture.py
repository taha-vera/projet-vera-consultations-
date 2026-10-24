#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Un vote qui attend le verrou pendant une publication ou une cloture est REFUSE.

CONSTAT (audit externe du 24/10/2026, N4). Mutant survivant : supprimer la
reverification faite sous verrou dans /api/repondre (« deja publie » et « groupe
plus declare ») laissait la suite verte. Le controle en amont du verrou ne protege
que l'instant de son propre appel : un vote qui l'a franchi peut ensuite ATTENDRE
le verrou pendant toute une publication ou une cloture, puis s'ecrire dans un
etat deja fige ou efface, et le votant lirait « enregistre » pour une voix qui ne
figure dans aucun resultat.

COMMENT LA COURSE EST FORCEE, SANS THREADS NI SOMMEIL. Le verrou global est
enveloppe dans un espion : a la prochaine acquisition, AVANT de prendre le vrai
verrou, il execute une action (publier le groupe, ou cloturer) -- exactement ce
que ferait l'autre requete pendant que le vote attend. La verification de
signature, qui a besoin d'un vrai client de vote, est remplacee par un oui : ce
n'est pas l'objet ici.

CE QUE CE TEST VERIFIE
  A. publication intercalee -> 410, et aucun compteur ni K consomme ;
  B. cloture intercalee      -> 410, et aucun K consomme ;
  C. sans course, le meme vote est accepte (temoin : sinon un 410 pourrait venir
     d'ailleurs).
"""

import hashlib
import os
import pathlib
import sys
import types

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_course_")
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

MDP = "motdepasse_test_course"
os.environ["VERA_ADMIN_USER"] = "rh_course"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

api.ECART_MINIMAL_OUVERTURE_SECONDES = 0
G = "GroupeCourse"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


class VerrouEspion:
    """Delegue au vrai verrou ; execute une action unique avant la prochaine
    acquisition, comme si une autre requete passait devant le vote."""

    def __init__(self, reel):
        self.reel = reel
        self.avant = None

    def __enter__(self):
        action, self.avant = self.avant, None
        if action:
            action()
        return self.reel.__enter__()

    def __exit__(self, *a):
        return self.reel.__exit__(*a)

    def locked(self):
        return self.reel.locked()

    def acquire(self, *a, **k):
        return self.reel.acquire(*a, **k)

    def release(self):
        return self.reel.release()


vrai_verrou = api.verrou
espion = VerrouEspion(vrai_verrou)
api.verrou = espion

# Verification de signature : acceptee (voir la docstring).
vrai_vbs = api.vbs
api.vbs = types.SimpleNamespace(**{n: getattr(vrai_vbs, n) for n in dir(vrai_vbs) if not n.startswith("__")})
api.vbs.verifier_signature = lambda *a, **k: True

client = TestClient(api.app, base_url="https://testserver")
client.post("/api/rh/connexion", json={"identifiant": "rh_course", "mot_de_passe": MDP})
SESSION = client.cookies.get("session_vera")


def nouvelle_consultation():
    client.post("/api/rh/question", json={"intitule": "Question de test, course ?"})
    r = client.post("/api/rh/declarer_groupes", json={"groupes": [G], "effectifs": {G: 50}})
    assert r.status_code == 200, r.text


compteur_k = {"n": 0}


def voter():
    """Un depot de vote avec un K neuf ; renvoie (reponse HTTP, empreinte du K)."""
    compteur_k["n"] += 1
    K = hashlib.sha256(b"K-course-%d" % compteur_k["n"]).digest()
    r = client.post("/api/repondre", json={
        "departement": G, "reponse": "oui",
        "K_hex": K.hex(), "randomizer_hex": ("11" * 32), "signature_hex": ("22" * 256)})
    return r, hashlib.sha384(K).hexdigest()


def consomme(empreinte):
    return empreinte in persistance.charger_tokens_consommes()


# --- C. temoin : sans course, le vote passe ---------------------------------
nouvelle_consultation()
r, emp = voter()
verifier(r.status_code == 200 and consomme(emp),
         "C. sans course, le vote est accepte (temoin)", f"{r.status_code} {r.text[:150]}")

# --- A. une publication passe devant le vote ---------------------------------
def publier_entre_temps():
    with vrai_verrou:
        api.effectif_par_departement[G] = 5
        resultat = api._publier_departement(G, 5)
        assert resultat.get("publie"), resultat


espion.avant = publier_entre_temps
r, emp = voter()
verifier(r.status_code == 410,
         "A1. publication intercalee pendant l'attente du verrou : 410, pas « enregistre »",
         f"{r.status_code} {r.text[:200]}")
verifier(not consomme(emp), "A2. ... et le K n'est pas consomme")

# --- B. une cloture passe devant le vote -------------------------------------
api.cloturer_consultation(SESSION)             # remise a zero propre
nouvelle_consultation()


def cloturer_entre_temps():
    api.cloturer_consultation(SESSION)


espion.avant = cloturer_entre_temps
r, emp = voter()
verifier(r.status_code == 410,
         "B1. cloture intercalee pendant l'attente du verrou : 410, pas « enregistre »",
         f"{r.status_code} {r.text[:200]}")
verifier(not consomme(emp), "B2. ... et le K n'est pas consomme")

api.verrou = vrai_verrou
api.vbs = vrai_vbs
print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : un vote qui attendait le verrou pendant une publication ou une cloture est refuse.")
sys.exit(0)
