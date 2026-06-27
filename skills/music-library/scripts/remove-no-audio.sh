#!/bin/bash
# Esborrar carpetes sense àudio (només imatges, text, video, etc.)
MUSIC_ROOT="/mnt/musica"
CONFIRM=""
[ "$1" == "--confirm" ] && CONFIRM="yes"

dirs=(
"2008 Selected Ambient Works 85-92 remaster"
"cds gravats"
"Gorillaz - All Songs Lyrics - Song Lyric - Testo Canzone - Testi Di Tutte Le Canzoni (Txt)"
"Kevin Ayers 1974 - The confessions of Dr. Dream & other stories"
"Kurt Cobain's Godspeed"
"More (jet films 1969) produced and directed by barbet schroeder"
)

echo "=== Carpetes sense àudio ==="
for dir in "${dirs[@]}"; do
  full="$MUSIC_ROOT/$dir"
  if [ -d "$full" ]; then
    size=$(du -sh "$full" 2>/dev/null | cut -f1)
    files=$(find "$full" -type f 2>/dev/null | wc -l)
    echo "  $dir ($files fitxers, $size)"
    if [ -n "$CONFIRM" ]; then
      rm -rf "$full"
      echo "    ✅ Esborrat"
    fi
  fi
done

echo ""
if [ -z "$CONFIRM" ]; then
  echo "📋 Dry-run. Usa --confirm per esborrar."
else
  echo "✅ Neteja completada."
fi