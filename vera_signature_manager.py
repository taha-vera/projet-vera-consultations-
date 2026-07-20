#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vera_signature_manager.py - Signature aveugle RSABSSA + persistance cle RSA (Porte 14)."""

import base64
import hashlib
import json
import secrets
import threading
import time

import vera_blind_sig as vbs

DUREE_VIE_CLE_SECONDES = 48 * 3600

try:
    import vera_persistance as _persistance
    _PERSISTANCE_DISPONIBLE = True
except ImportError:
    _persistance = None
    _PERSISTANCE_DISPONIBLE = False


def encoder_token_pour_url(token_complet):
    json_str = json.dumps(token_complet, sort_keys=True)
    return base64.urlsafe_b64encode(json_str.encode("utf-8")).decode("ascii")


def decoder_token_depuis_url(token_encode):
    try:
        json_str = base64.urlsafe_b64decode(token_encode.encode("ascii")).decode("utf-8")
        token_complet = json.loads(json_str)
    except Exception as e:
        raise ValueError("Token encode invalide: " + str(e))
    for champ in ("message", "signature", "randomizer"):
        if champ not in token_complet:
            raise ValueError("Champ manquant dans le token: " + champ)
    return token_complet


class TokenDejaUtiliseError(Exception):
    pass


class SignatureInvalideError(Exception):
    pass


class GestionnaireSignature:
    def __init__(self):
        self._verrou = threading.Lock()
        self._cles = {}
        self._consultation_ouverte = False
        self._ouverture_ts = None
        self._timer_destruction = None
        if _PERSISTANCE_DISPONIBLE:
            self._tokens_consommes = {e: True for e in _persistance.charger_tokens_consommes()}
        else:
            self._tokens_consommes = {}

    def ouvrir_consultation(self):
        with self._verrou:
            if self._consultation_ouverte:
                raise RuntimeError("Une consultation est deja active.")
            self._cles = {}
            ts_recharge = None
            if _PERSISTANCE_DISPONIBLE:
                toutes = _persistance.charger_toutes_cles_chiffrees()
                for dep, (priv, pub, ouv) in toutes.items():
                    if time.time() - ouv < DUREE_VIE_CLE_SECONDES:
                        self._cles[dep] = (priv, pub)
                        if ts_recharge is None or ouv < ts_recharge:
                            ts_recharge = ouv
                    else:
                        _persistance.effacer_cle_rsa()
                        self._cles = {}
                        ts_recharge = None
                        break
            self._ouverture_ts = ts_recharge if ts_recharge is not None else time.time()
            self._consultation_ouverte = True
        temps_ecoule = time.time() - self._ouverture_ts
        temps_restant = max(0.0, DUREE_VIE_CLE_SECONDES - temps_ecoule)
        self._timer_destruction = threading.Timer(temps_restant, self._detruire_cle_privee)
        self._timer_destruction.daemon = True
        self._timer_destruction.start()


    def fermer_consultation(self):
        if self._timer_destruction:
            self._timer_destruction.cancel()
            self._timer_destruction = None
        self._detruire_cle_privee()
        if _PERSISTANCE_DISPONIBLE:
            _persistance.effacer_cle_rsa()

    def _detruire_cle_privee(self):
        with self._verrou:
            for dep, (priv, pub) in list(self._cles.items()):
                if priv is not None:
                    self._cles[dep] = (b"\x00" * len(priv), pub)
            self._cles = {}
            self._consultation_ouverte = False

    def consultation_active(self):
        return self._consultation_ouverte

    def temps_restant_secondes(self):
        if self._ouverture_ts is None:
            return None
        ecoule = time.time() - self._ouverture_ts
        return max(0.0, DUREE_VIE_CLE_SECONDES - ecoule)

    def _obtenir_ou_creer_cle(self, departement):
        """Renvoie (priv, pub) du departement, generee a la volee si absente.
        DOIT etre appelee sous self._verrou."""
        if departement in self._cles:
            return self._cles[departement]
        priv, pub = vbs.generer_cles()
        priv = bytes(priv)
        pub = bytes(pub)
        self._cles[departement] = (priv, pub)
        if _PERSISTANCE_DISPONIBLE:
            _persistance.persister_cle_rsa_chiffree(departement, priv, pub, self._ouverture_ts)
        return priv, pub

    def cle_publique(self, departement):
        with self._verrou:
            if not self._consultation_ouverte:
                raise RuntimeError("Aucune consultation active.")
            _priv, pub = self._obtenir_ou_creer_cle(departement)
        return pub

    def signer_message_aveugle(self, departement, message_aveugle_bytes):
        """Signe a l'aveugle un message DEJA aveugle par le client (navigateur
        du votant). C'est la SEULE etape du protocole RSABSSA qui reste cote
        serveur dans le nouveau flux : le serveur ne voit jamais le message en
        clair (il est aveugle), ne fait PAS l'aveuglement (le client l'a fait)
        ni la finalisation (le client la fera). Il ne peut donc pas relier ce
        qu'il signe au token final -> unlinkability effective.
        Renvoie la signature aveugle (bytes)."""
        with self._verrou:
            if not self._consultation_ouverte:
                raise RuntimeError("Impossible de signer: aucune consultation active.")
            priv, _pub = self._obtenir_ou_creer_cle(departement)
            sig_aveugle = bytes(vbs.signer_aveugle(list(priv), list(message_aveugle_bytes)))
        return sig_aveugle

    def generer_token_signe(self, departement):
        raise RuntimeError(
            "generer_token_signe est obsolete (ancien Modele A). Flux Modele B : "
            "aveuglement cote client, voir signer_message_aveugle(departement, msg)."
        )

    def verifier_et_consommer(self, token_complet):
        raise RuntimeError(
            "verifier_et_consommer est obsolete (ancien Modele A). Flux Modele B : "
            "verification dans /api/repondre sous la cle publique du departement."
        )
