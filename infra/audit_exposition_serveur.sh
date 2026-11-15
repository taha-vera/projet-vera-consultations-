#!/usr/bin/env bash
# audit_exposition_serveur.sh -- ce que le serveur MONTRE au monde et dans quel etat il est.
#
# Complement de audit_integrite_deploiement.sh (qui verifie CE QUI TOURNE contre le depot) :
# celui-ci regarde l'EXPOSITION -- ports ouverts, pare-feu, routes publiques, en-tetes,
# certificat, SSH, mises a jour, droits sur les fichiers sensibles.
#
# LECTURE SEULE. Aucune ecriture hors de son propre rapport, aucun restart, aucun reload.
# `nginx -t` teste la configuration sans la charger. Les valeurs des variables secretes
# (HASH, KEY, SECRET, PASS, MDP, TOKEN) sont masquees : le rapport peut etre recopie tel quel.
#
# Usage (en root, sur le serveur) :
#   bash infra/audit_exposition_serveur.sh 2>&1 | tee /root/audit_exposition_$(date -u +%Y%m%dT%H%M%SZ).txt
#
# Les lignes "!! ECART" signalent un ecart detecte automatiquement ; leur absence ne vaut
# pas conformite -- lire les sorties.

set -u
DOMAINE="${DOMAINE:-vera-consultation.fr}"
BASE="${VERA_DB_PATH:-/root/vera_state.db}"
LOG_APP="${VERA_LOG_FILE:-/root/consultation.log}"

masquer() { sed -E 's/((HASH|KEY|SECRET|PASS|MDP|TOKEN)[A-Za-z_]*=)[^ "]*/\1<masque>/g'; }
titre()   { printf '\n==================== %s ====================\n' "$*"; }
run()     { printf '\n$ %s\n' "$*"; bash -c "$*" 2>&1 | masquer; }
ecart()   { printf '!! ECART : %s\n' "$*"; }

echo "Audit exposition -- $(date -u +%Y-%m-%dT%H:%M:%SZ) -- $(hostname) -- $DOMAINE"

# ---------------------------------------------------------------------------
titre "E1 -- ports a l'ecoute (attendu : 22, 80, 443 publics ; 8001 en 127.0.0.1 seulement)"
run "ss -tlnp"
ss -tln 2>/dev/null | awk 'NR>1 {print $4}' | grep -v -E '^(127\.0\.0\.|\[::1\]|::1)' \
    | grep -v -E ':(22|80|443)$' | grep -q . \
    && ecart "un port autre que 22/80/443 ecoute hors boucle locale."
ss -tln 2>/dev/null | grep -E '[:.]8001\b' | grep -v -E '127\.0\.0\.1:8001' | grep -q . \
    && ecart "le port 8001 (API) n'est pas limite a 127.0.0.1."

titre "E2 -- pare-feu"
run "ufw status verbose 2>/dev/null || echo 'ufw absent ou inactif'"
run "nft list ruleset 2>/dev/null | head -40"
echo "(Pare-feu Hetzner Cloud : a verifier dans la console, il n'est pas visible d'ici.)"

# ---------------------------------------------------------------------------
titre "E3 -- routes publiques, vues de l'exterieur (code HTTP, taille). Attendu : 200 pour /api/health, 401/403/404/405 pour le reste"
for chemin in /api/health /openapi.json /docs /redoc /docs/oauth2-redirect \
              /api/rh/resultats /api/rh/etat_departements /api/admin/creer_compte_rh \
              /.git/HEAD /.git/config /.env /vera_state.db /vera_consultation_api.py \
              /requirements.txt /LIMITS.md /static/../vera_consultation_api.py \
              /static/admin.html /admin.html /robots.txt; do
    r=$(curl -s -m 10 -o /dev/null -w '%{http_code} %{size_download}' "https://$DOMAINE$chemin" 2>&1)
    printf '%-40s %s\n' "$chemin" "$r"
    case "$chemin:$r" in
        /openapi.json:200*|/docs:200*|/redoc:200*) ecart "$chemin est servi publiquement : schema complet de l'API (routes admin comprises) lisible par tous." ;;
        /.git/*:200*|/.env:200*|/vera_state.db:200*|/vera_consultation_api.py:200*|/requirements.txt:200*|/LIMITS.md:200*) ecart "$chemin est servi : fichier du depot ou de donnees accessible." ;;
    esac
done

titre "E4 -- en-tetes de la page d'accueil et redirection HTTP"
run "curl -sI -m 10 https://$DOMAINE/"
run "curl -sI -m 10 http://$DOMAINE/ | head -5"
curl -sI -m 10 "https://$DOMAINE/" 2>/dev/null | grep -i '^server:' | grep -q '/' \
    && ecart "l'en-tete Server annonce un numero de version (server_tokens)."
run "curl -s -m 10 -o /dev/null -D - https://$DOMAINE/chemin-inexistant-xyz | head -12"

# ---------------------------------------------------------------------------
titre "E5 -- certificat TLS"
run "echo | openssl s_client -connect $DOMAINE:443 -servername $DOMAINE 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName"
run "certbot certificates 2>/dev/null | grep -E 'Certificate Name|Domains|Expiry'"
run "systemctl list-timers --no-pager 2>/dev/null | grep -i -E 'certbot|NEXT'"
run "nginx -t 2>&1"
run "nginx -T 2>/dev/null | grep -E '^\s*(ssl_protocols|ssl_ciphers|server_tokens|server_name|ssl_certificate )'"
fin=$(echo | openssl s_client -connect "$DOMAINE:443" -servername "$DOMAINE" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$fin" ]; then
    reste=$(( ( $(date -d "$fin" +%s) - $(date +%s) ) / 86400 ))
    echo "Jours avant expiration du certificat : $reste"
    [ "$reste" -lt 14 ] && ecart "le certificat expire dans moins de 14 jours."
fi

# ---------------------------------------------------------------------------
titre "E6 -- SSH : configuration effective"
run "sshd -T 2>/dev/null | grep -E '^(permitrootlogin|passwordauthentication|pubkeyauthentication|kbdinteractiveauthentication|maxauthtries|allowusers|port) '"
sshd -T 2>/dev/null | grep -q '^passwordauthentication yes' \
    && ecart "SSH accepte encore les mots de passe."
run "grep -c 'Failed password' /var/log/auth.log 2>/dev/null || journalctl -u ssh --since '24 hours ago' --no-pager 2>/dev/null | grep -c 'Failed password'"
run "systemctl is-active fail2ban 2>&1; fail2ban-client status sshd 2>&1 | head -8"

# ---------------------------------------------------------------------------
titre "E7 -- mises a jour et etat du systeme"
run "uname -r; lsb_release -ds 2>/dev/null; nginx -v 2>&1; /root/vera_blind_sig/.venv/bin/python3 --version"
run "systemctl is-enabled unattended-upgrades 2>&1; systemctl is-active unattended-upgrades 2>&1"
run "apt list --upgradable 2>/dev/null | grep -i -E 'security|openssl|nginx|systemd|python3|openssh' | head -20"
[ -f /var/run/reboot-required ] && ecart "un redemarrage est requis (noyau ou bibliotheque mis a jour)."
run "uptime -p; df -h / | tail -2; free -m | head -2"

# ---------------------------------------------------------------------------
titre "E8 -- droits sur les fichiers sensibles"
run "stat -c '%a %U:%G %n' $BASE /etc/vera /etc/vera/vera.env $LOG_APP /usr/local/bin/sauvegarder_base.sh 2>&1"
run "ls -la /root | grep -i -E 'vera|\\.db|\\.env|backup|sauvegarde'"
run "ls -la /var/log/nginx 2>&1 | head -12"
for f in /etc/vera/vera.env; do
    m=$(stat -c '%a' "$f" 2>/dev/null)
    [ -n "$m" ] && [ "$m" != "600" ] && ecart "$f a le mode $m (attendu : 600)."
done

# ---------------------------------------------------------------------------
titre "E9 -- journaux du service : erreurs et avertissements (7 jours, sans contenu de requete)"
run "journalctl -u vera-consultation --since '7 days ago' --no-pager 2>/dev/null | grep -c -E 'ERREUR|CRITIQUE|Traceback'"
run "journalctl -u vera-consultation --since '7 days ago' --no-pager 2>/dev/null | grep -E 'ERREUR|CRITIQUE|ATTENTION' | cut -c1-200 | tail -15"
run "wc -c $LOG_APP 2>&1; grep -c -E 'ERREUR|CRITIQUE|Traceback' $LOG_APP 2>&1"
run "systemctl show vera-consultation -p NRestarts -p ActiveEnterTimestamp -p MainPID 2>&1"

echo
echo "Fin de l'audit d'exposition."
