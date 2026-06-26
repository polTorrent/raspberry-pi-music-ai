#!/bin/bash
# clean-junk.sh — Remove junk files from music library
# Usage: bash clean-junk.sh [--dry-run|--confirm]
# Default is dry-run. Must use --confirm to actually delete.

set -uo pipefail

MUSIC_DIR="${MUSIC_DIR:-/mnt/music}"
CONFIRM=false
[ "$1" = "--confirm" 2>/dev/null ] && CONFIRM=true

echo "=== JUNK FILE CLEANUP ==="
if ! $CONFIRM; then
  echo "⚠️ DRY RUN — no files will be deleted. Use --confirm to actually delete."
fi
echo "Path: $MUSIC_DIR"
echo ""

if [ ! -d "$MUSIC_DIR" ]; then
  echo "ERROR: Music directory not found: $MUSIC_DIR"
  exit 1
fi

# 1. .DS_Store files
echo "--- .DS_Store ---"
COUNT=$(find "$MUSIC_DIR" -type f -iname '.DS_Store' 2>/dev/null | wc -l)
echo "Found: $COUNT"
if $CONFIRM && [ "$COUNT" -gt 0 ]; then
  find "$MUSIC_DIR" -type f -iname '.DS_Store' -delete 2>/dev/null
  echo "✓ Deleted"
fi
echo ""

# 2. __MACOSX directories
echo "--- __MACOSX ---"
COUNT=$(find "$MUSIC_DIR" -type d -name '__MACOSX' 2>/dev/null | wc -l)
echo "Found: $COUNT"
if $CONFIRM && [ "$COUNT" -gt 0 ]; then
  find "$MUSIC_DIR" -type d -name '__MACOSX' -exec rm -rf {} + 2>/dev/null
  echo "✓ Deleted"
fi
echo ""

# 3. Thumbs.db
echo "--- Thumbs.db ---"
COUNT=$(find "$MUSIC_DIR" -type f -iname 'Thumbs.db' 2>/dev/null | wc -l)
echo "Found: $COUNT"
if $CONFIRM && [ "$COUNT" -gt 0 ]; then
  find "$MUSIC_DIR" -type f -iname 'Thumbs.db' -delete 2>/dev/null
  echo "✓ Deleted"
fi
echo ""

# 4. desktop.ini
echo "--- desktop.ini ---"
COUNT=$(find "$MUSIC_DIR" -type f -iname 'desktop.ini' 2>/dev/null | wc -l)
echo "Found: $COUNT"
if $CONFIRM && [ "$COUNT" -gt 0 ]; then
  find "$MUSIC_DIR" -type f -iname 'desktop.ini' -delete 2>/dev/null
  echo "✓ Deleted"
fi
echo ""

# 5. Empty directories (after cleanup)
echo "--- Empty directories ---"
if $CONFIRM; then
  find "$MUSIC_DIR" -type d -empty -delete 2>/dev/null
  echo "✓ Empty directories removed"
else
  COUNT=$(find "$MUSIC_DIR" -maxdepth 4 -type d -empty 2>/dev/null | wc -l)
  echo "Found: $COUNT (would be deleted with --confirm)"
fi
echo ""

echo "=== CLEANUP COMPLETE ==="
if ! $CONFIRM; then
  echo "This was a dry run. Run with --confirm to actually delete files."
fi