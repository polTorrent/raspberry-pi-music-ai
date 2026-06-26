#!/bin/bash
# library-health.sh — Music library diagnostic report (READ-ONLY)
# Usage: bash library-health.sh
# Does NOT modify or delete anything.

set -uo pipefail

MUSIC_DIR="${MUSIC_DIR:-/mnt/music}"

echo "=== MUSIC LIBRARY HEALTH REPORT ==="
echo "Date: $(date '+%Y-%m-%d %H:%M')"
echo "Path: $MUSIC_DIR"
echo ""

if [ ! -d "$MUSIC_DIR" ]; then
  echo "ERROR: Music directory not found: $MUSIC_DIR"
  exit 1
fi

# 1. Overview
echo "=== 1. OVERVIEW ==="
TOTAL_DIRS=$(find "$MUSIC_DIR" -maxdepth 1 -type d | wc -l)
TOTAL_FILES=$(find "$MUSIC_DIR" -type f 2>/dev/null | wc -l)
AUDIO_FILES=$(find "$MUSIC_DIR" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' -o -iname '*.opus' -o -iname '*.wav' \) 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$MUSIC_DIR" 2>/dev/null | cut -f1)
echo "Root directories: $TOTAL_DIRS"
echo "Total files: $TOTAL_FILES"
echo "Audio files: $AUDIO_FILES"
echo "Total size: $TOTAL_SIZE"
echo ""

# 2. Format distribution
echo "=== 2. FORMAT DISTRIBUTION ==="
for ext in flac mp3 ogg m4a opus wav; do
  count=$(find "$MUSIC_DIR" -type f -iname "*.$ext" 2>/dev/null | wc -l)
  [ "$count" -gt 0 ] && echo "  .$ext: $count files"
done
echo ""

# 3. Junk files
echo "=== 3. JUNK FILES ==="
JUNK=$(find "$MUSIC_DIR" -type f \( -iname '.DS_Store' -o -iname 'Thumbs.db' -o -iname 'desktop.ini' \) 2>/dev/null | wc -l)
MACOSX=$(find "$MUSIC_DIR" -type d -name '__MACOSX' 2>/dev/null | wc -l)
echo "  .DS_Store / Thumbs.db / desktop.ini: $JUNK"
echo "  __MACOSX directories: $MACOSX"
echo ""

# 4. Duplicate filenames
echo "=== 4. DUPLICATE FILENAMES ==="
find "$MUSIC_DIR" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' \) -printf '%f\n' 2>/dev/null | sort | uniq -d > /tmp/dup_names.txt
DUP_COUNT=$(wc -l < /tmp/dup_names.txt)
echo "  Duplicate filenames: $DUP_COUNT"
echo ""

# 5. Empty directories
echo "=== 5. EMPTY DIRECTORIES ==="
EMPTY_DIRS=$(find "$MUSIC_DIR" -maxdepth 3 -type d -empty 2>/dev/null | wc -l)
echo "  Empty directories: $EMPTY_DIRS"
echo ""

# 6. Incomplete albums (1-2 audio files)
echo "=== 6. INCOMPLETE ALBUMS (1-2 files) ==="
INCOMPLETE=0
while IFS= read -r dir; do
  audio_count=$(find "$dir" -maxdepth 1 -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' \) 2>/dev/null | wc -l)
  if [ "$audio_count" -ge 1 ] && [ "$audio_count" -le 2 ]; then
    echo "  [$audio_count files] $dir"
    INCOMPLETE=$((INCOMPLETE + 1))
  fi
done < <(find "$MUSIC_DIR" -mindepth 2 -maxdepth 3 -type d 2>/dev/null)
echo "  Total incomplete: $INCOMPLETE"
echo ""

# 7. Cover art coverage
echo "=== 7. COVER ART ==="
COVER_COUNT=$(find "$MUSIC_DIR" -type f \( -iname 'cover.*' -o -iname 'folder.*' -o -iname 'album.*' -o -iname 'front.*' \) 2>/dev/null | wc -l)
ALBUM_DIRS=$(find "$MUSIC_DIR" -mindepth 2 -maxdepth 3 -type d 2>/dev/null | wc -l)
echo "  Album directories: $ALBUM_DIRS"
echo "  Covers found: $COVER_COUNT"
if [ "$ALBUM_DIRS" -gt 0 ]; then
  PCT=$((COVER_COUNT * 100 / ALBUM_DIRS))
  echo "  Coverage: ~${PCT}%"
fi
echo ""

# 8. Suspicious files (< 10 KB)
echo "=== 8. SUSPICIOUS FILES (< 10 KB) ==="
SUSPICIOUS=$(find "$MUSIC_DIR" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' \) -size -10k 2>/dev/null)
SUSPICIOUS_COUNT=$(echo "$SUSPICIOUS" | grep -c . 2>/dev/null || echo 0)
echo "  Audio files < 10 KB: $SUSPICIOUS_COUNT"
echo ""

# 9. Downloads folder
echo "=== 9. DOWNLOADS STAGING ==="
DOWNLOADS="$MUSIC_DIR/_downloads"
if [ -d "$DOWNLOADS" ]; then
  DL_COUNT=$(find "$DOWNLOADS" -type f 2>/dev/null | wc -l)
  DL_SIZE=$(du -sh "$DOWNLOADS" 2>/dev/null | cut -f1)
  echo "  Files: $DL_COUNT"
  echo "  Size: $DL_SIZE"
  echo "  Subdirectories:"
  find "$DOWNLOADS" -maxdepth 1 -type d 2>/dev/null | tail -15
fi
echo ""

echo "=== END OF REPORT ==="
echo "No files were modified or deleted."