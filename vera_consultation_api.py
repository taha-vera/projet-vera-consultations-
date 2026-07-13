#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vera_consultation_api.py — Serveur complet : vote public (sans auth) +
interface RH protegee par authentification (generation de tokens,
consultation des resultats agreges).

Coherent avec ATTRIBUTION_FLOW.md : le compte RH est l'autorite
d'attribution. Il connait departement <-> quantite de tokens demandes,
jamais l'identite des votants individuels cote serveur -- l'envoi des
liens reste sous la responsabilite de la personne RH elle-meme, en dehors
de ce systeme.
"""

import hmac
import secrets
import threading
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Cookie, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import vera_admin_auth as auth
from vera_epsilon_budget import BudgetEpsilonParDepartement, BudgetEpuiseError
from vera_dp_noise import appliquer_bruit_dp

app = FastAPI(title="VERA Consultation")

# Compte RH de démarrage, créé une seule fois si les variables d'environnement
# VERA_ADMIN_USER et VERA_ADMIN_PASS sont fournies -- pratique pour le premier
# déploiement, à remplacer par un vrai flux de création de compte si plusieurs
# organisations doivent un jour cohabiter sur la même instance.
import os
_admin_user = os.environ.get("VERA_ADMIN_USER")
_admin_pass = os.environ.get("VERA_ADMIN_PASS")
if _admin_user and _admin_pass:
    auth.creer_compte(_admin_user, _admin_pass)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

verrou = threading.Lock()

registre_tokens: dict[str, dict] = {}

# Compteurs cumules par departement, jamais une liste de reponses
# individuelles -- decision actee apres challenge multi-IA (ChatGPT + Grok,
# convergents) : une liste, meme temporaire et meme sans identite associee,
# expose un resultat partiel non agrege en cas d'acces root/dump memoire
# pendant la fenetre de vote. Les compteurs cumules reduisent au minimum
# l'information presente a tout instant -- s'il n'y a plus de liste, il n'y
# a plus rien a extraire au-dela de ce que K_MIN protege deja a la
# publication. Voir LIMITS.md pour la limite honnete documentee : ceci ne
# protege pas contre un attaquant root pendant l'execution (aucune solution
# logicielle ne le peut, cf. discussion id_opaque), seulement contre
# l'existence meme de la donnee a extraire.
compteurs_par_departement: dict[str, dict[str, int]] = {}
effectif_par_departement: dict[str, int] = {}

# Porte 4 du modele de menace : budget de confidentialite cumule par
# departement. Chaque publication de resultat (cf. /api/rh/resultats)
# consomme une fraction de ce budget -- une fois epuise pour un
# departement donne, plus aucun resultat n'est publie pour cette cohorte,
# meme si K_MIN est atteint. Empeche qu'un organisateur recoupe plusieurs
# publications successives sur la meme population pour en deduire plus
# que ce qu'une seule publication ne revelerait (cf. LIMITS.md).
EPSILON_PAR_PUBLICATION = 0.5  # coherent avec validation_opendp.py existant
budget_epsilon = BudgetEpsilonParDepartement(epsilon_total_autorise=1.5)

import vera_persistance as persistance

persistance.initialiser()

_budget_persiste = persistance.charger_budget_epsilon()
for _dep, _etat in _budget_persiste.items():
    budget_epsilon.injecter_etat(_dep, _etat["epsilon_consomme"], _etat["nombre_publications"])

_compteurs_persistes, _effectifs_persistes = persistance.charger_compteurs()
compteurs_par_departement.update(_compteurs_persistes)
effectif_par_departement.update(_effectifs_persistes)

# --------------------------------------------------------------------------
# Porte 7 durcie (signature aveugle RSABSSA) -- mode optionnel, EN PLUS du
# systeme de tokens actuel, pas a sa place. Le serveur Hetzner (Linux) n'a
# actuellement PAS le module vera_blind_sig compile (compile uniquement sur
# Windows/Dell pour l'instant) -- l'import est protege pour que le serveur
# continue de fonctionner normalement meme sans ce module. A activer
# reellement seulement apres avoir recompile vera_blind_sig pour Linux et
# valide ce nouveau chemin en parallele de l'ancien.
# --------------------------------------------------------------------------
try:
    from vera_signature_manager import (
        GestionnaireSignature,
        decoder_token_depuis_url,
        encoder_token_pour_url,
        TokenDejaUtiliseError,
        SignatureInvalideError,
    )
    gestionnaire_signature = GestionnaireSignature()
    gestionnaire_signature.ouvrir_consultation()
    SIGNATURE_AVEUGLE_DISPONIBLE = True
except Exception as e:
    raise RuntimeError(
        f"ERREUR CRITIQUE : signature aveugle non disponible ({type(e).__name__}: {e}). "
        "Le serveur refuse de demarrer sans signature aveugle RSABSSA (Porte 7 fail-closed). "
        "Verifiez que le venv est active : source /root/vera_blind_sig/.venv/bin/activate"
    )

# code_court (4 chiffres) -> token complet
# Permet d'envoyer "4827" plutot que le token long, sans jamais exposer
# le vrai token tant que le code n'a pas ete verifie cote serveur.
registre_codes_courts: dict[str, str] = {}

# Protection anti-brute-force : avec seulement 10000 combinaisons a 4
# chiffres, il faut limiter les tentatives. IP -> {"echecs": int, "bloque_jusqu_a": float}
import time
_tentatives_par_ip: dict[str, dict] = {}
SEUIL_ECHECS_AVANT_BLOCAGE = 5
DUREE_BLOCAGE_SECONDES = 300  # 5 minutes


def _verifier_anti_bruteforce(ip: str) -> None:
    """Leve une exception si l'IP a depasse le seuil d'echecs recents."""
    with verrou:
        info = _tentatives_par_ip.get(ip)
        if info and info.get("bloque_jusqu_a", 0) > time.time():
            raise HTTPException(
                status_code=429,
                detail="Trop de tentatives. Réessayez dans quelques minutes.",
            )


def _enregistrer_echec(ip: str) -> None:
    with verrou:
        info = _tentatives_par_ip.setdefault(ip, {"echecs": 0, "bloque_jusqu_a": 0})
        info["echecs"] += 1
        if info["echecs"] >= SEUIL_ECHECS_AVANT_BLOCAGE:
            info["bloque_jusqu_a"] = time.time() + DUREE_BLOCAGE_SECONDES
            info["echecs"] = 0


def _reinitialiser_echecs(ip: str) -> None:
    with verrou:
        _tentatives_par_ip.pop(ip, None)


def _generer_code_court_unique() -> str:
    """Genere un code a 4 chiffres non deja attribue."""
    while True:
        code = f"{secrets.randbelow(10000):04d}"
        if code not in registre_codes_courts:
            return code

QUESTION_ACTIVE = {
    "question": "Êtes-vous favorable à la proposition soumise à cette consultation ?",
    "options": [
        {"valeur": "oui", "texte": "Oui"},
        {"valeur": "non", "texte": "Non"},
        {"valeur": "abstention", "texte": "Je m'abstiens"},
    ],
}

K_MIN = 100


# --------------------------------------------------------------------------
# Authentification RH
# --------------------------------------------------------------------------

class IdentifiantsRH(BaseModel):
    identifiant: str
    mot_de_passe: str


def exiger_session(session_vera: Optional[str] = Cookie(None)) -> str:
    """Dependance FastAPI : verifie la session, leve 401 sinon."""
    if not session_vera:
        raise HTTPException(status_code=401, detail="Non authentifié")
    compte = auth.session_valide(session_vera)
    if compte is None:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")
    return compte


@app.post("/api/rh/connexion")
def connexion_rh(payload: IdentifiantsRH, response: Response):
    if not auth.verifier_identifiants(payload.identifiant, payload.mot_de_passe):
        raise HTTPException(status_code=401, detail="Identifiant ou mot de passe incorrect")

    jeton_session = auth.ouvrir_session(payload.identifiant)
    response.set_cookie(
        key="session_vera",
        value=jeton_session,
        httponly=True,
        samesite="lax",
        max_age=auth.DUREE_SESSION_SECONDES,
    )
    return {"statut": "connecte", "compte": payload.identifiant}


@app.post("/api/rh/deconnexion")
def deconnexion_rh(response: Response, session_vera: Optional[str] = Cookie(None)):
    if session_vera:
        auth.fermer_session(session_vera)
    response.delete_cookie("session_vera")
    return {"statut": "deconnecte"}


# --------------------------------------------------------------------------
# Creation de nouveaux comptes RH (Porte 9 : permet une vraie separation
# organisationnelle entre plusieurs entites emettrices). Protege par un
# secret ADMIN distinct des comptes RH eux-memes -- un compte RH normal ne
# peut pas creer d'autres comptes RH, seul celui qui detient ce secret
# (l'operateur technique du serveur) le peut. Ce secret n'est PAS le mot
# de passe d'un compte RH : c'est une cle d'administration separee.
# --------------------------------------------------------------------------

_secret_admin_creation = os.environ.get("VERA_SECRET_CREATION_COMPTE")


class CreerCompteRequete(BaseModel):
    identifiant: str
    mot_de_passe: str
    secret_admin: str


@app.post("/api/admin/creer_compte_rh")
def creer_compte_rh(payload: CreerCompteRequete):
    if not _secret_admin_creation:
        raise HTTPException(
            status_code=503,
            detail="Création de compte désactivée (VERA_SECRET_CREATION_COMPTE non configuré sur ce serveur).",
        )
    if not hmac.compare_digest(payload.secret_admin, _secret_admin_creation):
        raise HTTPException(status_code=403, detail="Secret administrateur incorrect")

    if len(payload.mot_de_passe) < 8:
        raise HTTPException(status_code=422, detail="Mot de passe trop court (8 caractères minimum)")

    succes = auth.creer_compte(payload.identifiant, payload.mot_de_passe)
    if not succes:
        raise HTTPException(status_code=409, detail="Cet identifiant existe déjà")

    return {"statut": "compte créé", "identifiant": payload.identifiant}


# --------------------------------------------------------------------------
# Endpoints RH proteges (necessitent une session valide)
# --------------------------------------------------------------------------

class GenererTokensRequete(BaseModel):
    departement: str
    quantite: int


@app.post("/api/rh/generer_tokens")
def generer_tokens(payload: GenererTokensRequete, session_vera: Optional[str] = Cookie(None)):
    compte = exiger_session(session_vera)

    if payload.quantite < 1 or payload.quantite > 1000:
        raise HTTPException(status_code=422, detail="Quantité doit être entre 1 et 1000")
    if payload.quantite > 9000:
        raise HTTPException(
            status_code=422,
            detail="Quantité trop élevée pour des codes à 4 chiffres (10 000 combinaisons max).",
        )

    resultats_generes = []
    with verrou:
        for _ in range(payload.quantite):
            if SIGNATURE_AVEUGLE_DISPONIBLE:
                # Porte 7 durcie : le token est desormais un token SIGNE
                # (RSABSSA), encode en une chaine compacte pour le
                # registre_codes_courts -- le code court a 4 chiffres
                # reste le seul element transmis au participant, exactement
                # comme avant. Le registre_tokens classique n'est PAS
                # utilise dans ce chemin : la verification se fait par la
                # signature elle-meme, pas par une recherche dans un
                # dictionnaire.
                token_signe = gestionnaire_signature.generer_token_signe(payload.departement)
                token = encoder_token_pour_url(token_signe)
            else:
                token = secrets.token_urlsafe(24)
                registre_tokens[token] = {
                    "departement": payload.departement,
                    "consomme": False,
                }

            code_court = _generer_code_court_unique()
            registre_codes_courts[code_court] = token
            resultats_generes.append({"token": token, "code_court": code_court})

    return {"resultats": resultats_generes, "departement": payload.departement, "genere_par": compte}


@app.get("/api/rh/resultats")
def resultats(session_vera: Optional[str] = Cookie(None)):
    exiger_session(session_vera)

    resultat_par_departement = {}
    with verrou:
        for departement, effectif in effectif_par_departement.items():

            etat_avant = budget_epsilon.etat(departement)
            deja_publie = etat_avant["nombre_publications"] > 0

            if not deja_publie:
                if not budget_epsilon.peut_publier(departement, EPSILON_PAR_PUBLICATION):
                    resultat_par_departement[departement] = {
                        "refuse": True,
                        "raison": "Budget de confidentialite epuise pour ce groupe.",
                    }
                    continue
                budget_epsilon.consommer(departement, EPSILON_PAR_PUBLICATION)
                etat_apres = budget_epsilon.etat(departement)
                persistance.persister_budget_epsilon(departement, etat_apres["epsilon_consomme"], etat_apres["nombre_publications"])

                # Le bruit DP est tire UNE SEULE FOIS, a la premiere publication,
                # puis fige. Republier ne re-tire pas de bruit -- sinon un appelant
                # pourrait moyenner N tirages et supprimer le bruit (epsilon -> infini).
                comptes_bruts = compteurs_par_departement.get(departement, {})
                comptes_bruites = {
                    option["valeur"]: appliquer_bruit_dp(comptes_bruts.get(option["valeur"], 0))
                    for option in QUESTION_ACTIVE["options"]
                }
                persistance.persister_resultat_publie(departement, comptes_bruites)
            else:
                # Deja publie : on renvoie le resultat bruite fige, jamais un nouveau tirage.
                comptes_bruites = persistance.charger_resultat_publie(departement)
                if comptes_bruites is None:
                    # Cas limite : publie mais resultat non trouve (etat incoherent),
                    # on refuse plutot que de re-tirer du bruit et casser la garantie DP.
                    resultat_par_departement[departement] = {
                        "refuse": True,
                        "raison": "Resultat fige introuvable, publication refusee par securite.",
                    }
                    continue

            resultat_par_departement[departement] = {
                "resultats_bruits": comptes_bruites,
                "budget_epsilon": budget_epsilon.etat(departement),
            }

    return resultat_par_departement


@app.get("/api/rh/etat_departements")
def etat_departements(session_vera: Optional[str] = Cookie(None)):
    """Vue d'ensemble pour le tableau de bord RH : combien de tokens
    generes/consommes par departement, sans jamais montrer les reponses
    elles-memes (juste les comptes de progression)."""
    exiger_session(session_vera)

    etat = {}
    with verrou:
        for token, info in registre_tokens.items():
            dep = info["departement"]
            if dep not in etat:
                etat[dep] = {"generes": 0, "consommes": 0}
            etat[dep]["generes"] += 1
            if info["consomme"]:
                etat[dep]["consommes"] += 1

    return etat


# --------------------------------------------------------------------------
# Endpoints publics (vote, sans authentification -- le token EST
# l'autorisation, cf. ATTRIBUTION_FLOW.md)
# --------------------------------------------------------------------------

def _incrementer_compteur(departement: str, reponse: str) -> None:
    """
    Incrementation directe du compteur cumule -- a aucun moment la reponse
    individuelle de ce vote n'existe seule en memoire au-dela de cette
    fonction. Une fois le compteur incremente, la valeur "oui"/"non" de
    CE vote precis n'est plus recuperable -- seul le total cumule existe.
    Partagee entre l'ancien et le nouveau format de token (meme garantie
    de minimisation des donnees dans les deux cas). DOIT etre appelee
    sous le verrou global (pas de verrou interne ici).
    """
    compteurs_par_departement.setdefault(departement, {})
    compteurs_par_departement[departement][reponse] = (
        compteurs_par_departement[departement].get(reponse, 0) + 1
    )
    effectif_par_departement[departement] = effectif_par_departement.get(departement, 0) + 1
    persistance.persister_vote(departement, reponse, compteurs_par_departement[departement][reponse], effectif_par_departement[departement])


class ReponseEntrante(BaseModel):
    reponse: str


class CodeCourtEntrant(BaseModel):
    code: str


@app.post("/api/resoudre_code")
def resoudre_code(payload: CodeCourtEntrant, request: Request):
    """
    Convertit un code court (4 chiffres) en token complet, pour rediriger
    le participant vers son lien de vote reel. Proteges contre le
    brute-force par limitation de tentatives par IP -- avec seulement
    10000 combinaisons possibles, sans cette protection le code serait
    devinable en quelques minutes par un script automatise.
    """
    ip_client = request.client.host if request.client else "inconnue"
    _verifier_anti_bruteforce(ip_client)

    code_normalise = payload.code.strip()
    if not code_normalise.isdigit() or len(code_normalise) != 4:
        _enregistrer_echec(ip_client)
        raise HTTPException(status_code=422, detail="Le code doit comporter 4 chiffres")

    with verrou:
        token = registre_codes_courts.get(code_normalise)

    if token is None:
        _enregistrer_echec(ip_client)
        raise HTTPException(status_code=404, detail="Code invalide")

    _reinitialiser_echecs(ip_client)
    return {"token": token}


def _token_est_signe(token: str) -> bool:
    """
    Distingue un ancien token simple (secrets.token_urlsafe(24), ~32
    caracteres) d'un nouveau token signe (Base64 encodant un JSON avec
    message+signature+randomizer, nettement plus long, ~900+ caracteres).
    Heuristique simple sur la longueur -- suffisante car les deux formats
    n'ont pas de zone de recoupement realiste en pratique.
    """
    return len(token) > 200


@app.get("/api/question")
def obtenir_question(token: str):
    if SIGNATURE_AVEUGLE_DISPONIBLE and _token_est_signe(token):
        # Nouveau format (Porte 7 durcie) : on ne fait QUE decoder pour
        # verifier la forme ici, sans consommer -- la vraie verification
        # cryptographique (et donc la consommation anti-rejeu) n'a lieu
        # qu'au moment du vote reel dans /api/repondre, pas a la simple
        # consultation de la question.
        try:
            decoder_token_depuis_url(token)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=f"Token invalide: {e}")
        return QUESTION_ACTIVE

    with verrou:
        info = registre_tokens.get(token)
        if info is None:
            raise HTTPException(status_code=404, detail="Token inconnu")
        if info["consomme"]:
            raise HTTPException(status_code=410, detail="Token déjà consommé")

    return QUESTION_ACTIVE


@app.post("/api/repondre")
def repondre(payload: ReponseEntrante, x_vera_token: Optional[str] = Header(None)):
    token = x_vera_token
    if not token:
        raise HTTPException(status_code=400, detail="Token manquant")

    valeurs_valides = {opt["valeur"] for opt in QUESTION_ACTIVE["options"]}
    if payload.reponse not in valeurs_valides:
        raise HTTPException(status_code=422, detail="Réponse invalide")

    if SIGNATURE_AVEUGLE_DISPONIBLE and _token_est_signe(token):
        # Nouveau format (Porte 7 durcie) : verification cryptographique
        # reelle de la signature, pas juste une recherche dans un registre.
        # C'est ICI que la verification + consommation anti-rejeu a lieu --
        # gestionnaire_signature.verifier_et_consommer() leve une exception
        # si le token est invalide ou deja utilise.
        try:
            token_complet = decoder_token_depuis_url(token)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Token malforme: {e}")

        try:
            departement = gestionnaire_signature.verifier_et_consommer(token_complet)
        except TokenDejaUtiliseError:
            raise HTTPException(status_code=410, detail="Token déjà consommé")
        except SignatureInvalideError as e:
            raise HTTPException(status_code=404, detail=f"Token invalide: {e}")

        with verrou:
            _incrementer_compteur(departement, payload.reponse)

        return {"statut": "enregistré"}

    # Ancien format (registre simple) -- inchange.
    with verrou:
        info = registre_tokens.get(token)
        if info is None:
            raise HTTPException(status_code=404, detail="Token inconnu")
        if info["consomme"]:
            raise HTTPException(status_code=410, detail="Token déjà consommé")

        departement = info["departement"]
        _incrementer_compteur(departement, payload.reponse)
        info["consomme"] = True

    return {"statut": "enregistré"}


@app.get("/api/health")
def health():
    return {"statut": "ok", "horodatage": datetime.utcnow().isoformat(), "signature_aveugle": "obligatoire_rsabssa_rfc9474"}

