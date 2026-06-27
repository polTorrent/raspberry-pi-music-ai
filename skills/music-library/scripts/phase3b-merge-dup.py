#!/usr/bin/env python3
"""
Fase 3b: Segona passada - fusionar duplicats restants.
"""
import os
import re
import shutil
from collections import defaultdict

MUSIC_ROOT = "/mnt/musica"
SKIP_DIRS = {"_descarregues", "Soulseek Downloads", "_backups"}
AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".m4a", ".wav", ".ape", ".wma", ".opus", ".mpc", ".aac"}

CONFIRM = "--confirm" in sys.argv if (sys := __import__('sys')) else False

def main():
    print(f"{'⚠️ MODE CONFIRM' if CONFIRM else '📋 MODE DRY-RUN'}")
    print()
    
    # Trobar duplicats
    norm_map = defaultdict(list)
    for item in sorted(os.listdir(MUSIC_ROOT)):
        full = os.path.join(MUSIC_ROOT, item)
        if not os.path.isdir(full) or item in SKIP_DIRS or item.startswith("_"):
            continue
        norm = item.lower().replace("_", " ")
        norm = re.sub(r'\s+', ' ', norm).strip()
        norm = re.sub(r'^the\s+', '', norm)
        norm_map[norm].append(item)
    
    duplicates = {k: v for k, v in norm_map.items() if len(v) > 1}
    
    print("=== Duplicats a fusionar ===")
    merges = []
    for norm, variants in sorted(duplicates.items()):
        # Triar el canònic: el que té més àlbums, desempat per nom més "correcte"
        best = variants[0]
        best_count = 0
        for v in variants:
            path = os.path.join(MUSIC_ROOT, v)
            count = sum(1 for f in os.listdir(path) if os.path.isdir(os.path.join(path, f)))
            if count > best_count:
                best = v
                best_count = count
        # Si tots iguals, triar el que té Title Case
        if best_count == 0:
            for v in variants:
                if v != v.lower() and v != v.upper():
                    best = v
                    break
        
        for v in variants:
            if v == best:
                continue
            src = os.path.join(MUSIC_ROOT, v)
            dst = os.path.join(MUSIC_ROOT, best)
            if not os.path.exists(src):
                continue
            # Moure àlbums
            for album in sorted(os.listdir(src)):
                album_src = os.path.join(src, album)
                album_dst = os.path.join(dst, album)
                if not os.path.isdir(album_src):
                    continue
                if os.path.exists(album_dst):
                    print(f"  ⚠️ Conflicte: {best}/{album} ja existeix")
                    continue
                if CONFIRM:
                    shutil.move(album_src, album_dst)
                    print(f"  ✅ {v}/{album} → {best}/{album}")
                else:
                    print(f"  📋 {v}/{album} → {best}/{album}")
            if CONFIRM:
                try:
                    os.rmdir(src)
                    print(f"  🗑️ {v}/ esborrat")
                except:
                    print(f"  ⚠️ {v}/ no buit, no esborrat")
    
    print("\n✅ Fase 3b completada.")

if __name__ == "__main__":
    main()