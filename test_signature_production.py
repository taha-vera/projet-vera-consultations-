#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_signature_production.py -- Teste la PRIMITIVE DE PRODUCTION (RSABSSA
RFC 9474, vera_signature_manager), pas le prototype archive/vera_token.py.

Comble le trou de preuve : la LOGIQUE de la Porte 7 etait testee sur un
prototype forgeable ; ici on exerce la VRAIE primitive cryptographique.

Isolation : on neutralise l'import de vera_persistance AVANT d'importer le
gestionnaire, ce qui le fait fonctionner en memoire pure (cles RSA generees a
la volee, tokens consommes en RAM). AUCUN acces a la base de production,
AUCUN besoin de VERA_DB_KEY. Le test ne touche rien de reel.

Invariants verifies par 'if ... raise' (survit a python -O).
"""

import sys

# --- Isolation : bloquer vera_persistance pour forcer le mode memoire pure ---
import builtins
_vrai_import = builtins.__import__
def _import_sans_persistance(nom, *a, **k):
    if nom == "vera_persistance":
        raise ImportError("neutralise pour le test (mode memoire pure)")
    return _vrai_import(nom, *a, **k)
builtins.__import__ = _import_sans_persistance

import vera_signature_manager as vsm

builtins.__import__ = _vrai_import  # on restaure

if vsm._PERSISTANCE_DISPONIBLE:
    print("ATTENTION : la persistance n'a pas ete neutralisee, test annule pour ne pas toucher la prod.")
    sys.exit(1)


class Echec(Exception):
    pass

def _ok(nom):
    print(f"OK   {nom}")


def main():
    print("Test PRIMITIVE DE PRODUCTION Porte 7 (RSABSSA, memoire pure)")
    print("-" * 60)
    g = vsm.GestionnaireSignature()
    g.ouvrir_consultation()
    ok = True

    # 1. Flux nominal
    try:
        token = g.generer_token_signe("dept_A")
        dep = g.verifier_et_consommer(token)
        if dep != "dept_A":
            raise Echec(f"departement attendu dept_A, obtenu {dep}")
        _ok("1. flux nominal (generer -> verifier -> consommer)")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. Anti-rejeu
    try:
        token = g.generer_token_signe("dept_B")
        g.verifier_et_consommer(token)
        try:
            g.verifier_et_consommer(token)
            raise Echec("la 2e consommation aurait du etre refusee")
        except vsm.TokenDejaUtiliseError:
            _ok("2. anti-rejeu (double consommation refusee)")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. Token force / aleatoire
    try:
        faux = {"message": "00"*32, "signature": "11"*256, "randomizer": "22"*32}
        try:
            g.verifier_et_consommer(faux)
            raise Echec("token force aurait du etre refuse")
        except vsm.SignatureInvalideError:
            _ok("3. token force/aleatoire rejete")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    # 4. Token malforme (pas de crash)
    try:
        for cas in ({}, {"message": "zz"}, {"message": "00", "signature": "00"}):
            try:
                g.verifier_et_consommer(cas)
                raise Echec(f"token malforme {cas} aurait du etre refuse")
            except vsm.SignatureInvalideError:
                pass
        _ok("4. token malforme rejete proprement (pas de crash)")
    except Echec as e:
        print(f"FAIL 4. {e}"); ok = False

    # 5. Round-trip encodage URL
    try:
        token = g.generer_token_signe("dept_C")
        encode = vsm.encoder_token_pour_url(token)
        redecode = vsm.decoder_token_depuis_url(encode)
        dep = g.verifier_et_consommer(redecode)
        if dep != "dept_C":
            raise Echec("round-trip URL casse")
        _ok("5. round-trip encodage/decodage URL")
    except Echec as e:
        print(f"FAIL 5. {e}"); ok = False

    # 6. Token d'un autre gestionnaire (autre cle) rejete
    try:
        g2 = vsm.GestionnaireSignature()
        g2.ouvrir_consultation()
        token_etranger = g2.generer_token_signe("dept_X")
        try:
            g.verifier_et_consommer(token_etranger)
            raise Echec("un token signe par une AUTRE cle aurait du etre refuse")
        except vsm.SignatureInvalideError:
            _ok("6. token d'une autre cle rejete (isolation des consultations)")
        g2.fermer_consultation()
    except Echec as e:
        print(f"FAIL 6. {e}"); ok = False

    g.fermer_consultation()
    print("-" * 60)
    if ok:
        print("PORTE 7 : primitive de PRODUCTION (RSABSSA) validee sur le vrai code.")
        sys.exit(0)
    else:
        print("ECHEC -- la primitive de production ne se comporte pas comme attendu.")
        sys.exit(1)


if __name__ == "__main__":
    main()
