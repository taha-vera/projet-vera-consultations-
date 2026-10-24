#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les scripts de verification du deploiement ne se trompent pas de temoin.

CONSTAT (audit externe du 19/10/2026, F4). infra/verifier_deploiement.sh
repond « CONFORME » -- et c'est ce mot qui autorise le `git push` -- mais ses
controles pouvaient passer a tort :
  * « le processus a demarre apres le dernier .py » comparait au mtime de
    /proc/PID, qui date un inode virtuel et non le lancement du processus ;
  * `git status --untracked-files=no` ignorait tout .py / .so depose a cote de
    l'application, que Python importerait pourtant ;
  * l'unite systemd en service n'etait jamais comparee a infra/ : un ExecStart
    ou un EnvironmentFile modifie a la main ne laissait aucune trace.

Ce test est une GARDE STRUCTURELLE (il lit les scripts, il ne les execute pas) :
il echoue si l'un de ces trois defauts revient. Il ne remplace pas l'essai sur
le serveur.
"""
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
echecs = []


def verifier(condition, message):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message)
        print(f"  ECHEC  {message}")


for nom in ("verifier_deploiement.sh", "audit_integrite_deploiement.sh"):
    src = (RACINE / "infra" / nom).read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    verifier(not re.search(r"-newer\s+\"?/proc/", code),
             f"{nom} : aucune comparaison de date avec le mtime de /proc/PID")
    verifier("lstart" in code,
             f"{nom} : l'heure de demarrage vient de `ps -o lstart`")

v = (RACINE / "infra" / "verifier_deploiement.sh").read_text(encoding="utf-8")
verifier("ls-files --others" in v and "*.so" in v and "*.py" in v,
         "verifier_deploiement.sh : detecte les .py / .so non suivis")
verifier(all(k in v for k in ("WorkingDirectory", "ExecStart", "EnvironmentFile",
                              "vera-consultation.service")),
         "verifier_deploiement.sh : compare l'unite en service au modele infra/")
verifier("vera_state_*.db.enc" in v and "find /root" in v,
         "verifier_deploiement.sh : cherche les anciennes sauvegardes V1 (F12)")

# N7 (audit externe du 24/10/2026) : le service ne tourne plus en root, et le
# verificateur doit le DIRE -- un « CONFORME » qui laisse passer un processus
# root alors que le modele demande un compte dedie rouvrirait le defaut.
code_v = "\n".join(l for l in v.splitlines() if not l.lstrip().startswith("#"))
verifier("ps -o user=" in code_v and "attendu" in code_v,
         "verifier_deploiement.sh : controle le compte sous lequel tourne le processus")
verifier("runuser" in code_v and "test -w" in code_v,
         "verifier_deploiement.sh : controle que ce compte ne peut pas ecrire dans le code servi")
verifier("User StateDirectory ProtectSystem" in code_v,
         "verifier_deploiement.sh : compare User, StateDirectory et ProtectSystem au modele")
verifier("700" in code_v and "VERA_DB_PATH" in code_v,
         "verifier_deploiement.sh : controle le dossier de la base (proprietaire, mode 700)")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).")
    sys.exit(1)
print("OK : les scripts de verification du deploiement gardent leurs temoins.")
