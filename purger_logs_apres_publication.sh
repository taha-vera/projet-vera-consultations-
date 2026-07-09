#!/bin/bash
# Purge les logs applicatifs apres cloture et diffusion d'une consultation.
# A executer manuellement une fois les resultats publies et communiques.

LOG_FILE="/root/consultation.log"

if [ -f "$LOG_FILE" ]; then
    TAILLE_AVANT=$(wc -l < "$LOG_FILE")
    echo "Purge de $LOG_FILE ($TAILLE_AVANT lignes) -- $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    > "$LOG_FILE"
    echo "Purge effectuee. Consultation cloturee, resultats deja diffuses."
else
    echo "Aucun fichier de log trouve a $LOG_FILE"
fi
