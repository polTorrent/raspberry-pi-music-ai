#!/bin/bash
# pi-services.sh — Manage Docker containers and Tailscale
# Usage: bash pi-services.sh [status|restart|navidrome|slskd|tailscale]

set -uo pipefail
ACTION="${1:-status}"

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/navidrome}"

status() {
  echo "=== SERVICE STATUS ==="
  echo ""

  echo "--- Docker containers ---"
  docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo "Docker not available"
  echo ""

  echo "--- Tailscale ---"
  if tailscale status >/dev/null 2>&1; then
    echo "✅ Tailscale connected"
    tailscale status 2>&1 | head -3
  else
    echo "❌ Tailscale not connected"
  fi
  echo ""

  echo "--- Navidrome ---"
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:4533/ 2>/dev/null | grep -q "200\|302\|401"; then
    echo "✅ Navidrome responding on :4533"
  else
    echo "❌ Navidrome not responding on :4533"
  fi
  echo ""

  echo "--- slskd ---"
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:5030/ 2>/dev/null | grep -q "200\|302\|401"; then
    echo "✅ slskd responding on :5030"
  else
    echo "❌ slskd not responding on :5030"
  fi
}

restart_all() {
  echo "Restarting all services..."
  cd "$COMPOSE_DIR" && docker compose restart
  sudo systemctl restart tailscaled
  echo "Done. Check status with: bash pi-services.sh status"
}

restart_navidrome() {
  echo "Restarting Navidrome..."
  cd "$COMPOSE_DIR" && docker compose restart navidrome
  echo "Done."
}

restart_slskd() {
  echo "Restarting slskd..."
  cd "$COMPOSE_DIR" && docker compose restart slskd
  echo "Done."
}

restart_tailscale() {
  echo "Restarting Tailscale..."
  sudo systemctl restart tailscaled
  sleep 2
  tailscale up 2>&1 || true
  echo "Done."
}

case "$ACTION" in
  status)    status ;;
  restart)   restart_all ;;
  navidrome) restart_navidrome ;;
  slskd)     restart_slskd ;;
  tailscale) restart_tailscale ;;
  *)         echo "Usage: bash pi-services.sh [status|restart|navidrome|slskd|tailscale]"; exit 1 ;;
esac