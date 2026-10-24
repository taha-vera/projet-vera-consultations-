#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sauvegarder_base.sh est EXECUTE, avec des chemins qui contiennent des apostrophes.

CONSTAT (audit externe du 24/10/2026, N4, mutant survivant sur A11). Le script
interpolait ses chemins dans le source Python d'un heredoc : un VERA_DB_PATH
contenant une apostrophe cassait la sauvegarde, ou y injectait du code. Corrige
en passant les chemins par sys.argv, mais AUCUN test ne lancait le script : le
mutant qui reinterpole les chemins survivait.

CE QUE FAIT CE TEST. Il cree un dossier jetable dont le nom contient une
apostrophe, des guillemets et un espace, y met une base avec deux lignes
d'historique et une cle de sauvegarde (600), lance le VRAI script avec les
chemins surcharges par l'environnement, puis :
  1. le script se termine avec le code 0 ;
  2. un fichier .db.enc est ecrit dans le dossier de sauvegarde ;
  3. dechiffre avec la cle, il contient exactement les deux lignes ;
  4. il ne contient QUE la table historique_consultations (pas de compteur, de
     jeton ni de cle : l'objet de la version 2 du script) ;
  5. un nom contenant du code Python (`'); import os; os.system('...`) n'est PAS
     execute : un fichier temoin n'apparait pas.
Ignore (code 2) si openssl ou shred manquent.
"""

import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "infra" / "sauvegarder_base.sh"
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


for outil in ("openssl", "shred", "bash"):
    if shutil.which(outil) is None:
        print(f"IGNORE : {outil} indisponible.")
        raise SystemExit(2)

racine_tmp = pathlib.Path(tempfile.mkdtemp(prefix="vera_sauv_"))
temoin = racine_tmp / "INJECTION_EXECUTEE"
# Le nom du dossier ressemble a une injection : si le chemin etait interpole dans
# du code Python, cette instruction creerait le fichier temoin.
# (pas de « / » dans un nom de dossier : le temoin est ecrit dans le repertoire
# courant du script, fixe a racine_tmp)
dossier = racine_tmp / "d'o\"ssier '); open('INJECTION_EXECUTEE','w').write('x') #"
dossier.mkdir()
base = dossier / "vera state.db"
conn = sqlite3.connect(base)
conn.execute("CREATE TABLE historique_consultations (groupe TEXT NOT NULL, close_unix REAL NOT NULL, "
             "PRIMARY KEY (groupe, close_unix))")
conn.execute("CREATE TABLE compteurs_votes (departement TEXT, reponse TEXT, compte INTEGER)")
conn.execute("INSERT INTO compteurs_votes VALUES ('SECRET','oui',3)")
conn.executemany("INSERT INTO historique_consultations VALUES (?,?)",
                 [("Atelier", 1700000000.0), ("Bureau", 1700000500.0)])
conn.commit()
conn.close()
cle = dossier / "cle sauvegarde"
cle.write_text("0123456789abcdef" * 4 + "\n")
cle.chmod(0o600)
sortie = dossier / "sauvegardes"

env = dict(os.environ,
           VERA_DB_PATH=str(base),
           VERA_DOSSIER_SAUVEGARDES=str(sortie),
           VERA_CLE_SAUVEGARDE_FICHIER=str(cle),
           VERA_PYTHON=sys.executable)
r = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=120,
                   cwd=str(racine_tmp))
verifier(r.returncode == 0, "1. le script se termine avec le code 0 malgre les caracteres speciaux",
         f"code {r.returncode}\n{r.stdout[-400:]}\n{r.stderr[-400:]}")
verifier(not temoin.exists(), "5. aucun code contenu dans le nom du chemin n'a ete execute")

fichiers = sorted(sortie.glob("vera_historique_*.db.enc")) if sortie.exists() else []
verifier(len(fichiers) == 1, "2. une sauvegarde chiffree a ete ecrite", str(fichiers))
if fichiers:
    clair = racine_tmp / "restaure.db"
    d = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
                        "-pass", f"file:{cle}", "-in", str(fichiers[0]), "-out", str(clair)],
                       capture_output=True, text=True)
    verifier(d.returncode == 0, "3a. elle se dechiffre avec la cle", d.stderr[-200:])
    if d.returncode == 0:
        c = sqlite3.connect(clair)
        lignes = sorted(c.execute("SELECT groupe, close_unix FROM historique_consultations").fetchall())
        tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        c.close()
        verifier(lignes == [("Atelier", 1700000000.0), ("Bureau", 1700000500.0)],
                 "3b. elle contient exactement les deux lignes d'historique", str(lignes))
        verifier(tables == ["historique_consultations"],
                 "4. et seulement cette table (aucun compteur, jeton ni cle)", str(tables))

shutil.rmtree(racine_tmp, ignore_errors=True)
print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : le script de sauvegarde supporte les chemins speciaux et n'execute rien.")
sys.exit(0)
