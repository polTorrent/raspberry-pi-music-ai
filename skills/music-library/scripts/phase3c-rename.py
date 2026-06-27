#!/usr/bin/env python3
"""
Fase 3c: Renombrar subcarpetes restants intentant extreure any del nom.
"""
import os
import re
import sys
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
    tags["album"] = get_tag(audio, "album", "TALB", "ALBUM")
    tags["date"] = get_tag(audio, "date", "TDRC", "TYER", "YEAR")
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
    if m and 1900 <= int(m.group(1)) <= 2030:
        return m.group(1)
    return None

def extract_year_from_name(name):
    # Patrons: (YYYY), [YYYY], YYYY -, YYYY al final, YYYY enmig
    patterns = [
        r'[\[(](\d{4})[\])]',
        r'^(\d{4})\s*[-]',
        r'[-\s](\d{4})\s*[-]',
        r'[-\s](\d{4})\s*$',
        r'\b(19\d{2})\b',
        r'\b(20[0-2]\d)\b',
    ]
    for p in patterns:
        m = re.search(p, name)
        if m:
            year = m.group(1)
            if 1900 <= int(year) <= 2030:
                return year
    return None

def extract_album_title(name):
    """Extreu títol d'àlbum del nom de carpeta, traient any i brossa."""
    title = name
    # Treure prefix d'any
    title = re.sub(r'^\d{4}\s*-\s*', '', title)
    title = re.sub(r'^[\[(]\d{4}[_\d]*[\])]\s*', '', title)
    # Treure "Artist - " del principi si existeix
    # (només si hi ha un altre " - " després)
    # Treure brossa de descarregadores
    title = re.sub(r'\s*[\[(][^\])]*(FLAC|320|192|256|VBR|MP3|EAC|LAME|APE|MPC|CD|hqshare|h33t|Bubanee|thedonga|Darkside|Nahueru|Falloutboy|Robbie60|bluesever|Full.Album|Advance|osloskop|emulek|musicmule|bajatodo|mp3-es|ShareConnector|Skavenger|Grafzahl|Nescix|Apx|Flg77|xy342)[^\])]*[\])]', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+[Bb]y\s+\w+$', '', title)
    title = re.sub(r'\s*www\.\S+', '', title)
    title = re.sub(r'\s+@\s*\d+\s*[Kk]bps\s*$', '', title)
    title = re.sub(r'\s+@\s*\d+\s*$', '', title)
    title = re.sub(r'^\(Album\)\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title)
    return title.strip(" -")

def main():
    print(f"{'⚠️ MODE CONFIRM' if CONFIRM else '📋 MODE DRY-RUN'}")
    print()
    
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
            if re.match(r'^\d{4}\s*-\s*', album_name):
                continue
            if re.match(r'^\(Disc\s+\d+\)', album_name):
                continue
            
            album_path = os.path.join(full, album_name)
            if not os.path.isdir(album_path):
                continue
            
            # Obtenir audio
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
                year = extract_year_from_name(album_name)
            if not year:
                year = extract_year_from_name(item)  # Provar del nom de l'artista
            
            if not album_title:
                album_title = extract_album_title(album_name)
            else:
                album_title = extract_album_title(album_title)
            
            # Netejar el títol
            # Treure "Artista - " del principi si coincideix
            artist_lower = item.lower().replace("_", " ")
            title_lower = album_title.lower()
            if title_lower.startswith(artist_lower + " - "):
                album_title = album_title[len(artist_lower)+3:]
            # Treure any del títol si ja el tenim al prefix
            album_title = re.sub(r'^\d{4}\s*-\s*', '', album_title)
            if year:
                album_title = re.sub(r'\s*[\[(]\d{4}[\])]', '', album_title)
                album_title = re.sub(r'\s*-\s*\d{4}\s*$', '', album_title)
            album_title = album_title.strip(" -")
            
            if not album_title:
                continue
            
            if year:
                new_name = f"{year} - {album_title}"
            else:
                new_name = album_title
            
            new_name = new_name.replace("/", "_")
            
            if new_name != album_name and new_name:
                new_path = os.path.join(full, new_name)
                if not os.path.exists(new_path):
                    renames.append((album_path, new_path, item, album_name, new_name))
    
    for src, dst, artist, old, new in renames:
        print(f"  {artist}/{old} → {new}")
    
    print(f"\nTotal: {len(renames)} subcarpetes a renombrar")
    
    if CONFIRM:
        done = 0
        for src, dst, artist, old, new in renames:
            if os.path.exists(dst):
                continue
            os.rename(src, dst)
            done += 1
        print(f"✅ {done} subcarpetes renombrades.")

if __name__ == "__main__":
    main()