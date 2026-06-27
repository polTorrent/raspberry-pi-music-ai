#!/bin/bash
# Organitzar descàrregues: moure àlbums completats de _descarregues a la biblioteca
# Per defecte només informa. Amb --confirm mou.
# Estructura objectiu: /mnt/musica/Artista/Àlbum/

MUSIC_DIR="/mnt/musica"
DL_DIR="$MUSIC_DIR/_descarregues"
CONFIRM="${1:-}"

echo "=== ORGANITZACIÓ DE DESCÀRREGUES ==="
echo "Data: $(date '+%d/%m/%Y %H:%M')"
echo ""

if [ ! -d "$DL_DIR" ]; then
    echo "No s'ha trobat $DL_DIR"
    exit 0
fi

if [ "$CONFIRM" = "--confirm" ]; then
    echo "⚠️ MODE MOURE ACTIVAT — es mouran fitxers"
else
    echo "📋 MODE INFORME — no es mourà res (usa --confirm per moure)"
fi
echo ""

MOVED=0
SKIPPED=0

while IFS= read -r album_dir; do
    [ -z "$album_dir" ] && continue
    [ "$album_dir" = "$DL_DIR" ] && continue

    album_name=$(basename "$album_dir")

    # Comptar fitxers d'àudio
    audio_count=$(find "$album_dir" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' -o -iname '*.wav' -o -iname '*.opus' \) 2>/dev/null | wc -l)

    if [ "$audio_count" -eq 0 ]; then
        continue
    fi

    # Determinar si sembla complet (3+ fitxers o és un single/EP)
    if [ "$audio_count" -lt 3 ]; then
        echo "  ⏭️  [$audio_count fitxers] $album_name — possible incomplet, saltant"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Intentar extreure artista dels tags del primer fitxer d'àudio
    first_audio=$(find "$album_dir" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.m4a' \) 2>/dev/null | head -1)

    artist=""
    if [ -n "$first_audio" ] && command -v ffprobe &>/dev/null; then
        artist=$(ffprobe -v quiet -show_entries format_tags=artist -of csv=p=0 "$first_audio" 2>/dev/null | tr -d '[:cntrl:]' | head -c 100)
    fi

    # Si no tenim artista dels tags, usar el nom del directori
    if [ -z "$artist" ]; then
        # Intentar extreure artista del nom (abans de " - ")
        artist=$(echo "$album_name" | sed -E 's/^(.*)\s*-\s*.*/\1/' | xargs)
        # Si no hi havia " - ", usar "Desconegut"
        if [ "$artist" = "$album_name" ]; then
            artist="Desconegut"
        fi
    fi

    # Netejar noms per filesystem
    artist_clean=$(echo "$artist" | sed 's/\//_/g' | sed 's/:/_/g' | xargs)
    album_clean=$(echo "$album_name" | sed 's/\//_/g' | sed 's/:/_/g' | xargs)

    target_dir="$MUSIC_DIR/$artist_clean/$album_clean"

    # Comprovar si ja existeix al destí
    if [ -d "$target_dir" ]; then
        existing_count=$(find "$target_dir" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' \) 2>/dev/null | wc -l)
        if [ "$existing_count" -ge "$audio_count" ]; then
            echo "  ⏭️  [$audio_count fitxers] $artist_clean / $album_clean — ja existeix ($existing_count fitxers), saltant"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
    fi

    if [ "$CONFIRM" = "--confirm" ]; then
        mkdir -p "$target_dir"
        cp -r "$album_dir"/* "$target_dir"/ 2>/dev/null
        if [ $? -eq 0 ]; then
            # Verificar que s'ha copiat correctament
            target_count=$(find "$target_dir" -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' \) 2>/dev/null | wc -l)
            if [ "$target_count" -ge "$audio_count" ]; then
                rm -rf "$album_dir"
                MOVED=$((MOVED + 1))
                echo "  ✅ [$audio_count fitxers] $album_name → $artist_clean/$album_clean"
            else
                echo "  ❌ Error copiant: $album_name (còpia incompleta, no s'ha esborrat l'original)"
                SKIPPED=$((SKIPPED + 1))
            fi
        else
            echo "  ❌ Error copiant: $album_name"
            SKIPPED=$((SKIPPED + 1))
        fi
    else
        MOVED=$((MOVED + 1))
        echo "  📋 [$audio_count fitxers] $album_name → $artist_clean/$album_clean"
    fi

done < <(find "$DL_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)

echo ""
echo "=== RESUM ==="
echo "Àlbums per moure: $MOVED"
echo "Saltats (incomplets o duplicats): $SKIPPED"
if [ "$CONFIRM" = "--confirm" ]; then
    echo "✅ Àlbums moguts a la biblioteca"
else
    echo "📋 Cap fitxer mogut. Usa: bash $0 --confirm per moure."
fi