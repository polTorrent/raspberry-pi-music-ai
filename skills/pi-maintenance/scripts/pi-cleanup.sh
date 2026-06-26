#!/bin/bash
# pi-cleanup.sh — Clean temporary files and old cache
# Usage: bash pi-cleanup.sh [--dry-run]

set -uo pipefail
DRY=false
[ "$1" = "--dry-run" 2>/dev/null ] && DRY=true

echo "=== SYSTEM CLEANUP ==="
if $DRY; then echo "⚠️ DRY RUN — nothing will be deleted"; fi
echo ""

# 1. APT cache
echo "📦 APT cache..."
APT_BEFORE=$(du -sh /var/cache/apt/archives 2>/dev/null | awk '{print $1}')
echo "   Before: $APT_BEFORE"
if $DRY; then
  echo "   [DRY-RUN] apt-get clean would run"
else
  sudo apt-get clean 2>/dev/null
  echo "   ✓ Cleaned"
fi
echo ""

# 2. Unused packages
echo "📦 Unused packages..."
if $DRY; then
  COUNT=$(apt list --autoremovable 2>/dev/null | grep -c autoremovable)
  echo "   [DRY-RUN] $COUNT packages would be removed"
else
  sudo apt-get autoremove -y 2>/dev/null
  echo "   ✓ Removed"
fi
echo ""

# 3. Journal logs older than 7 days
echo "📦 Journal logs..."
if $DRY; then
  echo "   [DRY-RUN] journalctl --vacuum-time=7d would run"
else
  sudo journalctl --vacuum-time=7d 2>/dev/null
  echo "   ✓ Cleaned"
fi
echo ""

# 4. /tmp files older than 7 days
echo "📦 /tmp old files..."
if $DRY; then
  echo "   [DRY-RUN] Files older than 7 days in /tmp would be deleted"
else
  find /tmp -type f -mtime +7 -delete 2>/dev/null
  echo "   ✓ Cleaned"
fi
echo ""

# 5. Docker dangling images and build cache
echo "📦 Docker cleanup..."
if $DRY; then
  echo "   [DRY-RUN] docker system prune would run"
else
  docker system prune -f 2>/dev/null
  echo "   ✓ Cleaned"
fi
echo ""

# 6. Old slskd downloads (30+ days)
DOWNLOADS="${DOWNLOADS_DIR:-/mnt/music/_downloads}"
if [ -d "$DOWNLOADS" ]; then
  echo "📦 Old downloads (30+ days)..."
  if $DRY; then
    COUNT=$(find "$DOWNLOADS" -maxdepth 1 -mindepth 1 -mtime +30 2>/dev/null | wc -l)
    echo "   [DRY-RUN] $COUNT items would be deleted"
  else
    find "$DOWNLOADS" -maxdepth 1 -mindepth 1 -mtime +30 -exec rm -rf {} + 2>/dev/null
    echo "   ✓ Cleaned"
  fi
fi
echo ""

echo "=== CLEANUP COMPLETE ==="