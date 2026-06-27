#!/bin/bash
# Wrapper per processar descàrregues automàticament
# Source de l'API key de slskd + execució de process-downloads.py

set -e

SCRIPT_DIR="/home/pi/.picoclaw/workspace/skills/music-library/scripts"
DL_DIR="/mnt/musica/_descarregues"
LOG_FILE="/home/pi/.picoclaw/workspace/logs/process-downloads.log"

# Crear dir de logs si no existeix
mkdir -p /home/pi/.picoclaw/workspace/logs

# Comprovar si hi ha descàrregues pendents
if [ ! -d "$DL_DIR" ]; then
    echo "$(date '+%Y-%m-%d %H:%M') — No existeix $DL_DIR" >> "$LOG_FILE"
    exit 0
fi

PENDING=$(find "$DL_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
if [ "$PENDING" -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M') — Sense descàrregues pendents" >> "$LOG_FILE"
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M') — Processant $PENDING descàrregues..." >> "$LOG_FILE"

# Source API key si existeix
if [ -f "$SCRIPT_DIR/env.sh" ]; then
    source "$SCRIPT_DIR/env.sh"
fi

# Executar process-downloads.py en mode confirm
cd /home/pi/.picoclaw/workspace
python3 "$SCRIPT_DIR/process-downloads.py" --confirm >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M') — Processat completat" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"