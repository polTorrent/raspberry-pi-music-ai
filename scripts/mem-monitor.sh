#!/bin/bash
# Monitoratge de memòria cada 6h — només alerta si hi ha problema

RAM_AVAIL_KB=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
SWAP_USED_KB=$(awk '/SwapTotal/ {st=$2} /SwapFree/ {sf=$2} END {print st-sf}' /proc/meminfo)

# slskd memory in KB
SLSKD_MEM_KB=$(docker stats --no-stream --format "{{.MemUsage}}" navidrome-slskd-1 2>/dev/null | sed 's/.*(\([0-9.]*[A-Za-z]*\)).*/\1/' | awk '
/MiB/ {print $1 * 1024}
/GiB/ {print $1 * 1048576}
/KiB/ {print $1}
/B/  {print $1 / 1024}
' 2>/dev/null)

RAM_AVAIL_MB=$((RAM_AVAIL_KB / 1024))
SWAP_USED_MB=$((SWAP_USED_KB / 1024))
SLSKD_MEM_MB=$((${SLSKD_MEM_KB:-0} / 1024))

ALERT=false
MSG="⚠️ Alerta de memòria:\n"

if [ "$RAM_AVAIL_MB" -lt 150 ]; then
    ALERT=true
    MSG="${MSG}• RAM disponible: ${RAM_AVAIL_MB} MB (< 150 MB)\n"
fi

if [ "$SWAP_USED_MB" -gt 500 ]; then
    ALERT=true
    MSG="${MSG}• Swap usat: ${SWAP_USED_MB} MB (> 500 MB)\n"
fi

if [ "$SLSKD_MEM_MB" -gt 200 ]; then
    ALERT=true
    MSG="${MSG}• slskd consumint: ${SLSKD_MEM_MB} MB (> 200 MB)\n"
fi

if [ "$ALERT" = true ]; then
    echo -e "$MSG"
    echo "Acció recomanada: docker restart navidrome-slskd-1"
    exit 0
else
    exit 1  # No output, no alert
fi