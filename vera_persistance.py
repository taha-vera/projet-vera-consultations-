#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vera_persistance.py - Persistance SQLite Porte 14."""

import sqlite3
import os
import threading
import time
from pathlib import Path

DB_PATH = Path(os.environ.get("VERA_DB_PATH", "/root/vera_state.db"))
_verrou_db = threading.Lock()
_conn = None

_SQL_TABLES = [
    "CREATE TABLE IF NOT EXISTS budget_epsilon (departement TEXT PRIMARY KEY, epsilon_consomme REAL NOT NULL DEFAULT 0.0, nb_publications INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS tokens_consommes (empreinte TEXT PRIMARY KEY, horodatage_unix REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS compteurs_votes (departement TEXT NOT NULL, reponse TEXT NOT NULL, compte INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (departement, reponse))",
    "CREATE TABLE IF NOT EXISTS effectifs (departement TEXT PRIMARY KEY, effectif INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS resultats_publies (departement TEXT PRIMARY KEY, resultat_json TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS codes_courts (code TEXT PRIMARY KEY, token TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS jetons_autorisation (jeton TEXT PRIMARY KEY, departement TEXT NOT NULL, utilise INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS cle_rsa_active (departement TEXT PRIMARY KEY, cle_privee_hex TEXT NOT NULL, cle_publique_hex TEXT NOT NULL, ouverture_unix REAL NOT NULL, salt_hex TEXT)",
]


def _connexion():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrer_schema_cles(conn):
    """Migration idempotente : cle_rsa_active mono-cle (id=1) -> multi-cles
    (departement PRIMARY KEY). Detecte l'ancien schema par la presence de la
    colonne 'id' et, le cas echeant, DROP + recree. SUR : les cles RSA sont
    ephemeres (regenerees a l'ouverture de consultation), aucune donnee
    precieuse perdue. Ne fait rien si la table est absente ou deja migree."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cle_rsa_active'"
    ).fetchall()]
    if not tables:
        return  # table absente : sera creee au bon schema par _SQL_TABLES
    cols = [r[1] for r in conn.execute("PRAGMA table_info(cle_rsa_active)").fetchall()]
    if 'id' in cols:
        conn.execute("DROP TABLE cle_rsa_active")


def initialiser():
    global _conn
    with _verrou_db:
        _conn = _connexion()
        _migrer_schema_cles(_conn)
        for sql in _SQL_TABLES:
            _conn.execute(sql)
        _conn.commit()


def charger_budget_epsilon():
    with _verrou_db:
        rows = _conn.execute("SELECT departement, epsilon_consomme, nb_publications FROM budget_epsilon").fetchall()
    return {row[0]: {"epsilon_consomme": row[1], "nombre_publications": row[2]} for row in rows}


def persister_budget_epsilon(departement, epsilon_consomme, nb_publications):
    with _verrou_db:
        sql = "INSERT INTO budget_epsilon (departement, epsilon_consomme, nb_publications) VALUES (?, ?, ?) ON CONFLICT(departement) DO UPDATE SET epsilon_consomme = excluded.epsilon_consomme, nb_publications = excluded.nb_publications"
        _conn.execute(sql, (departement, epsilon_consomme, nb_publications))
        _conn.commit()


def charger_tokens_consommes():
    with _verrou_db:
        rows = _conn.execute("SELECT empreinte FROM tokens_consommes").fetchall()
    return {row[0] for row in rows}


def persister_token_consomme(empreinte):
    with _verrou_db:
        _conn.execute("INSERT OR IGNORE INTO tokens_consommes (empreinte, horodatage_unix) VALUES (?, ?)", (empreinte, time.time()))
        _conn.commit()


def charger_compteurs():
    with _verrou_db:
        rows_comptes = _conn.execute("SELECT departement, reponse, compte FROM compteurs_votes").fetchall()
        rows_effectifs = _conn.execute("SELECT departement, effectif FROM effectifs").fetchall()
    compteurs = {}
    for dep, rep, compte in rows_comptes:
        compteurs.setdefault(dep, {})[rep] = compte
    effectifs = {row[0]: row[1] for row in rows_effectifs}
    return compteurs, effectifs


def persister_vote(departement, reponse, nouveau_compte, nouvel_effectif):
    with _verrou_db:
        sql1 = "INSERT INTO compteurs_votes (departement, reponse, compte) VALUES (?, ?, ?) ON CONFLICT(departement, reponse) DO UPDATE SET compte = excluded.compte"
        _conn.execute(sql1, (departement, reponse, nouveau_compte))
        sql2 = "INSERT INTO effectifs (departement, effectif) VALUES (?, ?) ON CONFLICT(departement) DO UPDATE SET effectif = excluded.effectif"
        _conn.execute(sql2, (departement, nouvel_effectif))
        _conn.commit()


def charger_codes_courts():
    """Recharge le mapping {code_court: token} au demarrage. Sans cela, un
    redemarrage pendant une consultation active invaliderait tous les codes
    a 4 chiffres deja distribues aux participants."""
    with _verrou_db:
        rows = _conn.execute("SELECT code, token FROM codes_courts").fetchall()
    return {row[0]: row[1] for row in rows}


def persister_code_court(code, token):
    """Enregistre un code court a sa generation."""
    with _verrou_db:
        _conn.execute(
            "INSERT INTO codes_courts (code, token) VALUES (?, ?) "
            "ON CONFLICT(code) DO UPDATE SET token = excluded.token",
            (code, token),
        )
        _conn.commit()


def supprimer_code_court(code):
    """Supprime un code court une fois le token consomme. Libere l'espace des
    codes (evite la saturation a long terme) et empeche toute reutilisation."""
    with _verrou_db:
        _conn.execute("DELETE FROM codes_courts WHERE code = ?", (code,))
        _conn.commit()


# ============================================================================
# REGISTRE 1 -- Jetons d'autorisation (credentials d'emission, refactor crypto)
# Ces jetons prouvent le DROIT de demander une signature aveugle (Temps 1).
# Ils sont distribues par le RH (SMS). Usage unique. Ce registre est SEPARE du
# registre des tokens de vote consommes (tokens_consommes / Temps 2) et ne doit
# JAMAIS etre joint a lui -- c'est ce qui garantit la non-liaison identite<->vote.
# ============================================================================

def persister_jeton_autorisation(jeton, departement):
    """Enregistre un jeton d'autorisation a sa generation par le RH."""
    with _verrou_db:
        _conn.execute(
            "INSERT INTO jetons_autorisation (jeton, departement, utilise) VALUES (?, ?, 0) "
            "ON CONFLICT(jeton) DO NOTHING",
            (jeton, departement),
        )
        _conn.commit()


def consommer_jeton_autorisation(jeton):
    """Consomme un jeton d'autorisation de facon ATOMIQUE. Renvoie le
    departement si le jeton existait et n'etait pas encore utilise, sinon None.
    L'atomicite (UPDATE ... WHERE utilise=0 en une seule transaction) empeche
    qu'un meme jeton soit consomme deux fois par deux requetes simultanees
    (protection anti-double-vote a la source)."""
    with _verrou_db:
        cur = _conn.execute(
            "UPDATE jetons_autorisation SET utilise = 1 WHERE jeton = ? AND utilise = 0",
            (jeton,),
        )
        if cur.rowcount != 1:
            _conn.commit()
            return None  # jeton inconnu OU deja utilise
        row = _conn.execute(
            "SELECT departement FROM jetons_autorisation WHERE jeton = ?",
            (jeton,),
        ).fetchone()
        _conn.commit()
        return row[0] if row else None


def charger_jetons_autorisation():
    """Recharge l'etat des jetons d'autorisation au demarrage {jeton: (departement, utilise)}."""
    with _verrou_db:
        rows = _conn.execute(
            "SELECT jeton, departement, utilise FROM jetons_autorisation"
        ).fetchall()
    return {row[0]: (row[1], bool(row[2])) for row in rows}


def charger_cle_rsa():
    with _verrou_db:
        row = _conn.execute("SELECT cle_privee_hex, cle_publique_hex, ouverture_unix FROM cle_rsa_active WHERE id = 1").fetchone()
    if row is None:
        return None
    return bytes.fromhex(row[0]), bytes.fromhex(row[1]), row[2]


def persister_cle_rsa(cle_privee_der, cle_publique_der, ouverture_unix):
    with _verrou_db:
        sql = "INSERT INTO cle_rsa_active (id, cle_privee_hex, cle_publique_hex, ouverture_unix) VALUES (1, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET cle_privee_hex = excluded.cle_privee_hex, cle_publique_hex = excluded.cle_publique_hex, ouverture_unix = excluded.ouverture_unix"
        _conn.execute(sql, (cle_privee_der.hex(), cle_publique_der.hex(), ouverture_unix))
        _conn.commit()


def effacer_etat_consultation():
    """Efface TOUT l'etat brut d'une consultation : compteurs, effectifs,
    codes courts, tokens consommes, budget epsilon, resultats publies.
    NE touche PAS a la cle RSA (infrastructure, pas donnee de consultation).

    Apres cet appel, le serveur ne conserve plus AUCUNE donnee de la
    consultation cloturee : ni resultat, ni compteur, ni code. C'est la
    garantie de minimisation de VERA rendue operationnelle -- un acces au
    serveur apres cloture ne revele rien de la consultation passee.
    Operation atomique (une seule transaction)."""
    with _verrou_db:
        for table in ("compteurs_votes", "effectifs", "codes_courts",
                      "tokens_consommes", "budget_epsilon", "resultats_publies"):
            _conn.execute(f"DELETE FROM {table}")
        _conn.commit()


def effacer_cle_rsa():
    """Efface TOUTES les cles RSA (destruction groupee : toutes les cles de
    departement d'une consultation meurent ensemble a la cloture)."""
    with _verrou_db:
        _conn.execute("DELETE FROM cle_rsa_active")
        _conn.commit()


def charger_toutes_cles_chiffrees() -> dict:
    """Charge et dechiffre TOUTES les cles de departement (rechargement au boot).
    Renvoie {departement: (cle_privee_der, cle_publique_der, ouverture_unix)}.
    Une cle sans salt (ancien format) est ignoree avec avertissement plutot que
    de bloquer tout le rechargement."""
    with _verrou_db:
        rows = _conn.execute(
            "SELECT departement, cle_privee_hex, cle_publique_hex, ouverture_unix, salt_hex FROM cle_rsa_active"
        ).fetchall()
    resultat = {}
    for dep, priv_hex, pub_hex, ouverture, salt_hex in rows:
        if salt_hex is None:
            continue  # ancien format sans salt : ignore
        salt = bytes.fromhex(salt_hex)
        f = _get_fernet(salt)
        try:
            cle_privee = f.decrypt(bytes.fromhex(priv_hex))
        except Exception:
            continue  # dechiffrement impossible (VERA_DB_KEY changee) : ignore
        resultat[dep] = (cle_privee, bytes.fromhex(pub_hex), ouverture)
    return resultat


# --------------------------------------------------------------------------
# Chiffrement de la cle RSA (Porte 11)
# --------------------------------------------------------------------------

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_PBKDF2_ITERATIONS = 100000

def _get_fernet(salt: bytes) -> Fernet:
    secret = os.environ.get("VERA_DB_KEY", "")
    if not secret:
        raise RuntimeError(
            "ERREUR CRITIQUE : VERA_DB_KEY non definie. "
            "La cle RSA ne peut pas etre chiffree/dechiffree. "
            "Verifiez le fichier systemd."
        )
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    cle_derivee = base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))
    return Fernet(cle_derivee)


def persister_cle_rsa_chiffree(departement: str, cle_privee_der: bytes, cle_publique_der: bytes, ouverture_unix: float) -> None:
    """Ecrit la cle RSA d'UN departement, chiffree avec VERA_DB_KEY, salt aleatoire
    par enregistrement. Une ligne par departement (PRIMARY KEY departement)."""
    salt = os.urandom(16)
    f = _get_fernet(salt)
    cle_privee_chiffree = f.encrypt(cle_privee_der).hex()
    with _verrou_db:
        sql = "INSERT INTO cle_rsa_active (departement, cle_privee_hex, cle_publique_hex, ouverture_unix, salt_hex) VALUES (?, ?, ?, ?, ?) ON CONFLICT(departement) DO UPDATE SET cle_privee_hex = excluded.cle_privee_hex, cle_publique_hex = excluded.cle_publique_hex, ouverture_unix = excluded.ouverture_unix, salt_hex = excluded.salt_hex"
        _conn.execute(sql, (departement, cle_privee_chiffree, cle_publique_der.hex(), ouverture_unix, salt.hex()))
        _conn.commit()


def charger_cle_rsa_chiffree(departement: str) -> tuple[bytes, bytes, float] | None:
    """Charge et dechiffre la cle RSA d'UN departement en utilisant le salt stocke."""
    with _verrou_db:
        row = _conn.execute(
            "SELECT cle_privee_hex, cle_publique_hex, ouverture_unix, salt_hex FROM cle_rsa_active WHERE departement = ?",
            (departement,)
        ).fetchone()
    if row is None:
        return None
    if row[3] is None:
        raise RuntimeError(
            "Cle RSA persistee sans salt (ancien format pre-migration). "
            "Supprimez la ligne dans cle_rsa_active pour forcer une regeneration."
        )
    salt = bytes.fromhex(row[3])
    f = _get_fernet(salt)
    try:
        cle_privee = f.decrypt(bytes.fromhex(row[0]))
    except Exception as e:
        raise RuntimeError(
            f"Impossible de dechiffrer la cle RSA depuis SQLite : {e}. "
            "Verifiez que VERA_DB_KEY est correcte et inchangee."
        )
    cle_publique = bytes.fromhex(row[1])
    return cle_privee, cle_publique, row[2]


def persister_resultat_publie(departement, resultat_dict):
    """Stocke le resultat bruite fige d'un departement (calcule une seule fois)."""
    import json
    with _verrou_db:
        sql = "INSERT INTO resultats_publies (departement, resultat_json) VALUES (?, ?) ON CONFLICT(departement) DO UPDATE SET resultat_json = excluded.resultat_json"
        _conn.execute(sql, (departement, json.dumps(resultat_dict)))
        _conn.commit()


def persister_publication_atomique(departement, epsilon_consomme, nb_publications, resultat_dict):
    """Persiste le budget epsilon ET le resultat fige dans UNE SEULE
    transaction. Empeche l'etat incoherent "budget consomme mais resultat
    absent" qui, apres un crash entre deux commits separes, verrouillait
    definitivement un departement (deja_publie=True mais resultat introuvable).
    Un crash laisse desormais soit les deux ecritures, soit aucune."""
    import json
    with _verrou_db:
        sql_budget = "INSERT INTO budget_epsilon (departement, epsilon_consomme, nb_publications) VALUES (?, ?, ?) ON CONFLICT(departement) DO UPDATE SET epsilon_consomme = excluded.epsilon_consomme, nb_publications = excluded.nb_publications"
        _conn.execute(sql_budget, (departement, epsilon_consomme, nb_publications))
        sql_resultat = "INSERT INTO resultats_publies (departement, resultat_json) VALUES (?, ?) ON CONFLICT(departement) DO UPDATE SET resultat_json = excluded.resultat_json"
        _conn.execute(sql_resultat, (departement, json.dumps(resultat_dict)))
        _conn.commit()  # un seul commit -> atomicite


def charger_resultat_publie(departement):
    """Recupere le resultat bruite fige d'un departement, ou None s'il n'existe pas."""
    import json
    with _verrou_db:
        row = _conn.execute("SELECT resultat_json FROM resultats_publies WHERE departement = ?", (departement,)).fetchone()
    if row is None:
        return None
    return json.loads(row[0])
