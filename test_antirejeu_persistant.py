#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_antirejeu_persistant.py -- Porte 14 : l'anti-rejeu doit survivre a un
redemarrage. Scenario : consommer un token, simuler un redemarrage (recreer
le gestionnaire depuis la base), verifier que le rejeu est refuse.

Isolation totale : base temporaire jetable + cle de test. Ne touche jamais
la prod. C'est le test le plus sensible en securite (Porte 14).
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ["VERA_DB_KEY"] = "cle_de_test_antirejeu_jetable"

import vera_persistance as p

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
p.DB_PATH = Path(_tmp.name)
p.initialiser()

import vera_signature_manager as vsm


class Echec(Exception):
    pass

def _ok(nom):
    print(f"OK   {nom}")

def _nettoyer():
    for suff in ("", "-wal", "-shm"):
        try:
            Path(str(_tmp.name) + suff).unlink()
        except FileNotFoundError:
            pass


def main():
    print("Test anti-rejeu PERSISTANT (Porte 14, base jetable)")
    print("-" * 55)
    ok = True

    # 1. Consommer un token avec un premier gestionnaire.
    try:
        g1 = vsm.GestionnaireSignature()
        g1.ouvrir_consultation()
        token = g1.generer_token_signe("dept_A")
        dep = g1.verifier_et_consommer(token)
        if dep != "dept_A":
            raise Echec("consommation initiale echouee")
        _ok("1. token consomme par le 1er gestionnaire")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. Verifier que le token consomme est bien PERSISTE en base.
    try:
        consommes = p.charger_tokens_consommes()
        if len(consommes) < 1:
            raise Echec("aucun token consomme trouve en base -- persistance cassee")
        _ok("2. token consomme present en base (persiste)")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. SIMULER UN REDEMARRAGE : nouveau gestionnaire, recharge depuis la base.
    #    Note : on garde la meme cle RSA (persistee), donc le token reste
    #    cryptographiquement valide -- seul l'anti-rejeu doit le bloquer.
    try:
        # Fermer le 1er sans detruire la cle en base (on veut la reutiliser).
        # On recree simplement un gestionnaire : __init__ recharge _tokens_consommes.
        g2 = vsm.GestionnaireSignature()
        g2.ouvrir_consultation()  # recharge la cle RSA persistee + tokens consommes
        try:
            g2.verifier_et_consommer(token)  # rejeu du MEME token
            raise Echec("REJEU ACCEPTE apres redemarrage -- faille Porte 14 !")
        except vsm.TokenDejaUtiliseError:
            _ok("3. rejeu du token APRES redemarrage refuse (Porte 14 tient)")
        g2.fermer_consultation()
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    _nettoyer()
    print("-" * 55)
    if ok:
        print("PORTE 14 : anti-rejeu survit au redemarrage -- verifie.")
        sys.exit(0)
    else:
        print("ECHEC -- l'anti-rejeu ne survit pas au redemarrage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
