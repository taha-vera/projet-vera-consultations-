#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Un depot de vote n'est tolere que 24 h apres l'expiration des cles (F9).

CONSTAT (audit externe du 19/10/2026, F9). A l'expiration des sept jours, la
cle privee est detruite mais les cles PUBLIQUES restent, pour que les votes deja
signes puissent etre deposes. Ce registre n'avait aucune borne de temps : il
vivait jusqu'a la cloture ou au prochain redemarrage, et des depots restaient
acceptes des jours apres la fin annoncee. La documentation promettait « plus
aucun vote n'est accepte ».

CE QUE CE TEST VERIFIE (chemin HTTP reel, expiration simulee)
  1. juste apres l'expiration, un vote DEJA signe est encore accepte (200) :
     le votant qui a obtenu sa signature a l'echeance ne perd pas sa voix ;
  2. a 23 h apres l'expiration, il l'est encore ;
  3. a 25 h, un vote pourtant parfaitement signe est refuse (503, « Aucune
     consultation active ») ET rien n'est ecrit : le compteur ne bouge pas ;
  4. une fois la marge depassee, le refus est definitif : le registre est vide
     (meme apres retour de l'horloge, le depot n'est pas re-accepte) ;
  5. apres expiration, plus aucune signature n'est emise (cle privee detruite).

EXIGE le module Rust compile, comme tests/test_parcours_http.py.
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_marge_")
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
    print("IGNORE : fastapi.testclient indisponible (httpx manquant ?).")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_test_marge"
os.environ["VERA_ADMIN_USER"] = "rh_marge"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402
import vera_signature_manager as sm  # noqa: E402

G = "GroupeMarge"
H = 3600
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


verifier(sm.DELAI_GRACE_DEPOT_SECONDES == 24 * H,
         "0. la marge de depot est de 24 h (constante nommee)",
         str(sm.DELAI_GRACE_DEPOT_SECONDES))

client = TestClient(api.app, base_url="https://testserver")
client.post("/api/rh/connexion", json={"identifiant": "rh_marge", "mot_de_passe": MDP})
client.post("/api/rh/question", json={"intitule": "Question de test ?"})
client.post("/api/rh/declarer_groupes", json={"groupes": [G], "effectifs": {G: 100}})
client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + 2})
r = client.post("/api/rh/generer_autorisations", json={"departement": G, "quantite": 4})
jetons = [a["jeton"] for a in r.json()["autorisations"]]
time.sleep(2.2)
pub = bytes.fromhex(client.get("/api/cle_publique",
                               params={"departement": G}).json()["cle_publique_hex"])


def credential(jeton):
    """Aveuglement client + signature serveur + finalisation client."""
    message = os.urandom(32)
    aveugle, secret, rnd = vbs.aveugler_message(list(pub), list(message))
    rs = client.post("/api/signer_aveugle", json={
        "jeton_autorisation": jeton, "message_aveugle_hex": bytes(aveugle).hex()})
    assert rs.status_code == 200, rs.text
    sig = bytes(vbs.finaliser_signature(
        list(pub), list(message), list(aveugle), list(secret),
        list(bytes.fromhex(rs.json()["signature_aveugle_hex"])), list(rnd)))
    return {"K_hex": message.hex(), "randomizer_hex": bytes(rnd).hex(),
            "signature_hex": sig.hex(), "reponse": "oui", "departement": G,
            "pad": "x" * 100}


# Quatre votants obtiennent leur signature AVANT l'expiration.
creds = [credential(j) for j in jetons]


def total_oui():
    c, _ = persistance.charger_compteurs()
    return c.get(G, {}).get("oui", 0)


gest = api.gestionnaire_signature
ouverture_reelle = gest._ouverture_ts
duree = sm.DUREE_VIE_CLE_SECONDES


def horloge_a(heures_apres_expiration):
    gest._ouverture_ts = time.time() - duree - heures_apres_expiration * H


# --- Expiration (le timer fait exactement cela) ----------------------------
gest._expirer_cle()

horloge_a(0.01)
r = client.post("/api/repondre", json=creds[0])
verifier(r.status_code == 200,
         "1. juste apres l'expiration, un vote deja signe est accepte",
         f"recu {r.status_code} : {r.text[:120]}")

horloge_a(23)
r = client.post("/api/repondre", json=creds[1])
verifier(r.status_code == 200, "2. a 23 h apres l'expiration, il l'est encore",
         f"recu {r.status_code} : {r.text[:120]}")
avant = total_oui()

horloge_a(25)
r = client.post("/api/repondre", json=creds[2])
verifier(r.status_code == 503 and "Aucune consultation" in r.text,
         "3a. a 25 h, un vote parfaitement signe est refuse (503)",
         f"recu {r.status_code} : {r.text[:120]} -- depot accepte apres la marge")
verifier(total_oui() == avant, "3b. et rien n'a ete ecrit : le compteur ne bouge pas",
         f"{avant} -> {total_oui()}")

horloge_a(2)   # l'horloge « revient » : le registre est deja vide
r = client.post("/api/repondre", json=creds[3])
verifier(r.status_code == 503,
         "4. le refus est definitif : la marge depassee ne se rouvre pas",
         f"recu {r.status_code}")

# --- 5. Aucune nouvelle signature apres expiration -------------------------
horloge_a(0.01)
autre = os.urandom(32)
aveugle2, _, _ = vbs.aveugler_message(list(pub), list(autre))
r = client.post("/api/signer_aveugle", json={
    "jeton_autorisation": jetons[3], "message_aveugle_hex": bytes(aveugle2).hex()})
verifier(r.status_code >= 400,
         "5. apres l'expiration, plus aucune signature n'est emise",
         f"recu {r.status_code}")

gest._ouverture_ts = ouverture_reelle
client.post("/api/rh/cloturer", json={})

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : un depot n'est tolere que pendant la marge de 24 h apres l'expiration.")
sys.exit(0)
