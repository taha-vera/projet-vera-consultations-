#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vera_admin_auth.py — Authentification pour l'interface RH (generation de
tokens de vote). Separe de l'authentification des participants (qui n'en
ont pas besoin, juste leur token de vote individuel).

Principe : un compte RH par organisation, mot de passe hashe (jamais en
clair, ni en memoire au-dela du necessaire ni en log), session par jeton
opaque distinct des tokens de vote (pour ne jamais melanger les deux
espaces de noms).
"""

import hashlib
import hmac
import os
import secrets
import threading
import time

# --------------------------------------------------------------------------
# Stockage des comptes RH (en memoire pour ce prototype -- a migrer vers
# une vraie base si le besoin de persistance au-dela d'un redemarrage
# devient reel)
# --------------------------------------------------------------------------

_verrou = threading.Lock()

# identifiant_compte -> {"hash_mdp": bytes, "sel": bytes}
_comptes_rh: dict[str, dict] = {}

# jeton_session -> {"compte": str, "expire_a": float}
_sessions: dict[str, dict] = {}

DUREE_SESSION_SECONDES = 8 * 3600  # 8h, une journee de travail


def _hacher_mot_de_passe(mot_de_passe: str, sel: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256, 200k iterations -- standard raisonnable pour un
    prototype, a durcir (argon2) si le projet passe en production reelle."""
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), sel, 200_000)


def creer_compte(identifiant: str, mot_de_passe: str) -> bool:
    """Cree un compte RH. Retourne False si l'identifiant existe deja."""
    with _verrou:
        if identifiant in _comptes_rh:
            return False
        sel = secrets.token_bytes(16)
        hash_mdp = _hacher_mot_de_passe(mot_de_passe, sel)
        _comptes_rh[identifiant] = {"hash_mdp": hash_mdp, "sel": sel}
        return True


def verifier_identifiants(identifiant: str, mot_de_passe: str) -> bool:
    """Verifie un mot de passe en temps constant (hmac.compare_digest)
    pour eviter les attaques par mesure de timing."""
    with _verrou:
        compte = _comptes_rh.get(identifiant)
        if compte is None:
            # Calcul factice pour ne pas reveler par le timing que le
            # compte n'existe pas
            _hacher_mot_de_passe(mot_de_passe, secrets.token_bytes(16))
            return False
        hash_calcule = _hacher_mot_de_passe(mot_de_passe, compte["sel"])
        return hmac.compare_digest(hash_calcule, compte["hash_mdp"])


def ouvrir_session(identifiant: str) -> str:
    """Genere un jeton de session opaque, distinct des tokens de vote."""
    jeton = "sess_" + secrets.token_urlsafe(32)
    with _verrou:
        _sessions[jeton] = {
            "compte": identifiant,
            "expire_a": time.time() + DUREE_SESSION_SECONDES,
        }
    return jeton


def session_valide(jeton_session: str) -> str | None:
    """Retourne l'identifiant du compte si la session est valide et non
    expiree, sinon None. Purge les sessions expirees au passage."""
    with _verrou:
        maintenant = time.time()
        expirees = [j for j, s in _sessions.items() if s["expire_a"] < maintenant]
        for j in expirees:
            del _sessions[j]

        session = _sessions.get(jeton_session)
        if session is None:
            return None
        return session["compte"]


def fermer_session(jeton_session: str) -> None:
    with _verrou:
        _sessions.pop(jeton_session, None)
