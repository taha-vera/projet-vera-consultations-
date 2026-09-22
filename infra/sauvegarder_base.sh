#!/usr/bin/env bash
# sauvegarder_base.sh - Sauvegarde chiffree et journalisee de vera_state.db.
#
# POURQUOI CE SCRIPT EXISTE : aucune sauvegarde de la base n'existait hors du
# serveur Hetzner. Un incident sur ce serveur (disque perdu, panne materielle,
# suppression accidentelle) effacerait toute consultation en cours ou deja
# publiee, meme avec VERA_DB_KEY en lieu sur -- cette cle dechiffre une cle
# RSA, elle ne remplace pas la base elle-meme. Constat du 21/09/2026, en
# fermant le point ouvert par PROCEDURE_REPRISE_VERA.md.
#
# CE QUE CE SCRIPT FAIT : une copie coherente de la base (via l'API de
# sauvegarde du module sqlite3 de Python, pas une copie de fichier brute --
# une copie brute pendant une ecriture produirait un fichier corrompu),
# chiffree avec VERA_BACKUP_KEY, deposee dans /root/sauvegardes_vera/, avec
# rotation sur 7 jours.
#
# Passe par Python plutot que par l'outil `sqlite3` en ligne de commande :
# ce dernier n'est pas installe par defaut et n'est utilise nulle part
# ailleurs dans ce projet (verifie le 22/09/2026, avant d'ajouter une
# dependance systeme qui n'existait pas). Le module sqlite3 de Python fait
# la meme sauvegarde a chaud, sans rien installer de plus.
#
# CE QUE CE SCRIPT NE FAIT PAS : il n'envoie rien hors de ce serveur. Une
# sauvegarde qui reste sur la meme machine que l'original ne protege pas
# contre la perte du serveur lui-meme -- seulement contre une corruption ou
# une erreur de manipulation locale. Voir la note de bas de fichier sur la
# recuperation periodique.

set -euo pipefail

BASE_SOURCE="${VERA_DB_PATH:-/root/vera_state.db}"
DOSSIER_SAUVEGARDES="/root/sauvegardes_vera"
RETENTION_JOURS=7
CLE_SAUVEGARDE_FICHIER="/root/.vera_backup_key"
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

if [ ! -x "$PYTHON" ]; then
    log "ERREUR : interpreteur Python introuvable a $PYTHON."
    log "Ajuster VERA_PYTHON si le venv est ailleurs (voir PROCEDURE_REPRISE_VERA.md)."
    exit 1
fi

mkdir -p "$DOSSIER_SAUVEGARDES"
chmod 700 "$DOSSIER_SAUVEGARDES"

copie_temporaire="$(mktemp /tmp/vera_backup_XXXXXX.db)"
trap 'rm -f "$copie_temporaire"' EXIT

# Copie coherente a chaud : le module sqlite3 de Python gere le
# verrouillage lui-meme, contrairement a `cp` sur un fichier en cours
# d'ecriture.
"$PYTHON" -c "
import sqlite3, sys
src = sqlite3.connect('$BASE_SOURCE')
dst = sqlite3.connect('$copie_temporaire')
with dst:
    src.backup(dst)
dst.close()
src.close()
"

fichier_chiffre="$DOSSIER_SAUVEGARDES/vera_state_${horodatage}.db.enc"
openssl enc -aes-256-cbc -pbkdf2 -salt \
    -pass "file:$CLE_SAUVEGARDE_FICHIER" \
    -in "$copie_temporaire" \
    -out "$fichier_chiffre"

taille=$(stat -c%s "$fichier_chiffre")
log "Sauvegarde ecrite : $fichier_chiffre ($taille octets)"

# Rotation : ne garder que les fichiers de moins de RETENTION_JOURS jours.
find "$DOSSIER_SAUVEGARDES" -name 'vera_state_*.db.enc' -mtime "+$RETENTION_JOURS" -print -delete \
    | while read -r f; do log "Supprime (retention $RETENTION_JOURS j) : $f"; done

log "OK. $(ls "$DOSSIER_SAUVEGARDES"/vera_state_*.db.enc 2>/dev/null | wc -l) sauvegarde(s) conservee(s)."

# RESTAURATION (a la main, en cas B de PROCEDURE_REPRISE_VERA.md) :
#   openssl enc -d -aes-256-cbc -pbkdf2 \
#     -pass "file:/root/.vera_backup_key" \
#     -in vera_state_<date>.db.enc -out vera_state.db
#
# RECUPERATION HORS DU SERVEUR (a faire toi-meme, periodiquement -- ce
# script ne l'automatise pas) : depuis ton telephone, en Termux,
#   scp root@<ip-serveur>:/root/sauvegardes_vera/vera_state_*.db.enc .
# Une sauvegarde qui ne quitte jamais ce serveur ne protege pas contre la
# perte de ce serveur precisement -- seulement contre une corruption locale.
