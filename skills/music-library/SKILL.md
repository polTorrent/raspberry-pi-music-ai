---
name: music-library
description: >
  Analyze, clean, and maintain a music library on disk. Use when the user asks
  to check library health, find duplicates, download missing cover art, detect
  incomplete albums, find corrupt or low-quality files, clean up junk files
  (DS_Store, __MACOSX), or organize downloaded albums. All destructive operations
  require explicit user confirmation.
---

# Music Library

Skill for analyzing and maintaining the health of a music library on disk.

## Configuration

- **Music directory**: `/mnt/music` (or set via `MUSIC_DIR` env var)
- **Downloads staging**: `$MUSIC_DIR/_downloads`
- **Library structure**: `Artist/Album/track.ext`

## Scripts

All scripts are in `scripts/`. Run with `bash scripts/<script>.sh`.

### library-health.sh — Full Diagnostic (Read-Only)

```bash
bash scripts/library-health.sh
```

**Does NOT modify anything.** Produces a full diagnostic report covering:

1. Library overview (directories, file count, total size)
2. Format distribution (FLAC, MP3, OGG, M4A, etc.)
3. Junk files (non-audio, non-image files)
4. Duplicate detection (same filename in different directories)
5. Empty directories
6. Incomplete albums (directories with 1–2 audio files)
7. Cover art coverage (cover.jpg/folder.jpg/album.jpg)
8. Suspicious files (audio files < 10 KB)
9. Downloads staging folder status

### verify-duplicates.sh — MD5 Duplicate Verification

```bash
bash scripts/verify-duplicates.sh
```

Takes the list of suspected duplicates from `library-health.sh` and verifies
them with MD5 checksums. Reports true duplicates (identical content) vs.
false positives (same name, different content).

**Read-only** — does not delete anything. Use the output to decide what to remove manually.

### clean-junk.sh — Remove Junk Files

```bash
bash scripts/clean-junk.sh --dry-run   # Preview
bash scripts/clean-junk.sh --confirm   # Actually delete
```

Removes:
- `.DS_Store` files
- `__MACOSX` directories
- `Thumbs.db` files
- `.m3u` / `.m3u8` playlist files (optional)
- Empty directories (after cleanup)

**Requires `--confirm` flag.** Without it, runs in dry-run mode.

## Library Organization Guidelines

The expected folder structure is:

```
/mnt/music/
├── Artist Name/
│   ├── Album Name/
│   │   ├── track01.flac
│   │   ├── track02.flac
│   │   └── cover.jpg
│   └── Another Album/
│       └── ...
├── _downloads/
│   └── (Soulseek staging — organize before scanning)
```

When organizing downloaded albums:
1. Move from `_downloads/` to `Artist/Album/`
2. Merge duplicate folders (keep the one with more/better files)
3. Remove empty directories
4. Trigger a Navidrome scan (happens automatically every 15 min)

## Safety

- `library-health.sh` is always read-only
- `verify-duplicates.sh` is always read-only
- `clean-junk.sh` requires `--confirm` and defaults to dry-run
- No script ever deletes audio files — only junk and empty directories