#!/usr/bin/env bash
# migrer_vers_utilisateur_dedie.sh -- fait passer le service de root a un compte
# dedie (audit externe du 24/10/2026, N7). A lancer UNE FOIS, en root, depuis le
# clone de travail, HORS consultation active :
#
#   cd /root/repo-push && bash infra/migrer_vers_utilisateur_dedie.sh
#
# CE QUE CE SCRIPT FAIT, dans l'ordre. Tout ce qui precede l'etape 5 (arret du
# service) est sans effet sur le service en cours : si une precondition ou une
# des etapes 1 a 4 echoue, rien n'a change pour les votants.
#   0. verifie : root, clone propre, AUCUNE consultation (base vide sauf
#      historique_consultations), unite cible presente ;
#   1. cree le compte systeme `vera` (sans shell, sans dossier personnel) ;
#   2. clone le code dans /opt/vera, proprietaire root, lecture seule pour vera ;
#   3. cree /opt/vera-venv (interpreteur du venv actuel), installe les
#      dependances, recompile le module Rust (--locked), verifie que `vera`
#      sait tout importer ;
#   4. cree /var/lib/vera (0700) et /var/log/vera (0750) ;
#   5. ARRETE le service ;
#   6. copie la base par l'API de sauvegarde SQLite, controle l'integrite et les
#      effectifs de chaque table, puis range l'ancienne ailleurs ;
#   7. garde l'ancienne unite et la crontab, installe la nouvelle unite ;
#   8. pointe la sauvegarde nocturne sur la nouvelle base ;
#   9. DEMARRE le service, attend /api/health, controle que le processus tourne
#      sous `vera`. Si ca echoue : retour arriere AUTOMATIQUE (voir
#      annuler_migration_utilisateur_dedie.sh) ;
#  10. lance le verificateur de deploiement depuis le nouveau dossier.
#
# Ce que le script ne fait PAS : il ne supprime rien (ni l'ancienne base, ni
# l'ancien venv, ni /root/consultation.log) ; il ne touche pas a nginx ni a
# /etc/vera/vera.env ; il ne pousse rien. Les variables VERA_* ci-dessous
# existent pour que le test le fasse tourner dans un faux systeme de fichiers.
set -euo pipefail

REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
UTILISATEUR="${VERA_UTILISATEUR:-vera}"
GROUPE="${VERA_GROUPE:-$UTILISATEUR}"
# Proprietaire du code et du venv : root en production ; ne change que pour le test.
PROPRIETAIRE_CODE="${VERA_PROPRIETAIRE_CODE:-root:root}"
DEST_CODE="${VERA_DEST_CODE:-/opt/vera}"
DEST_VENV="${VERA_DEST_VENV:-/opt/vera-venv}"
DEST_ETAT="${VERA_DEST_ETAT:-/var/lib/vera}"
DEST_LOGS="${VERA_DEST_LOGS:-/var/log/vera}"
ANCIENNE_BASE="${VERA_ANCIENNE_BASE:-/root/vera_state.db}"
ANCIEN_VENV="${VERA_ANCIEN_VENV:-/root/vera_blind_sig/.venv}"
DOSSIER_UNITES="${VERA_DOSSIER_UNITES:-/etc/systemd/system}"
DOSSIER_AVANT="${VERA_DOSSIER_AVANT:-/root/avant_migration_vera}"
IMPORTS="${VERA_IMPORTS:-vera_blind_sig fastapi uvicorn opendp cryptography}"
API="${VERA_API:-http://127.0.0.1:8001}"
ATTENTE="${VERA_ATTENTE_SANTE:-30}"
UNITE="vera-consultation.service"
# L'unite cible est livree sous un nom a part tant que la migration n'a pas eu lieu :
# infra/vera-consultation.service reste le modele de l'unite EN SERVICE, que
# verifier_deploiement.sh compare a la realite. Une fois la migration faite, un
# commit de bascule renomme la cible en vera-consultation.service ; ce script
# retombe alors sur ce nom.
MODELE_UNITE="$REPO/infra/vera-consultation-durci.service"
[ -f "$MODELE_UNITE" ] || MODELE_UNITE="$REPO/infra/vera-consultation.service"

etape() { printf '\n== %s\n' "$*"; }
die()   { printf '\nERREUR : %s\n' "$*" >&2; exit 1; }

# --- 0. Preconditions : rien n'est modifie avant qu'elles passent toutes -----
etape "0. Preconditions"
[ "${VERA_MIGRATION_TEST:-0}" = "1" ] || [ "$(id -u)" = "0" ] || die "a lancer en root."
[ -f "$MODELE_UNITE" ] || die "modele d'unite introuvable : $MODELE_UNITE"
# Le nom du compte est celui de l'unite ; VERA_UTILISATEUR ne change que pour le test.
grep -q '^User=vera$' "$MODELE_UNITE" \
    || die "le modele d'unite ne declare pas User=vera : mauvaise version du depot ?"
[ -z "$(git -C "$REPO" status --porcelain --untracked-files=no)" ] \
    || die "le clone $REPO a des modifications non commitees."
[ "$(git -C "$REPO" rev-parse --abbrev-ref HEAD)" = "main" ] \
    || die "le clone n'est pas sur la branche main."

if [ -f "$ANCIENNE_BASE" ]; then
    # Aucune consultation : toutes les tables sont vides, sauf l'historique.
    occupees=$(python3 - "$ANCIENNE_BASE" <<'PY'
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
noms = [r[0] for r in c.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
for n in noms:
    if n == "historique_consultations":
        continue
    k = c.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
    if k:
        print(f"{n}={k}")
PY
) || die "la base $ANCIENNE_BASE est illisible."
    [ -z "$occupees" ] || die "une consultation est en cours ou des donnees restent ($occupees). Cloturer d'abord : la migration se fait entre deux consultations."
    echo "base $ANCIENNE_BASE : aucune consultation en cours."
else
    echo "pas de base a $ANCIENNE_BASE : rien a copier (serveur neuf)."
fi

# --- 1. Le compte ----------------------------------------------------------
etape "1. Compte systeme $UTILISATEUR"
if id "$UTILISATEUR" >/dev/null 2>&1; then
    echo "existe deja."
else
    useradd --system --no-create-home --home-dir /nonexistent \
            --shell /usr/sbin/nologin "$UTILISATEUR"
fi

# --- 2. Le code, en lecture seule pour le compte ---------------------------
etape "2. Code dans $DEST_CODE (proprietaire root)"
if [ -d "$DEST_CODE/.git" ]; then
    git -C "$DEST_CODE" pull --ff-only "$REPO" main
else
    git clone --no-hardlinks "$REPO" "$DEST_CODE"
fi
# origin = le depot publie, comme dans le clone de travail ; on ne tire jamais
# depuis origin ici, seulement depuis le clone de travail (chemin explicite).
if origine=$(git -C "$REPO" remote get-url origin 2>/dev/null); then
    git -C "$DEST_CODE" remote set-url origin "$origine"
fi
chown -R "$PROPRIETAIRE_CODE" "$DEST_CODE"
chmod -R go-w,a+rX "$DEST_CODE"

# --- 3. L'environnement Python, HORS du depot ------------------------------
etape "3. Environnement Python dans $DEST_VENV"
INTERPRETE="$(readlink -f "$ANCIEN_VENV/bin/python3" 2>/dev/null || true)"
[ -x "${INTERPRETE:-}" ] || INTERPRETE="$(command -v python3)"
echo "interpreteur : $INTERPRETE"
[ -x "$DEST_VENV/bin/python3" ] || "$INTERPRETE" -m venv "$DEST_VENV"
"$DEST_VENV/bin/python3" -m pip install --quiet -r "$DEST_CODE/requirements.txt"
(
    cd "$REPO/vera_blind_sig"
    VIRTUAL_ENV="$DEST_VENV" PATH="$HOME/.cargo/bin:$PATH" \
    PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 \
        maturin develop --release --locked
)
chown -R "$PROPRIETAIRE_CODE" "$DEST_VENV"
chmod -R go-w,a+rX "$DEST_VENV"
# Le compte sait-il tout importer ? C'est CE test qui attrape un interpreteur
# sous /root (illisible pour lui) ou un module non compile.
( cd / && runuser -u "$UTILISATEUR" -- "$DEST_VENV/bin/python3" -c \
    "import $(echo "$IMPORTS" | sed 's/ /, /g')" ) \
    || die "le compte $UTILISATEUR ne sait pas importer : $IMPORTS. Rien n'a change pour le service."

# --- 4. Les dossiers d'ecriture --------------------------------------------
etape "4. $DEST_ETAT et $DEST_LOGS"
install -d -o "$UTILISATEUR" -g "$GROUPE" -m 0700 "$DEST_ETAT"
install -d -o "$UTILISATEUR" -g "$GROUPE" -m 0750 "$DEST_LOGS"

# A partir d'ici le service est arrete : on revient en arriere si ca echoue.
revenir() {
    printf '\nECHEC : %s\nRetour arriere automatique.\n' "$1" >&2
    VERA_DEST_ETAT="$DEST_ETAT" VERA_ANCIENNE_BASE="$ANCIENNE_BASE" \
    VERA_DOSSIER_UNITES="$DOSSIER_UNITES" VERA_DOSSIER_AVANT="$DOSSIER_AVANT" \
    VERA_API="$API" VERA_ATTENTE_SANTE="$ATTENTE" bash "$REPO/infra/annuler_migration_utilisateur_dedie.sh" || true
    exit 1
}

# --- 5. Arret ---------------------------------------------------------------
etape "5. Arret du service"
mkdir -p "$DOSSIER_AVANT"; chmod 700 "$DOSSIER_AVANT"
[ -f "$DOSSIER_UNITES/$UNITE" ] && cp -p "$DOSSIER_UNITES/$UNITE" "$DOSSIER_AVANT/$UNITE.avant"
crontab -l > "$DOSSIER_AVANT/crontab.avant" 2>/dev/null || : > "$DOSSIER_AVANT/crontab.avant"
systemctl stop "$UNITE"

# --- 6. La base --------------------------------------------------------------
etape "6. Copie de la base"
if [ -f "$ANCIENNE_BASE" ]; then
    python3 - "$ANCIENNE_BASE" "$DEST_ETAT/vera_state.db" <<'PY' || revenir "copie ou controle de la base"
import os, sqlite3, sys
src_chemin, dst_chemin = sys.argv[1], sys.argv[2]
if os.path.exists(dst_chemin):
    os.remove(dst_chemin)
src = sqlite3.connect(f"file:{src_chemin}?mode=ro", uri=True)
dst = sqlite3.connect(dst_chemin)
src.backup(dst)
assert dst.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "integrity_check"
noms = [r[0] for r in src.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
for n in noms:
    a = src.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
    b = dst.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
    assert a == b, f"table {n} : {a} lignes dans la source, {b} dans la copie"
print(f"copie controlee : {len(noms)} tables, integrite ok")
dst.close(); src.close()
PY
    chown "$UTILISATEUR:$GROUPE" "$DEST_ETAT/vera_state.db"
    chmod 600 "$DEST_ETAT/vera_state.db"
    mv "$ANCIENNE_BASE" "$DOSSIER_AVANT/vera_state.db.avant"
    for f in "$ANCIENNE_BASE-journal" "$ANCIENNE_BASE-wal" "$ANCIENNE_BASE-shm"; do
        [ -e "$f" ] && mv "$f" "$DOSSIER_AVANT/" || true
    done
fi

# --- 7. L'unite -------------------------------------------------------------
etape "7. Nouvelle unite"
install -m 0644 "$MODELE_UNITE" "$DOSSIER_UNITES/$UNITE"
systemctl daemon-reload

# --- 8. La sauvegarde nocturne ----------------------------------------------
etape "8. Crontab de la sauvegarde"
ancienne_ligne="VERA_DB_PATH=$ANCIENNE_BASE"
nouvelle_ligne="VERA_DB_PATH=$DEST_ETAT/vera_state.db VERA_PYTHON=$DEST_VENV/bin/python3"
if grep -qF "$ancienne_ligne" "$DOSSIER_AVANT/crontab.avant"; then
    # Un VERA_PYTHON deja present (PROCEDURE_REPRISE_VERA.md, partie 2, etape 7, en pose un)
    # est retire : il pointerait sur l'ancien venv.
    sed -E "s#VERA_PYTHON=[^ ]+ ##g; s#$ancienne_ligne#$nouvelle_ligne#" "$DOSSIER_AVANT/crontab.avant" | crontab -
    echo "crontab mise a jour : la sauvegarde lit maintenant $DEST_ETAT/vera_state.db"
else
    echo "ATTENTION : aucune ligne « $ancienne_ligne » dans la crontab. La sauvegarde"
    echo "nocturne ne trouvera plus la base : mettre VERA_DB_PATH=$DEST_ETAT/vera_state.db a la main."
fi

# --- 9. Demarrage et controles ----------------------------------------------
etape "9. Demarrage"
systemctl start "$UNITE" || revenir "systemctl start a echoue"
sain=0
for _ in $(seq 1 "$ATTENTE"); do
    if curl -sf "$API/api/health" >/dev/null 2>&1; then sain=1; break; fi
    sleep 1
done
if [ "$sain" != "1" ]; then
    journalctl -u "$UNITE" -n 30 --no-pager 2>/dev/null || true
    revenir "le service ne repond pas sur $API/api/health apres ${ATTENTE} s"
fi
PID=$(systemctl show "$UNITE" -p MainPID --value)
proprietaire=$(ps -o user= -p "$PID" 2>/dev/null | tr -d ' ')
[ "$proprietaire" = "$UTILISATEUR" ] \
    || revenir "le processus $PID tourne sous « $proprietaire », pas sous $UTILISATEUR"
echo "service en bonne sante, processus $PID sous $UTILISATEUR."

# --- 10. Verificateur depuis le nouveau dossier -----------------------------
etape "10. Verificateur de deploiement"
MODELE_UNITE_FICHIER="$MODELE_UNITE" bash "$DEST_CODE/infra/verifier_deploiement.sh" | tail -25 || true

cat <<EOF

MIGRATION TERMINEE.
 - Ancienne base, ancienne unite, crontab d'origine : $DOSSIER_AVANT (rien n'est supprime).
 - Retour arriere possible : bash infra/annuler_migration_utilisateur_dedie.sh
 - A faire quelques jours plus tard, une fois sur : supprimer $DOSSIER_AVANT/vera_state.db.avant
   (il ne contient que l'historique) et l'ancien venv $ANCIEN_VENV.
 - Note du durcissement : systemd-analyze security vera-consultation | tail -2
EOF
