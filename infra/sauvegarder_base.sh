#!/usr/bin/env bash
# sauvegarder_base.sh - Sauvegarde chiffree de l'historique des consultations.
#
# VERSION 2 (22/09/2026). La version 1 sauvegardait toute la base --
# compteurs, jetons, cle RSA -- chaque nuit, et en gardait 7 (en realite 8,
# voir plus bas). Un audit cible a montre que c'etait exactement la fuite
# que le projet a fermee en abandonnant journal_mode=WAL, a l'echelle du
# jour au lieu de la milliseconde : deux etats consecutifs de
# `jetons_autorisation` (ou `tokens_consommes`) et de `compteurs_votes`,
# lus ensemble, reconstituent quel jeton correspond a quelle reponse --
# `vera_persistance.py`, commentaire sur l'abandon du WAL, et section sur
# `jetons_autorisation` comme "cinquieme trace de participation". Pire :
# meme avec UNE seule sauvegarde gardee, la base vivante a cote sur le
# meme disque formait deja la paire comparable. Reduire la retention ne
# fermait rien.
#
# CE QUE CETTE VERSION SAUVEGARDE : uniquement la table
# `historique_consultations` (nom de groupe + horodatage de cloture).
# C'est la seule table de vera_persistance.py qui n'est PAS effacee par
# `effacer_etat_consultation()` -- elle existe pour faire respecter la
# regle des 4 consultations / 12 mois, pas pour reprendre un vote en
# cours. Elle ne contient jamais de compteur, de jeton ni de cle : rien
# qui se laisse mettre en correspondance avec un vote individuel.
#
# CE QUE CA VEUT DIRE EN PRATIQUE : une consultation active ne survit
# PAS a la perte du serveur. Ce script ne tente plus de le permettre --
# PROCEDURE_REPRISE_VERA.md le disait deja ouvertement avant cette
# version. Ce qui est protege, c'est la regle des 4/12 mois et rien
# d'autre.

set -euo pipefail

BASE_SOURCE="${VERA_DB_PATH:-/root/vera_state.db}"
# Les deux chemins peuvent etre surcharges (tests/test_sauvegarde_chemins_speciaux.py
# lance ce script dans un dossier jetable) ; sans variable, valeurs de production.
DOSSIER_SAUVEGARDES="${VERA_DOSSIER_SAUVEGARDES:-/root/sauvegardes_vera}"
RETENTION_JOURS=7
CLE_SAUVEGARDE_FICHIER="${VERA_CLE_SAUVEGARDE_FICHIER:-/root/.vera_backup_key}"
PYTHON="${VERA_PYTHON:-/root/vera_blind_sig/.venv/bin/python3}"

horodatage="$(date -u +%Y%m%dT%H%M%SZ)"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

if [ ! -f "$BASE_SOURCE" ]; then
    log "ERREUR : base introuvable a $BASE_SOURCE. Rien a sauvegarder."
    exit 1
fi

if [ ! -f "$CLE_SAUVEGARDE_FICHIER" ]; then
    log "ERREUR : $CLE_SAUVEGARDE_FICHIER absent. Generer une cle une fois avec :"
    log "  openssl rand -hex 32 > $CLE_SAUVEGARDE_FICHIER && chmod 600 $CLE_SAUVEGARDE_FICHIER"
    log "Cette valeur doit AUSSI aller dans l'enveloppe de sequestre, a cote de VERA_DB_KEY."
    exit 1
fi

# PERMISSIONS DU FICHIER DE CLE, PAS SEULEMENT SA PRESENCE.
#
# Un fichier de cle lisible par d'autres que root sur ce serveur mono-
# utilisateur n'a pas de sens legitime -- releve par un audit cible le
# 22/09/2026, qui notait que seule l'existence etait verifiee.
permissions=$(stat -c '%a' "$CLE_SAUVEGARDE_FICHIER")
if [ "$permissions" != "600" ]; then
    log "ERREUR : $CLE_SAUVEGARDE_FICHIER a les permissions $permissions, 600 attendu."
    log "  chmod 600 $CLE_SAUVEGARDE_FICHIER"
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    log "ERREUR : interpreteur Python introuvable a $PYTHON."
    log "Ajuster VERA_PYTHON si le venv est ailleurs (voir PROCEDURE_REPRISE_VERA.md)."
    exit 1
fi

mkdir -p "$DOSSIER_SAUVEGARDES"
chmod 700 "$DOSSIER_SAUVEGARDES"

copie_temporaire="$(mktemp /tmp/vera_backup_XXXXXX.db)"
trap 'shred -u "$copie_temporaire" 2>/dev/null || rm -f "$copie_temporaire"' EXIT

# Export d'UNE SEULE table, pas une copie de la base entiere. Pas
# d'API .backup() ici : elle copierait tout, y compris ce qu'on a
# precisement decide de ne plus jamais sortir de la base vivante.
#
# Les deux chemins passent par sys.argv, JAMAIS interpoles dans le source Python
# (audit du 20/10/2026, A11) : un VERA_DB_PATH contenant une apostrophe aurait
# cassé le script, ou pire, injecté du code. Le delimiteur 'PY' entre guillemets
# empeche l'interpolation par le shell.
"$PYTHON" - "$BASE_SOURCE" "$copie_temporaire" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
dst.execute(
    'CREATE TABLE historique_consultations '
    '(groupe TEXT NOT NULL, close_unix REAL NOT NULL, '
    'PRIMARY KEY (groupe, close_unix))'
)
lignes = src.execute('SELECT groupe, close_unix FROM historique_consultations').fetchall()
dst.executemany(
    'INSERT INTO historique_consultations (groupe, close_unix) VALUES (?, ?)',
    lignes,
)
dst.commit()
dst.close()
src.close()
PY

# ECRITURE ATOMIQUE : chiffrer vers un fichier .tmp, verifier qu'il se
# dechiffre, puis renommer seulement en cas de succes. Une interruption
# en cours d'ecriture (disque plein, processus tue) laisse alors un
# .tmp orphelin au pire, jamais un .enc final tronque compte dans la
# retention comme s'il etait bon -- releve par le meme audit.
fichier_final="$DOSSIER_SAUVEGARDES/vera_historique_${horodatage}.db.enc"
fichier_tmp="${fichier_final}.tmp"
trap 'shred -u "$copie_temporaire" 2>/dev/null || rm -f "$copie_temporaire"; rm -f "$fichier_tmp"' EXIT

openssl enc -aes-256-cbc -pbkdf2 -salt \
    -pass "file:$CLE_SAUVEGARDE_FICHIER" \
    -in "$copie_temporaire" \
    -out "$fichier_tmp"

if ! openssl enc -d -aes-256-cbc -pbkdf2 \
        -pass "file:$CLE_SAUVEGARDE_FICHIER" \
        -in "$fichier_tmp" | "$PYTHON" -c "
import sqlite3, sys, tempfile
data = sys.stdin.buffer.read()
with tempfile.NamedTemporaryFile(suffix='.db') as f:
    f.write(data)
    f.flush()
    sqlite3.connect(f.name).execute('SELECT COUNT(*) FROM historique_consultations')
"; then
    log "ERREUR : le fichier chiffre vient d'etre ecrit mais ne se relit pas correctement."
    log "Rien n'a ete conserve pour cette execution -- pas de sauvegarde silencieusement cassee."
    exit 1
fi

mv "$fichier_tmp" "$fichier_final"
taille=$(stat -c%s "$fichier_final")
log "Sauvegarde ecrite et verifiee : $fichier_final ($taille octets)"

# Rotation : ne garder que les fichiers de moins de RETENTION_JOURS jours.
# NOTE : `find -mtime +N` retient en pratique jusqu'a N+1 jours (arrondi
# de find sur les jours entiers, verifie le 22/09/2026) -- sans
# consequence ici, cette table ne contient plus rien de sensible.
find "$DOSSIER_SAUVEGARDES" -name 'vera_historique_*.db.enc' -mtime "+$RETENTION_JOURS" -print -delete \
    | while read -r f; do log "Supprime (retention $RETENTION_JOURS j) : $f"; done

log "OK. $(ls "$DOSSIER_SAUVEGARDES"/vera_historique_*.db.enc 2>/dev/null | wc -l) sauvegarde(s) conservee(s)."

# RESTAURATION :
#   openssl enc -d -aes-256-cbc -pbkdf2 \
#     -pass "file:/root/.vera_backup_key" \
#     -in vera_historique_<date>.db.enc -out historique_restaure.db
#
# Ceci restaure UNIQUEMENT le registre des 4 consultations / 12 mois, pas
# une consultation active -- voir l'en-tete de ce fichier. Une base
# neuve (cas B de PROCEDURE_REPRISE_VERA.md) peut reimporter cette table
# directement pour ne pas perdre la regle de frequence.
