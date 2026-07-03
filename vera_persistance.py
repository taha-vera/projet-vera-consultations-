#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vera_persistance.py - Persistance SQLite Porte 14."""

import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path("/root/vera_state.db")
_verrou_db = threading.Lock()
_conn = None

_SQL_TABLES = [
    "CREATE TABLE IF NOT EXISTS budget_epsilon (departement TEXT PRIMARY KEY, epsilon_consomme REAL NOT NULL DEFAULT 0.0, nb_publications INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS tokens_consommes (empreinte TEXT PRIMARY KEY, horodatage_unix REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS compteurs_votes (departement TEXT NOT NULL, reponse TEXT NOT NULL, compte INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (departement, reponse))",
    "CREATE TABLE IF NOT EXISTS effectifs (departement TEXT PRIMARY KEY, effectif INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS cle_rsa_active (id INTEGER PRIMARY KEY CHECK (id = 1), cle_privee_hex TEXT NOT NULL, cle_publique_hex TEXT NOT NULL, ouverture_unix REAL NOT NULL)",
]


def _connexion():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialiser():
    global _conn
    with _verrou_db:
        _conn = _connexion()
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


def effacer_cle_rsa():
    with _verrou_db:
        _conn.execute("DELETE FROM cle_rsa_active WHERE id = 1")
        _conn.commit()
