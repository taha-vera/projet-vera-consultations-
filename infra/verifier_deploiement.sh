#!/usr/bin/env bash
# verifier_deploiement.sh -- a lancer APRES chaque deploiement.
#
# Repond a une seule question : ce qui est servi est-il exactement ce qui est
# commite ? `active (running)` ne le prouve pas (constat du 13/10/2026).
# Lecture seule. Code de sortie 0 = conforme, 1 = au moins un ecart.
#
#   bash infra/verifier_deploiement.sh

set -u
REPO="${REPO:-/root/repo-push}"
UNITE="${UNITE:-vera-consultation.service}"
SITE_NGINX="${SITE_NGINX:-/etc/nginx/sites-enabled/vera-consultation}"
VITRINE="${VITRINE:-/var/www/vera/index.html}"
DOMAINE="${DOMAINE:-vera-consultation.fr}"
API="http://127.0.0.1:8001"

echecs=0
ok()  { printf '  OK     %s\n' "$*"; }
ko()  { printf '  ECART  %s\n' "$*"; echecs=$((echecs + 1)); }
h()   { sha256sum | cut -d' ' -f1; }

echo "Commit : $(git -C "$REPO" log -1 --format='%h %ci %s')"

# 1. Le clone est un commit, pas un etat bricole.
[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ] \
    && ok "clone propre" || ko "modifications locales non commitees dans $REPO"

# 2. Le processus tourne bien depuis le clone, et a ete redemarre apres
#    le dernier changement de code.
PID=$(systemctl show "$UNITE" -p MainPID --value)
if [ -z "$PID" ] || [ "$PID" = "0" ]; then
    ko "$UNITE n'a pas de processus"
else
    cwd=$(readlink "/proc/$PID/cwd")
    [ "$cwd" = "$REPO" ] && ok "cwd du processus = $REPO" || ko "cwd du processus = $cwd"
    recents=$(find "$REPO" -maxdepth 1 -name '*.py' -newer "/proc/$PID")
    [ -z "$recents" ] && ok "processus demarre apres le dernier .py modifie" \
        || ko "non charges (redemarrer) : $recents"
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

echo
[ "$echecs" -eq 0 ] && echo "CONFORME." || echo "$echecs ECART(S). Le deploiement n'est PAS effectif."
exit $(( echecs > 0 ))
