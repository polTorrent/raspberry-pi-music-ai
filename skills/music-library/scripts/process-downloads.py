#!/usr/bin/env python3
"""
process-downloads.py — Mou àlbums de _descarregues a la biblioteca amb format estàndard.

Estàndard:
  Artista/YYYY - Àlbum/NN - Títol.ext

Llegeix tags amb mutagen per determinar artista, àlbum, any, track numbers.
Si falten tags, intenta inferir del nom del directori.
Esborra fitxers brossa (.cue, .m3u, .log, .sfv, .nfo, .bmp, .txt, Thumbs.db, desktop.ini).
Si ja existeix al destí, salta.
Necessita sudo per chown dels fitxers (slskd baixa com a root).

Ús:
  python3 process-downloads.py            # dry-run (informe)
  python3 process-downloads.py --confirm  # mou realment
"""

import os
import sys
import re
import shutil
import subprocess
from pathlib import Path

try:
    from mutagen import File as MutagenFile
except ImportError:
    print("Error: mutagen no instal·lat. Run: pip3 install mutagen")
    sys.exit(1)

MUSIC_DIR = "/mnt/musica"
DL_DIR = os.path.join(MUSIC_DIR, "_descarregues")

AUDIO_EXTS = {'.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav', '.wma'}
JUNK_EXTS = {'.cue', '.m3u', '.m3u8', '.log', '.sfv', '.nfo', '.bmp', '.txt'}
JUNK_FILES = {'thumbs.db', 'desktop.ini', '.ds_store'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png'}


def sanitize(name):
    """Neteja un nom per usar-lo com a directori/fitxer."""
    # Caràcters il·legals a filesystems
    name = name.replace('/', '_')
    name = name.replace(':', '_')
    name = name.replace('\\', '_')
    # Eliminar espais al principi/final
    name = name.strip()
    # Elimitar dobles espais
    while '  ' in name:
        name = name.replace('  ', ' ')
    return name


def read_tags(filepath):
    """Llegeix tags d'un fitxer d'àudio amb mutagen."""
    try:
        audio = MutagenFile(filepath)
        if audio is None:
            return {}
    except Exception:
        return {}

    tags = {}
    
    # Mutagen returns different tag formats per filetype
    def get(key, *altkeys):
        for k in [key] + list(altkeys):
            if k in audio:
                val = audio[k]
                if isinstance(val, list):
                    val = val[0] if val else ''
                return str(val).strip()
        return ''

    tags['artist'] = get('artist', 'ARTIST', 'TPE1')
    tags['album'] = get('album', 'ALBUM', 'TALB')
    tags['albumartist'] = get('albumartist', 'ALBUMARTIST', 'TPE2')
    tags['date'] = get('date', 'DATE', 'TDRC', 'YEAR', 'TYER')
    tags['tracknumber'] = get('tracknumber', 'TRACKNUMBER', 'TRCK')
    tags['discnumber'] = get('discnumber', 'DISCNUMBER', 'TPOS')
    tags['title'] = get('title', 'TITLE', 'TIT2')
    tags['genre'] = get('genre', 'GENRE', 'TCON')
    
    return tags


def extract_year(date_str):
    """Extreu l'any d'un string de data (pot ser '2005', '2005-06-10', etc.)."""
    if not date_str:
        return ''
    m = re.search(r'(\d{4})', date_str)
    return m.group(1) if m else ''


def parse_tracknumber(tn):
    """Extreu el número de pista (pot ser '3', '03', '3/15', etc.)."""
    if not tn:
        return ''
    m = re.match(r'(\d+)', tn)
    return m.group(1) if m else ''


def parse_discnumber(dn):
    """Extreu el número de disc."""
    if not dn:
        return ''
    m = re.match(r'(\d+)', dn)
    return m.group(1) if m else ''


def infer_from_dirname(dirname):
    """Intenta extreure artista, any i àlbum del nom del directori."""
    artist = ''
    year = ''
    album = dirname
    
    # Patró: "Artista - YYYY - Àlbum" o "Artista - YYYY - Àlbum [FLAC]"
    m = re.match(r'^(.+?)\s*-\s*(\d{4})\s*-\s*(.+)$', dirname)
    if m:
        artist = m.group(1).strip()
        year = m.group(2)
        album = m.group(3).strip()
    else:
        # Patró: "Artista - Àlbum (YYYY)" o "Artista - Àlbum [YYYY]"
        m = re.match(r'^(.+?)\s*-\s*(.+?)[\(\[](\d{4})', dirname)
        if m:
            artist = m.group(1).strip()
            album = m.group(2).strip()
            year = m.group(3)
        else:
            # Patró: "YYYY - Àlbum" (sense artista, l'any és el primer element)
            m = re.match(r'^(\d{4})\s*-\s*(.+)$', dirname)
            if m:
                year = m.group(1)
                album = m.group(2).strip()
            else:
                # Patró: "Artista - Àlbum"
                m = re.match(r'^(.+?)\s*-\s*(.+)$', dirname)
                if m:
                    artist = m.group(1).strip()
                    album = m.group(2).strip()
                else:
                    # Patró: "(YYYY) Àlbum" — sense artista
                    m = re.match(r'^[\(\[]?(\d{4})[\)\]]?\s*(.+)$', dirname)
                    if m:
                        year = m.group(1)
                        album = m.group(2).strip()
    
    # Netejar sufixos comuns del nom de l'àlbum
    album = re.sub(r'\s*\[FLAC\]\s*$', '', album, flags=re.IGNORECASE)
    album = re.sub(r'\s*\[WEB\s*FLAC\]\s*$', '', album, flags=re.IGNORECASE)
    album = re.sub(r'\s*\{[^}]*\}\s*$', '', album)  # {ECM 1073} etc.
    album = re.sub(r'\s*\[[^\]]*\]\s*$', '', album)  # [FLAC] etc.
    album = album.strip()
    
    return artist, year, album


# Àlbums coneguts sense artista als tags — inferir del nom de l'àlbum
KNOWN_ALBUM_ARTISTS = {
    'three imaginary boys': 'The Cure',
    'disintegration': 'The Cure',
    'boys don\'t cry': 'The Cure',
    'the head on the door': 'The Cure',
    'kiss me kiss me kiss me': 'The Cure',
    'wish': 'The Cure',
    'faith': 'The Cure',
    'seventeen seconds': 'The Cure',
    'porno': 'The Cure',
    'tubular bells': 'Mike Oldfield',
    'ok computer': 'Radiohead',
    'the bends': 'Radiohead',
    'kid a': 'Radiohead',
    'amelie': 'Radiohead',
    'made in timeland': 'King Gizzard & The Lizard Wizard',
    'laminated denim': 'King Gizzard & The Lizard Wizard',
}


def guess_artist_from_album(album_name):
    """Intenta endevinar l'artista pel nom de l'àlbum."""
    key = album_name.lower().strip()
    return KNOWN_ALBUM_ARTISTS.get(key, '')


def get_title_from_filename(filename):
    """Extreu el títol d'un nom de fitxer si no hi ha tag."""
    # Treure extensió
    name = os.path.splitext(filename)[0]
    # Treure prefix de número: "01 - ", "01. ", "01 ", "A1 - "
    name = re.sub(r'^\d+\s*[-.]\s*', '', name)
    name = re.sub(r'^[A-D]\d+\s*[-.]\s*', '', name)
    return name.strip()


def process_album(album_path, confirm=False):
    """Processa un àlbum de _descarregues i el moure a la biblioteca."""
    dirname = os.path.basename(album_path)
    
    # Llistar fitxers d'àudio
    all_files = sorted(os.listdir(album_path))
    audio_files = [f for f in all_files if os.path.splitext(f)[1].lower() in AUDIO_EXTS]
    junk_files = [f for f in all_files 
                 if os.path.splitext(f)[1].lower() in JUNK_EXTS 
                 or f.lower() in JUNK_FILES]
    image_files = [f for f in all_files if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
    
    if not audio_files:
        return ('skip', dirname, 'Sense fitxers d\'àudio')
    
    # Llegir tags del primer fitxer amb tags vàlids
    tags = {}
    for af in audio_files:
        tags = read_tags(os.path.join(album_path, af))
        if tags.get('albumartist') or tags.get('artist'):
            break
    
    # Determinar artista, àlbum, any
    artist = tags.get('albumartist') or tags.get('artist') or ''
    album = tags.get('album') or ''
    year = extract_year(tags.get('date', ''))
    
    # Si falten tags, inferir del nom del directori
    if not artist or not album:
        inf_artist, inf_year, inf_album = infer_from_dirname(dirname)
        if not artist:
            artist = inf_artist
        if not album:
            album = inf_album
        if not year:
            year = inf_year
    
    # Si encara no tenim artista, intentar endevinar pel nom de l'àlbum
    if not artist or artist == dirname:
        guessed = guess_artist_from_album(album)
        if guessed:
            artist = guessed
    
    if not artist:
        artist = 'Desconegut'
    if not album:
        album = dirname
    
    # Detectar multi-disc: si hi ha subcarpetes amb àudio
    subdirs = [d for d in all_files if os.path.isdir(os.path.join(album_path, d))]
    has_subdirs_audio = any(
        any(os.path.splitext(f)[1].lower() in AUDIO_EXTS 
            for f in os.listdir(os.path.join(album_path, d)))
        for d in subdirs
    )
    
    # Detectar multi-disc per prefix de fitxer (ex: "1-01", "2-01")
    multi_disc_prefix = False
    if not has_subdirs_audio and len(audio_files) > 0:
        disc_prefixes = set()
        for f in audio_files:
            m = re.match(r'^(\d+)-\d+', f)
            if m:
                disc_prefixes.add(m.group(1))
        if len(disc_prefixes) > 1:
            multi_disc_prefix = True
            has_subdirs_audio = True  # Tractar com multi-disc
    
    # Per àlbums multi-disc en fitxers plans (prefix D-TT), crear subcarpetes virtuals
    if multi_disc_prefix and not subdirs:
        # Crear subcarpetes virtuals agrupant per prefix de disc
        virtual_discs = {}
        for f in audio_files:
            m = re.match(r'^(\d+)-(\d+)', f)
            if m:
                disc = m.group(1)
                virtual_discs.setdefault(disc, []).append(f)
        # Convertir a estructura de subcarpetes per al renombrat
        has_subdirs_audio = True
        # Reescriure audio_files per processar com a multi-disc
        # Crear subdirs virtuals
        subdirs = list(virtual_discs.keys())
    
    # Construir path destí
    artist_clean = sanitize(artist)
    album_clean = sanitize(album)
    if year:
        album_dir_name = f"{year} - {album_clean}"
    else:
        album_dir_name = album_clean
    
    target_dir = os.path.join(MUSIC_DIR, artist_clean, album_dir_name)
    
    # Comprovar si ja existeix
    if os.path.exists(target_dir):
        existing_audio = [f for f in os.listdir(target_dir) 
                         if os.path.splitext(f)[1].lower() in AUDIO_EXTS]
        if len(existing_audio) >= len(audio_files):
            return ('skip', dirname, f'Ja existeix a {artist_clean}/{album_dir_name} ({len(existing_audio)} fitxers)')
    
    # Preparar el pla de renombrat
    rename_plan = []  # (src_path, dst_filename)
    
    if has_subdirs_audio:
        # Multi-disc: processar cada subcarpeta (real o virtual)
        for sd in sorted(subdirs):
            disc_num = ''
            if multi_disc_prefix:
                # Subcarpeta virtual: els fitxers ja són a l'arrel, filtrar per prefix
                disc_num = sd
                sd_audio = sorted(virtual_discs[sd])
                sd_path = album_path  # Els fitxers són a l'arrel
            else:
                # Subcarpeta real
                sd_path = os.path.join(album_path, sd)
                sd_audio = sorted([f for f in os.listdir(sd_path) 
                                  if os.path.splitext(f)[1].lower() in AUDIO_EXTS])
                disc_tags = read_tags(os.path.join(sd_path, sd_audio[0])) if sd_audio else {}
                disc_num = parse_discnumber(disc_tags.get('discnumber', ''))
                if not disc_num:
                    # Intentar extreure del nom de la subcarpeta
                    m = re.search(r'(\d+)', sd)
                    disc_num = m.group(1) if m else '1'
            
            disc_dir = f"(Disc {disc_num})"
            for f in sd_audio:
                f_path = os.path.join(sd_path, f)
                f_tags = read_tags(f_path)
                track = parse_tracknumber(f_tags.get('tracknumber', ''))
                title = f_tags.get('title', '') or get_title_from_filename(f)
                ext = os.path.splitext(f)[1]
                if track:
                    new_name = f"{int(track):02d} - {sanitize(title)}{ext}"
                else:
                    # Per a fitxers amb prefix D-TT sense track tag
                    m = re.match(r'^\d+-(\d+)', f)
                    if m:
                        track = m.group(1)
                        new_name = f"{int(track):02d} - {sanitize(title)}{ext}"
                    else:
                        new_name = sanitize(f)
                rename_plan.append((f_path, os.path.join(disc_dir, new_name)))
    else:
        # Single folder
        for f in audio_files:
            f_path = os.path.join(album_path, f)
            f_tags = read_tags(f_path)
            track = parse_tracknumber(f_tags.get('tracknumber', ''))
            title = f_tags.get('title', '') or get_title_from_filename(f)
            ext = os.path.splitext(f)[1]
            if track:
                new_name = f"{int(track):02d} - {sanitize(title)}{ext}"
            else:
                # Si no hi ha track number, intentar extreure'l del nom
                m = re.match(r'^(\d+)', f)
                if m:
                    new_name = f"{int(m.group(1)):02d} - {sanitize(title)}{ext}"
                else:
                    new_name = sanitize(f)
            rename_plan.append((f_path, new_name))
    
    # Report
    status = 'move' if confirm else 'preview'
    return (status, dirname, {
        'artist': artist,
        'album': album,
        'year': year,
        'target': f"{artist_clean}/{album_dir_name}",
        'audio_count': len(audio_files),
        'junk_count': len(junk_files),
        'image_count': len(image_files),
        'multi_disc': has_subdirs_audio,
        'rename_plan': rename_plan,
    })


def process_multi_cd(dl_dir, cd_dirs, confirm=False):
    """Processa múltiples directoris de descàrrega que són discs d'un mateix àlbum."""
    # Llegir tags del primer fitxer amb tags del primer CD
    first_cd_path = os.path.join(dl_dir, cd_dirs[0])
    all_audio = []
    for cd in cd_dirs:
        cd_path = os.path.join(dl_dir, cd)
        audio = sorted([f for f in os.listdir(cd_path) 
                       if os.path.splitext(f)[1].lower() in AUDIO_EXTS])
        all_audio.extend([(cd, f) for f in audio])
    
    if not all_audio:
        return ('skip', ', '.join(cd_dirs), 'Sense fitxers d\'àudio')
    
    # Llegir tags del primer fitxer amb tags
    tags = {}
    for cd, f in all_audio:
        tags = read_tags(os.path.join(dl_dir, cd, f))
        if tags.get('albumartist') or tags.get('artist'):
            break
    
    artist = tags.get('albumartist') or tags.get('artist') or ''
    album = tags.get('album') or ''
    year = extract_year(tags.get('date', ''))
    
    # Inferir del nom del primer directori
    if not artist or not album:
        inf_artist, inf_year, inf_album = infer_from_dirname(cd_dirs[0])
        if not artist:
            artist = inf_artist
        if not album:
            album = inf_album
        if not year:
            year = inf_year
    
    if not artist or artist == cd_dirs[0]:
        guessed = guess_artist_from_album(album)
        if guessed:
            artist = guessed
    
    if not artist:
        artist = 'Desconegut'
    if not album:
        album = cd_dirs[0]
    
    artist_clean = sanitize(artist)
    album_clean = sanitize(album)
    if year:
        album_dir_name = f"{year} - {album_clean}"
    else:
        album_dir_name = album_clean
    
    target_dir = os.path.join(MUSIC_DIR, artist_clean, album_dir_name)
    
    # Check if already exists
    total_audio = len(all_audio)
    if os.path.exists(target_dir):
        existing_audio = [f for f in os.listdir(target_dir) 
                         if os.path.splitext(f)[1].lower() in AUDIO_EXTS]
        if len(existing_audio) >= total_audio:
            return ('skip', ', '.join(cd_dirs), f'Ja existeix a {artist_clean}/{album_dir_name} ({len(existing_audio)} fitxers)')
    
    # Build rename plan with disc subfolders
    rename_plan = []
    for i, (cd, f) in enumerate(all_audio):
        cd_num = i + 1
        # Try to get disc number from tags
        f_tags = read_tags(os.path.join(dl_dir, cd, f))
        dn = parse_discnumber(f_tags.get('discnumber', ''))
        if dn:
            cd_num = int(dn)
        
        disc_dir = f"(Disc {cd_num})"
        track = parse_tracknumber(f_tags.get('tracknumber', ''))
        title = f_tags.get('title', '') or get_title_from_filename(f)
        ext = os.path.splitext(f)[1]
        if track:
            new_name = f"{int(track):02d} - {sanitize(title)}{ext}"
        else:
            m = re.match(r'^(\d+)', f)
            if m:
                new_name = f"{int(m.group(1)):02d} - {sanitize(title)}{ext}"
            else:
                new_name = sanitize(f)
        rename_plan.append((os.path.join(dl_dir, cd, f), os.path.join(disc_dir, new_name)))
    
    status = 'move' if confirm else 'preview'
    return (status, ', '.join(cd_dirs), {
        'artist': artist,
        'album': album,
        'year': year,
        'target': f"{artist_clean}/{album_dir_name}",
        'audio_count': total_audio,
        'junk_count': 0,
        'image_count': 0,
        'multi_disc': True,
        'rename_plan': rename_plan,
    })


def main():
    confirm = '--confirm' in sys.argv
    
    print("=" * 60)
    print("PROCESSAT DE DESCÀRREGUES")
    print("=" * 60)
    print(f"Data: {subprocess.check_output(['date', '+%d/%m/%Y %H:%M']).decode().strip()}")
    if confirm:
        print("⚠️  MODE CONFIRM — es mouran fitxers")
    else:
        print("📋 MODE INFORME — no es mourà res (usa --confirm)")
    print()
    
    if not os.path.isdir(DL_DIR):
        print(f"No s'ha trobat {DL_DIR}")
        return
    
    # Netejar descàrregues completades de slskd
    try:
        headers = {'X-API-Key': os.environ.get('SLSKD_API_KEY', '')}
        if headers['X-API-Key']:
            import requests
            requests.delete('http://localhost:5030/api/v0/transfers/downloads/all/completed',
                          headers=headers, timeout=5)
    except Exception:
        pass
    
    # Chown dels fitxers (slskd baixa com a root)
    if confirm:
        subprocess.run(['sudo', 'chown', '-R', 'pi:pi', DL_DIR], 
                      capture_output=True, timeout=30)
    
    album_dirs = sorted([d for d in os.listdir(DL_DIR) 
                        if os.path.isdir(os.path.join(DL_DIR, d))])
    
    # Detectar multi-CD en directoris separats (ex: "Magma - Bobino ... (CD1)" i "(CD2)")
    cd_pattern = re.compile(r'\(CD\s*(\d+)\s*\)', re.IGNORECASE)
    cd_groups = {}  # base_name -> [(cd_num, dir_name), ...]
    for d in album_dirs:
        m = cd_pattern.search(d)
        if m:
            base = cd_pattern.sub('', d).strip().rstrip('-').strip()
            cd_num = m.group(1)
            cd_groups.setdefault(base, []).append((int(cd_num), d))
    
    # Marcar directoris que són part d'un grup multi-CD
    merged_dirs = set()
    merged_groups = {}  # base -> sorted list of (cd_num, dir_name)
    for base, cds in cd_groups.items():
        if len(cds) > 1:
            cds.sort()
            merged_groups[base] = cds
            for _, dirname in cds:
                merged_dirs.add(dirname)
    
    moved = 0
    skipped = 0
    errors = 0
    
    # Processar grups fusionats primer
    for base, cds in sorted(merged_groups.items()):
        cd_dirs = [d for _, d in cds]
        result = process_multi_cd(DL_DIR, cd_dirs, confirm)
        # Handle result similar to single album
        if result[0] == 'skip':
            print(f"  ⏭️  {', '.join(cd_dirs)} — {result[2]}")
            skipped += 1
        elif result[0] == 'move' or result[0] == 'preview':
            info = result[2]
            multi = " [multi-disc]"
            print(f"  {'✅' if confirm else '📋'} [{info['audio_count']} audio] {', '.join(cd_dirs)}")
            print(f"     → {info['target']}{multi}")
            for src, dst in info['rename_plan']:
                src_name = os.path.basename(src)
                print(f"       {src_name}  →  {dst}")
            if confirm:
                target = os.path.join(MUSIC_DIR, info['target'])
                os.makedirs(target, exist_ok=True)
                success = True
                for src, dst in info['rename_plan']:
                    dst_path = os.path.join(target, dst)
                    dst_dir = os.path.dirname(dst_path)
                    if dst_dir:
                        os.makedirs(dst_dir, exist_ok=True)
                    try:
                        shutil.move(src, dst_path)
                    except Exception as e:
                        print(f"     ❌ Error: {e}")
                        success = False
                        errors += 1
                # Move images
                for cd_dir in cd_dirs:
                    cd_path = os.path.join(DL_DIR, cd_dir)
                    for img in [f for f in sorted(os.listdir(cd_path)) 
                                if os.path.splitext(f)[1].lower() in IMAGE_EXTS]:
                        try:
                            shutil.move(os.path.join(cd_path, img), os.path.join(target, 'cover.jpg'))
                            break
                        except Exception:
                            pass
                # Clean up
                if success:
                    for cd_dir in cd_dirs:
                        cd_path = os.path.join(DL_DIR, cd_dir)
                        for junk in [f for f in os.listdir(cd_path) 
                                    if os.path.splitext(f)[1].lower() in JUNK_EXTS or f.lower() in JUNK_FILES]:
                            try:
                                os.unlink(os.path.join(cd_path, junk))
                            except Exception:
                                pass
                        try:
                            os.rmdir(cd_path)
                        except OSError:
                            pass
                    print(f"     ✅ Mogut i netejat")
                    moved += 1
            print()
    
    for dirname in album_dirs:
        album_path = os.path.join(DL_DIR, dirname)
        
        # Skip if already processed as part of a merged multi-CD group
        if dirname in merged_dirs:
            continue
        
        result = process_album(album_path, confirm)
        status = result[0]
        
        if status == 'skip':
            print(f"  ⏭️  {result[1]} — {result[2]}")
            skipped += 1
            continue
        
        info = result[2]
        multi = " [multi-disc]" if info['multi_disc'] else ""
        print(f"  {'✅' if confirm else '📋'} [{info['audio_count']} audio, {info['junk_count']} junk] "
              f"{dirname}")
        print(f"     → {info['target']}{multi}")
        
        # Mostrar renombrat
        for src, dst in info['rename_plan']:
            src_name = os.path.basename(src)
            print(f"       {src_name}  →  {dst}")
        
        if confirm:
            # Crear directori destí
            target = os.path.join(MUSIC_DIR, info['target'])
            os.makedirs(target, exist_ok=True)
            
            # Moure i renombrar fitxers
            success = True
            for src, dst in info['rename_plan']:
                dst_path = os.path.join(target, dst)
                dst_dir = os.path.dirname(dst_path)
                if dst_dir:
                    os.makedirs(dst_dir, exist_ok=True)
                try:
                    shutil.move(src, dst_path)
                except Exception as e:
                    print(f"     ❌ Error moure {src}: {e}")
                    success = False
                    errors += 1
            
            # Moure imatges (cover.jpg)
            for img in [f for f in sorted(os.listdir(album_path)) 
                        if os.path.splitext(f)[1].lower() in IMAGE_EXTS]:
                src_img = os.path.join(album_path, img)
                dst_img = os.path.join(target, 'cover.jpg' if img.lower() in ('cover.jpg', 'folder.jpg', 'album.jpg', 'front.jpg') else img)
                try:
                    shutil.move(src_img, dst_img)
                except Exception:
                    pass
            
            # Esborrar brossa
            for junk in [f for f in os.listdir(album_path) 
                        if os.path.splitext(f)[1].lower() in JUNK_EXTS or f.lower() in JUNK_FILES]:
                try:
                    os.unlink(os.path.join(album_path, junk))
                except Exception:
                    pass
            
            # Esborrar directori origen si està buit
            if success:
                try:
                    # Esborrar subcarpetes buides
                    for root, dirs, files in os.walk(album_path, topdown=False):
                        for d in dirs:
                            try:
                                os.rmdir(os.path.join(root, d))
                            except OSError:
                                pass
                    os.rmdir(album_path)
                    print(f"     ✅ Mogut i netejat")
                    moved += 1
                except OSError:
                    print(f"     ⚠️  Mogut però no es pot esborrar el directori origen (potser queden fitxers)")
                    moved += 1
            else:
                print(f"     ⚠️  Mogut amb errors")
        print()
    
    print("=" * 60)
    print(f"RESUM: {moved} moguts, {skipped} saltats, {errors} errors")
    if not confirm:
        print("Per moure realment: python3 process-downloads.py --confirm")
    print("=" * 60)


if __name__ == '__main__':
    main()