#!/usr/bin/env bash
# annuler_migration_utilisateur_dedie.sh -- remet le service comme avant la
# migration vers un compte dedie. Appele AUTOMATIQUEMENT par
# migrer_vers_utilisateur_dedie.sh quand le service ne repond pas ou ne tourne
# pas sous le bon compte ; utilisable a la main :
#
#   cd /root/repo-push && bash infra/annuler_migration_utilisateur_dedie.sh
#
# Ce que ca fait : arrete le service ; recopie la base ACTUELLE (celle de
# /var/lib/vera, avec ce qui a pu s'y ecrire depuis le demarrage) vers
# l'ancien emplacement ; remet l'ancienne unite et l'ancienne crontab, telles
# que gardees avant la migration ; recharge systemd ; redemarre ; attend
# /api/health. Ce que ca ne fait PAS : supprimer le compte, /opt/vera,
# /opt/vera-venv ni /var/lib/vera (inoffensifs, et utiles pour comprendre
# l'echec ; une nouvelle migration les reprend).
set -euo pipefail

DEST_ETAT="${VERA_DEST_ETAT:-/var/lib/vera}"
ANCIENNE_BASE="${VERA_ANCIENNE_BASE:-/root/vera_state.db}"
DOSSIER_UNITES="${VERA_DOSSIER_UNITES:-/etc/systemd/system}"
DOSSIER_AVANT="${VERA_DOSSIER_AVANT:-/root/avant_migration_vera}"
API="${VERA_API:-http://127.0.0.1:8001}"
ATTENTE="${VERA_ATTENTE_SANTE:-30}"
UNITE="vera-consultation.service"

[ -f "$DOSSIER_AVANT/$UNITE.avant" ] \
    || { echo "ERREUR : $DOSSIER_AVANT/$UNITE.avant absent : rien a restaurer." >&2; exit 1; }

echo "== Arret du service"
systemctl stop "$UNITE" || true

echo "== Base"
if [ -f "$DEST_ETAT/vera_state.db" ]; then
    python3 - "$DEST_ETAT/vera_state.db" "$ANCIENNE_BASE" <<'PY'
import os, sqlite3, sys
src_chemin, dst_chemin = sys.argv[1], sys.argv[2]
if os.path.exists(dst_chemin):
    os.remove(dst_chemin)
src = sqlite3.connect(f"file:{src_chemin}?mode=ro", uri=True)
dst = sqlite3.connect(dst_chemin)
src.backup(dst)
assert dst.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "integrity_check"
dst.close(); src.close()
os.chmod(dst_chemin, 0o600)
print("base recopiee vers", dst_chemin)
PY
elif [ -f "$DOSSIER_AVANT/vera_state.db.avant" ]; then
    cp -p "$DOSSIER_AVANT/vera_state.db.avant" "$ANCIENNE_BASE"
    echo "ancienne base remise telle qu'elle etait."
fi

echo "== Unite et crontab"
install -m 0644 "$DOSSIER_AVANT/$UNITE.avant" "$DOSSIER_UNITES/$UNITE"
systemctl daemon-reload
if [ -s "$DOSSIER_AVANT/crontab.avant" ]; then
    crontab "$DOSSIER_AVANT/crontab.avant"
    echo "crontab d'origine remise."
fi

echo "== Redemarrage"
systemctl start "$UNITE"
for _ in $(seq 1 "$ATTENTE"); do
    if curl -sf "$API/api/health" >/dev/null 2>&1; then
        echo "service de nouveau en bonne sante (ancienne configuration)."
        exit 0
    fi
    sleep 1
done
echo "ERREUR : le service ne repond pas apres le retour arriere : journalctl -u $UNITE -n 50" >&2
exit 1
