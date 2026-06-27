#!/bin/bash
# Resum setmanal de memòria — diumenge 9h

RAM_AVAIL_KB=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
RAM_TOTAL_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
SWAP_TOTAL_KB=$(awk '/SwapTotal/ {print $2}' /proc/meminfo)
SWAP_FREE_KB=$(awk '/SwapFree/ {print $2}' /proc/meminfo)
SWAP_USED_MB=$(( (SWAP_TOTAL_KB - SWAP_FREE_KB) / 1024 ))
RAM_AVAIL_MB=$((RAM_AVAIL_KB / 1024))
RAM_TOTAL_MB=$((RAM_TOTAL_KB / 1024))
SWAPPINESS=$(cat /proc/sys/vm/swappiness)

# Top consumers
TOP_MEM=$(ps aux --sort=-%mem | head -6 | tail -5 | awk '{printf "  %s: %s MB (%s%%)\n", $11, int($6/1024), $4}')

# Docker stats
DOCKER_STATS=$(docker stats --no-stream --format "  {{.Name}}: {{.MemUsage}} ({{.MemPerc}})" 2>/dev/null)

cat << EOF
📊 Resum setmanal de memòria — $(date '+%d/%m/%Y')

RAM: ${RAM_AVAIL_MB} MB disponibles de ${RAM_TOTAL_MB} MB
Swap: ${SWAP_USED_MB} MB usats de 1024 MB
Swappiness: ${SWAPPINESS}

Top consumidors de RAM:
${TOP_MEM}

Docker:
${DOCKER_STATS}

⚠️ Recordatori: Els límits de memòria Docker (mem_limit: 256m) NO estan actius perquè el kernel 32-bit no té cgroups de memòria activats. slskd pot fugarse de memòria. Si veus RAM baixa, reinicia'l amb: docker restart navidrome-slskd-1
EOF