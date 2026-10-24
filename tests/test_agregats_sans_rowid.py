#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les tables d'agregats ne conservent pas l'ordre d'insertion (rowid).

CONSTAT (audit externe du 24/10/2026, N2). Seule tokens_consommes etait
WITHOUT ROWID. compteurs_votes et effectifs gardaient un rowid implicite :
la ligne d'un groupe (ou d'une reponse d'un groupe) naissant au premier vote qui
la concerne, `SELECT rowid` restituait l'ordre des premiers votes entre groupes
et entre reponses. Le texte de LIMITS.md affirmait pourtant « sans ordre
d'insertion ». Meme canal que celui ferme pour les jetons consommes.

CE QUE CE TEST VERIFIE
  1. base neuve : `SELECT rowid` echoue sur tokens_consommes, compteurs_votes et
     effectifs (aucune colonne rowid) ;
  2. base ANCIENNE (schema avec rowid, comptes presents) : apres initialiser(),
     les trois tables sont sans rowid ET les comptes sont intacts (la migration
     ne perd pas les votes en cours) ;
  3. la migration est idempotente : un second passage ne change rien ;
  4. les ecritures normales (increment d'un vote) fonctionnent apres migration.
"""

import os
import pathlib
import sqlite3
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

chemin = tempfile.mktemp(suffix=".db", prefix="vera_rowid_")
os.environ["VERA_DB_PATH"] = chemin
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ["VERA_VERROU_PROCESSUS"] = chemin + ".lock"

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


TABLES = ("tokens_consommes", "compteurs_votes", "effectifs")


def a_un_rowid(conn, table):
    try:
        conn.execute(f"SELECT rowid FROM {table} LIMIT 1").fetchall()
        return True
    except sqlite3.OperationalError:
        return False


# --- Base ANCIENNE : schema avec rowid, des votes en cours ---------------
ancien = sqlite3.connect(chemin)
ancien.execute("CREATE TABLE tokens_consommes (empreinte TEXT PRIMARY KEY)")
ancien.execute("CREATE TABLE compteurs_votes (departement TEXT NOT NULL, reponse TEXT NOT NULL, "
               "compte INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (departement, reponse))")
ancien.execute("CREATE TABLE effectifs (departement TEXT PRIMARY KEY, effectif INTEGER NOT NULL DEFAULT 0)")
ancien.executemany("INSERT INTO compteurs_votes VALUES (?,?,?)",
                   [("Zeta", "oui", 7), ("Alpha", "non", 3), ("Alpha", "oui", 5)])
ancien.executemany("INSERT INTO effectifs VALUES (?,?)", [("Zeta", 7), ("Alpha", 8)])
ancien.executemany("INSERT INTO tokens_consommes VALUES (?)", [("e1",), ("e2",)])
ancien.commit()
verifier(all(a_un_rowid(ancien, t) for t in TABLES),
         "0. (preuve du montage) l'ancienne base a bien un rowid sur les trois tables")
ancien.close()

import vera_persistance as p  # noqa: E402

p.initialiser()
conn = sqlite3.connect(chemin)

verifier(not any(a_un_rowid(conn, t) for t in TABLES),
         "1/2. apres initialiser() sur une ancienne base, plus aucun rowid",
         str({t: a_un_rowid(conn, t) for t in TABLES}))
verifier(sorted(conn.execute("SELECT departement, reponse, compte FROM compteurs_votes").fetchall())
         == [("Alpha", "non", 3), ("Alpha", "oui", 5), ("Zeta", "oui", 7)],
         "2a. les compteurs en cours sont conserves")
verifier(sorted(conn.execute("SELECT departement, effectif FROM effectifs").fetchall())
         == [("Alpha", 8), ("Zeta", 7)], "2b. les effectifs en cours sont conserves")
verifier(sorted(conn.execute("SELECT empreinte FROM tokens_consommes").fetchall()) == [("e1",), ("e2",)],
         "2c. les empreintes anti-rejeu sont conservees")
conn.close()

# --- Idempotence ----------------------------------------------------------
c2 = sqlite3.connect(chemin)
p._migrer_agregats_sans_rowid(c2)
p._migrer_tokens_sans_rowid(c2)
verifier(sorted(c2.execute("SELECT departement, reponse, compte FROM compteurs_votes").fetchall())
         == [("Alpha", "non", 3), ("Alpha", "oui", 5), ("Zeta", "oui", 7)],
         "3. un second passage de la migration ne change rien")
c2.close()

# --- Base NEUVE -----------------------------------------------------------
neuve = tempfile.mktemp(suffix=".db", prefix="vera_rowid_neuve_")
c3 = sqlite3.connect(neuve)
for sql in p._SQL_TABLES:
    c3.execute(sql)
verifier(not any(a_un_rowid(c3, t) for t in TABLES),
         "1. base neuve : aucun rowid sur les trois tables")
c3.close()

# --- Ecritures normales apres migration ----------------------------------
p.vider_cache = getattr(p, "vider_cache", None)
try:
    c4 = sqlite3.connect(chemin)
    c4.execute("INSERT INTO compteurs_votes (departement, reponse, compte) VALUES ('Alpha','oui',1) "
               "ON CONFLICT(departement, reponse) DO UPDATE SET compte = compte + 1")
    c4.commit()
    v = c4.execute("SELECT compte FROM compteurs_votes WHERE departement='Alpha' AND reponse='oui'").fetchone()[0]
    verifier(v == 6, "4. l'upsert d'un vote fonctionne sur la table migree", f"compte={v}")
    c4.close()
except Exception as e:  # pragma: no cover
    verifier(False, "4. l'upsert d'un vote fonctionne sur la table migree", repr(e))

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : compteurs_votes, effectifs et tokens_consommes n'ont plus de rowid.")
sys.exit(0)
