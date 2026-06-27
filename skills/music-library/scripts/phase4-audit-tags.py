#!/usr/bin/env python3
"""
Fase 4: Auditoria de tags.
Escaneja tots els fitxers d'àudio i genera un report de tags faltants/incorrectes.
- Tags essencials: title, artist, album, albumartist, date, tracknumber, genre
- Identifica àlbums sense albumartist, sense date, sense genre
- identifica tags amb valors sospitosos (URLs, "desconocido", etc.)
"""
import os
import re
import sys
import json
from collections import defaultdict
from mutagen import File

MUSIC_ROOT = "/mnt/musica"
SKIP_DIRS = {"_descarregues", "Soulseek Downloads", "_backups"}
AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".m4a", ".wav", ".ape", ".wma", ".opus", ".mpc", ".aac"}
ESSENTIAL_TAGS = ["title", "artist", "album", "albumartist", "date", "tracknumber", "genre"]

# Tags sospitosos
SUSPICIOUS_PATTERNS = [
    (r'https?://', 'URL'),
    (r'www\.', 'URL'),
    (r'desconocido', 'desconocido'),
    (r'unknown\s*(artist|album|title)', 'unknown'),
    (r'^\[+\d+\]+$', 'numero_sol'),
    (r'^\d+$', 'numero_sol'),
]

def get_tag(audio, *keys):
    for key in keys:
        if key in audio:
            val = audio[key]
            if isinstance(val, list):
                val = val[0] if val else ""
            return str(val).strip()
    return None

def read_all_tags(filepath):
    tags = {}
    try:
        audio = File(filepath)
        if audio is None:
            return None
    except Exception as e:
        return {"_error": str(e)}
    
    tags["title"] = get_tag(audio, "title", "TIT2")
    tags["artist"] = get_tag(audio, "artist", "TPE1", "Author")
    tags["album"] = get_tag(audio, "album", "TALB", "WM/AlbumTitle")
    tags["albumartist"] = get_tag(audio, "albumartist", "TPE2", "ALBUMARTIST", "album_artist")
    tags["date"] = get_tag(audio, "date", "TDRC", "TYER", "WM/Year", "YEAR", "originaldate")
    tags["tracknumber"] = get_tag(audio, "tracknumber", "TRCK")
    tags["discnumber"] = get_tag(audio, "discnumber", "TPOS")
    tags["genre"] = get_tag(audio, "genre", "TCON")
    tags["_format"] = os.path.splitext(filepath)[1].lower().lstrip(".")
    tags["_has_cover"] = bool(audio.tags and any(
        k for k in audio.keys() if 'apic' in str(k).lower() or 'picture' in str(k).lower() or 'covr' in str(k).lower()
    ))
    return tags

def check_suspicious(value):
    if not value:
        return None
    for pattern, label in SUSPICIOUS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return label
    return None

def main():
    report = {
        "summary": {},
        "albums": [],
        "suspicious": [],
    }
    
    total_files = 0
    total_albums = 0
    files_missing_tags = defaultdict(int)
    albums_missing = defaultdict(list)
    suspicious_found = []
    
    for artist_name in sorted(os.listdir(MUSIC_ROOT)):
        artist_path = os.path.join(MUSIC_ROOT, artist_name)
        if not os.path.isdir(artist_path) or artist_name in SKIP_DIRS or artist_name.startswith("_"):
            continue
        
        for album_name in sorted(os.listdir(artist_path)):
            album_path = os.path.join(artist_path, album_name)
            if not os.path.isdir(album_path):
                continue
            
            # Recollir tots els fitxers d'àudio (inclouent subcarpetes per multi-disc)
            audio_files = []
            for dirpath, dirnames, filenames in os.walk(album_path):
                for f in sorted(filenames):
                    if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                        audio_files.append(os.path.join(dirpath, f))
            
            if not audio_files:
                continue
            
            total_albums += 1
            album_missing = {"artist": artist_name, "album": album_name, "files": len(audio_files), "missing": defaultdict(list), "suspicious": []}
            
            for filepath in audio_files:
                total_files += 1
                tags = read_all_tags(filepath)
                if tags is None:
                    album_missing["missing"]["unreadable"].append(os.path.basename(filepath))
                    continue
                if "_error" in tags:
                    album_missing["missing"]["error"].append(os.path.basename(filepath))
                    continue
                
                for tag_name in ESSENTIAL_TAGS:
                    val = tags.get(tag_name)
                    if not val:
                        files_missing_tags[tag_name] += 1
                        album_missing["missing"][tag_name].append(os.path.basename(filepath))
                    else:
                        # Comprovar sospitosos
                        susp = check_suspicious(val)
                        if susp:
                            suspicious_found.append({
                                "artist": artist_name,
                                "album": album_name,
                                "file": os.path.basename(filepath),
                                "tag": tag_name,
                                "value": val[:100],
                                "type": susp,
                            })
                
                # Comprovar cover
                if not tags.get("_has_cover"):
                    files_missing_tags["cover"] += 1
            
            # Si l'àlbum té tags faltants, afegir-lo al report
            real_missing = {k: v for k, v in album_missing["missing"].items() if v}
            if real_missing:
                album_missing["missing"] = real_missing
                report["albums"].append(dict(album_missing))
            
            # Tags sospitosos a nivell d'àlbum
            if album_missing["suspicious"]:
                report["suspicious"].extend(album_missing["suspicious"])
    
    # Resum
    report["summary"] = {
        "total_files": total_files,
        "total_albums": total_albums,
        "files_missing_tags": dict(files_missing_tags),
        "albums_with_issues": len(report["albums"]),
        "suspicious_count": len(suspicious_found),
    }
    report["suspicious"] = suspicious_found
    
    # Imprimir resum
    print("=" * 60)
    print("AUDITORIA DE TAGS - RESUM")
    print("=" * 60)
    print(f"Fitxers escanejats: {total_files}")
    print(f"Àlbums escanejats: {total_albums}")
    print()
    print("Tags faltants per tag:")
    for tag in ESSENTIAL_TAGS + ["cover"]:
        count = files_missing_tags.get(tag, 0)
        pct = (count / total_files * 100) if total_files else 0
        print(f"  {tag:15s}: {count:6d} fitxers ({pct:.1f}%)")
    print()
    print(f"Àlbums amb tags faltants: {len(report['albums'])}")
    print(f"Tags sospitosos detectats: {len(suspicious_found)}")
    print()
    
    # Top problemes per àlbum
    print("=" * 60)
    print("ÀLBUMS MÉS PROBLEMÀTICS (top 20)")
    print("=" * 60)
    # Ordenar per nombre de tags faltants
    def score(album):
        return sum(len(v) for v in album["missing"].values())
    top = sorted(report["albums"], key=score, reverse=True)[:20]
    for album in top:
        missing_summary = ", ".join(f"{k}({len(v)})" for k, v in sorted(album["missing"].items()))
        print(f"  {album['artist']}/{album['album']} ({album['files']}f): {missing_summary}")
    print()
    
    # Tags sospitosos
    if suspicious_found:
        print("=" * 60)
        print(f"TAGS SOSPITOSOS ({len(suspicious_found)} casos)")
        print("=" * 60)
        # Agrupar per tipus
        by_type = defaultdict(list)
        for s in suspicious_found:
            by_type[s["type"]].append(s)
        for stype, items in sorted(by_type.items()):
            print(f"\n--- {stype} ({len(items)} casos) ---")
            for item in items[:15]:
                print(f"  {item['artist']}/{item['album']}/{item['file']}")
                print(f"    {item['tag']} = \"{item['value']}\"")
            if len(items) > 15:
                print(f"  ... i {len(items)-15} més")
    
    # Guardar report complet a JSON
    report_path = "/home/pi/.picoclaw/workspace/memory/tag-audit-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nReport complet: {report_path}")
    
    # També guardar un report llegible
    txt_path = "/home/pi/.picoclaw/workspace/memory/tag-audit-report.txt"
    with open(txt_path, "w") as f:
        f.write("AUDITORIA DE TAGS\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Fitxers escanejats: {total_files}\n")
        f.write(f"Àlbums escanejats: {total_albums}\n\n")
        f.write("Tags faltants per tag:\n")
        for tag in ESSENTIAL_TAGS + ["cover"]:
            count = files_missing_tags.get(tag, 0)
            pct = (count / total_files * 100) if total_files else 0
            f.write(f"  {tag:15s}: {count:6d} fitxers ({pct:.1f}%)\n")
        f.write(f"\nÀlbums amb tags faltants: {len(report['albums'])}\n")
        f.write(f"Tags sospitosos: {len(suspicious_found)}\n\n")
        f.write("=" * 60 + "\n")
        f.write("LLISTAT COMPLET D'ÀLBUMS AMB PROBLEMES\n")
        f.write("=" * 60 + "\n\n")
        for album in sorted(report["albums"], key=lambda a: (a["artist"], a["album"])):
            missing_summary = ", ".join(f"{k}({len(v)})" for k, v in sorted(album["missing"].items()))
            f.write(f"{album['artist']}/{album['album']} ({album['files']}f): {missing_summary}\n")
        f.write("\n" + "=" * 60 + "\n")
        f.write("TAGS SOSPITOSOS\n")
        f.write("=" * 60 + "\n")
        for s in suspicious_found:
            f.write(f"  {s['artist']}/{s['album']}/{s['file']}\n")
            f.write(f"    {s['tag']} = \"{s['value']}\"\n")
    print(f"Report llegible: {txt_path}")

if __name__ == "__main__":
    main()