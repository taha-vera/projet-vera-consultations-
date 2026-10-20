#!/usr/bin/env bash
# audit_integrite_deploiement.sh -- audit cible du 13/10/2026, points 1 a 6.
#
# LECTURE SEULE. Ne modifie rien : pas de restart, pas de reload, pas de
# git fetch, pas d'ecriture hors de son propre rapport. Les valeurs des
# variables secretes (HASH, KEY, SECRET, PASS, MDP, TOKEN) sont masquees
# avant affichage -- le rapport peut etre recopie tel quel dans une
# conversation.
#
# Usage (en root, sur le serveur) :
#   bash infra/audit_integrite_deploiement.sh 2>&1 | tee /root/audit_deploiement_$(date -u +%Y%m%dT%H%M%SZ).txt
#
# Chaque commande est affichee precedee de "$ ", puis sa sortie brute.
# Les lignes "!! ECART" signalent un ecart detecte automatiquement ; leur
# absence ne vaut pas conformite -- lire les sorties.

set -u
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
UNITE="${UNITE:-vera-consultation.service}"
SITE_NGINX="${SITE_NGINX:-/etc/nginx/sites-enabled/vera-consultation}"
DOMAINE="${DOMAINE:-vera-consultation.fr}"

masquer() { sed -E 's/((HASH|KEY|SECRET|PASS|MDP|TOKEN)[A-Za-z_]*=)[^ "]*/\1<masque>/g'; }
titre()   { printf '\n==================== %s ====================\n' "$*"; }
run()     { printf '\n$ %s\n' "$*"; bash -c "$*" 2>&1 | masquer; }
ecart()   { printf '!! ECART : %s\n' "$*"; }

echo "Audit integrite deploiement -- $(date -u +%Y-%m-%dT%H:%M:%SZ) -- $(hostname)"
run "git -C $REPO rev-parse HEAD; git -C $REPO log -1 --format='%ci %s'"
run "git -C $REPO status --porcelain --untracked-files=no"
[ -n "$(git -C "$REPO" status --porcelain --untracked-files=no 2>/dev/null)" ] \
    && ecart "le clone a des modifications locales non commitees : ce qui tourne n'est PAS un commit."
run "git -C $REPO ls-remote origin HEAD"
loc=$(git -C "$REPO" rev-parse HEAD 2>/dev/null); dist=$(git -C "$REPO" ls-remote origin HEAD 2>/dev/null | cut -f1)
[ -n "$dist" ] && [ "$loc" != "$dist" ] && ecart "HEAD local ($loc) != HEAD GitHub ($dist)."

# ---------------------------------------------------------------------------
titre "POINT 1 -- unites systemd"
run "systemctl list-units --type=service --state=running --no-pager --plain"
run "systemctl list-unit-files --no-pager | grep -i -E 'vera|uvicorn|gunicorn'"
run "grep -rl -i -E 'vera|/root/' /etc/systemd/system /lib/systemd/system 2>/dev/null"
run "systemctl cat $UNITE --no-pager"
run "systemctl show $UNITE -p FragmentPath -p DropInPaths -p WorkingDirectory -p ExecStart -p EnvironmentFiles -p Environment -p MainPID -p ActiveEnterTimestamp"

PID=$(systemctl show "$UNITE" -p MainPID --value 2>/dev/null)
if [ -n "$PID" ] && [ "$PID" != "0" ]; then
    run "readlink /proc/$PID/cwd"
    [ "$(readlink /proc/$PID/cwd)" != "$REPO" ] && ecart "le processus tourne depuis $(readlink /proc/$PID/cwd), pas $REPO."
    run "tr '\\0' ' ' < /proc/$PID/cmdline; echo"
    run "ps -o pid,lstart,cmd -p $PID"
    # Fichiers Python plus recents que le demarrage du processus = code commite
    # mais PAS charge (redemarrage oublie).
    # Comparaison a l'heure de DEMARRAGE reelle (ps lstart), pas au mtime de
    # /proc/PID : celui-ci date la creation d'un inode virtuel, pas le
    # lancement du processus (audit externe du 19/10/2026, F4).
    DEBUT=$(date -d "$(ps -o lstart= -p "$PID")" +%s 2>/dev/null)
    if [ -z "$DEBUT" ]; then
        ecart "heure de demarrage du processus illisible (ps)."
    else
        RECENTS=""
        for f in "$REPO"/*.py; do
            [ "$(stat -c %Y "$f")" -gt "$DEBUT" ] && RECENTS="$RECENTS $(basename "$f")"
        done
        run "echo 'py plus recents que le demarrage :${RECENTS:- aucun}'"
        [ -n "$RECENTS" ] && ecart "des .py du clone sont plus recents que le processus : non charges ($RECENTS)."
    fi
    # Module natif reellement mappe en memoire, et sa date.
    # NB : ancre sur le segment de chemin "/vera_blind_sig." (le prefixe du
    # fichier compile, ex. vera_blind_sig.cpython-314-....so) et non sur la
    # seule sous-chaine "vera_blind_sig", qui apparait aussi dans le nom du
    # dossier du venv et matchait a tort des .so sans rapport (ex.
    # _cffi_backend.cpython-*.so, constat du 13/10/2026).
    run "grep -o '/[^ ]*/vera_blind_sig\\.[^ ]*\\.so' /proc/$PID/maps | sort -u"
    SO=$(grep -o '/[^ ]*/vera_blind_sig\.[^ ]*\.so' /proc/"$PID"/maps | sort -u | head -1)
    [ -n "$SO" ] && run "stat -c '%y  %n' '$SO'"
else
    ecart "aucun MainPID pour $UNITE."
fi

# D'ou vient le module Rust installe ? (maturin/pip notent la source)
VENV_SP=$(ls -d /root/vera_blind_sig/.venv/lib/python3*/site-packages 2>/dev/null | head -1)
run "ls -d $VENV_SP/vera_blind_sig* 2>/dev/null"
run "cat $VENV_SP/vera_blind_sig-*.dist-info/direct_url.json 2>/dev/null; echo; stat -c '%y  %n' $VENV_SP/vera_blind_sig-*.dist-info/RECORD 2>/dev/null"
run "git -C $REPO log -1 --format='%ci %h %s' -- vera_blind_sig/src/lib.rs vera_blind_sig/Cargo.toml vera_blind_sig/Cargo.lock"
# /root/vera_blind_sig contient-il des SOURCES (copie parallele) en plus du venv ?
run "ls -la /root/vera_blind_sig/ 2>/dev/null; ls -la /root/vera_blind_sig/src 2>/dev/null"
if [ -f /root/vera_blind_sig/src/lib.rs ]; then
    run "diff -q /root/vera_blind_sig/src/lib.rs $REPO/vera_blind_sig/src/lib.rs && echo IDENTIQUE"
fi

# Copies figees restantes (l'ancien WorkingDirectory) : encore presentes = piege
# rearmable par tout ce qui tourne avec cwd=/root.
run "for f in \$(git -C $REPO ls-files '*.py' 'static/*' 'index.html'); do [ -e /root/\$f ] && { cmp -s /root/\$f $REPO/\$f && echo \"identique  /root/\$f\" || echo \"DIVERGE    /root/\$f\"; }; done"
run "find / -xdev \\( -path /proc -o -path $REPO -o -path '*/.git' \\) -prune -o \\( -name 'vera_consultation_api.py' -o -name 'vera_signature_manager.py' -o -name 'vote.html' -o -name 'blindrsa-bundle.js' -o -name 'admin.html' \\) -print 2>/dev/null"

# ---------------------------------------------------------------------------
titre "POINT 2 -- nginx reellement actif"
run "ls -la /etc/nginx/sites-enabled/ /etc/nginx/sites-available/ /etc/nginx/conf.d/"
run "nginx -T 2>/dev/null | grep -n -E '^# configuration file|server_name|listen|default_server|^\\s*root |include'"
run "cmp $SITE_NGINX $REPO/infra/nginx-vera-consultation.conf && echo IDENTIQUE"
cmp -s "$SITE_NGINX" "$REPO/infra/nginx-vera-consultation.conf" \
    || ecart "la conf nginx active differe de infra/nginx-vera-consultation.conf (diff ci-dessous)."
run "diff $REPO/infra/nginx-vera-consultation.conf $SITE_NGINX | head -60"
run "stat -c '%y  %n' $SITE_NGINX; git -C $REPO log -1 --format='%ci %h %s' -- infra/nginx-vera-consultation.conf"
# nginx -T lit le DISQUE ; ce qui est en memoire ne change qu'au reload.
# La CSP renvoyee reellement prouve si le reload a eu lieu.
run "curl -sk -o /dev/null -D - --resolve $DOMAINE:443:127.0.0.1 https://$DOMAINE/static/admin.html | grep -i content-security-policy"
run "grep -o \"script-src[^;]*\" $SITE_NGINX | sort -u"
# Page d'accueil : nginx lit /var/www/vera (infra/nginx-vera-consultation.conf,
# location = /). GUIDE_DEPLOIEMENT.md disait /root/vitrine jusqu'au 13/10/2026
# -- corrige ; ce controle verifie qu'aucune des deux copies ne diverge.
run "ls -la /var/www/vera/ 2>&1"
run "cmp /var/www/vera/index.html $REPO/index.html && echo IDENTIQUE"
cmp -s /var/www/vera/index.html "$REPO/index.html" || ecart "la vitrine servie differe de index.html du depot."
run "curl -sk --resolve $DOMAINE:443:127.0.0.1 https://$DOMAINE/ | sha256sum; sha256sum $REPO/index.html"

# ---------------------------------------------------------------------------
titre "POINT 3 -- cron, timers, taches planifiees"
run "crontab -l -u root"
run "for u in \$(cut -d: -f1 /etc/passwd); do c=\$(crontab -l -u \$u 2>/dev/null) && [ -n \"\$c\" ] && echo \"--- \$u\" && echo \"\$c\"; done"
run "cat /etc/crontab; ls -la /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly"
run "grep -rn -E 'vera|/root/' /etc/crontab /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly /var/spool/cron 2>/dev/null"
run "systemctl list-timers --all --no-pager"
run "atq 2>&1"
# Chaque chemin de script cite : dans le clone, ou copie a part ?
run "grep -rhoE '/[A-Za-z0-9_./-]+\\.(sh|py)' /etc/crontab /etc/cron.d /var/spool/cron /etc/systemd/system 2>/dev/null | sort -u | while read p; do case \$p in $REPO/*) echo \"clone      \$p\";; *) b=\$(basename \$p); t=\$(git -C $REPO ls-files | grep -m1 \"/\\?\$b\$\"); if [ -n \"\$t\" ]; then cmp -s \$p $REPO/\$t && echo \"HORS CLONE identique a \$t : \$p\" || echo \"HORS CLONE DIVERGE de \$t : \$p\"; else echo \"hors clone (pas dans le depot) \$p\"; fi;; esac; done"

# ---------------------------------------------------------------------------
titre "POINT 4 -- sauvegardes et instantanes"
run "ls -la /root/sauvegardes_vera/ 2>&1 | tail -12"
run "find / -xdev \\( -path /proc -o -path $REPO/.git \\) -prune -o \\( -name '*vera*.db*' -o -name '*vera*.enc' -o -name '*vera*.tar*' -o -name '*vera*.bak' \\) -printf '%TY-%Tm-%Td %s  %p\\n' 2>/dev/null"
run "ls /root/sauvegarder_base.sh /usr/local/bin/*sauvegard* 2>&1; for f in /root/sauvegarder_base.sh /usr/local/bin/sauvegarder_base.sh; do [ -f \$f ] && { cmp -s \$f $REPO/infra/sauvegarder_base.sh && echo \"identique \$f\" || echo \"DIVERGE \$f\"; }; done"
run "grep -c 'VERSION 2' \$(grep -rhoE '/[A-Za-z0-9_./-]*sauvegard[A-Za-z0-9_./-]*\\.sh' /etc/crontab /etc/cron.d /var/spool/cron 2>/dev/null | sort -u) 2>&1"
run "command -v hcloud restic borg rsnapshot duplicity 2>&1"
echo "(Instantanes/sauvegardes Hetzner : a verifier dans la console Hetzner Cloud -> serveur -> Backups / Snapshots. Non visible depuis le serveur.)"

# ---------------------------------------------------------------------------
titre "POINT 5 -- variables d'environnement portant un chemin"
if [ -n "${PID:-}" ] && [ "$PID" != "0" ]; then
    run "tr '\\0' '\\n' < /proc/$PID/environ | sort"
    run "tr '\\0' '\\n' < /proc/$PID/environ | grep -E '=.*/' | grep -v -E '^(PATH|INVOCATION_ID|JOURNAL_STREAM)='"
    run "tr '\\0' '\\n' < /proc/$PID/environ | grep -E '^(PYTHONPATH|PYTHONHOME|PYTHONSTARTUP|VIRTUAL_ENV|VERA_)'"
fi
run "grep -n -E 'PYTHONPATH|VERA_|cd /root' /root/.bashrc /root/.profile /etc/environment /etc/profile.d/* 2>/dev/null"
run "grep -rn -E 'os\\.environ(\\.get)?\\(|getenv\\(' $REPO --include=*.py --include=*.sh -h | grep -o -E '\"[A-Z_]+\"' | sort -u"

# ---------------------------------------------------------------------------
titre "POINT 6 -- service vs depot, octet par octet"
for f in static/vote.html static/blindrsa-bundle.js static/admin.html; do
    run "curl -s http://127.0.0.1:8001/$f | sha256sum; sha256sum $REPO/$f"
    [ "$(curl -s "http://127.0.0.1:8001/$f" | sha256sum | cut -d' ' -f1)" != "$(sha256sum "$REPO/$f" | cut -d' ' -f1)" ] \
        && ecart "$f servi != $REPO/$f"
done
run "curl -s http://127.0.0.1:8001/vote | sha256sum; sha256sum $REPO/static/vote.html"
echo
echo "Fin de l'audit."
