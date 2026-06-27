#!/usr/bin/env python3
"""
Reorganitzar carpetes v2: usa tags mutagen correctament.
"""
import os
import re
import sys
import shutil
from mutagen import File

MUSIC_ROOT = "/mnt/musica"
SKIP_DIRS = {"_descarregues", "Soulseek Downloads", "_backups"}
CONFIRM = "--confirm" in sys.argv
AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".m4a", ".wav", ".ape", ".wma", ".opus", ".mpc", ".aac"}

def get_tag(audio, *keys):
    for key in keys:
        if key in audio:
            val = audio[key]
            if isinstance(val, list):
                val = val[0] if val else ""
            return str(val).strip()
    return None

def read_tags(filepath):
    tags = {}
    try:
        audio = File(filepath)
        if audio is None:
            return tags
    except Exception:
        return tags
    tags["artist"] = get_tag(audio, "artist", "TPE1", "Author", "WM/AlbumArtist", "ALBUMARTIST", "albumartist")
    tags["album"] = get_tag(audio, "album", "TALB", "WM/AlbumTitle", "ALBUM")
    tags["date"] = get_tag(audio, "date", "TDRC", "TYER", "WM/Year", "YEAR", "originaldate")
    tags["albumartist"] = get_tag(audio, "albumartist", "TPE2", "WM/AlbumArtist", "ALBUMARTIST", "album_artist")
    for k in tags:
        if tags[k]:
            tags[k] = tags[k].strip()
    return tags

def clean_name(name):
    if not name:
        return name
    name = re.sub(r'\s*[\[(][^\])]*(FLAC|320|192|256|VBR|Vbr|MP3|EAC|LAME|APE|MPC|mpc|CD|hqshare|h33t|Bubanee|thedonga|Darkside|Nahueru|Falloutboy|Robbie60|bluesever|Server Alliance|Eac|eac|Full Album|Full.Album|Advance|ADVANCE|osloskop|emulek|musicmule|bajatodo|mp3-es|ShareConnector|Skavenger|Grafzahl|Nescix|Apx|Flg77|xy342)[^\])]*[\])]', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+[Bb]y\s+[A-Z][\w\s]+$', '', name)
    name = re.sub(r'\s+[Bb]y\s+\w+$', '', name)
    name = re.sub(r'\s*www\.\S+', '', name)
    name = re.sub(r'\s*https?://\S+', '', name)
    name = re.sub(r'\s*@\s*\d+\s*[Kk]bps\s*$', '', name)
    name = re.sub(r'\s*@\s*\d+\s*$', '', name)
    name = re.sub(r'\s*@\s*\d+\s*[Kk]bits\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^[\[(]\d{4}[_\d]*[\])]\s*', '', name)
    name = re.sub(r'^[\[(]\d{4}[\])]\s*', '', name)
    name = re.sub(r'^\d{4}\s*-\s*', '', name)
    name = re.sub(r'^\(Album\)\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name)
    return name.strip(" -")

def clean_artist(name):
    if not name:
        return name
    name = re.sub(r'https?://\S+', '', name)
    if ' - ' in name and not name.startswith('The '):
        name = re.sub(r'\s*-\s*.*$', '', name)
    name = name.replace('_', ' ')
    name = re.sub(r'\s+', ' ', name)
    return name.strip(" -")

def parse_year_from_name(name):
    m = re.search(r'[\[(](\d{4})[\])]', name)
    if m:
        return m.group(1)
    m = re.match(r'^(\d{4})', name)
    if m:
        return m.group(1)
    return None

def get_album_info(folder_path):
    name = os.path.basename(folder_path)
    audio_files = []
    for f in os.listdir(folder_path):
        ext = os.path.splitext(f)[1].lower()
        if ext in AUDIO_EXTS:
            audio_files.append(os.path.join(folder_path, f))
    audio_files.sort()
    artist = None
    album = None
    year = None
    if audio_files:
        tags = read_tags(audio_files[0])
        artist = tags.get("artist") or tags.get("albumartist")
        album = tags.get("album")
        year = tags.get("date")
    if not artist:
        if " - " in name:
            parts = name.split(" - ", 1)
            if not re.match(r'^\d{4}', parts[0].strip()):
                artist = parts[0].strip()
                if not album:
                    album = parts[1].strip() if len(parts) > 1 else None
        if not artist:
            artist = name
    if not album:
        album = clean_name(name)
    else:
        album = clean_name(album)
    artist = clean_artist(artist)
    if not artist:
        artist = clean_name(name)
    if not year:
        year = parse_year_from_name(name)
    if year:
        m = re.match(r'(\d{4})', year)
        if m:
            year = m.group(1)
    return artist, album, year

def is_artist_folder(folder_path):
    has_subdirs = has_audio = False
    try:
        for item in os.listdir(folder_path):
            full_path = os.path.join(folder_path, item)
            if os.path.isdir(full_path):
                has_subdirs = True
            elif os.path.splitext(item)[1].lower() in AUDIO_EXTS:
                has_audio = True
    except Exception:
        pass
    return has_subdirs and not has_audio

def main():
    print(f"{'⚠️ MODE CONFIRM' if CONFIRM else '📋 MODE DRY-RUN'}")
    print()
    root_items = sorted(os.listdir(MUSIC_ROOT))
    moves = []
    for item in root_items:
        full_path = os.path.join(MUSIC_ROOT, item)
        if not os.path.isdir(full_path) or item in SKIP_DIRS or item.startswith("_"):
            continue
        if is_artist_folder(full_path):
            continue
        artist, album, year = get_album_info(full_path)
        artist_safe = artist.replace("/", "_").strip()
        album_safe = album.replace("/", "_").strip() if album else "Unknown Album"
        if year:
            new_album_name = f"{year} - {album_safe}"
        else:
            new_album_name = album_safe
        new_artist_path = os.path.join(MUSIC_ROOT, artist_safe)
        new_album_path = os.path.join(new_artist_path, new_album_name)
        if new_album_path == full_path:
            continue
        artist_exists = os.path.exists(new_artist_path)
        dest_exists = os.path.exists(new_album_path)
        moves.append({
            "src": full_path,
            "src_name": item,
            "artist": artist_safe,
            "album": new_album_name,
            "dest": new_album_path,
            "artist_exists": artist_exists,
            "dest_exists": dest_exists,
        })
    by_artist = {}
    for m in moves:
        by_artist.setdefault(m["artist"], []).append(m)
    print(f"Total àlbums a reorganitzar: {len(moves)}")
    print(f"Artistes nous: {len([a for a in by_artist if not os.path.exists(os.path.join(MUSIC_ROOT, a))])}")
    print()
    conflicts = [m for m in moves if m["dest_exists"]]
    for artist in sorted(by_artist.keys()):
        albums = by_artist[artist]
        print(f"📁 {artist}/")
        for m in albums:
            tag = " ⚠️CONFLICTE" if m["dest_exists"] else (" (nova)" if not m["artist_exists"] else "")
            print(f"  {m['src_name']}  →  {m['album']}{tag}")
        print()
    print(f"=== RESUM ===")
    print(f"Àlbums a moure: {len(moves)}")
    print(f"Conflictes: {len(conflicts)}")
    if conflicts:
        print("\n⚠️ CONFLICTES:")
        for m in conflicts:
            print(f"  {m['src_name']} → {m['dest']}")
    if CONFIRM:
        print("\nExecutant...")
        done = 0
        skipped = 0
        for m in moves:
            if m["dest_exists"]:
                print(f"  ⏭️ Salto conflicte: {m['src_name']}")
                skipped += 1
                continue
            if m["dest"].startswith(m["src"] + os.sep):
                tmp = m["src"] + ".__tmp__"
                os.rename(m["src"], tmp)
                os.makedirs(os.path.dirname(m["dest"]), exist_ok=True)
                os.rename(tmp, m["dest"])
            else:
                os.makedirs(os.path.dirname(m["dest"]), exist_ok=True)
                try:
                    os.rename(m["src"], m["dest"])
                except OSError:
                    shutil.move(m["src"], m["dest"])
            done += 1
        print(f"✅ {done} àlbums reorganitzats. {skipped} saltats per conflicte.")
    else:
        print("\n📋 Dry-run. Usa --confirm per executar.")

if __name__ == "__main__":
    main()