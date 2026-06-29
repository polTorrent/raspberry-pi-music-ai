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
- **Library structure**: `Artist/YYYY - Album/NN - Song.ext`

## Scripts

All scripts are in `scripts/`.

### Diagnostics & Cleanup

| Script | Mode | Description |
|---|---|---|
| `library-health.sh` | Read-only | Full diagnostic: formats, junk, duplicates, empty dirs, incomplete albums, cover coverage, suspicious files |
| `verify-duplicates.sh` | Read-only | MD5 verification of suspected duplicates — true vs false positives |
| `clean-junk.sh` | `--confirm` | Removes `.DS_Store`, `__MACOSX`, `Thumbs.db`, `.m3u`, `.nfo`, empty dirs. Dry-run by default |
| `clean-junk-full.sh` | `--confirm` | Extended junk cleanup (`.cue`, `.log`, `.sfv`, `.bmp`, `desktop.ini`) |
| `library-audit.sh` | Read-only | Deep audit: file count, size, artists, albums, orphan files, cover coverage, minor formats |

### Download Processing Pipeline

| Script | Mode | Description |
|---|---|---|
| `process-downloads.py` | `--confirm` | Reads tags with mutagen, moves downloads to `Artist/YYYY - Album/NN - Song.ext`, handles multi-disc, merges split CDs, deletes junk (`.cue .m3u .log .sfv .nfo`), moves `cover.jpg` |
| `auto-process-downloads.sh` | Cron wrapper | Checks `_downloads` for pending folders, runs `process-downloads.py --confirm`, logs to `logs/process-downloads.log` |
| `organize-downloads.sh` | `--confirm` | Basic download organizer (legacy, prefer `process-downloads.py`) |

### Library Normalization

| Script | Mode | Description |
|---|---|---|
| `reorganize-folders-v2.py` | `--confirm` | Moves albums to `Artist/YYYY - Album/` format, resolves multi-disc conflicts |
| `remove-no-audio.sh` | `--confirm` | Removes directories with no audio files (photos, videos, text only) |
| `phase3-fix.py` | `--confirm` | Fixes disguised artists by reading tags, moves albums to correct artist folder |
| `phase3b-merge-dup.py` | `--confirm` | Merges duplicate artist folders |
| `phase3c-rename.py` | `--confirm` | Renames subfolders to `YYYY - Title` format |
| `phase4-audit-tags.py` | Read-only | Audits 8 essential tags across library, reports missing/suspicious values |
| `phase5d-autofix.py` | `--confirm` | Auto-fills missing tags from folder/file names (never overwrites existing) |
| `embed-covers.py` | `--confirm` | Embeds cover art into audio files |

### Cover Art

| Script | Mode | Description |
|---|---|---|
| `download-covers.sh` | Interactive | Downloads missing cover art via iTunes API |

## Download Processing Flow

```
slskd downloads to _downloads/
    ↓
auto-process-downloads.sh (cron 03:00 daily)
    ↓
process-downloads.py --confirm
    → reads tags with mutagen
    → creates Artist/YYYY - Album/
    → renames files to NN - Song.ext
    → handles multi-disc (Disc 1, Disc 2...)
    → merges split CDs
    → deletes junk files (.cue .m3u .log .sfv .nfo .accurip .lrc)
    → moves cover.jpg
    ↓
Navidrome scan (cron 03:20 daily)
    ↓
Available in Symfonium
```

## Library Structure

The expected folder structure is:

```
/mnt/music/
├── Artist Name/
│   ├── 1979 - Album Title/
│   │   ├── 01 - First Song.flac
│   │   ├── 02 - Second Song.flac
│   │   └── cover.jpg
│   └── 1985 - Another Album/
│       ├── Disc 1/
│       │   ├── 01 - Track One.flac
│       │   └── 02 - Track Two.flac
│       └── Disc 2/
│           └── ...
├── Various Artists/
│   └── 2024 - Compilation Name/
│       └── ...
└── _downloads/
    └── (Soulseek staging — auto-processed daily)
```

## Safety

- `library-health.sh` is always read-only
- `verify-duplicates.sh` is always read-only
- `library-audit.sh` is always read-only
- `phase4-audit-tags.py` is always read-only
- `clean-junk.sh` / `clean-junk-full.sh` require `--confirm`, default to dry-run
- `process-downloads.py` requires `--confirm`, otherwise dry-run
- All normalization scripts require `--confirm`
- No script ever deletes audio files — only junk and empty directories
- `phase5d-autofix.py` only fills missing tags, never overwrites existing values