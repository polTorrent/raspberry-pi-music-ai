#!/usr/bin/env python3
"""
embed-covers.py — Incrusta portades (cover.jpg) dins els fitxers d'àudio.
Format suportat: FLAC, MP3, OGG, M4A/MP4, WMA, WAV
NO sobreescriu portades ja existents.
Ús:
  python3 embed-covers.py            # dry-run (mostra què faria)
  python3 embed-covers.py --confirm  # aplica canvis
  python3 embed-covers.py --status    # només mostra quants àlbums tenen cover.jpg
"""

import os
import sys
import base64
from pathlib import Path

try:
    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import ID3, APIC, ID3NoHeaderError
    from mutagen.oggvorbis import OggVorbis
    from mutagen.oggopus import OggOpus
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.asf import ASF
    from mutagen.wave import WAVE
    from mutagen.apev2 import APEv2
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

MUSIC_DIR = "/mnt/musica"
COVER_NAMES = [
    "cover.jpg", "cover.jpeg", "cover.png",
    "folder.jpg", "folder.png",
    "album.jpg", "album.png",
    "front.jpg", "front.png",
]
AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".opus", ".m4a", ".wma", ".wav", ".wv", ".ape"}


def find_cover(album_dir):
    """Buscar fitxer de portada al directori."""
    for name in COVER_NAMES:
        path = os.path.join(album_dir, name)
        if os.path.isfile(path) and os.path.getsize(path) > 1000:
            return path
    # Buscar qualsevol jpg/png/jpeg al directori
    for f in os.listdir(album_dir):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(album_dir, f)
            if os.path.isfile(path) and os.path.getsize(path) > 1000:
                return path
    return None


def read_cover(path):
    """Llegir imatge i determinar MIME type."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    else:
        mime = "image/jpeg"  # assumir jpeg
    return data, mime


def has_embedded_cover(filepath):
    """Comprovar si el fitxer ja té portada incrustada."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".flac":
            audio = FLAC(filepath)
            return len(audio.pictures) > 0
        elif ext == ".mp3":
            try:
                tags = ID3(filepath)
                return any(k.startswith("APIC") for k in tags.keys())
            except ID3NoHeaderError:
                return False
        elif ext in (".ogg", ".opus"):
            if ext == ".ogg":
                audio = OggVorbis(filepath)
            else:
                audio = OggOpus(filepath)
            pics = audio.get("metadata_block_picture", [])
            return len(pics) > 0
        elif ext == ".m4a":
            audio = MP4(filepath)
            return "covr" in audio.tags
        elif ext == ".wma":
            audio = ASF(filepath)
            return "WM/Picture" in audio
        elif ext == ".wav":
            audio = WAVE(filepath)
            # WAV no suporta portades normalment
            return True  # skip
        else:
            return True  # skip formats no suportats
    except Exception:
        return True  # si no podem llegir, skip per seguretat


def embed_flac(filepath, cover_data, mime):
    """Incrustar portada en FLAC."""
    audio = FLAC(filepath)
    # Netejar pictures existents
    audio.clear_pictures()
    pic = Picture()
    pic.data = cover_data
    pic.type = 3  # front cover
    pic.mime = mime
    pic.desc = "Cover"
    audio.add_picture(pic)
    audio.save()


def embed_mp3(filepath, cover_data, mime):
    """Incrustar portada en MP3 (APIC frame)."""
    try:
        tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = ID3()
    # Netejar APIC existents
    for key in list(tags.keys()):
        if key.startswith("APIC"):
            del tags[key]
    tags.add(APIC(
        encoding=3,  # UTF-8
        mime=mime,
        type=3,  # front cover
        desc="Cover",
        data=cover_data,
    ))
    tags.save(filepath)


def embed_ogg(filepath, cover_data, mime):
    """Incrustar portada en OGG/Opus via METADATA_BLOCK_PICTURE."""
    if filepath.endswith(".opus"):
        audio = OggOpus(filepath)
    else:
        audio = OggVorbis(filepath)
    pic = Picture()
    pic.data = cover_data
    pic.type = 3
    pic.mime = mime
    pic.desc = "Cover"
    pic_data = base64.b64encode(pic.write()).decode("ascii")
    audio["metadata_block_picture"] = [pic_data]
    audio.save()


def embed_m4a(filepath, cover_data, mime):
    """Incrustar portada en M4A/MP4."""
    audio = MP4(filepath)
    if mime == "image/png":
        cover_format = MP4Cover.FORMAT_PNG
    else:
        cover_format = MP4Cover.FORMAT_JPEG
    audio["covr"] = [MP4Cover(cover_data, imageformat=cover_format)]
    audio.save()


def embed_wma(filepath, cover_data, mime):
    """Incrustar portada en WMA (ASF)."""
    from mutagen.asf import ASFByteArrayAttribute
    audio = ASF(filepath)
    audio["WM/Picture"] = [ASFByteArrayAttribute(cover_data)]
    audio.save()


def process_album(album_dir, confirm=False, dry_run=True):
    """Processar un àlbum: trobar cover.jpg i incrustar-lo."""
    cover_path = find_cover(album_dir)
    if not cover_path:
        return 0, 0, "no_cover"

    cover_data, mime = read_cover(cover_path)

    audio_files = []
    for f in sorted(os.listdir(album_dir)):
        ext = os.path.splitext(f)[1].lower()
        if ext in AUDIO_EXTS:
            audio_files.append(os.path.join(album_dir, f))

    if not audio_files:
        return 0, 0, "no_audio"

    embedded = 0
    skipped = 0
    errors = 0

    for filepath in audio_files:
        ext = os.path.splitext(filepath)[1].lower()

        # Skip formats no suportats
        if ext in (".wv", ".ape", ".mpc"):
            skipped += 1
            continue

        # Comprovar si ja té portada
        if has_embedded_cover(filepath):
            skipped += 1
            continue

        if dry_run:
            embedded += 1
            continue

        try:
            if ext == ".flac":
                embed_flac(filepath, cover_data, mime)
            elif ext == ".mp3":
                embed_mp3(filepath, cover_data, mime)
            elif ext in (".ogg", ".opus"):
                embed_ogg(filepath, cover_data, mime)
            elif ext == ".m4a":
                embed_m4a(filepath, cover_data, mime)
            elif ext == ".wma":
                embed_wma(filepath, cover_data, mime)
            elif ext == ".wav":
                # WAV normalment no suporta portades
                skipped += 1
                continue
            else:
                skipped += 1
                continue
            embedded += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ⚠️ Error: {filepath}: {e}")

    return embedded, skipped, "ok" if errors == 0 else f"errors:{errors}"


def main():
    if not HAS_MUTAGEN:
        print("❌ Mutagen no instal·lat. Executa: pip3 install mutagen")
        sys.exit(1)

    confirm = "--confirm" in sys.argv
    status_only = "--status" in sys.argv
    dry_run = not confirm

    print("=" * 60)
    if status_only:
        print("ESTAT DE PORTADES")
    elif dry_run:
        print("FASE 7: INCRUSTAR PORTADES — DRY RUN (no modifica res)")
    else:
        print("FASE 7: INCRUSTAR PORTADES — CONFIRM (aplicant canvis)")
    print("=" * 60)

    # Trobar tots els directoris d'àlbum
    album_dirs = []
    for artist_dir in sorted(os.listdir(MUSIC_DIR)):
        artist_path = os.path.join(MUSIC_DIR, artist_dir)
        if not os.path.isdir(artist_path) or artist_dir.startswith("_") or artist_dir.startswith("."):
            continue
        for album_name in sorted(os.listdir(artist_path)):
            album_path = os.path.join(artist_path, album_name)
            if not os.path.isdir(album_path):
                continue
            # Comprovar si té fitxers d'àudio
            has_audio = any(
                os.path.splitext(f)[1].lower() in AUDIO_EXTS
                for f in os.listdir(album_path)
            )
            if has_audio:
                album_dirs.append(album_path)

    print(f"Àlbums totals: {len(album_dirs)}")

    # Comptar estats
    with_cover_file = 0
    without_cover = 0
    for d in album_dirs:
        if find_cover(d):
            with_cover_file += 1
        else:
            without_cover += 1

    print(f"Amb cover.jpg: {with_cover_file}")
    print(f"Sense cover.jpg: {without_cover}")
    print("")

    if status_only:
        return

    if without_cover > 0:
        print(f"⚠️ {without_cover} àlbums sense cover.jpg — aquests no es poden incrustar.")
        print("   Executa primer download-covers.sh per descarregar-les.")
        print("")

    total_embedded = 0
    total_skipped = 0
    total_errors = 0
    processed = 0

    for album_dir in album_dirs:
        embedded, skipped, status = process_album(album_dir, confirm=confirm, dry_run=dry_run)
        total_embedded += embedded
        total_skipped += skipped
        if status.startswith("errors:"):
            total_errors += int(status.split(":")[1])
        processed += 1

        if embedded > 0:
            artist = os.path.basename(os.path.dirname(album_dir))
            album = os.path.basename(album_dir)
            action = "incrustaria" if dry_run else "incrustat"
            print(f"  {'📐' if dry_run else '✅'} {artist}/{album} → {embedded} fitxers {action}")

        if processed % 50 == 0:
            print(f"  --- Progrés: {processed}/{len(album_dirs)} àlbums ---")

    print("")
    print("=" * 60)
    print("RESUM")
    print("=" * 60)
    if dry_run:
        print(f"Fitxers que es modificarien: {total_embedded}")
    else:
        print(f"Fitxers modificats: {total_embedded}")
    print(f"Fitxers saltats (ja tenen portada o format no suportat): {total_skipped}")
    print(f"Errors: {total_errors}")
    print(f"Àlbums sense cover.jpg (pendents de descarregar): {without_cover}")
    print("")
    if dry_run and total_embedded > 0:
        print("Per aplicar els canvis, executa:")
        print("  python3 embed-covers.py --confirm")


if __name__ == "__main__":
    main()