#!/usr/bin/env python3
"""
Fase 5d: Auto-fix tags per a TOTA la resta de la biblioteca.
Per a cada àlbum:
- albumartist: si falta, copiar de artist tag
- album: si falta, copiar del nom de la carpeta de l'àlbum
- date: si falta, extreure del nom de la carpeta (YYYY - ...)
- tracknumber: si falta, extreure del nom del fitxer (NN - ...)
- title: si falta, extreure del nom del fitxer
- genre: si falta, deixar buit (no inventar)
- Tags sospitosos: "desconocido", "unknown", URLs → netejar
"""
import os
import re
import sys
from mutagen import File
from mutagen.id3 import TPE2, TIT2, TRCK, TDRC, TALB, TCON, TYER

MUSIC = "/mnt/musica"
SKIP_DIRS = {"_descarregues", "Soulseek Downloads", "_backups", "Pink Floyd", "Eugenio"}
AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".m4a", ".wav", ".ape", ".wma", ".opus", ".mpc", ".aac"}

# Patrons sospitosos
SUSPICIOUS_VALUES = {"desconocido", "unknown artist", "unknown album", "unknown", 
                     "interprete desconocido", "album desconocido", "genero desconocido",
                     "intérprete desconocido", "álbum desconocido", "género desconocido"}

def get_tag(audio, *keys):
    for key in keys:
        if key in audio:
            val = audio[key]
            if isinstance(val, list):
                val = val[0] if val else ""
            return str(val).strip()
    return None

def is_suspicious(value):
    if not value:
        return False
    val_lower = value.lower().strip()
    if val_lower in SUSPICIOUS_VALUES:
        return True
    if "desconocido" in val_lower:
        return True
    if val_lower.startswith("unknown album"):
        return True
    if "http://" in val_lower or "https://" in val_lower or "www." in val_lower:
        return True
    return False

def extract_tracknum(filename):
    basename = os.path.splitext(os.path.basename(filename))[0]
    m = re.match(r'^(\d+)', basename)
    return int(m.group(1)) if m else None

def extract_title_from_filename(filename):
    basename = os.path.splitext(os.path.basename(filename))[0]
    basename = re.sub(r'^\d+\s*[-\.]\s*', '', basename)
    basename = re.sub(r'^\d+\s+', '', basename)
    return basename.strip()

def extract_year_from_albumname(albumname):
    m = re.match(r'^(\d{4})', albumname)
    return m.group(1) if m else None

def fix_album_name(albumname):
    return re.sub(r'^\d{4}\s*-\s*', '', albumname)

def clean_title(title):
    if not title:
        return None
    title = re.sub(r'^\d+\s*-\s*', '', title)
    return title.strip() if title else None

total_artists = 0
total_albums = 0
files_fixed = 0
files_total = 0
files_skipped = 0
errors = []
suspicious_cleaned = 0

for artist_name in sorted(os.listdir(MUSIC)):
    artist_path = os.path.join(MUSIC, artist_name)
    if not os.path.isdir(artist_path) or artist_name in SKIP_DIRS or artist_name.startswith("_"):
        continue
    
    total_artists += 1
    
    for album_name in sorted(os.listdir(artist_path)):
        album_path = os.path.join(artist_path, album_name)
        if not os.path.isdir(album_path):
            continue
        
        total_albums += 1
        clean_album = fix_album_name(album_name)
        year = extract_year_from_albumname(album_name)
        
        # Recollir fitxers d'àudio
        audio_files = []
        for dirpath, dirnames, filenames in os.walk(album_path):
            for f in sorted(filenames):
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    audio_files.append(os.path.join(dirpath, f))
        
        if not audio_files:
            continue
        
        for filepath in audio_files:
            files_total += 1
            try:
                audio = File(filepath)
                if audio is None:
                    files_skipped += 1
                    continue
                
                changed = False
                is_mp3 = filepath.lower().endswith('.mp3')
                is_flac_ogg = filepath.lower().endswith(('.flac', '.ogg'))
                is_m4a = filepath.lower().endswith('.m4a')
                
                if is_mp3:
                    if audio.tags is None:
                        audio.add_tags()
                    
                    # === ALBUMARTIST ===
                    current_aa = get_tag(audio, 'albumartist', 'TPE2')
                    if not current_aa or is_suspicious(current_aa):
                        # Copiar de artist
                        current_artist = get_tag(audio, 'artist', 'TPE1')
                        aa_value = current_artist if current_artist and not is_suspicious(current_artist) else artist_name
                        audio.tags["TPE2"] = TPE2(encoding=3, text=[aa_value])
                        changed = True
                        if current_aa and is_suspicious(current_aa):
                            suspicious_cleaned += 1
                    
                    # === ALBUM ===
                    current_album = get_tag(audio, 'album', 'TALB')
                    if not current_album or is_suspicious(current_album):
                        audio.tags["TALB"] = TALB(encoding=3, text=[clean_album])
                        changed = True
                        if current_album and is_suspicious(current_album):
                            suspicious_cleaned += 1
                    
                    # === ARTIST ===
                    current_artist = get_tag(audio, 'artist', 'TPE1')
                    if not current_artist or is_suspicious(current_artist):
                        from mutagen.id3 import TPE1
                        audio.tags["TPE1"] = TPE1(encoding=3, text=[artist_name])
                        changed = True
                        if current_artist and is_suspicious(current_artist):
                            suspicious_cleaned += 1
                    
                    # === TITLE ===
                    current_title = get_tag(audio, 'title', 'TIT2')
                    if not current_title:
                        new_title = extract_title_from_filename(filepath)
                        if new_title:
                            audio.tags.add(TIT2(encoding=3, text=[new_title]))
                            changed = True
                    elif re.match(r'^\d+\s*-\s*', current_title):
                        cleaned = clean_title(current_title)
                        if cleaned:
                            audio.tags["TIT2"] = TIT2(encoding=3, text=[cleaned])
                            changed = True
                    
                    # === TRACKNUMBER ===
                    current_tn = get_tag(audio, 'tracknumber', 'TRCK')
                    if not current_tn:
                        tn = extract_tracknum(filepath)
                        if tn:
                            audio.tags.add(TRCK(encoding=3, text=[str(tn)]))
                            changed = True
                    
                    # === DATE ===
                    current_date = get_tag(audio, 'date', 'TDRC', 'TYER')
                    if not current_date or str(current_date) == "0000":
                        if year:
                            audio.tags.add(TDRC(encoding=3, text=[year]))
                            if 'TYER' in audio.tags:
                                del audio.tags['TYER']
                            changed = True
                    
                    if changed:
                        audio.save()
                        files_fixed += 1
                
                elif is_flac_ogg:
                    if audio.tags is None:
                        audio.add_tags()
                    
                    # ALBUMARTIST
                    current_aa = get_tag(audio, 'albumartist')
                    if not current_aa or is_suspicious(current_aa):
                        current_artist = get_tag(audio, 'artist')
                        aa_value = current_artist if current_artist and not is_suspicious(current_artist) else artist_name
                        audio['albumartist'] = aa_value
                        changed = True
                    
                    # ALBUM
                    current_album = get_tag(audio, 'album')
                    if not current_album or is_suspicious(current_album):
                        audio['album'] = clean_album
                        changed = True
                    
                    # ARTIST
                    current_artist = get_tag(audio, 'artist')
                    if not current_artist or is_suspicious(current_artist):
                        audio['artist'] = artist_name
                        changed = True
                    
                    # TITLE
                    if not get_tag(audio, 'title'):
                        new_title = extract_title_from_filename(filepath)
                        if new_title:
                            audio['title'] = new_title
                            changed = True
                    
                    # TRACKNUMBER
                    if not get_tag(audio, 'tracknumber'):
                        tn = extract_tracknum(filepath)
                        if tn:
                            audio['tracknumber'] = str(tn)
                            changed = True
                    
                    # DATE
                    current_date = get_tag(audio, 'date')
                    if not current_date or str(current_date) == "0000":
                        if year:
                            audio['date'] = year
                            changed = True
                    
                    if changed:
                        audio.save()
                        files_fixed += 1
                
                elif is_m4a:
                    if audio.tags is None:
                        audio.add_tags()
                    
                    # ALBUMARTIST
                    current_aa = get_tag(audio, 'albumartist')
                    if not current_aa or is_suspicious(current_aa):
                        current_artist = get_tag(audio, 'artist')
                        aa_value = current_artist if current_artist and not is_suspicious(current_artist) else artist_name
                        audio['albumartist'] = aa_value
                        changed = True
                    
                    # ALBUM
                    if 'album' not in audio or not str(audio['album'][0]).strip() or is_suspicious(str(audio['album'][0])):
                        audio['album'] = clean_album
                        changed = True
                    
                    # ARTIST
                    current_artist = get_tag(audio, 'artist')
                    if not current_artist or is_suspicious(current_artist):
                        audio['artist'] = artist_name
                        changed = True
                    
                    # TITLE
                    if not get_tag(audio, 'title'):
                        new_title = extract_title_from_filename(filepath)
                        if new_title:
                            audio['title'] = new_title
                            changed = True
                    
                    # TRACKNUMBER
                    if not get_tag(audio, 'tracknumber'):
                        tn = extract_tracknum(filepath)
                        if tn:
                            audio['tracknumber'] = str(tn)
                            changed = True
                    
                    # DATE
                    current_date = get_tag(audio, 'date')
                    if not current_date or str(current_date) == "0000":
                        if year:
                            audio['date'] = year
                            changed = True
                    
                    if changed:
                        audio.save()
                        files_fixed += 1
                
            except Exception as e:
                errors.append(f"Error {filepath}: {e}")

print("=" * 60)
print("FASE 5d: AUTO-FIX RESTA DE BIBLIOTECA")
print("=" * 60)
print(f"Artistes processats: {total_artists}")
print(f"Àlbums processats: {total_albums}")
print(f"Fitxers totals: {files_total}")
print(f"Fitxers corregits: {files_fixed}")
print(f"Fitxers saltats (no llegibles): {files_skipped}")
print(f"Tags sospitosos netejats: {suspicious_cleaned}")
print(f"Errors: {len(errors)}")
if errors:
    print("\nPrimers 15 errors:")
    for e in errors[:15]:
        print(f"  {e}")