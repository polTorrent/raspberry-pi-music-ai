# System Overview

Current state of the Raspberry Pi Music AI server as of 2026-06-27.

## Hardware

| Component | Details |
|---|---|
| Board | Raspberry Pi (armv7l, 32-bit) |
| RAM | 1 GB |
| OS | Raspbian Bullseye (Linux 6.1) |
| Storage (OS) | 30 GB microSD |
| Storage (music) | 1.8 TB USB drive, ext4, mounted at `/mnt/musica` |

## Services (Docker Compose at `~/navidrome/`)

| Service | Port | Purpose |
|---|---|---|
| Navidrome | 4533 | Music streaming server (Subsonic API) |
| slskd | 5030/5031 | Soulseek download client |

- Navidrome user: `patata`
- slskd downloads to: `/mnt/musica/_descarregues`
- slskd is in a leechers group (no upload requirements)

## Network

| Access | Address |
|---|---|
| LAN | `192.168.1.39` |
| Remote (Tailscale VPN) | `100.75.250.11` |

## Memory Optimization (2026-06-26)

The Pi has only 1 GB RAM. The following changes were applied to prevent OOM and keep services stable:

| Setting | Before | After | File |
|---|---|---|---|
| Swap size | 100 MB | 1024 MB | `/etc/dphys-swapfile` (CONF_SWAPSIZE=1024) |
| Swappiness | 60 | 10 | `/etc/sysctl.d/99-swappiness.conf` (vm.swappiness=10) |
| slskd memory | ~328 MB | ~257 MB | Restarted to release fragmented memory |

After optimization:
- RAM available: 589 MB (was 476 MB)
- Swap used: reduced after slskd restart

> **Docker memory limits**: `mem_limit: 256m` and `memswap_limit: 512m` are set in `docker-compose.yml`, but the 32-bit kernel does not have cgroups memory support enabled. Docker silently ignores these limits. They are kept for future use on a 64-bit kernel.

## Cron Jobs

### Download Processing Pipeline

| Schedule | Job ID | Script | Description |
|---|---|---|---|
| Daily 03:00 | `953c6bd0b432783b` | `auto-process-downloads.sh` | Checks `_descarregues` for new downloads, runs `process-downloads.py --confirm` to organize them into `Artist/YYYY - Album/NN - Song.ext`, deletes junk files, moves cover art. Log: `logs/process-downloads.log` |
| Daily 03:20 | `f247a846a51cbb3b` | Navidrome scan | Triggers a library scan so new content is available to all clients |

**Automated flow:**
```
slskd downloads → 03:00 process & organize → 03:20 Navidrome scan → available in Symfonium
```

### Memory Monitoring

| Schedule | Job ID | Script | Description |
|---|---|---|---|
| Every 6 hours | `da190c5ef697e178` | `scripts/mem-monitor.sh` | Alerts only if: RAM available < 150 MB, OR swap used > 500 MB, OR slskd container > 200 MB |
| Sundays 09:00 | `6c67a651ed461e18` | `scripts/mem-weekly.sh` | Weekly summary with current memory values + reminder about inactive Docker limits |

### Music Recommendations

| Schedule | Job ID | Description |
|---|---|---|
| Mondays 10:00 | `7d5c9cf83ee1d962` | Analyzes Navidrome listening history + web search for new releases → personalized weekly recommendations |

## Music Library Normalization (2026-06-27)

A multi-phase normalization was performed to clean up the library structure:

| Phase | Description | Status | Details |
|---|---|---|---|
| 1 | Delete junk files | ✅ Done | 255 files deleted (.m3u, .log, .cue, .sfv, .bmp, Thumbs.db, desktop.ini) |
| 2 | Reorganize folders | ✅ Done | 212 albums moved to `Artist/YYYY - Album/`, 7 non-audio dirs removed (833 MB), 2 conflicts resolved |
| 3 | Fix disguised artists | ✅ Done | 227 albums moved to correct artist, 256 subfolders renamed to `YYYY - Title`, 3 duplicate artists merged (BoC, Can, Neu!) |
| 4 | Tag audit | 🔄 Planned | Audit 8 essential tags: artist, album, date, track number, title, genre, album artist, disc number |
| 5 | Fix tags A–M, N–Z | 🔄 In progress | Pink Floyd tags fixed, 471 covers embedded. More artists pending. |
| 6 | Embed cover art | 🔄 Planned | 46% coverage → target 100% |
| 7 | Final cleanup | 🔄 Planned | Remove empty dirs, final verification |

### Library stats after normalization

| Metric | Value |
|---|---|
| Artists | 323 |
| Albums | 543 |
| Audio files | ~11,500 |
| Total size | ~170 GB |
| Scrobbles | ~1,700 |

## Skills

| Skill | Path | Purpose |
|---|---|---|
| pi-maintenance | `skills/pi-maintenance/` | System health, Docker, Tailscale, disk, updates |
| music-library | `skills/music-library/` | Library health, cleanup, normalization, cover art |
| music-recommendations | `skills/music-recommendations/` | Weekly AI recommendations from listening history + web |
| soulseek-music | `skills/soulseek-music/` | Soulseek search with quality ranking + download |