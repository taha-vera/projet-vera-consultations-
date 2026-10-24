#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La marge de depot de 24 h survit a un redemarrage du service (audit A6).

CONSTAT (audit externe du 20/10/2026, A6, simule avec GestionnaireSignature).
A l'expiration des sept jours, la cle privee est detruite et effacee de la
base ; les cles PUBLIQUES, gardees en memoire pour la marge de depot (F9), ne
survivaient pas a un redemarrage. Un deploiement en fin de consultation, ou un
`Restart=on-failure`, pendant les 24 h suivantes : le vote d'un membre qui avait
obtenu sa signature avant l'echeance recevait 404, vote.html proposait
« Reessayer l'envoi » sans fin, et la voix etait perdue (jeton consomme).
La documentation promettait 24 h sans condition.

CE QUE CE TEST VERIFIE (GestionnaireSignature reel, horloge simulee, base jetable)
  1. expiration PENDANT que le service tourne, puis redemarrage dans la marge :
     la cle publique est encore servie, la cle privee ne l'est PAS (aucune
     signature n'est emise), la consultation n'est pas « active » ;
  2. expiration PENDANT que le service est arrete : meme resultat au demarrage ;
  3. apres la fin de la marge, un redemarrage ne ressuscite rien et la table est
     videe ;
  4. la cloture explicite vide la table : plus rien ne subsiste ;
  5. la table ne contient JAMAIS de cle privee ;
  6. controle negatif : sans la persistance des cles publiques, le scenario 1
     echoue (c'est ce que mesurait l'audit).
"""

import os
import pathlib
import sys
import tempfile
import types

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

if not os.environ.get("VERA_DB_PATH"):
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_marge_redem_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

try:
    import vera_blind_sig as vbs  # noqa: F401
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)

import vera_persistance as persistance  # noqa: E402
persistance.initialiser()
import vera_signature_manager as sm  # noqa: E402

if not callable(getattr(sm.vbs, "generer_cles", None)):
    print("IGNORE : module Rust non compile.")
    raise SystemExit(2)

H = 3600
D = "GroupeRedemarrage"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


# Horloge simulee, appliquee au seul module de signature.
_reel = sm.time
decalage = {"s": 0.0}
sm.time = types.SimpleNamespace(time=lambda: _reel.time() + decalage["s"],
                                sleep=_reel.sleep)


def nouvelle_instance():
    """Un « redemarrage » : un gestionnaire neuf, sur la meme base."""
    g = sm.GestionnaireSignature()
    g.ouvrir_consultation()
    return g


def arreter(g):
    if g._timer_destruction:
        g._timer_destruction.cancel()


def repartir_de_zero():
    decalage["s"] = 0.0
    g = sm.GestionnaireSignature()
    g.ouvrir_consultation()
    g.fermer_consultation()
    persistance.effacer_etat_consultation()


def tables_cles():
    privees = persistance._conn.execute("SELECT COUNT(*) FROM cle_rsa_active").fetchone()[0]
    publiques = persistance._conn.execute("SELECT COUNT(*) FROM cles_publiques_expirees").fetchone()[0]
    return privees, publiques


DUREE = sm.DUREE_VIE_CLE_SECONDES
GRACE = sm.DELAI_GRACE_DEPOT_SECONDES

# --- 1. expiration pendant que le service tourne, puis redemarrage ---------
repartir_de_zero()
g1 = nouvelle_instance()
pub = g1.cle_publique(D)
decalage["s"] = DUREE + 1 * H
g1._expirer_cle()                       # ce que fait le timer
arreter(g1)
decalage["s"] = DUREE + 5 * H           # redemarrage 4 h plus tard, dans la marge
g2 = nouvelle_instance()
try:
    servie = g2.cle_publique_si_existe(D)
except Exception as e:   # noqa: BLE001
    servie = f"EXCEPTION {type(e).__name__}: {e}"
verifier(servie == pub,
         "1a. redemarrage dans la marge : la cle publique est encore servie",
         str(servie)[:100])
verifier(not g2.consultation_active(),
         "1b. ... la consultation n'est pas « active » (plus de signature)")
try:
    g2.signer_message_aveugle(D, b"\x00" * 256)
    signe = True
except Exception:   # noqa: BLE001
    signe = False
verifier(not signe, "1c. ... et aucune signature ne peut etre emise (cle privee detruite)")
priv_n, pub_n = tables_cles()
verifier(priv_n == 0 and pub_n == 1,
         "5. la base ne garde AUCUNE cle privee ; une cle publique par groupe",
         f"privees={priv_n} publiques={pub_n}")
arreter(g2)

# --- 3. apres la fin de la marge, rien ne ressuscite -----------------------
decalage["s"] = DUREE + GRACE + 1 * H
g3 = nouvelle_instance()
try:
    g3.cle_publique_si_existe(D)
    refuse = False
except Exception:   # noqa: BLE001
    refuse = True
verifier(refuse, "3a. apres la marge, un redemarrage ne sert plus la cle publique")
verifier(tables_cles() == (0, 0), "3b. ... et la table des cles publiques est videe",
         str(tables_cles()))
arreter(g3)

# --- 2. expiration pendant que le service est ARRETE -----------------------
repartir_de_zero()
g1 = nouvelle_instance()
pub = g1.cle_publique(D)
arreter(g1)                              # le service s'arrete, rien n'a expire
decalage["s"] = DUREE + 2 * H            # il repart apres l'echeance, dans la marge
g2 = nouvelle_instance()
try:
    servie = g2.cle_publique_si_existe(D)
except Exception as e:   # noqa: BLE001
    servie = f"EXCEPTION {type(e).__name__}: {e}"
verifier(servie == pub,
         "2a. expiration pendant l'arret : la cle publique est servie au demarrage",
         str(servie)[:100])
verifier(tables_cles() == (0, 1),
         "2b. ... la cle privee a ete detruite en base au demarrage",
         str(tables_cles()))
arreter(g2)

# --- 7. des redemarrages repetes ne PROLONGENT PAS la marge (audit 2, N4) ----
# Mutant releve par l'audit du 24/10/2026 : fin_marge = maintenant + 24 h au lieu
# de debut + 7 j + 24 h. Chaque redemarrage repoussait alors la fin de la marge :
# un service redemarre toutes les 20 h gardait indefiniment les cles publiques.
repartir_de_zero()
g1 = nouvelle_instance()
pub = g1.cle_publique(D)
decalage["s"] = DUREE + 1 * H
g1._expirer_cle()
arreter(g1)
servies = []
for delta in (DUREE + 10 * H, DUREE + 20 * H, DUREE + 23 * H):
    decalage["s"] = delta                       # trois redemarrages dans la marge
    gx = nouvelle_instance()
    try:
        servies.append(gx.cle_publique_si_existe(D) == pub)
    except Exception:   # noqa: BLE001
        servies.append(False)
    arreter(gx)
verifier(all(servies), "7a. trois redemarrages dans la marge : la cle publique est servie a chacun",
         str(servies))
decalage["s"] = DUREE + GRACE + 1 * H          # 1 h apres la fin REELLE de la marge
gz = nouvelle_instance()
# AVANT toute lecture : le controle a la lecture (cle_publique_si_existe) repose
# sur _ouverture_ts et masquerait un mauvais calcul de fin de marge au demarrage.
verifier(gz._cles_publiques_expirees == {} and tables_cles() == (0, 0),
         "7b0. des le demarrage (sans aucune lecture), la marge terminee n'est pas restauree",
         f"{len(gz._cles_publiques_expirees)} cle(s) en memoire, tables {tables_cles()}")
try:
    gz.cle_publique_si_existe(D)
    refuse = False
except Exception:   # noqa: BLE001
    refuse = True
verifier(refuse, "7b. apres la fin reelle de la marge, les redemarrages precedents ne l'ont pas prolongee")
verifier(tables_cles() == (0, 0), "7c. ... et la table des cles publiques est videe", str(tables_cles()))
arreter(gz)

# --- 4. la cloture explicite vide tout -------------------------------------
g2.fermer_consultation()
verifier(tables_cles() == (0, 0), "4. la cloture explicite vide les deux tables",
         str(tables_cles()))

# --- 4bis. effacer_etat_consultation vide AUSSI la table, a elle seule -----
# (filet de securite : la cloture ne doit pas dependre de l'ordre des appels).
persistance.persister_cles_publiques_expirees({D: (b"\x01" * 8, 1.0)})
verifier(tables_cles()[1] == 1, "4bis-a. (preparation) une cle publique est en base")
persistance.effacer_etat_consultation()
verifier(tables_cles()[1] == 0,
         "4bis-b. effacer_etat_consultation vide la table des cles publiques",
         str(tables_cles()))

# --- 6. controle negatif : sans persistance, le scenario 1 echoue ----------
repartir_de_zero()
g1 = nouvelle_instance()
pub = g1.cle_publique(D)
decalage["s"] = DUREE + 1 * H
_ancienne = persistance.persister_cles_publiques_expirees
persistance.persister_cles_publiques_expirees = lambda cles: None   # comportement d'avant
try:
    g1._expirer_cle()
finally:
    persistance.persister_cles_publiques_expirees = _ancienne
arreter(g1)
decalage["s"] = DUREE + 5 * H
g2 = nouvelle_instance()
try:
    g2.cle_publique_si_existe(D)
    perdue = False
except Exception:   # noqa: BLE001
    perdue = True
verifier(perdue,
         "6. controle negatif : sans la persistance, la cle est perdue au redemarrage "
         "(le test detecte bien le defaut de l'audit)")
arreter(g2)
g2.fermer_consultation()

sm.time = _reel
print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la marge de depot de 24 h survit a un redemarrage du service.")
sys.exit(0)
