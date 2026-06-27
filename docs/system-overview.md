# System Overview

Example configuration of the Raspberry Pi Music AI server.

## Hardware

| Component | Details |
|---|---|
| Board | Raspberry Pi (armv7l, 32-bit) |
| RAM | 1 GB |
| OS | Raspbian Bullseye (Linux 6.1) |
| Storage (OS) | microSD card |
| Storage (music) | External USB drive, ext4 |

## Services (Docker Compose)

| Service | Port | Purpose |
|---|---|---|
| Navidrome | 4533 | Music streaming server (Subsonic API) |
| slskd | 5030/5031 | Soulseek download client |

- Navidrome user: `<your-username>`
- slskd downloads to a configurable download folder

## Network

| Access | Address |
|---|---|
| LAN | `<your-pi-local-ip>` |
| Remote (Tailscale VPN) | `<your-tailscale-ip>` |

## Memory Optimization

The Pi has only 1 GB RAM. The following changes are recommended to prevent OOM and keep services stable:

| Setting | Before | After | File |
|---|---|---|---|
| Swap size | 100 MB | 1024 MB | `/etc/dphys-swapfile` (CONF_SWAPSIZE=1024) |
| Swappiness | 60 | 10 | `/etc/sysctl.d/99-swappiness.conf` (vm.swappiness=10) |

> **Docker memory limits**: `mem_limit: 256m` and `memswap_limit: 512m` can be set in `docker-compose.yml`, but 32-bit kernels may not have cgroups memory support enabled. Docker silently ignores these limits in that case.

## Cron Jobs

### Download Processing Pipeline

| Schedule | Script | Description |
|---|---|---|
| Daily 03:00 | `auto-process-downloads.sh` | Checks download folder for new downloads, runs `process-downloads.py --confirm` to organize them into `Artist/YYYY - Album/NN - Song.ext`, deletes junk files, moves cover art |
| Daily 03:20 | Navidrome scan | Triggers a library scan so new content is available to all clients |

**Automated flow:**
```
slskd downloads → 03:00 process & organize → 03:20 Navidrome scan → available in Symfonium
```

### Memory Monitoring

| Schedule | Script | Description |
|---|---|---|
| Every 6 hours | `scripts/mem-monitor.sh` | Alerts if: RAM available < 150 MB, OR swap used > 500 MB, OR slskd container > 200 MB |
| Sundays 09:00 | `scripts/mem-weekly.sh` | Weekly summary with current memory values + reminder about inactive Docker limits |

### Music Recommendations

| Schedule | Description |
|---|---|
| Mondays 10:00 | Analyzes Navidrome listening history + web search for new releases → personalized weekly recommendations |

## Music Library Normalization

A multi-phase normalization approach to clean up the library structure:

| Phase | Description | Example |
|---|---|---|
| 1 | Delete junk files | e.g. 250+ files removed (.m3u, .log, .cue, .sfv, .bmp, Thumbs.db) |
| 2 | Reorganize folders | e.g. 200+ albums moved to `Artist/YYYY - Album/` |
| 3 | Fix disguised artists | e.g. 200+ albums fixed, duplicate artists merged, subfolders renamed |
| 4 | Tag audit | Recommended: audit 8 essential tags |
| 5 | Fix tags | Recommended: fix tags per artist |
| 6 | Embed cover art | Recommended: improve coverage |
| 7 | Final cleanup | Recommended: remove empty dirs, final verification |

## Skills

| Skill | Path | Purpose |
|---|---|---|
| pi-maintenance | `skills/pi-maintenance/` | System health, Docker, Tailscale, disk, updates |
| music-library | `skills/music-library/` | Library health, cleanup, normalization, cover art |
| music-recommendations | `skills/music-recommendations/` | Weekly AI recommendations from listening history + web |
| soulseek-music | `skills/soulseek-music/` | Soulseek search with quality ranking + download |