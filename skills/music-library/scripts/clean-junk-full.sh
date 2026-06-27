#!/bin/bash
# Neteja completa de fitxers brossa (.m3u, .sfv, .log, .bmp)
# Els .cue es revisen: només s'esborren si l'àlbum té fitxers separats per pista
# Mode informe per defecte, --confirm per esborrar

MUSIC_ROOT="/mnt/musica"
CONFIRM=""
[ "$1" == "--confirm" ] && CONFIRM="yes"

if [ -z "$CONFIRM" ]; then
  echo "📋 MODE INFORME — no s'esborrarà res (usa --confirm per esborrar)"
else
  echo "⚠️ MODE DE BORRAT ACTIVAT"
fi
echo ""

# .m3u — playlists, sempre brossa
echo "=== .m3u (playlists) ==="
count_m3u=0
while IFS= read -r f; do
  echo "  $f"
  count_m3u=$((count_m3u+1))
  [ -n "$CONFIRM" ] && rm -f "$f"
done < <(find "$MUSIC_ROOT" -type f -name "*.m3u" 2>/dev/null | grep -v '_descarregues')
echo "Total: $count_m3u"
echo ""

# .sfv — checksums, sempre brossa
echo "=== .sfv (checksums) ==="
count_sfv=0
while IFS= read -r f; do
  echo "  $f"
  count_sfv=$((count_sfv+1))
  [ -n "$CONFIRM" ] && rm -f "$f"
done < <(find "$MUSIC_ROOT" -type f -name "*.sfv" 2>/dev/null | grep -v '_descarregues')
echo "Total: $count_sfv"
echo ""

# .log — EAC/log rip, sempre brossa
echo "=== .log (rip logs) ==="
count_log=0
while IFS= read -r f; do
  echo "  $f"
  count_log=$((count_log+1))
  [ -n "$CONFIRM" ] && rm -f "$f"
done < <(find "$MUSIC_ROOT" -type f -name "*.log" 2>/dev/null | grep -v '_descarregues')
echo "Total: $count_log"
echo ""

# .bmp — imatges inútils
echo "=== .bmp (imatges) ==="
count_bmp=0
while IFS= read -r f; do
  echo "  $f"
  count_bmp=$((count_bmp+1))
  [ -n "$CONFIRM" ] && rm -f "$f"
done < <(find "$MUSIC_ROOT" -type f -name "*.bmp" 2>/dev/null | grep -v '_descarregues')
echo "Total: $count_bmp"
echo ""

# .cue — NOMÉS esborrar si l'àlbum té fitxers separats per pista
# Si l'àlbum té un sol FLAC + .cue, el .cue és necessari
echo "=== .cue (analitzant...) ==="
count_cue_keep=0
count_cue_delete=0
while IFS= read -r f; do
  dir=$(dirname "$f")
  # Comptar fitxers d'àudio al directori
  audio_count=$(find "$dir" -maxdepth 1 -type f \( -name "*.flac" -o -name "*.mp3" -o -name "*.ape" -o -name "*.wav" \) 2>/dev/null | wc -l)
  if [ "$audio_count" -le 1 ]; then
    echo "  ⚠️ KEEP (single-file): $f"
    count_cue_keep=$((count_cue_keep+1))
  else
    echo "  ✅ JUNK (multi-file): $f"
    count_cue_delete=$((count_cue_delete+1))
    [ -n "$CONFIRM" ] && rm -f "$f"
  fi
done < <(find "$MUSIC_ROOT" -type f -name "*.cue" 2>/dev/null | grep -v '_descarregues')
echo "Mantenir: $count_cue_keep | Esborrar: $count_cue_delete"
echo ""

# Directoris buits
echo "=== Directoris buits ==="
count_empty=0
while IFS= read -r d; do
  echo "  $d"
  count_empty=$((count_empty+1))
  [ -n "$CONFIRM" ] && rmdir "$d" 2>/dev/null
done < <(find "$MUSIC_ROOT" -type d -empty 2>/dev/null | grep -v '_descarregues')
echo "Total: $count_empty"
echo ""

total=$((count_m3u + count_sfv + count_log + count_bmp + count_cue_delete + count_empty))
echo "=== RESUM ==="
echo "Esborrats: $total fitxers/directoris"
echo "Mantinguts: $count_cue_keep .cue (single-file FLAC, necessaris)"
if [ -z "$CONFIRM" ]; then
  echo "📋 Cap fitxer esborrat. Usa --confirm per esborrar."
else
  echo "✅ Neteja completada."
fi