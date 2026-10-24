#!/usr/bin/env bash
# verifier_deploiement.sh -- a lancer APRES chaque deploiement.
#
# Repond a une seule question : ce qui est servi est-il exactement ce qui est
# commite ? `active (running)` ne le prouve pas (constat du 13/10/2026).
# Lecture seule. Code de sortie 0 = conforme, 1 = au moins un ecart.
#
#   bash infra/verifier_deploiement.sh

set -u
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
UNITE="${UNITE:-vera-consultation.service}"
SITE_NGINX="${SITE_NGINX:-/etc/nginx/sites-enabled/vera-consultation}"
VITRINE="${VITRINE:-/var/www/vera/index.html}"
DOMAINE="${DOMAINE:-vera-consultation.fr}"
API="http://127.0.0.1:8001"
# Le modele d'unite auquel comparer l'unite en service. Par defaut celui du depot ;
# surchargeable pour verifier une migration en cours (migrer_vers_utilisateur_dedie.sh
# l'utilise pour comparer a infra/vera-consultation-durci.service).
MODELE="${MODELE_UNITE_FICHIER:-$REPO/infra/vera-consultation.service}"

echecs=0
ok()  { printf '  OK     %s\n' "$*"; }
ko()  { printf '  ECART  %s\n' "$*"; echecs=$((echecs + 1)); }
att() { printf '  ATTENTION  %s\n' "$*"; }      # information, ne fait pas echouer
h()   { sha256sum | cut -d' ' -f1; }

echo "Commit : $(git -C "$REPO" log -1 --format='%h %ci %s')"

# 1. Le clone est un commit, pas un etat bricole.
[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ] \
    && ok "clone propre" || ko "modifications locales non commitees dans $REPO"

# 1b. Aucun code NON SUIVI que Python chargerait. `status --untracked-files=no`
#     (ci-dessus) ignore ces fichiers : un .py depose a cote de l'application,
#     ou un module compile (.so) non commite, serait importe sans que le
#     depot n'en porte trace (audit externe du 19/10/2026, F4). On liste aussi
#     les fichiers ignores (pas de --exclude-standard), a la racine seulement :
#     c'est la que le processus cherche ses modules.
inconnus=$(git -C "$REPO" ls-files --others -- ':(top,glob)*.py' ':(top,glob)*.so' \
    ':(top,glob)*.pth' 2>/dev/null)
[ -z "$inconnus" ] && ok "aucun .py / .so / .pth non suivi a la racine" \
    || ko "code non suivi par git, importable par le processus : $(echo $inconnus)"

# 1c. Le commit en service est-il publie ? Information seulement : le flux
#     documente est « verifier, PUIS git push », donc HEAD en avance sur
#     origin est normal juste apres un deploiement. Ce qui est signale, c'est
#     un serveur qui tourne sur un code que personne d'autre ne peut relire.
tete=$(git -C "$REPO" rev-parse HEAD)
distant=$(timeout 15 git -C "$REPO" ls-remote origin refs/heads/main 2>/dev/null | cut -f1)
if [ -z "$distant" ]; then
    att "depot distant injoignable : on ne sait pas si ce commit est publie"
elif [ "$distant" = "$tete" ]; then
    ok "HEAD = origin/main (code publie)"
else
    att "HEAD != origin/main : ce code tourne mais n'est PAS publie -- git push apres verification"
fi

# 2. Le processus tourne bien depuis le clone, et a ete redemarre apres
#    le dernier changement de code.
PID=$(systemctl show "$UNITE" -p MainPID --value)
if [ -z "$PID" ] || [ "$PID" = "0" ]; then
    ko "$UNITE n'a pas de processus"
else
    cwd=$(readlink "/proc/$PID/cwd")
    [ "$cwd" = "$REPO" ] && ok "cwd du processus = $REPO" \
        || ko "cwd du processus = $cwd, pas $REPO (lancer ce script depuis le dossier du service : bash $cwd/infra/verifier_deploiement.sh)"
    # 2b. Le COMPTE du processus (audit externe du 24/10/2026, N7). Le modele
    #     d'unite dit sous quel compte il doit tourner ; sans `User=` il tourne en
    #     root. Un service « conforme » qui tourne en root alors que le modele
    #     demande `vera` ne l'est pas.
    attendu=$(grep -h '^User=' "$MODELE" 2>/dev/null | tail -1 | sed 's/^User=//')
    attendu="${attendu:-root}"
    reel_user=$(ps -o user= -p "$PID" 2>/dev/null | tr -d ' ')
    [ "$reel_user" = "$attendu" ] && ok "processus sous le compte $attendu" \
        || ko "processus sous le compte « $reel_user » (le modele d'unite demande « $attendu »)"
    # 2c. Ce compte ne peut PAS reecrire le code servi : c'est ce que le compte
    #     dedie protege (static/vote.html, le bundle, le Python). Test par
    #     `runuser`, donc seulement en root ; hors root on le dit, on ne le saute pas en silence.
    if [ "$attendu" != "root" ]; then
        if [ "$(id -u)" != "0" ]; then
            att "pas root : impossible de verifier que $attendu ne peut pas ecrire dans $REPO"
        else
            ecrivables=""
            for f in "$REPO" "$REPO/static/vote.html" "$REPO/static/blindrsa-bundle.js" "$REPO/vera_consultation_api.py"; do
                runuser -u "$attendu" -- test -w "$f" 2>/dev/null && ecrivables="$ecrivables $(basename "$f")"
            done
            [ -z "$ecrivables" ] && ok "le compte $attendu ne peut pas ecrire dans le code servi" \
                || ko "le compte $attendu PEUT ecrire :$ecrivables (chown -R root:root $REPO && chmod -R go-w $REPO)"
        fi
    fi
    # Heure de DEMARRAGE du processus : `ps -o lstart=`. Le mtime de /proc/PID,
    # utilise avant, est celui d'un inode du systeme de fichiers virtuel, cree
    # a la premiere consultation du repertoire et non au lancement du
    # processus : il pouvait donner un faux « demarre apres » (audit F4).
    debut=$(date -d "$(ps -o lstart= -p "$PID")" +%s 2>/dev/null)
    if [ -z "$debut" ]; then
        ko "heure de demarrage du processus $PID illisible (ps)"
    else
        recents=""
        for f in "$REPO"/*.py; do
            [ "$(stat -c %Y "$f")" -gt "$debut" ] && recents="$recents $(basename "$f")"
        done
        [ -z "$recents" ] && ok "processus demarre apres le dernier .py modifie" \
            || ko "non charges (redemarrer) :$recents"
    fi
    # 3. Module Rust : compile apres le dernier commit qui touche ses sources ?
    #    Ancre sur "/vera_blind_sig." (prefixe du .so compile), pas sur la
    #    seule sous-chaine "vera_blind_sig" -- celle-ci apparait aussi dans le
    #    nom du dossier du venv et matchait a tort un .so sans rapport, ex.
    #    _cffi_backend.cpython-*.so (constat du 13/10/2026).
    so=$(grep -o '/[^ ]*/vera_blind_sig\.[^ ]*\.so' "/proc/$PID/maps" | sort -u | head -1)
    commit_rs=$(git -C "$REPO" log -1 --format=%ct -- vera_blind_sig/src vera_blind_sig/Cargo.toml vera_blind_sig/Cargo.lock)
    if [ -z "$so" ]; then
        ko "module vera_blind_sig introuvable dans la memoire du processus"
    elif [ "$(stat -c %Y "$so")" -ge "$commit_rs" ]; then
        ok "module Rust compile apres le dernier commit de ses sources"
    else
        ko "module Rust ($so, $(stat -c %y "$so")) PLUS ANCIEN que le dernier commit de vera_blind_sig/ -- recompiler (maturin build + pip install)"
    fi
fi

# 3b. L'unite systemd en service = le modele du depot, sur ce qui commande
#     l'execution : repertoire, ligne de lancement, fichier de secrets, NOMS des
#     variables (jamais leurs valeurs). Une unite modifiee a la main -- autre
#     ExecStart, autre EnvironmentFile -- change ce qui tourne sans laisser de
#     trace dans git (audit F4). `systemctl cat` inclut les drop-ins.
reel=$(systemctl cat "$UNITE" 2>/dev/null)
if [ -z "$reel" ] || [ ! -f "$MODELE" ]; then
    ko "unite ou modele illisible : comparaison impossible"
else
    for cle in WorkingDirectory ExecStart EnvironmentFile User StateDirectory ProtectSystem; do
        a=$(grep -h "^$cle=" "$MODELE" | tail -1)
        b=$(printf '%s\n' "$reel" | grep "^$cle=" | tail -1)
        [ "$a" = "$b" ] && ok "unite : $cle conforme au modele" \
            || ko "unite : $cle differe du modele (modele : ${a:-absent} / en service : ${b:-absent})"
    done
    # Une variable par ligne Environment= (c'est la forme du modele).
    noms() { grep -h '^Environment=' | sed 's/^Environment=//; s/^"//; s/=.*//' | sort -u; }
    na=$(noms < "$MODELE"); nb=$(printf '%s\n' "$reel" | noms)
    [ "$na" = "$nb" ] && ok "unite : memes noms de variables d'environnement que le modele" \
        || ko "unite : noms de variables differents du modele ($(diff <(echo "$na") <(echo "$nb") | grep '^[<>]' | tr '\n' ' '))"

    # 3c. Le FICHIER DE SECRETS (audit F6) : les trois secrets ne sont plus dans
    #     l'unite (le controle des noms ci-dessus le garantit : un `Environment=`
    #     VERA_DB_KEY ferait apparaitre un nom de trop) mais dans un fichier
    #     dont les droits comptent. On controle droits et NOMS, jamais valeurs :
    #     rien de ce qui suit ne lit une valeur vers l'ecran.
    FICHIER_SECRETS=$(grep -h '^EnvironmentFile=' "$MODELE" | tail -1 | sed 's/^EnvironmentFile=//; s/^-//')
    EXEMPLE="$REPO/infra/vera.env.exemple"
    if [ -z "$FICHIER_SECRETS" ] || [ ! -f "$EXEMPLE" ]; then
        ko "fichier de secrets : chemin ou modele (infra/vera.env.exemple) introuvable"
    elif [ ! -f "$FICHIER_SECRETS" ]; then
        ko "fichier de secrets $FICHIER_SECRETS absent -- le service ne demarre pas sans lui"
    else
        [ "$(stat -c '%U:%G %a' "$FICHIER_SECRETS")" = "root:root 600" ] \
            && ok "fichier de secrets : root:root, mode 600" \
            || ko "fichier de secrets : droits $(stat -c '%U:%G %a' "$FICHIER_SECRETS") (attendu root:root 600)"
        [ "$(stat -c '%U:%G %a' "$(dirname "$FICHIER_SECRETS")")" = "root:root 700" ] \
            && ok "dossier des secrets : root:root, mode 700" \
            || ko "dossier des secrets : droits $(stat -c '%U:%G %a' "$(dirname "$FICHIER_SECRETS")") (attendu root:root 700)"
        lister() { grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$1" | cut -d= -f1 | sort -u; }
        sa=$(lister "$EXEMPLE"); sb=$(lister "$FICHIER_SECRETS")
        [ "$sa" = "$sb" ] && ok "fichier de secrets : memes noms que le modele (3 variables)" \
            || ko "fichier de secrets : noms differents du modele ($(diff <(echo "$sa") <(echo "$sb") | grep '^[<>]' | tr '\n' ' '))"
        vides=$(grep -cE '^[A-Za-z_][A-Za-z0-9_]*=(CHANGER_MOI)?$' "$FICHIER_SECRETS")
        [ "$vides" = "0" ] && ok "fichier de secrets : aucune valeur vide ni « CHANGER_MOI »" \
            || ko "fichier de secrets : $vides valeur(s) vide(s) ou « CHANGER_MOI »"
    fi
fi

# 3d. La base (audit externe du 24/10/2026, N7). Le modele d'unite fixe VERA_DB_PATH
#     et le compte ; le dossier de la base doit appartenir a ce compte, en 700 :
#     c'est le seul endroit ou le processus ecrit. Une ancienne base restee a
#     son emplacement d'avant est signalee : elle ne sert plus, mais elle existe.
base_modele=$(grep -h '^Environment="VERA_DB_PATH=' "$MODELE" 2>/dev/null \
    | tail -1 | sed 's/^Environment="VERA_DB_PATH=//; s/"$//')
compte_modele=$(grep -h '^User=' "$MODELE" 2>/dev/null | tail -1 | sed 's/^User=//')
if [ -n "$base_modele" ] && [ -n "$compte_modele" ]; then
    dossier_base=$(dirname "$base_modele")
    if [ ! -d "$dossier_base" ]; then
        ko "dossier de la base $dossier_base absent"
    else
        [ "$(stat -c '%U %a' "$dossier_base")" = "$compte_modele 700" ] \
            && ok "dossier de la base : $compte_modele, mode 700" \
            || ko "dossier de la base $dossier_base : $(stat -c '%U %a' "$dossier_base") (attendu $compte_modele 700)"
        [ -f "$base_modele" ] && ok "base presente a $base_modele" \
            || ko "base absente de $base_modele"
    fi
    case "$base_modele" in
        /root/*) ;;   # modele ancien : la base reste sous /root, rien a signaler
        *) [ -e /root/vera_state.db ] \
               && att "/root/vera_state.db existe encore (ancienne base de la migration) : a supprimer une fois la migration confirmee" ;;
    esac
fi

# 4. Fichiers servis par l'application = fichiers du depot.
for f in static/vote.html static/blindrsa-bundle.js static/admin.html; do
    [ "$(curl -sf "$API/$f" | h)" = "$(h < "$REPO/$f")" ] \
        && ok "$f servi = depot" || ko "$f servi != depot"
done

# 5. nginx : fichier sur disque = depot, et configuration EN MEMOIRE = disque
#    (la CSP renvoyee prouve que le reload a eu lieu).
cmp -s "$SITE_NGINX" "$REPO/infra/nginx-vera-consultation.conf" \
    && ok "conf nginx sur disque = depot" \
    || ko "conf nginx sur disque != depot (cp infra/nginx-vera-consultation.conf $SITE_NGINX)"
csp_servie=$(curl -sk -D - -o /dev/null --resolve "$DOMAINE:443:127.0.0.1" \
    "https://$DOMAINE/static/admin.html" | grep -i '^content-security-policy' | grep -o "script-src[^;]*")
if [ -n "$csp_servie" ] && grep -qF "$csp_servie" "$REPO/infra/nginx-vera-consultation.conf"; then
    ok "CSP servie presente dans la conf du depot (reload effectue)"
else
    ko "CSP servie absente de la conf du depot -- nginx -t && systemctl reload nginx"
fi

# 6. Vitrine (copie, servie par nginx depuis /var/www/vera -- voir
#    infra/nginx-vera-consultation.conf, location = /).
[ "$(curl -sk --resolve "$DOMAINE:443:127.0.0.1" "https://$DOMAINE/" | h)" = "$(h < "$REPO/index.html")" ] \
    && ok "vitrine servie = index.html du depot" \
    || ko "vitrine servie != index.html du depot (cp $REPO/index.html $VITRINE)"

# 7. Aucune sauvegarde de la V1 (vera_state_*.db.enc). La V1 de
#    sauvegarder_base.sh ecrivait la base ENTIERE (jetons, compteurs) ; la V2 ne
#    sauvegarde que l'historique et ne purge que vera_historique_*. Un fichier V1
#    oublie reforme la paire de lectures (jetons + compteurs a deux instants) que
#    l'abandon du mode WAL a fermee (audit externe du 20/10/2026, F12). Ne
#    regarde que CE serveur ; une copie envoyee sur un telephone ou un autre
#    support doit etre supprimee a la main (LIMITS.md, section 15).
v1=$(find /root /home /tmp /var /srv /opt -xdev -name 'vera_state_*.db.enc' 2>/dev/null)
if [ -z "$v1" ]; then
    ok "aucune ancienne sauvegarde V1 (vera_state_*.db.enc) sur ce serveur"
else
    ko "sauvegarde(s) V1 contenant la base entiere : $(echo $v1) -- shred -u <fichier>"
fi

echo
[ "$echecs" -eq 0 ] && echo "CONFORME." || echo "$echecs ECART(S). Le deploiement n'est PAS effectif."
exit $(( echecs > 0 ))
