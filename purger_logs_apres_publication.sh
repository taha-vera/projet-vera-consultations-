#!/bin/bash
# Purge les logs applicatifs apres cloture et diffusion d'une consultation.
# A executer manuellement une fois les resultats publies et communiques.

# Le journal est sous /var/log/vera depuis que le service tourne sous un compte
# dedie (N7). Sur un serveur pas encore migre, il est encore a l'ancien endroit.
LOG_FILE="${VERA_LOG_FILE:-/var/log/vera/consultation.log}"
if [ ! -f "$LOG_FILE" ] && [ -z "${VERA_LOG_FILE:-}" ] && [ -f /root/consultation.log ]; then
    LOG_FILE="/root/consultation.log"
fi

if [ -f "$LOG_FILE" ]; then
    TAILLE_AVANT=$(wc -l < "$LOG_FILE")
    echo "Purge de $LOG_FILE ($TAILLE_AVANT lignes) -- $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    > "$LOG_FILE"
    echo "Purge effectuee. Consultation cloturee, resultats deja diffuses."
else
    echo "Aucun fichier de log trouve a $LOG_FILE"
fi
