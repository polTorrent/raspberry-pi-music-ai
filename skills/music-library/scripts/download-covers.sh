#!/bin/bash
# Descarregar portades per àlbums que no en tenen
# Multi-font: iTunes → Deezer → MusicBrainz Cover Art Archive
# Totes les APIs són gratuïtes i sense clau
# NOMÉS descarrega portades, no modifica fitxers existents

MUSIC_DIR="/mnt/musica"
UA="PicoClawMusicLibrary/1.0 (picoclaw@self-hosted)"

echo "=== DESCÀRREGA DE PORTADES (multi-font) ==="
echo "Data: $(date '+%d/%m/%Y %H:%M')"
echo "Fonts: iTunes → Deezer → MusicBrainz"
echo ""

# Trobar directoris d'àlbum sense portada
echo "Identificant àlbums sense portada..."
> /tmp/albums_no_cover.txt

find "$MUSIC_DIR" -mindepth 2 -maxdepth 3 -type d 2>/dev/null | while IFS= read -r dir; do
    has_cover=false
    for cover in cover.jpg cover.jpeg cover.png folder.jpg folder.png album.jpg album.png front.jpg front.png Cover.jpg Cover.jpeg Cover.png Folder.jpg Folder.png Album.jpg Album.png Front.jpg Front.png; do
        if [ -f "$dir/$cover" ]; then
            has_cover=true
            break
        fi
    done
    if [ "$has_cover" = false ]; then
        img_count=$(find "$dir" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) 2>/dev/null | wc -l)
        if [ "$img_count" -gt 0 ]; then
            has_cover=true
        fi
    fi
    audio_count=$(find "$dir" -maxdepth 1 -type f \( -iname '*.mp3' -o -iname '*.flac' -o -iname '*.ogg' -o -iname '*.m4a' -o -iname '*.wav' -o -iname '*.opus' \) 2>/dev/null | wc -l)
    if [ "$audio_count" -gt 0 ] && [ "$has_cover" = false ]; then
        echo "$dir" >> /tmp/albums_no_cover.txt
    fi
done

NO_COVER_COUNT=$(wc -l < /tmp/albums_no_cover.txt)
echo "Àlbums sense portada: $NO_COVER_COUNT"
echo ""

if [ "$NO_COVER_COUNT" -eq 0 ]; then
    echo "✅ Tots els àlbums ja tenen portada!"
    exit 0
fi

# Funció per extreure artista i àlbum del path
parse_album_info() {
    local dir="$1"
    local basename
    local parent

    basename=$(basename "$dir")
    parent=$(basename "$(dirname "$dir")")

    # Netejar nom de l'àlbum (treure anys, claudàtors, underscores, punts)
    local album_name
    album_name=$(echo "$basename" | sed -E 's/\(?[0-9]{4}\)?\s*[-]?\s*//g' | sed -E 's/\[[0-9]{4}\]//g' | sed 's/_/ /g' | sed 's/\.//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Netejar nom de l'artista
    local artist_name
    artist_name=$(echo "$parent" | sed -E 's/\(?[0-9]{4}\)?\s*[-]?\s*//g' | sed 's/_/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Si el parent és un any, usar només album
    if echo "$parent" | grep -qE '^\(?[0-9]{4}\)?$'; then
        artist_name=""
    fi

    echo "$artist_name|$album_name"
}

# Funció per URL-encodear
urlencode() {
    echo "$1" | sed 's/ /+/g; s/&/%26/g; s/\?/%3F/g; s/'"'"'/%27/g; s/"/%22/g; s/\[/%5B/g; s/\]/%5D/g; s/(/%28/g; s/)/%29/g'
}

# === FONT 1: iTunes ===
try_itunes() {
    local artist="$1"
    local album="$2"
    local query

    if [ -n "$artist" ]; then
        query="$artist $album"
    else
        query="$album"
    fi
    query=$(urlencode "$query")

    local api_url="https://itunes.apple.com/search?term=${query}&entity=album&limit=1"
    local json
    json=$(curl -s -m 10 "$api_url" 2>/dev/null)

    local artwork_url
    artwork_url=$(echo "$json" | jq -r '.results[0].artworkUrl100 // empty' 2>/dev/null)

    if [ -z "$artwork_url" ] || [ "$artwork_url" = "null" ]; then
        echo ""
        return
    fi

    # iTunes dóna 100x100, demanar 600x600
    echo "$artwork_url" | sed 's/100x100/600x600/g'
}

# === FONT 2: Deezer ===
try_deezer() {
    local artist="$1"
    local album="$2"
    local query

    if [ -n "$artist" ]; then
        query="artist:\"$artist\" album:\"$album\""
    else
        query="$album"
    fi
    query=$(urlencode "$query")

    local api_url="https://api.deezer.com/search?q=${query}&limit=1"
    local json
    json=$(curl -s -m 10 "$api_url" 2>/dev/null)

    local cover_url
    cover_url=$(echo "$json" | jq -r '.data[0].album.cover_xl // empty' 2>/dev/null)

    if [ -z "$cover_url" ] || [ "$cover_url" = "null" ]; then
        # Provar sense cometes (cerca més ampla)
        if [ -n "$artist" ]; then
            query=$(urlencode "$artist $album")
        else
            query=$(urlencode "$album")
        fi
        api_url="https://api.deezer.com/search?q=${query}&limit=1"
        json=$(curl -s -m 10 "$api_url" 2>/dev/null)
        cover_url=$(echo "$json" | jq -r '.data[0].album.cover_xl // empty' 2>/dev/null)
    fi

    if [ -z "$cover_url" ] || [ "$cover_url" = "null" ]; then
        echo ""
        return
    fi

    echo "$cover_url"
}

# === FONT 3: MusicBrainz Cover Art Archive ===
try_musicbrainz() {
    local artist="$1"
    local album="$2"
    local query

    if [ -n "$artist" ]; then
        query="artist:$(urlencode "$artist")+release:$(urlencode "$album")"
    else
        query="release:$(urlencode "$album")"
    fi

    # Cercar release a MusicBrainz
    local api_url="https://musicbrainz.org/ws/2/release/?query=${query}&fmt=json&limit=1"
    local json
    json=$(curl -s -m 10 -A "$UA" "$api_url" 2>/dev/null)

    local mbid
    mbid=$(echo "$json" | jq -r '.releases[0].id // empty' 2>/dev/null)

    if [ -z "$mbid" ] || [ "$mbid" = "null" ]; then
        echo ""
        return
    fi

    # Obtenir portada del Cover Art Archive
    echo "https://coverartarchive.org/release/${mbid}/front"
}

# Descarregar portades
echo "=== DESCARREGANT PORTADES ==="
echo ""

DOWNLOADED=0
FAILED=0
FOUND_ITUNES=0
FOUND_DEEZER=0
FOUND_MB=0

while IFS= read -r dir; do
    [ -z "$dir" ] && continue

    basename=$(basename "$dir")
    IFS='|' read -r artist album <<< "$(parse_album_info "$dir")"

    cover_path="$dir/cover.jpg"
    found_url=""
    source_name=""

    # Provar iTunes
    found_url=$(try_itunes "$artist" "$album")
    if [ -n "$found_url" ]; then
        FOUND_ITUNES=$((FOUND_ITUNES + 1))
        source_name="iTunes"
    else
        sleep 0.3
        # Provar Deezer
        found_url=$(try_deezer "$artist" "$album")
        if [ -n "$found_url" ]; then
            FOUND_DEEZER=$((FOUND_DEEZER + 1))
            source_name="Deezer"
        else
            sleep 0.3
            # Provar MusicBrainz
            found_url=$(try_musicbrainz "$artist" "$album")
            if [ -n "$found_url" ]; then
                FOUND_MB=$((FOUND_MB + 1))
                source_name="MusicBrainz"
            fi
        fi
    fi

    if [ -z "$found_url" ]; then
        FAILED=$((FAILED + 1))
        sleep 0.3
        continue
    fi

    # Descarregar la imatge
    http_code=$(curl -s -o "$cover_path" -w "%{http_code}" -m 15 "$found_url" 2>/dev/null)

    if [ "$http_code" = "200" ] && [ -f "$cover_path" ] && [ -s "$cover_path" ]; then
        size=$(stat -c%s "$cover_path" 2>/dev/null || stat -f%z "$cover_path" 2>/dev/null)
        if [ "$size" -gt 1000 ]; then
            DOWNLOADED=$((DOWNLOADED + 1))
            echo "  ✅ [$DOWNLOADED] $basename → cover.jpg (${size} bytes) [$source_name]"
        else
            rm -f "$cover_path"
            FAILED=$((FAILED + 1))
        fi
    else
        rm -f "$cover_path"
        FAILED=$((FAILED + 1))
    fi

    sleep 0.5

    TOTAL=$((DOWNLOADED + FAILED))
    if [ $((TOTAL % 25)) -eq 0 ] && [ $TOTAL -gt 0 ]; then
        echo "  --- Progrés: $TOTAL/$NO_COVER_COUNT processats (✅$DOWNLOADED ❌$FAILED) ---"
    fi

done < /tmp/albums_no_cover.txt

echo ""
echo "=== RESUM ==="
echo "Portades descarregades: $DOWNLOADED"
echo "  - iTunes: $FOUND_ITUNES"
echo "  - Deezer: $FOUND_DEEZER"
echo "  - MusicBrainz: $FOUND_MB"
echo "No trobades: $FAILED"
echo "Total processats: $((DOWNLOADED + FAILED))"
echo ""
echo "⚠️ Només s'han afegit cover.jpg nous. Cap fitxer existent modificat."