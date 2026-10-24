#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aucune reponse de /api/signer_aveugle ne distingue un jeton utilise d'un jeton libre.

CE QUE CE TEST PROTEGE (audit du 20/10/2026, constat A1)

L'organisateur detient tous les jetons : il les a generes. Si la route de
signature repondait differemment selon qu'un jeton a deja servi ou non, il
pourrait, apres l'ouverture, sonder chaque jeton avec un message aveugle
volontairement invalide (256 octets a 0xff, toujours >= n) et lire QUI a vote
et a quelle heure -- sans acces a la base, sans journal, sans rien consommer.
Mesure sur le code d'avant le correctif : jeton utilise -> 403, jeton libre
-> 422.

CE QU'IL VERIFIE, EN HTTP, SUR LA VRAIE ROUTE
  1. sonde invalide : jeton utilise, jeton libre et jeton inconnu recoivent
     exactement la meme reponse (statut ET corps) ;
  2. la sonde ne consomme rien : le jeton libre signe ensuite normalement ;
  3. second message VALIDE sur un jeton qui vient de signer : meme reponse que
     pour un jeton inconnu ;
  4. consultation expiree : meme reponse pour un jeton utilise et un jeton libre ;
  5. une longueur invalide reste refusee en 422, pour tous les jetons de la
     meme facon (la longueur ne depend pas du jeton) ;
  6. tout refus fait le MEME TRAVAIL (une lecture du cache des signatures, une
     recherche du departement, une analyse de cle) : pas de branche plus courte
     pour un jeton utilise ou inconnu (audit du 24/10/2026, N8).

Un test qui lirait le code au lieu d'appeler la route ne verrait pas une
regression : celui-ci appelle la route.
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_indist_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

try:
    import vera_blind_sig as vbs
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)
if not callable(getattr(vbs, "generer_cles", None)):
    print("IGNORE : module Rust non compile.")
    raise SystemExit(2)
try:
    from fastapi.testclient import TestClient
except ImportError:
    print("IGNORE : fastapi.testclient indisponible.")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_indistinguable"
os.environ["VERA_ADMIN_USER"] = "rh_indist"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402

# Ce test fixe l'ouverture a quelques secondes ; l'ecart minimal de production
# (une heure) n'a pas a le ralentir.
if hasattr(api, "ECART_MINIMAL_OUVERTURE_SECONDES"):
    api.ECART_MINIMAL_OUVERTURE_SECONDES = 0

GROUPE = "Indistinguable"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


def forme(r):
    """Ce qu'un appelant peut observer : statut et corps."""
    return (r.status_code, r.text)


client = TestClient(api.app, base_url="https://testserver")
r = client.post("/api/rh/connexion", json={"identifiant": "rh_indist", "mot_de_passe": MDP})
assert r.status_code == 200, r.text
assert client.post("/api/rh/question", json={"intitule": "Question de test, indistinguable ?"}).status_code == 200
assert client.post("/api/rh/declarer_groupes", json={"groupes": [GROUPE], "effectifs": {GROUPE: 5}}).status_code == 200
assert client.post("/api/rh/ouverture", json={"ouverture_unix": time.time() + 2}).status_code == 200
r = client.post("/api/rh/generer_autorisations", json={"departement": GROUPE, "quantite": 4})
assert r.status_code == 200, r.text
jetons = [a["jeton"] for a in r.json()["autorisations"]]
time.sleep(2.3)

pub = bytes.fromhex(client.get("/api/cle_publique", params={"departement": GROUPE}).json()["cle_publique_hex"])


def signer(jeton, message=None):
    msg = message if message is not None else os.urandom(32)
    aveugle, _, _ = vbs.aveugler_message(list(pub), list(msg))
    return client.post("/api/signer_aveugle", json={
        "jeton_autorisation": jeton, "message_aveugle_hex": bytes(aveugle).hex()})


def sonde(jeton, hexa="ff" * 256):
    return client.post("/api/signer_aveugle", json={
        "jeton_autorisation": jeton, "message_aveugle_hex": hexa})


UTILISE, LIBRE, LIBRE2, LIBRE3 = jetons
INCONNU = "jeton-qui-n-a-jamais-existe"

# Alice (UTILISE) vote : son jeton est consomme.
r = signer(UTILISE)
verifier(r.status_code == 200, "0. un jeton libre signe normalement", f"recu {r.status_code} : {r.text[:150]}")

# --- 1. sonde invalide (m >= n) ------------------------------------------
ru, rl, ri = sonde(UTILISE), sonde(LIBRE), sonde(INCONNU)
verifier(forme(ru) == forme(rl) == forme(ri),
         "1. sonde m >= n : jeton utilise, libre et inconnu recoivent la meme reponse",
         f"utilise={forme(ru)} libre={forme(rl)} inconnu={forme(ri)}")
verifier(ru.status_code == 403,
         "1b. cette reponse est un 403 (pas un 422 qui signerait un jeton libre)",
         f"recu {ru.status_code}")

# --- 2. la sonde ne consomme rien ----------------------------------------
sonde(LIBRE); sonde(LIBRE)
r = signer(LIBRE)
verifier(r.status_code == 200,
         "2. apres des sondes, le jeton libre signe encore normalement",
         f"recu {r.status_code} : {r.text[:150]}")

# --- 3. second message VALIDE sur un jeton qui vient de signer ------------
r_second = signer(UTILISE)                       # message different, jeton utilise
r_inconnu = signer(INCONNU)                      # jeton qui n'existe pas
verifier(forme(r_second) == forme(r_inconnu),
         "3. second message valide sur un jeton utilise = reponse d'un jeton inconnu",
         f"utilise={forme(r_second)} inconnu={forme(r_inconnu)}")
r_second2 = signer(LIBRE)                        # LIBRE vient de signer a l'etape 2
verifier(forme(r_second2) == forme(r_inconnu),
         "3b. meme chose pour un jeton qui vient de signer (cache, dans l'heure)",
         f"recu {forme(r_second2)}")

# --- 5. longueur invalide : meme reponse pour tous -----------------------
trop_court = "ab" * 10
formes = {forme(sonde(j, trop_court)) for j in (UTILISE, LIBRE2, INCONNU)}
verifier(len(formes) == 1 and next(iter(formes))[0] == 422,
         "5. longueur invalide : 422 identique pour tous les jetons",
         str(formes))

# --- 4. consultation expiree : meme reponse -------------------------------
_reel = api.gestionnaire_signature.consultation_active
api.gestionnaire_signature.consultation_active = lambda: False
try:
    e_utilise = sonde(UTILISE)
    e_libre = sonde(LIBRE3)
    e_inconnu = sonde(INCONNU)
finally:
    api.gestionnaire_signature.consultation_active = _reel
verifier(forme(e_utilise) == forme(e_libre) == forme(e_inconnu) and e_libre.status_code == 503,
         "4. consultation expiree : meme reponse (503) pour utilise, libre et inconnu",
         f"utilise={forme(e_utilise)} libre={forme(e_libre)} inconnu={forme(e_inconnu)}")

# --- 6. MEME TRAVAIL pour tout jeton qui ne peut pas signer (audit N8) ------
# La duree d'une reponse ne se teste pas de facon fiable (c'est du bruit). Ce
# qui se teste, c'est l'ABSENCE de branche plus courte : chaque refus doit lire
# le jeton, chercher le departement, et analyser UNE cle publique. Avant le
# correctif, un jeton utilise ou inconnu s'arretait avant l'analyse de la cle
# (12 microsecondes d'ecart mesurees, 36 avec 1500 signatures en cache).
compteurs = {"cle": 0, "deja": 0, "dept": 0}
_ser = api.serialization
_charger = _ser.load_der_public_key
_deja = api.persistance.jeton_a_deja_signe
_dept = api.persistance.lire_departement_jeton


def _compte_cle(*a, **k):
    compteurs["cle"] += 1
    return _charger(*a, **k)


def _compte_deja(*a, **k):
    compteurs["deja"] += 1
    return _deja(*a, **k)


def _compte_dept(*a, **k):
    compteurs["dept"] += 1
    return _dept(*a, **k)


_ser.load_der_public_key = _compte_cle
api.persistance.jeton_a_deja_signe = _compte_deja
api.persistance.lire_departement_jeton = _compte_dept
try:
    cas = {
        "jeton utilise, sonde m >= n": lambda: sonde(UTILISE),
        "jeton libre, sonde m >= n": lambda: sonde(LIBRE2),
        "jeton inconnu, sonde m >= n": lambda: sonde(INCONNU),
        "jeton utilise, second message valide": lambda: signer(UTILISE),
        "jeton inconnu, message valide": lambda: signer(INCONNU),
    }
    for nom, appel in cas.items():
        for k in compteurs:
            compteurs[k] = 0
        rep = appel()
        verifier(rep.status_code == 403 and compteurs == {"cle": 1, "deja": 1, "dept": 1},
                 f"6. {nom} : 403 apres exactement une lecture de chaque sorte",
                 f"statut {rep.status_code}, travail {compteurs}")
finally:
    _ser.load_der_public_key = _charger
    api.persistance.jeton_a_deja_signe = _deja
    api.persistance.lire_departement_jeton = _dept

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : aucune reponse de /api/signer_aveugle ne distingue un jeton utilise d'un jeton libre.")
sys.exit(0)
