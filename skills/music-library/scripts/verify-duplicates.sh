#!/bin/bash
# verify-duplicates.sh — MD5-verify suspected duplicates (READ-ONLY)
# Usage: bash verify-duplicates.sh
# Does NOT delete anything. Reports true vs false duplicates.

set -uo pipefail

MUSIC_DIR="${MUSIC_DIR:-/mnt/music}"

echo "=== DUPLICATE VERIFICATION (MD5) ==="
echo ""

# Find duplicate filenames
find "$MUSIC_DIR" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' \) -printf '%f\n' 2>/dev/null | sort | uniq -d > /tmp/dup_names.txt

DUP_COUNT=$(wc -l < /tmp/dup_names.txt)
echo "Duplicate filenames found: $DUP_COUNT"
echo ""

if [ "$DUP_COUNT" -eq 0 ]; then
  echo "✅ No duplicate filenames detected."
  exit 0
fi

TRUE_DUP=0
FALSE_DUP=0
TOTAL_RECOVERABLE="0"

while IFS= read -r name; do
  FILES=$(find "$MUSIC_DIR" -type f -iname "$name" 2>/dev/null)
  FILE_COUNT=$(echo "$FILES" | grep -c . 2>/dev/null || echo 0)

  if [ "$FILE_COUNT" -le 1 ]; then
    continue
  fi

  # Compute MD5 for each file with this name
  declare -A HASHES
  while IFS= read -r f; do
    HASH=$(md5sum "$f" 2>/dev/null | awk '{print $1}')
    HASHES["$HASH"]+="$f\n"
  done <<< "$FILES"

  HASH_COUNT=${#HASHES[@]}
  if [ "$HASH_COUNT" -eq 1 ]; then
    # All files have same MD5 = true duplicate
    TRUE_DUP=$((TRUE_DUP + 1))
    SIZE=$(du -b $(echo "$FILES" | head -1) 2>/dev/null | cut -f1)
    echo "TRUE DUPLICATE: $name"
    echo "$FILES" | while read -r f; do echo "  $f"; done
    echo "  MD5: $(echo "${!HASHES[@]}" | tr -d '[:space:]')"
    echo "  Recoverable: $(numfmt --to=iec $((SIZE * (FILE_COUNT - 1))) 2>/dev/null || echo "$SIZE bytes")"
    echo ""
  else
    FALSE_DUP=$((FALSE_DUP + 1))
    echo "FALSE POSITIVE: $name (different content)"
    echo "$FILES" | while read -r f; do
      HASH=$(md5sum "$f" 2>/dev/null | awk '{print $1}')
      echo "  $HASH  $f"
    done
    echo ""
  fi
  unset HASHES
done < /tmp/dup_names.txt

echo "=== SUMMARY ==="
echo "True duplicates (identical content): $TRUE_DUP"
echo "False positives (same name, different content): $FALSE_DUP"
echo ""
echo "⚠️ This report is read-only. No files were deleted."
echo "Review the output and remove duplicates manually if desired."