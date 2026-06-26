#!/bin/bash
# pi-updates.sh — Check and apply system updates
# Usage: bash pi-updates.sh [check|apply]

set -uo pipefail
ACTION="${1:-check}"

check() {
  echo "=== PENDING UPDATES ==="
  UPDATES=$(apt list --upgradable 2>/dev/null | grep -v "^Listing")
  COUNT=$(echo "$UPDATES" | grep -c . 2>/dev/null || echo 0)

  if [ "$COUNT" -eq 0 ] 2>/dev/null; then
    echo "✅ System is up to date"
    return
  fi

  echo "$COUNT packages upgradable:"
  echo ""
  echo "$UPDATES"
  echo ""

  # Highlight security updates
  SECURITY=$(echo "$UPDATES" | grep -i security 2>/dev/null)
  if [ -n "$SECURITY" ]; then
    echo "⚠️  Security updates available:"
    echo "$SECURITY"
  fi
}

apply() {
  echo "=== APPLYING UPDATES ==="
  sudo apt update
  sudo apt full-upgrade -y
  sudo apt autoremove -y
  echo ""
  echo "✅ Updates applied"
  echo "A reboot may be needed if kernel was updated."
}

case "$ACTION" in
  check) check ;;
  apply) apply ;;
  *)     echo "Usage: bash pi-updates.sh [check|apply]"; exit 1 ;;
esac