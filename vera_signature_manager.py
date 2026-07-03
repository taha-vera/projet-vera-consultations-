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
        self._cle_privee_der = None
        self._cle_publique_der = None
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
            cle_rechargee = False
            if _PERSISTANCE_DISPONIBLE:
                etat_persiste = _persistance.charger_cle_rsa()
                if etat_persiste is not None:
                    cle_privee, cle_publique, ouverture_unix = etat_persiste
                    age = time.time() - ouverture_unix
                    if age < DUREE_VIE_CLE_SECONDES:
                        self._cle_privee_der = cle_privee
                        self._cle_publique_der = cle_publique
                        self._ouverture_ts = ouverture_unix
                        cle_rechargee = True
                    else:
                        _persistance.effacer_cle_rsa()
            if not cle_rechargee:
                self._cle_privee_der, self._cle_publique_der = vbs.generer_cles()
                self._cle_privee_der = bytes(self._cle_privee_der)
                self._cle_publique_der = bytes(self._cle_publique_der)
                self._ouverture_ts = time.time()
                if _PERSISTANCE_DISPONIBLE:
                    _persistance.persister_cle_rsa(self._cle_privee_der, self._cle_publique_der, self._ouverture_ts)
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
            if self._cle_privee_der is not None:
                self._cle_privee_der = b"\x00" * len(self._cle_privee_der)
                self._cle_privee_der = None
            self._consultation_ouverte = False

    def consultation_active(self):
        return self._consultation_ouverte

    def temps_restant_secondes(self):
        if self._ouverture_ts is None:
            return None
        ecoule = time.time() - self._ouverture_ts
        return max(0.0, DUREE_VIE_CLE_SECONDES - ecoule)

    def cle_publique(self):
        if self._cle_publique_der is None:
            raise RuntimeError("Aucune consultation active.")
        return self._cle_publique_der

    def generer_token_signe(self, departement):
        with self._verrou:
            if not self._consultation_ouverte or self._cle_privee_der is None:
                raise RuntimeError("Impossible de generer un token: aucune consultation active.")
            identifiant_unique = secrets.token_urlsafe(16)
            message_dict = {"departement": departement, "alea": identifiant_unique}
            message = json.dumps(message_dict, sort_keys=True).encode("utf-8")
            blind_msg, secret_aveuglement, randomizer = vbs.aveugler_message(self._cle_publique_der, message)
            blind_msg = bytes(blind_msg)
            secret_aveuglement = bytes(secret_aveuglement)
            randomizer = bytes(randomizer)
            sig_aveugle = bytes(vbs.signer_aveugle(self._cle_privee_der, blind_msg))
            signature = bytes(vbs.finaliser_signature(self._cle_publique_der, message, blind_msg, secret_aveuglement, sig_aveugle, randomizer))
        return {"message": message.hex(), "signature": signature.hex(), "randomizer": randomizer.hex()}

    def verifier_et_consommer(self, token_complet):
        try:
            message = bytes.fromhex(token_complet["message"])
            signature = bytes.fromhex(token_complet["signature"])
            randomizer = bytes.fromhex(token_complet["randomizer"])
        except (KeyError, ValueError) as e:
            raise SignatureInvalideError("Token malforme: " + str(e))
        empreinte = hashlib.sha256(message + signature).hexdigest()
        with self._verrou:
            if self._tokens_consommes.get(empreinte):
                raise TokenDejaUtiliseError("Ce token a deja ete utilise")
            if self._cle_publique_der is None:
                raise SignatureInvalideError("Cle publique non disponible.")
            valide = vbs.verifier_signature(self._cle_publique_der, message, signature, randomizer)
            if not valide:
                raise SignatureInvalideError("Signature invalide")
            self._tokens_consommes[empreinte] = True
            if _PERSISTANCE_DISPONIBLE:
                _persistance.persister_token_consomme(empreinte)
        try:
            message_dict = json.loads(message.decode("utf-8"))
            return message_dict["departement"]
        except (json.JSONDecodeError, KeyError) as e:
            raise SignatureInvalideError("Contenu du message invalide: " + str(e))
