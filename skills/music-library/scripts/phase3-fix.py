#!/usr/bin/env python3
"""
Fase 3: Correccions d'estructura.
1. Fusionar artistes duplicats
2. Esborrar carpetes no musicals
3. Fix artistes disfressats (llegir tags, moure àlbum a artista correcte)
4. Renombrar subcarpetes a YYYY - Títol
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
    tags["artist"] = get_tag(audio, "artist", "TPE1", "Author", "albumartist", "ALBUMARTIST")
    tags["album"] = get_tag(audio, "album", "TALB", "WM/AlbumTitle", "ALBUM")
    tags["date"] = get_tag(audio, "date", "TDRC", "TYER", "WM/Year", "YEAR", "originaldate")
    tags["albumartist"] = get_tag(audio, "albumartist", "TPE2", "ALBUMARTIST", "album_artist")
    for k in tags:
        if tags[k]:
            tags[k] = tags[k].strip()
    return tags

def get_audio_files(folder):
    files = []
    for f in os.listdir(folder):
        ext = os.path.splitext(f)[1].lower()
        if ext in AUDIO_EXTS:
            files.append(os.path.join(folder, f))
    files.sort()
    return files

def parse_year(text):
    if not text:
        return None
    m = re.match(r'(\d{4})', str(text))
    if m:
        return m.group(1)
    return None

def parse_year_from_name(name):
    m = re.search(r'[\[(](\d{4})[\])]', name)
    if m:
        return m.group(1)
    m = re.match(r'^(\d{4})', name)
    if m:
        return m.group(1)
    return None

# ============================================================
# PAS 1: Fusionar artistes duplicats
# ============================================================
def merge_duplicates():
    print("=== PAS 1: Fusionar artistes duplicats ===")
    merges = [
        ("Boards Of Canada", "Boards of Canada"),
        ("CAN", "Can"),
        ("NEU!", "Neu!"),
    ]
    for canonical, dup in merges:
        canon_path = os.path.join(MUSIC_ROOT, canonical)
        dup_path = os.path.join(MUSIC_ROOT, dup)
        if not os.path.exists(dup_path):
            print(f"  ⏭️ {dup} no existeix, salto")
            continue
        if not os.path.exists(canon_path):
            # Si el canònic no existeix, renombrar el dup
            if CONFIRM:
                os.rename(dup_path, canon_path)
                print(f"  ✅ {dup} → {canonical} (renombrat)")
            else:
                print(f"  📋 {dup} → {canonical} (renombrat)")
            continue
        # Moure els àlbums del dup al canònic
        for album in sorted(os.listdir(dup_path)):
            src = os.path.join(dup_path, album)
            dst = os.path.join(canon_path, album)
            if not os.path.isdir(src):
                continue
            if os.path.exists(dst):
                print(f"  ⚠️ Conflicte: {canonical}/{album} ja existeix")
                continue
            if CONFIRM:
                shutil.move(src, dst)
                print(f"  ✅ {dup}/{album} → {canonical}/{album}")
            else:
                print(f"  📋 {dup}/{album} → {canonical}/{album}")
        if CONFIRM:
            os.rmdir(dup_path)
            print(f"  🗑️ {dup}/ esborrat (buit)")
    print()

# ============================================================
# PAS 2: Esborrar carpetes no musicals
# ============================================================
def remove_non_music():
    print("=== PAS 2: Esborrar carpetes no musicals ===")
    non_music = [
        "Comic The Ghost In The Shell - Spanish-Español",
    ]
    for name in non_music:
        path = os.path.join(MUSIC_ROOT, name)
        if os.path.exists(path):
            size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        size += os.path.getsize(fp)
                    except:
                        pass
            if CONFIRM:
                shutil.rmtree(path)
                print(f"  ✅ Esborrat: {name} ({size//1024//1024} MB)")
            else:
                print(f"  📋 Esborrar: {name} ({size//1024//1024} MB)")
        else:
            print(f"  ⏭️ {name} no existeix")
    print()

# ============================================================
# PAS 3: Fix artistes disfressats
# ============================================================
def fix_disguised_artists():
    print("=== PAS 3: Fix artistes disfressats ===")
    moves = []
    
    for item in sorted(os.listdir(MUSIC_ROOT)):
        full = os.path.join(MUSIC_ROOT, item)
        if not os.path.isdir(full) or item in SKIP_DIRS or item.startswith("_"):
            continue
        
        # Comprovar si és carpeta d'artista (té subdirs, no té audio directe)
        has_subdirs = has_audio = False
        for f in os.listdir(full):
            if os.path.isdir(os.path.join(full, f)):
                has_subdirs = True
            elif os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                has_audio = True
        if not has_subdirs or has_audio:
            continue
        
        # Per cada àlbum dins l'artista
        for album_name in sorted(os.listdir(full)):
            album_path = os.path.join(full, album_name)
            if not os.path.isdir(album_path):
                continue
            
            audio_files = get_audio_files(album_path)
            if not audio_files:
                # Potser és multi-disc
                for sub in os.listdir(album_path):
                    sub_path = os.path.join(album_path, sub)
                    if os.path.isdir(sub_path):
                        audio_files = get_audio_files(sub_path)
                        if audio_files:
                            break
                if not audio_files:
                    continue
            
            tags = read_tags(audio_files[0])
            tag_artist = tags.get("artist") or tags.get("albumartist")
            
            if not tag_artist:
                continue
            
            # Normalitzar tag_artist
            tag_artist = tag_artist.strip()
            tag_artist = tag_artist.replace("_", " ")
            tag_artist = re.sub(r'\s+', ' ', tag_artist)
            
            # Comparar amb el nom de carpeta d'artista
            folder_artist = item
            
            # Si són diferents (case-insensitive, sense underscores)
            norm_folder = folder_artist.lower().replace("_", " ").strip()
            norm_tag = tag_artist.lower().strip()
            
            if norm_folder != norm_tag and len(tag_artist) > 2:
                # L'artista real del tag és diferent del nom de carpeta
                # Verificar que no és una variació menor
                if norm_folder.replace("the ", "") != norm_tag.replace("the ", ""):
                    moves.append({
                        "old_artist": folder_artist,
                        "new_artist": tag_artist,
                        "album": album_name,
                        "src": album_path,
                        "dest": os.path.join(MUSIC_ROOT, tag_artist, album_name),
                    })
    
    for m in moves:
        conflict = " ⚠️CONFLICTE" if os.path.exists(m["dest"]) else ""
        print(f"  {m['old_artist']}/{m['album']} → {m['new_artist']}/{m['album']}{conflict}")
    
    print(f"\nTotal: {len(moves)} àlbums a moure")
    
    if CONFIRM:
        done = 0
        for m in moves:
            if os.path.exists(m["dest"]):
                continue
            os.makedirs(os.path.dirname(m["dest"]), exist_ok=True)
            shutil.move(m["src"], m["dest"])
            done += 1
        # Netejar carpetes d'artista buides
        for m in moves:
            old_path = os.path.join(MUSIC_ROOT, m["old_artist"])
            if os.path.exists(old_path):
                try:
                    os.rmdir(old_path)
                except:
                    pass
        print(f"✅ {done} àlbums moguts.")
    print()

# ============================================================
# PAS 4: Renombrar subcarpetes a YYYY - Títol
# ============================================================
def rename_subfolders():
    print("=== PAS 4: Renombrar subcarpetes a YYYY - Títol ===")
    renames = []
    
    for item in sorted(os.listdir(MUSIC_ROOT)):
        full = os.path.join(MUSIC_ROOT, item)
        if not os.path.isdir(full) or item in SKIP_DIRS or item.startswith("_"):
            continue
        
        has_subdirs = has_audio = False
        for f in os.listdir(full):
            if os.path.isdir(os.path.join(full, f)):
                has_subdirs = True
            elif os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                has_audio = True
        if not has_subdirs or has_audio:
            continue
        
        for album_name in sorted(os.listdir(full)):
            album_path = os.path.join(full, album_name)
            if not os.path.isdir(album_path):
                continue
            
            # Saltar (Disc N)
            if re.match(r'^\(Disc\s+\d+\)', album_name):
                continue
            # Saltar si ja té format YYYY - Títol
            if re.match(r'^\d{4}\s*-\s*', album_name):
                continue
            
            # Obtenir any i títol dels tags
            audio_files = get_audio_files(album_path)
            if not audio_files:
                for sub in os.listdir(album_path):
                    sub_path = os.path.join(album_path, sub)
                    if os.path.isdir(sub_path):
                        audio_files = get_audio_files(sub_path)
                        if audio_files:
                            break
            if not audio_files:
                continue
            
            tags = read_tags(audio_files[0])
            year = parse_year(tags.get("date"))
            album_title = tags.get("album")
            
            if not year:
                year = parse_year_from_name(album_name)
            
            if not album_title:
                # Netejar nom de carpeta
                album_title = album_name
                album_title = re.sub(r'^\d{4}\s*-\s*', '', album_title)
                album_title = re.sub(r'^[\[(]\d{4}[_\d]*[\])]\s*', '', album_title)
                album_title = re.sub(r'^\(Album\)\s*', '', album_title, flags=re.IGNORECASE)
            
            # Netejar títol
            album_title = re.sub(r'\s+', ' ', album_title).strip()
            
            if year:
                new_name = f"{year} - {album_title}"
            else:
                new_name = album_title
            
            # Normalitzar per filesystem
            new_name = new_name.replace("/", "_")
            
            if new_name != album_name and new_name:
                new_path = os.path.join(full, new_name)
                if not os.path.exists(new_path):
                    renames.append({
                        "artist": item,
                        "old": album_name,
                        "new": new_name,
                        "src": album_path,
                        "dest": new_path,
                    })
    
    for r in renames:
        print(f"  {r['artist']}/{r['old']} → {r['new']}")
    
    print(f"\nTotal: {len(renames)} subcarpetes a renombrar")
    
    if CONFIRM:
        done = 0
        for r in renames:
            if os.path.exists(r["dest"]):
                continue
            os.rename(r["src"], r["dest"])
            done += 1
        print(f"✅ {done} subcarpetes renombrades.")
    print()

# ============================================================
# MAIN
# ============================================================
def main():
    print(f"{'⚠️ MODE CONFIRM' if CONFIRM else '📋 MODE DRY-RUN'}")
    print()
    
    merge_duplicates()
    remove_non_music()
    fix_disguised_artists()
    rename_subfolders()

if __name__ == "__main__":
    main()