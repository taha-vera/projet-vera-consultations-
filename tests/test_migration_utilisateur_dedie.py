#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La migration vers un compte dedie est EXECUTEE, pas seulement lue.

POURQUOI CE TEST. infra/migrer_vers_utilisateur_dedie.sh deplace la base d'un
service qui sert des votes, remplace son unite systemd et sa crontab. Un script
de cette nature ne se relit pas : il s'execute, y compris sur ses chemins
d'echec, parce que c'est la qu'il decide de laisser le service dans un etat
connu ou non. Ce test le fait tourner dans un faux systeme de fichiers :
vrais git, python, sqlite, chown, install ; fausses commandes systemctl,
crontab, useradd, runuser, maturin, curl, ps. (Ce que ce test NE voit PAS :
un vrai systemd, un vrai `User=vera`, les durcissements de l'unite. Cela se
verifie sur un serveur neuf -- PROCEDURE_REPRISE_VERA.md, essai de migration.)

SCENARIOS
  S1  chemin nominal : base copiee a l'identique, ancienne base rangee, unite
      et crontab remplacees, ordre arret < rechargement < demarrage, code en
      lecture seule pour les autres, dossiers 0700 / 0750 ;
  S2  une consultation en cours (une ligne dans compteurs_votes) : refus AVANT
      tout changement -- le service n'est meme pas arrete ;
  S2b clone de travail non propre : refus ;
  S3  retour arriere manuel : ce qui a ete ecrit dans la nouvelle base depuis le
      demarrage est rapporte a l'ancien emplacement ; unite et crontab d'origine ;
  S4  le service ne repond pas : retour arriere AUTOMATIQUE, etat d'avant ;
  S5  le premier demarrage echoue : meme chose ;
  S6  le processus tourne sous un autre compte que celui attendu : meme chose.
"""
import os
import pathlib
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
echecs = []

import grp
import pwd
MOI = pwd.getpwuid(os.getuid()).pw_name
MON_GROUPE = grp.getgrgid(os.getgid()).gr_name


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


# --- Les fausses commandes ---------------------------------------------------
STUBS = {
    "systemctl": r'''#!/bin/bash
echo "systemctl $*" >> "$STUB_LOG"
case "$1" in
  show) echo 4242 ;;
  start)
    if [ -n "${STUB_START_FAIL_ONCE:-}" ] && [ ! -e "$STUB_LOG.deja_echoue" ]; then
      touch "$STUB_LOG.deja_echoue"; exit 1
    fi ;;
esac
exit 0
''',
    "crontab": r'''#!/bin/bash
case "$1" in
  -l) [ -f "$STUB_CRON" ] && cat "$STUB_CRON" || exit 1 ;;
  -)  cat > "$STUB_CRON" ;;
  *)  cat "$1" > "$STUB_CRON" ;;
esac
''',
    "useradd": '#!/bin/bash\necho "useradd $*" >> "$STUB_LOG"\n',
    "runuser": '#!/bin/bash\nshift 3\nexec "$@"\n',   # runuser -u X -- cmd...
    "maturin": '#!/bin/bash\necho "maturin $*" >> "$STUB_LOG"\n',
    "curl": '#!/bin/bash\n[ -n "${STUB_CURL_FAIL:-}" ] && exit 1\nexit 0\n',
    "ps": '#!/bin/bash\necho "${STUB_PS_USER:-$STUB_PS_USER_DEFAUT}"\n',
    "journalctl": '#!/bin/bash\nexit 0\n',
}

def cron_origine(t):
    """La ligne de production, avec le chemin de la base du faux serveur."""
    return ("# m h  dom mon dow   command\n"
            f"0 3 * * * VERA_PYTHON=/root/app/.venv/bin/python3 VERA_DB_PATH={t}/root_vera_state.db"
            " /usr/local/bin/sauvegarder_base.sh"
            " >> /root/sauvegarde_vera.log 2>&1\n")


UNITE_ORIGINE = "[Service]\nUser=root\nExecStart=/root/vera_blind_sig/.venv/bin/python3 ancien\n"


def commande(*a, cwd=None, env=None):
    return subprocess.run(a, cwd=cwd, env=env, capture_output=True, text=True)


def monde(base_occupee=False, sale=False):
    """Un faux serveur : depot git, ancienne base, ancienne unite, crontab."""
    t = pathlib.Path(tempfile.mkdtemp(prefix="vera_migr_"))
    depot = t / "repo-push"
    (depot / "infra").mkdir(parents=True)
    for nom in ("migrer_vers_utilisateur_dedie.sh", "annuler_migration_utilisateur_dedie.sh",
                "vera-consultation-durci.service"):
        shutil.copy(RACINE / "infra" / nom, depot / "infra" / nom)
    (depot / "infra" / "verifier_deploiement.sh").write_text(
        "#!/bin/bash\necho 'CONFORME.'\n")
    (depot / "requirements.txt").write_text("")
    (depot / "vera_blind_sig").mkdir()
    (depot / "vera_blind_sig" / "Cargo.toml").write_text("[package]\n")
    for c in (["git", "init", "-q", "-b", "main"],
              ["git", "config", "user.email", "t@example.org"],
              ["git", "config", "user.name", "t"],
              ["git", "add", "-A"], ["git", "commit", "-q", "-m", "init"]):
        r = commande(*c, cwd=depot)
        assert r.returncode == 0, r.stderr
    if sale:
        (depot / "requirements.txt").write_text("# modifie\n")

    base = t / "root_vera_state.db"
    c = sqlite3.connect(base)
    c.execute("CREATE TABLE historique_consultations (groupe TEXT, date TEXT)")
    c.execute("INSERT INTO historique_consultations VALUES ('Atelier', '2026-10-01')")
    c.execute("CREATE TABLE compteurs_votes (departement TEXT, reponse TEXT, compte INTEGER)")
    c.execute("CREATE TABLE jetons_autorisation (jeton TEXT)")
    if base_occupee:
        c.execute("INSERT INTO compteurs_votes VALUES ('Atelier', 'oui', 3)")
    c.commit(); c.close()

    unites = t / "etc_systemd"; unites.mkdir()
    (unites / "vera-consultation.service").write_text(UNITE_ORIGINE)
    bin_ = t / "bin"; bin_.mkdir()
    for nom, corps in STUBS.items():
        (bin_ / nom).write_text(corps); (bin_ / nom).chmod(0o755)
    cron = t / "crontab.txt"; cron.write_text(cron_origine(t))
    return t, depot


def lancer(t, depot, script="migrer_vers_utilisateur_dedie.sh", extra=None):
    env = dict(os.environ)
    env.update({
        "PATH": f"{t / 'bin'}:{os.environ['PATH']}",
        "STUB_LOG": str(t / "appels.log"), "STUB_CRON": str(t / "crontab.txt"),
        # Le test tourne sous N'IMPORTE QUEL compte (CI, poste d'un developpeur) : le
        # « compte du service » et le proprietaire du code sont celui qui le lance.
        "VERA_MIGRATION_TEST": "1", "VERA_UTILISATEUR": MOI, "VERA_GROUPE": MON_GROUPE,
        "VERA_PROPRIETAIRE_CODE": f"{MOI}:{MON_GROUPE}", "STUB_PS_USER_DEFAUT": MOI,
        "VERA_DEST_CODE": str(t / "opt_vera"), "VERA_DEST_VENV": str(t / "opt_vera_venv"),
        "VERA_DEST_ETAT": str(t / "var_lib_vera"), "VERA_DEST_LOGS": str(t / "var_log_vera"),
        "VERA_ANCIENNE_BASE": str(t / "root_vera_state.db"),
        "VERA_ANCIEN_VENV": str(t / "inexistant"),
        "VERA_DOSSIER_UNITES": str(t / "etc_systemd"),
        "VERA_DOSSIER_AVANT": str(t / "avant"),
        "VERA_IMPORTS": "sqlite3", "VERA_ATTENTE_SANTE": "2", "HOME": str(t),
    })
    env.update(extra or {})
    # umask 0 : le clone est cree grand ouvert (fichiers 666, dossiers 777), de sorte
    # que seul le chmod du script le rend « lecture seule pour les autres ». Avec le
    # umask habituel (022), un script SANS ce chmod passait ce test (essai du 24/10).
    return subprocess.run(["bash", str(depot / "infra" / script)], cwd=depot, env=env,
                          capture_output=True, text=True, preexec_fn=lambda: os.umask(0))


def appels(t):
    f = t / "appels.log"
    return f.read_text().splitlines() if f.exists() else []


def lignes_base(chemin, table):
    c = sqlite3.connect(chemin)
    r = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    c.close()
    return r


# --- S1 : chemin nominal -------------------------------------------------------
print("S1 -- chemin nominal")
t, depot = monde()
r = lancer(t, depot)
verifier(r.returncode == 0, "S1a. la migration se termine avec succes", r.stdout[-600:] + r.stderr[-600:])
verifier("MIGRATION TERMINEE" in r.stdout, "S1b. le message de fin est affiche")
nouvelle = t / "var_lib_vera" / "vera_state.db"
verifier(nouvelle.exists() and lignes_base(nouvelle, "historique_consultations") == 1,
         "S1c. la base est copiee, avec sa ligne d'historique")
verifier(stat.S_IMODE(nouvelle.stat().st_mode) == 0o600, "S1d. la base copiee est en mode 600")
verifier(not (t / "root_vera_state.db").exists()
         and (t / "avant" / "vera_state.db.avant").exists(),
         "S1e. l'ancienne base est rangee a part, pas supprimee")
verifier((t / "etc_systemd" / "vera-consultation.service").read_text()
         == (RACINE / "infra" / "vera-consultation-durci.service").read_text(),
         "S1f. la nouvelle unite est celle du modele cible du depot")
verifier((t / "avant" / "vera-consultation.service.avant").read_text() == UNITE_ORIGINE,
         "S1g. l'ancienne unite est gardee")
cron = (t / "crontab.txt").read_text()
verifier(f"VERA_DB_PATH={t}/var_lib_vera/vera_state.db" in cron
         and f"VERA_DB_PATH={t}/root_vera_state.db" not in cron
         and f"VERA_PYTHON={t}/opt_vera_venv/bin/python3" in cron,
         "S1h. la sauvegarde nocturne pointe sur la nouvelle base et le nouveau Python", cron)
verifier(cron.count("VERA_PYTHON=") == 1 and "/root/app/.venv" not in cron,
         "S1h2. un ancien VERA_PYTHON de la crontab est remplace, pas duplique", cron)
verifier((t / "avant" / "crontab.avant").read_text() == cron_origine(t),
         "S1i. la crontab d'origine est gardee")
a = appels(t)
def position(prefixe):
    return next((i for i, l in enumerate(a) if l.startswith(prefixe)), None)
i_stop, i_reload, i_start = position("systemctl stop"), position("systemctl daemon-reload"), position("systemctl start")
verifier(None not in (i_stop, i_reload, i_start) and i_stop < i_reload < i_start,
         "S1j. ordre : arret, puis rechargement de l'unite, puis demarrage", "\n".join(a))
verifier(any(l.startswith("maturin develop --release --locked") for l in a),
         "S1k. le module Rust est recompile avec --locked")
code = t / "opt_vera"
cible = code / "infra" / "vera-consultation-durci.service"
verifier(cible.exists() and not (cible.stat().st_mode & 0o022),
         "S1l. le code deploye est en lecture seule pour le groupe et les autres")
tete_depot = commande("git", "rev-parse", "HEAD", cwd=depot).stdout.strip()
tete_code = commande("git", "rev-parse", "HEAD", cwd=code).stdout.strip()
verifier(tete_depot == tete_code and tete_depot != "", "S1m. /opt/vera est au meme commit que le clone de travail")
verifier(stat.S_IMODE((t / "var_lib_vera").stat().st_mode) == 0o700
         and stat.S_IMODE((t / "var_log_vera").stat().st_mode) == 0o750,
         "S1n. dossiers d'ecriture : etat 0700, journal 0750")
verifier(commande("git", "status", "--porcelain", cwd=code).stdout.strip() == "",
         "S1o. le clone deploye reste propre apres les chmod")

# --- S3 : retour arriere manuel apres S1 ------------------------------------------
print("S3 -- retour arriere manuel")
c = sqlite3.connect(nouvelle)
c.execute("INSERT INTO historique_consultations VALUES ('Bureau', '2026-10-02')")
c.commit(); c.close()
r = lancer(t, depot, "annuler_migration_utilisateur_dedie.sh")
verifier(r.returncode == 0, "S3a. le retour arriere se termine avec succes", r.stdout[-400:] + r.stderr[-400:])
verifier((t / "root_vera_state.db").exists()
         and lignes_base(t / "root_vera_state.db", "historique_consultations") == 2,
         "S3b. ce qui a ete ecrit depuis le demarrage est rapporte a l'ancien emplacement")
verifier((t / "etc_systemd" / "vera-consultation.service").read_text() == UNITE_ORIGINE,
         "S3c. l'ancienne unite est remise")
verifier((t / "crontab.txt").read_text() == cron_origine(t), "S3d. la crontab d'origine est remise")

# --- S1bis : on peut migrer de nouveau apres un retour arriere ------------------------
print("S1bis -- nouvelle migration apres un retour arriere")
r = lancer(t, depot)
verifier(r.returncode == 0 and lignes_base(t / "var_lib_vera" / "vera_state.db",
                                          "historique_consultations") == 2,
         "S1bis. la migration reprend ce qui existe deja et emporte les 2 lignes",
         r.stdout[-400:] + r.stderr[-400:])
shutil.rmtree(t)

# --- S2 : consultation en cours ----------------------------------------------------------
print("S2 -- consultation en cours")
t, depot = monde(base_occupee=True)
avant = (t / "root_vera_state.db").read_bytes()
r = lancer(t, depot)
verifier(r.returncode != 0 and "consultation" in r.stderr.lower(),
         "S2a. refus avec un message qui parle de la consultation", r.stderr[-300:])
verifier(not any(l.startswith("systemctl stop") for l in appels(t)),
         "S2b. le service n'a pas ete arrete")
verifier(not (t / "opt_vera").exists() and not (t / "var_lib_vera").exists(),
         "S2c. rien n'a ete cree")
verifier((t / "root_vera_state.db").read_bytes() == avant, "S2d. l'ancienne base est intacte")
verifier((t / "crontab.txt").read_text() == cron_origine(t), "S2e. la crontab est intacte")
shutil.rmtree(t)

print("S2bis -- clone de travail non propre")
t, depot = monde(sale=True)
r = lancer(t, depot)
verifier(r.returncode != 0 and not (t / "opt_vera").exists()
         and not any(l.startswith("systemctl stop") for l in appels(t)),
         "S2bis. refus, service non arrete, rien cree", r.stderr[-300:])
shutil.rmtree(t)

# --- S4, S5, S6 : echecs APRES l'arret du service ------------------------------------------
def echec_apres_arret(nom, extra, attendu_stderr):
    print(nom)
    t, depot = monde()
    r = lancer(t, depot, extra=extra)
    verifier(r.returncode != 0, f"{nom[:2]}a. la migration echoue (code non nul)")
    verifier("Retour arriere automatique" in r.stderr, f"{nom[:2]}b. le retour arriere automatique est declenche", r.stderr[-300:])
    verifier(attendu_stderr in r.stderr, f"{nom[:2]}c. la cause est dite : {attendu_stderr}", r.stderr[-300:])
    verifier((t / "root_vera_state.db").exists()
             and lignes_base(t / "root_vera_state.db", "historique_consultations") == 1,
             f"{nom[:2]}d. la base est de nouveau a son ancien emplacement")
    verifier((t / "etc_systemd" / "vera-consultation.service").read_text() == UNITE_ORIGINE,
             f"{nom[:2]}e. l'ancienne unite est remise")
    verifier((t / "crontab.txt").read_text() == cron_origine(t), f"{nom[:2]}f. la crontab d'origine est remise")
    shutil.rmtree(t)

echec_apres_arret("S4 -- le service ne repond pas", {"STUB_CURL_FAIL": "1"}, "ne repond pas")
echec_apres_arret("S5 -- le premier demarrage echoue", {"STUB_START_FAIL_ONCE": "1"}, "systemctl start a echoue")
echec_apres_arret("S6 -- mauvais compte", {"STUB_PS_USER": "un_autre_compte_que_" + MOI}, "tourne sous")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la migration vers un compte dedie tient sur son chemin nominal et sur ses echecs.")
