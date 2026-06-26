#!/bin/bash
# pi-status.sh — Full system health report
# Usage: bash pi-status.sh [--json]

set -uo pipefail
JSON=false
[ "$1" = "--json" 2>/dev/null ] && JSON=true

if $JSON; then
  echo "{"
  echo "  \"hostname\": \"$(hostname)\","
  echo "  \"uptime\": \"$(uptime -p | sed 's/up //')\","
  TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
  echo "  \"temperature_c\": \"$(echo "scale=1; $TEMP / 1000" | bc 2>/dev/null || echo "N/A")\","
  echo "  \"load\": \"$(cat /proc/loadavg | awk '{print $1, $2, $3}')\","
  echo "  \"ram\": \"$(free -h | grep Mem | awk '{print $2, $3, $4, $7}')\","
  echo "  \"swap\": \"$(free -h | grep Swap | awk '{print $2, $3, $4}')\","
  echo "  \"disk\": ["
  df -h | grep -vE "tmpfs|devtmpfs|overlay" | awk 'NR>1{printf "    {\"mount\": \"%s\", \"size\": \"%s\", \"used\": \"%s\", \"free\": \"%s\", \"pct\": \"%s\"}%s\n", $6, $2, $3, $4, $5, (NR>1?",":"")}' 2>/dev/null
  echo "  ],"
  echo "  \"docker\": ["
  docker ps --format '{{.Names}}|{{.Status}}' 2>/dev/null | awk -F'|' '{printf "    {\"name\": \"%s\", \"status\": \"%s\"}%s\n", $1, $2, (NR>1?",":"")}'
  echo "  ],"
  echo "  \"tailscale\": \"$(tailscale status 2>&1 | head -1)\""
  echo "}"
  exit 0
fi

echo "=== SYSTEM STATUS ==="
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p)"
echo ""

echo "--- CPU ---"
echo "Model: $(cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2 | xargs)"
echo "Load: $(cat /proc/loadavg)"
echo ""

echo "--- Temperature ---"
TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
if [ -n "$TEMP" ]; then
  TEMP_C=$(echo "scale=1; $TEMP / 1000" | bc 2>/dev/null || echo "$((TEMP/1000))")
  echo "Temperature: ${TEMP_C}°C"
  if [ "$TEMP" -gt 85000 ] 2>/dev/null; then
    echo "⚠️  CRITICAL: Temperature above 85°C!"
  elif [ "$TEMP" -gt 75000 ] 2>/dev/null; then
    echo "⚠️  WARNING: Temperature above 75°C"
  fi
fi
echo ""

echo "--- Memory ---"
free -h
echo ""

echo "--- Disk ---"
df -h | grep -vE "tmpfs|devtmpfs|overlay"
echo ""

echo "--- Docker ---"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo "Docker not running"
echo ""

echo "--- Tailscale ---"
tailscale status 2>&1 | head -5
echo ""

echo "--- Top processes by CPU ---"
ps aux --sort=-%cpu | head -10
echo ""

echo "--- Pending updates ---"
apt list --upgradable 2>/dev/null | grep -c upgradable | xargs -I{} echo "{} packages upgradable"
echo ""

echo "=== END ==="