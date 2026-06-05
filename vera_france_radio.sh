#!/bin/bash
# VERA — Multi-radio France capture
# Captures all Radio France streams overnight

STREAMS=(
    "fip|http://icecast.radiofrance.fr/fip-hifi.aac"
    "france-inter|http://icecast.radiofrance.fr/franceinter-hifi.aac"
    "france-culture|http://icecast.radiofrance.fr/franceculture-hifi.aac"
    "france-musique|http://icecast.radiofrance.fr/francemusique-hifi.aac"
    "france-info|http://icecast.radiofrance.fr/franceinfo-hifi.aac"
    "mouv|http://icecast.radiofrance.fr/mouv-hifi.aac"
    "france-bleu|http://icecast.radiofrance.fr/francebleu-hifi.aac"
)

DURATION=28800  # 8 heures
OUTPUT_DIR="/tmp/vera_radio"
mkdir -p $OUTPUT_DIR

echo "===================================================="
echo "VERA — Capture Radio France — $(date)"
echo "Durée : 8 heures par station"
echo "===================================================="

for entry in "${STREAMS[@]}"; do
    name="${entry%%|*}"
    url="${entry##*|}"
    echo "[START] $name"
    ffmpeg -i "$url" -t $DURATION -ar 44100 -ac 1 -f f32le \
        "$OUTPUT_DIR/${name}.raw" -loglevel quiet &
    echo "  PID $! — $name en cours"
done

echo ""
echo "7 stations capturées en parallèle."
echo "Résultats dans $OUTPUT_DIR"
echo "Laisse tourner toute la nuit."
wait
echo "===================================================="
echo "VERA — Capture terminée — $(date)"
echo "===================================================="
