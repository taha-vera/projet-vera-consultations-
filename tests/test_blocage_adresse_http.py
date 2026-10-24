#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le blocage par ADRESSE n'enferme pas l'organisateur (audit A3), sans rouvrir l'amplification CPU.

LE DEFAUT (audit externe du 20/10/2026)
Le blocage par adresse etait verifie AVANT les identifiants. Derriere une
adresse partagee, un voisin qui envoyait cinq mauvais mots de passe bloquait
l'organisateur MEME AVEC LE BON mot de passe, de 5 minutes a une heure, entretenu
par cinq requetes par heure : pas de cloture, donc pas d'effacement promis.

LA CONTRAINTE QU'IL NE FAUT PAS RELACHER
Verifier les identifiants a chaque requete, y compris sur une adresse bloquee,
ferait payer 200 000 iterations de PBKDF2 a chaque fois, sur un service
mono-processus qui sert aussi les votants : une dizaine d'adresses a 1 requete
par seconde (limite nginx) occuperaient un coeur. Le correctif en autorise donc
UNE par periode sur une adresse bloquee ; les autres recoivent 429 sans calcul.

CE QU'IL VERIFIE, EN HTTP
  1. cinq echecs bloquent l'adresse ;
  2. la premiere requete suivante, avec le BON mot de passe, est acceptee ;
  3. apres une verification, les requetes de la meme periode sont refusees en
     429 SANS appeler le calcul de verification (compte des appels) ;
  4. une fois la periode ecoulee, le bon mot de passe passe de nouveau ;
  5. une verification qui echoue pendant le blocage ne le compte pas comme un
     echec de plus (un voisin qui se trompe ne rallonge pas le blocage) ;
  6. un mauvais mot de passe reste refuse : 429 pendant le blocage, 401 sinon.
"""

import os
import pathlib
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    import tempfile
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_blocage_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("IGNORE : fastapi.testclient indisponible.")
    raise SystemExit(2)

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_blocage_adresse"
os.environ["VERA_ADMIN_USER"] = "rh_blocage"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402

PERIODE = 1.0
api.INTERVALLE_VERIFICATION_IP_BLOQUEE = PERIODE   # le test ne doit pas attendre 30 s

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


appels = {"n": 0}
_reel = api.auth.verifier_identifiants


def _compte(*a, **k):
    appels["n"] += 1
    return _reel(*a, **k)


api.auth.verifier_identifiants = _compte


def tenter(client, mdp):
    return client.post("/api/rh/connexion",
                       json={"identifiant": "rh_blocage", "mot_de_passe": mdp})


voisin = TestClient(api.app, base_url="https://testserver")

# --- 1. cinq echecs d'un voisin bloquent l'adresse ------------------------
codes = [tenter(voisin, "faux").status_code for _ in range(api.SEUIL_ECHECS_AVANT_BLOCAGE)]
verifier(codes == [401] * api.SEUIL_ECHECS_AVANT_BLOCAGE,
         "1a. cinq mauvais mots de passe : 401 chacun", str(codes))
ip = next(iter(api._tentatives_par_ip))
verifier(api._tentatives_par_ip[ip].get("bloque_jusqu_a", 0) > time.time(),
         "1b. l'adresse est bloquee apres le seuil")
blocages_avant = api._tentatives_par_ip[ip]["blocages"]

# --- 2. le bon mot de passe passe MEME sur l'adresse bloquee ---------------
# (derriere une adresse partagee, c'est l'organisateur). On le teste en second,
# apres avoir consomme la verification de la periode avec un mauvais, pour
# verifier le point 5 d'abord.
r_faux = tenter(voisin, "faux")
verifier(r_faux.status_code == 429,
         "5a. un mauvais mot de passe verifie pendant le blocage : 429",
         f"recu {r_faux.status_code}")
verifier(api._tentatives_par_ip[ip]["blocages"] == blocages_avant,
         "5b. ... et n'allonge ni ne recompte le blocage",
         f"blocages {blocages_avant} -> {api._tentatives_par_ip[ip]['blocages']}")

# --- 3. dans la meme periode : 429 SANS calcul -----------------------------
avant = appels["n"]
rapides = [tenter(voisin, MDP).status_code for _ in range(20)]
verifier(set(rapides) == {429},
         "3a. vingt requetes dans la meme periode : toutes 429",
         str(set(rapides)))
verifier(appels["n"] == avant,
         "3b. ... sans AUCUN calcul de verification (pas d'amplification CPU)",
         f"{appels['n'] - avant} verification(s) payee(s) pour 20 requetes")

# --- 4. la periode ecoulee, le BON mot de passe passe ----------------------
time.sleep(PERIODE + 0.2)
r_ok = tenter(voisin, MDP)
verifier(r_ok.status_code == 200,
         "2/4. periode ecoulee : le bon mot de passe est accepte malgre le blocage",
         f"recu {r_ok.status_code} : {r_ok.text[:150]}")
verifier(ip not in api._tentatives_par_ip,
         "4b. une connexion reussie remet l'adresse a zero")

# --- 6. apres reussite, un mauvais mot de passe est de nouveau un 401 -------
verifier(tenter(voisin, "faux").status_code == 401,
         "6. adresse remise a zero : un mauvais mot de passe redonne 401, pas 429")

# --- Sur une adresse bloquee, le premier essai de la periode est verifie ----
for _ in range(api.SEUIL_ECHECS_AVANT_BLOCAGE - 1):
    tenter(voisin, "faux")
r1 = tenter(voisin, MDP)   # adresse bloquee depuis l'echec precedent ? (seuil atteint)
# Le seuil vaut 5 : un echec deja compte (point 6) + quatre ici = bloquee. La
# requete suivante est la premiere d'une periode neuve : elle est verifiee.
verifier(r1.status_code == 200,
         "2. adresse tout juste bloquee : le bon mot de passe passe tout de suite",
         f"recu {r1.status_code}")

# --- 7. N3 (audit du 24/10/2026) : un voisin actif ne prend pas la periode ---
# Le voisin envoie, une fois par periode et sans cesse, un mauvais mot de passe
# pour un AUTRE identifiant. Avant : une seule periode par adresse, prise par lui
# des qu'elle s'ouvrait -> l'organisateur n'etait jamais verifie.
api._tentatives_par_ip.clear()
api._tentatives_par_compte.clear()
for _ in range(api.SEUIL_ECHECS_AVANT_BLOCAGE):
    voisin.post("/api/rh/connexion", json={"identifiant": "voisin_inconnu", "mot_de_passe": "x"})
time.sleep(PERIODE + 0.2)
r_voisin = voisin.post("/api/rh/connexion", json={"identifiant": "voisin_inconnu", "mot_de_passe": "x"})
verifier(r_voisin.status_code == 429, "7a. le voisin prend la periode de l'identifiant inconnu",
         f"recu {r_voisin.status_code}")
r_orga = tenter(voisin, MDP)
verifier(r_orga.status_code == 200,
         "7b. ... et l'organisateur (identifiant existant) a SA periode : bon mot de passe accepte",
         f"recu {r_orga.status_code} : {r_orga.text[:120]}")

# --- 8. identifiants inconnus : une seule verification par periode ----------
api._tentatives_par_ip.clear()
api._tentatives_par_compte.clear()
for _ in range(api.SEUIL_ECHECS_AVANT_BLOCAGE):
    voisin.post("/api/rh/connexion", json={"identifiant": "voisin_inconnu", "mot_de_passe": "x"})
time.sleep(PERIODE + 0.2)
avant = appels["n"]
for i in range(30):
    voisin.post("/api/rh/connexion", json={"identifiant": f"inconnu_{i}", "mot_de_passe": "x"})
verifier(appels["n"] - avant <= 1,
         "8a. trente identifiants inconnus distincts : au plus UNE verification payee",
         f"{appels['n'] - avant} verification(s)")
cles = api._tentatives_par_ip[next(iter(api._tentatives_par_ip))].get("derniere_verif_bloquee", {})
verifier(set(cles) <= {"*", "rh_blocage"},
         "8b. le limiteur ne grossit pas avec les identifiants inventes", str(cles))

# --- 9. N5 : le blocage croissant ne repart pas de 5 minutes apres une heure --
class _Horloge:
    maintenant = 1_000_000.0
    def __getattr__(self, nom):
        return getattr(time, nom)
    def time(self):
        return self.maintenant

h = _Horloge()
reel = api.time
api.time = h
try:
    api._tentatives_par_ip.clear()
    IP9 = "203.0.113.9"
    durees = []
    for _ in range(8):
        for _ in range(api.SEUIL_ECHECS_AVANT_BLOCAGE):
            api._enregistrer_echec(IP9)
        durees.append(round(api._tentatives_par_ip[IP9]["bloque_jusqu_a"] - h.maintenant))
        h.maintenant = api._tentatives_par_ip[IP9]["bloque_jusqu_a"] + 60   # reprise 1 min apres la fin
finally:
    api.time = reel
verifier(durees == [300, 600, 1200, 2400, 3600, 3600, 3600, 3600],
         "9. huit blocages successifs : durees croissantes puis plafonnees, sans retour a 5 minutes",
         str(durees))

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : l'adresse bloquee n'enferme pas l'organisateur, sans calcul inutile.")
sys.exit(0)
