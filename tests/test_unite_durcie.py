#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'unite cible (compte dedie) dit ce qu'on croit qu'elle dit, et colle au script.

infra/vera-consultation-durci.service est l'unite que la migration installe
(audit externe du 24/10/2026, N7). Deux choses peuvent la faire mentir sans
qu'aucun test d'execution ne le voie :
  * une ligne perdue ou affaiblie lors d'une retouche (User=, ProtectSystem=,
    CapabilityBoundingSet=...) : le service tournerait « durci » en apparence ;
  * un chemin de l'unite qui n'est plus celui que le script de migration cree :
    l'unite pointerait sur un dossier que personne n'a prepare, et le service
    ne demarrerait pas, un soir de migration.

GARDE STRUCTURELLE : lit les fichiers, ne lance pas systemd. Ce qu'elle ne
voit pas (un reglage refuse par la vraie version de systemd, un appel systeme
bloque par le filtre) se voit sur un serveur neuf, pas ici.
"""
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


unite = (RACINE / "infra" / "vera-consultation-durci.service").read_text(encoding="utf-8")
code = "\n".join(l for l in unite.splitlines() if not l.lstrip().startswith("#"))


def valeur(cle):
    m = re.findall(rf"^{cle}=(.*)$", code, re.M)
    return m[-1].strip() if m else None


def env(nom):
    m = re.findall(rf'^Environment="{nom}=(.*)"\s*$', code, re.M)
    return m[-1] if m else None


# --- 1. Le compte ------------------------------------------------------------------------
verifier(valeur("User") == "vera" and valeur("Group") == "vera",
         "1a. le service tourne sous le compte vera (User= et Group=)")

# --- 2. Les durcissements qui font l'objet de la migration -------------------------------
attendu = {
    "NoNewPrivileges": "true", "ProtectSystem": "strict", "ProtectHome": "yes",
    "PrivateTmp": "yes", "PrivateDevices": "yes", "ProtectKernelTunables": "yes",
    "ProtectKernelModules": "yes", "ProtectControlGroups": "yes",
    "RestrictSUIDSGID": "yes", "LockPersonality": "yes", "UMask": "0077",
    "SystemCallFilter": "@system-service", "StateDirectoryMode": "0700",
}
for cle, v in attendu.items():
    verifier(valeur(cle) == v, f"2. {cle}={v}", f"trouve : {valeur(cle)!r}")
verifier(re.search(r"^CapabilityBoundingSet=\s*$", code, re.M) is not None,
         "2b. CapabilityBoundingSet= vide : aucune capacite (le port 8001 n'en demande pas)")
familles = (valeur("RestrictAddressFamilies") or "").split()
verifier(set(familles) == {"AF_INET", "AF_INET6", "AF_UNIX"},
         "2c. familles d'adresses limitees a TCP/IP et aux sockets locales", str(familles))

# --- 3. Aucun chemin sous /root : ProtectHome=yes le rend invisible -----------------------------
sous_root = [l for l in code.splitlines() if "/root" in l]
verifier(not sous_root, "3. aucun chemin sous /root dans l'unite (invisible avec ProtectHome=yes)",
         "\n      ".join(sous_root))

# --- 4. Les secrets restent dans leur fichier, lu avant l'abaissement des droits ----------------
verifier(valeur("EnvironmentFile") == "/etc/vera/vera.env",
         "4a. les secrets sont lus dans /etc/vera/vera.env")
secrets = ("VERA_DB_KEY", "VERA_ADMIN_HASH", "VERA_SECRET_CREATION_COMPTE")
dans_unite = [n for n in secrets if env(n) is not None]
verifier(not dans_unite, "4b. aucun secret en Environment=", str(dans_unite))

# --- 5. Variables posees : la base doit etre nommee, le code en lecture seule ---------------------
verifier((env("VERA_DB_PATH") or "").startswith("/var/lib/vera/"),
         "5a. VERA_DB_PATH nomme la base sous /var/lib/vera (le code retombait sur /root)",
         str(env("VERA_DB_PATH")))
verifier(env("PYTHONDONTWRITEBYTECODE") == "1",
         "5b. PYTHONDONTWRITEBYTECODE=1 (le code est en lecture seule)")
verifier("MemoryDenyWriteExecute" not in code,
         "5c. MemoryDenyWriteExecute absent, comme l'unite l'explique (cffi / cryptography)")

# --- 6. Coherence avec le script de migration : memes dossiers ---------------------------------------
script = (RACINE / "infra" / "migrer_vers_utilisateur_dedie.sh").read_text(encoding="utf-8")


def defaut(nom):
    m = re.search(rf'^{nom}="\$\{{[A-Z_]+:-([^}}]*)\}}"', script, re.M)
    return m.group(1) if m else None


verifier(valeur("WorkingDirectory") == defaut("DEST_CODE"),
         "6a. WorkingDirectory = dossier de code que le script cree",
         f"unite {valeur('WorkingDirectory')!r}, script {defaut('DEST_CODE')!r}")
verifier((valeur("ExecStart") or "").startswith(str(defaut("DEST_VENV")) + "/bin/python3 "),
         "6b. ExecStart utilise le venv que le script cree",
         f"unite {valeur('ExecStart')!r}, script {defaut('DEST_VENV')!r}")
verifier(env("VERA_DB_PATH") == str(defaut("DEST_ETAT")) + "/vera_state.db",
         "6c. VERA_DB_PATH = dossier d'etat que le script cree + vera_state.db",
         f"unite {env('VERA_DB_PATH')!r}, script {defaut('DEST_ETAT')!r}")
verifier(valeur("StateDirectory") == pathlib.PurePosixPath(str(defaut("DEST_ETAT"))).name
         and str(defaut("DEST_ETAT")).startswith("/var/lib/"),
         "6d. StateDirectory= designe le meme dossier que le script",
         f"unite {valeur('StateDirectory')!r}, script {defaut('DEST_ETAT')!r}")
verifier(str(valeur("StandardOutput")).endswith(str(defaut("DEST_LOGS")) + "/consultation.log")
         or str(valeur("StandardOutput")) == f"append:{defaut('DEST_LOGS')}/consultation.log",
         "6e. le journal est dans le dossier que le script cree",
         f"unite {valeur('StandardOutput')!r}, script {defaut('DEST_LOGS')!r}")
verifier(valeur("LogsDirectory") == pathlib.PurePosixPath(str(defaut("DEST_LOGS"))).name,
         "6f. LogsDirectory= designe le meme dossier de journaux que le script")

# --- 6bis. systemd lui-meme lit l'unite (si disponible ici) ---------------------------------------------
# Une directive mal orthographiee ou inconnue de la version installee est IGNOREE par systemd
# avec un simple avertissement : l'unite « durcie » ne le serait pas. `systemd-analyze` le dit.
import os
import shutil
import subprocess
import tempfile

analyse = shutil.which("systemd-analyze")
if analyse is None:
    print("  IGNORE  6bis. systemd-analyze absent : syntaxe et note de securite non verifiees ici")
else:
    d = tempfile.mkdtemp(prefix="vera_unite_")
    chemin = os.path.join(d, "vera-consultation.service")
    shutil.copy(RACINE / "infra" / "vera-consultation-durci.service", chemin)
    r = subprocess.run([analyse, "verify", chemin], capture_output=True, text=True)
    sortie = r.stdout + r.stderr
    # Le seul avertissement attendu : le venv n'existe pas sur la machine qui lance le test.
    # Seules comptent les lignes qui parlent de NOTRE unite : sur un systeme plus recent, verify
    # signale aussi des unites du systeme (ex. xfs_scrub, CPUAccounting=) qui ne nous concernent pas
    # -- constate sur le serveur le 24/10/2026, ou ces lignes faisaient echouer ce test a tort.
    inattendus = [l for l in sortie.splitlines()
                  if l.strip() and "vera-consultation.service" in l
                  and "is not executable" not in l and "No such file" not in l]
    verifier(not inattendus, "6bis-a. systemd-analyze verify : aucune directive inconnue ni valeur refusee",
             "\n      ".join(inattendus))
    r = subprocess.run([analyse, "security", "--offline=true", chemin],
                       capture_output=True, text=True)
    m = re.search(r"exposure level for [^:]+: ([0-9.]+)", r.stdout)
    note = float(m.group(1)) if m else None
    # L'ancienne unite (root, NoNewPrivileges seul) fait 9,2 ; la cible 1,7 a l'ecriture de ce test.
    verifier(note is not None and note < 4.0,
             "6bis-b. note d'exposition systemd (hors ligne) sous 4,0 (ancienne unite : 9,2)",
             f"note : {note}")
    shutil.rmtree(d)

# --- 7. Le modele en service (ancienne unite) n'a PAS ete modifie par erreur ----------------------
ancienne = (RACINE / "infra" / "vera-consultation.service")
if ancienne.exists():
    t = "\n".join(l for l in ancienne.read_text(encoding="utf-8").splitlines()
                  if not l.lstrip().startswith("#"))
    migre = re.search(r"^User=vera\s*$", t, re.M) is not None
    # Deux etats valides : avant la migration (ancienne unite, sans User=) ou apres la
    # bascule (identique a la cible). Un melange des deux ne l'est pas.
    verifier(migre == (t == code) or not migre,
             "7. infra/vera-consultation.service est soit l'ancienne unite, soit identique a la cible")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : l'unite cible tient ses durcissements et colle au script de migration.")
