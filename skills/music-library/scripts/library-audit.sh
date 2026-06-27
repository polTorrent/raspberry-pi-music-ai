#!/bin/bash
# Audita la biblioteca musical i genera un pla de normalització
# Read-only: no modifica res
set -e

MUSIC_ROOT="/mnt/musica"
REPORT="/home/pi/.picoclaw/workspace/library-audit-report.txt"

echo "Generant auditoria completa..."
echo "=== AUDITORIA BIBLIOTECA MUSICAL ===" > "$REPORT"
echo "Data: $(date '+%d/%m/%Y %H:%M')" >> "$REPORT"
echo "" >> "$REPORT"

# 1. Carpentetes a l'arrel que son albums (no artistes)
echo "=== 1. ÀLBUMS A L'ARREL (sense carpeta d'artista) ===" >> "$REPORT"
root_albums=0
for d in "$MUSIC_ROOT"/*/; do
  base=$(basename "$d")
  [[ "$base" == "_descarregues" ]] && continue
  [[ "$base" == "Soulseek Downloads" ]] && continue
  [[ "$base" == "musica gerard" ]] && continue
  subdirs=$(find "$d" -maxdepth 1 -type d 2>/dev/null | tail -n +2 | wc -l)
  if [ "$subdirs" -eq 0 ]; then
    echo "  $base" >> "$REPORT"
    root_albums=$((root_albums+1))
  fi
done
echo "Total: $root_albums" >> "$REPORT"
echo "" >> "$REPORT"

# 2. Artistes amb estructura correcta
echo "=== 2. ARTISTES AMB SUBCARPETES ===" >> "$REPORT"
artists=0
for d in "$MUSIC_ROOT"/*/; do
  base=$(basename "$d")
  [[ "$base" == "_descarregues" ]] && continue
  [[ "$base" == "Soulseek Downloads" ]] && continue
  [[ "$base" == "musica gerard" ]] && continue
  subdirs=$(find "$d" -maxdepth 1 -type d 2>/dev/null | tail -n +2 | wc -l)
  if [ "$subdirs" -gt 0 ]; then
    echo "  $base ($subdirs albums)" >> "$REPORT"
    artists=$((artists+1))
  fi
done
echo "Total: $artists" >> "$REPORT"
echo "" >> "$REPORT"

# 3. Noms de carpeta que no segueixen YYYY - Títol
echo "=== 3. CARPETES D'ÀLBUM NO ESTÀNDARD (no YYYY - Títol) ===" >> "$REPORT"
nonstandard=0
find "$MUSIC_ROOT" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | grep -v '_descarregues' | grep -v 'Soulseek Downloads' | grep -v 'musica gerard' | while read d; do
  base=$(basename "$d")
  # Normal = comença amb 4 digits + espai + guió + espai
  if ! echo "$base" | grep -qP '^\d{4}\s*-\s*'; then
    echo "  $base" >> "$REPORT"
  fi
done
# També carpetes d'arrel
for d in "$MUSIC_ROOT"/*/; do
  base=$(basename "$d")
  [[ "$base" == "_descarregues" ]] && continue
  [[ "$base" == "Soulseek Downloads" ]] && continue
  [[ "$base" == "musica gerard" ]] && continue
  subdirs=$(find "$d" -maxdepth 1 -type d 2>/dev/null | tail -n +2 | wc -l)
  if [ "$subdirs" -eq 0 ]; then
    if ! echo "$base" | grep -qP '^\d{4}\s*-\s*'; then
      # Ja listat en seccio 1
      :
    fi
  fi
done
echo "" >> "$REPORT"

# 4. Fitxers brossa
echo "=== 4. FITXERS BROSSA ===" >> "$REPORT"
junk_count=0
for ext in DS_Store Thumbs.db desktop.ini nfo sfv cue m3u pls log bmp; do
  c=$(find "$MUSIC_ROOT" -type f \( -name "*.$ext" -o -name ".$ext" \) 2>/dev/null | grep -v '_descarregues' | wc -l)
  if [ "$c" -gt 0 ]; then
    echo "  .$ext: $c fitxers" >> "$REPORT"
    junk_count=$((junk_count+c))
  fi
done
# __MACOSX dirs
macosx=$(find "$MUSIC_ROOT" -type d -name "__MACOSX" 2>/dev/null | wc -l)
echo "  __MACOSX dirs: $macosx" >> "$REPORT"
echo "Total brossa: $junk_count fitxers + $macosx carpetes" >> "$REPORT"
echo "" >> "$REPORT"

# 5. Imatges soltes (no incrustades)
echo "=== 5. IMATGES SOLTES (jpg/png) ===" >> "$REPORT"
images=$(find "$MUSIC_ROOT" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) 2>/dev/null | grep -v '_descarregues' | wc -l)
echo "  Total imatges soltes: $images" >> "$REPORT"
echo "" >> "$REPORT"

# 6. Directoris buits
echo "=== 6. DIRECTORIS BUITS ===" >> "$REPORT"
find "$MUSIC_ROOT" -type d -empty 2>/dev/null | grep -v '_descarregues' >> "$REPORT"
echo "" >> "$REPORT"

# 7. Formats minoritaris
echo "=== 7. FORMATS MINORITARIS ===" >> "$REPORT"
for fmt in ogg m4a opus wav wma; do
  c=$(find "$MUSIC_ROOT" -type f -name "*.$fmt" 2>/dev/null | grep -v '_descarregues' | wc -l)
  if [ "$c" -gt 0 ]; then
    echo "  .$fmt: $c fitxers" >> "$REPORT"
  fi
done
echo "" >> "$REPORT"

# 8. Resum
echo "=== RESUM ===" >> "$REPORT"
echo "Àlbums a l'arrel (sense organitzar): $root_albums" >> "$REPORT"
echo "Artistes amb estructura: $artists" >> "$REPORT"
echo "Fitxers brossa: $junk_count" >> "$REPORT"
echo "Imatges soltes: $images" >> "$REPORT"
echo "" >> "$REPORT"
echo "=== FI DE L'AUDITORIA ===" >> "$REPORT"

echo "Auditoria completada. Report a: $REPORT"
cat "$REPORT"