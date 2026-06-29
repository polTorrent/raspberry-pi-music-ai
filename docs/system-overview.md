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

| Service | Port | Network | Purpose |
|---|---|---|---|
| Navidrome | 4533 | Direct (LAN/Tailscale) | Music streaming server (Subsonic API) |
| slskd | 5030/5031 | Via Gluetun VPN | Soulseek download client |
| Gluetun | — | VPN tunnel | ProtonVPN WireGuard gateway for slskd |

- Navidrome user: `<your-username>`
- slskd downloads to a configurable download folder
- Only slskd traffic is routed through the VPN. Navidrome runs on the direct network for low-latency streaming.

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Telegram Chat                         │
│                      (you ↔ PicoClaw)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PicoClaw   │  Go binary, Telegram bot
                    │  (gateway)  │  13 skills, 8 cron jobs
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐    │     ┌──────▼──────┐
       │ Venice Proxy│    │     │  Shell/Py   │
       │ (Python)    │    │     │  Scripts     │
       │ :8899       │    │     │ (skills)    │
       └──────┬──────┘    │     └──────┬──────┘
              │            │            │
       ┌──────▼──────┐    │     ┌──────▼──────┐
       │ Venice.ai   │    │     │ Docker       │
       │ API (LLM)   │    │     │ ┌─────────┐  │
       │ GLM 5.2     │    │     │ │Gluetun  │  │
       └─────────────┘    │     │ │(VPN)    │  │
                          │     │ └────┬────┘  │
                          │     │      │ net   │
                          │     │ ┌────▼────┐  │
                          │     │ │ slskd   │  │
                          │     │ │(Soulseek)│  │
                          │     │ └─────────┘  │
                          │     │ ┌─────────┐  │
                          │     │ │Navidrome│  │
                          │     │ │(direct) │  │
                          │     │ └─────────┘  │
                          │     └─────────────┘
                          │
                   ┌──────▼──────┐
                   │ Tailscale   │
                   │ VPN (remote │
                   │ access)     │
                   └─────────────┘
```

### Traffic routing

| Service | Route | Why |
|---|---|---|
| Navidrome | Direct (LAN / Tailscale) | Low-latency streaming, no VPN overhead |
| slskd | Via Gluetun → ProtonVPN | Hide IP from Soulseek peers |
| PicoClaw | Direct (outbound HTTPS to Venice.ai) | API calls, no VPN needed |
| Tailscale | Direct (WireGuard mesh) | Remote admin access |

## Security & Privacy

### ProtonVPN WireGuard via Gluetun

- **Gluetun** is a lightweight VPN client container that establishes a WireGuard tunnel to ProtonVPN.
- **slskd** uses `network_mode: "service:gluetun"`, so all its traffic (Soulseek peer connections, downloads) goes through the VPN tunnel.
- **Navidrome** runs on the host network directly — it is NOT routed through the VPN, ensuring fast local and remote streaming via Tailscale.
- The VPN exit IP is the only IP visible to Soulseek peers.

### Kill switch

- Gluetun includes a built-in **kill switch**: if the VPN tunnel drops, all outbound traffic from the container is blocked.
- This prevents slskd from leaking your real IP address if the VPN connection is interrupted.
- Configured via Gluetun's firewall rules (`FIREWALL_OUTBOUND_SUBNETS` restricts traffic to the tunnel).

## Network Access

| Access | Address |
|---|---|
| LAN | `<your-pi-local-ip>` |
| Remote (Tailscale VPN) | `<your-tailscale-ip>` |
| VPN exit IP (Soulseek peers see this) | `<your-protonvpn-exit-ip>` |

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

### Backup

| Schedule | Script | Description |
|---|---|---|
| Daily 04:00 | `backup-navidrome.sh` | Backs up navidrome.db, slskd.db, and docker-compose.yml to `/mnt/musica/_backups/`. Keeps last 7 backups, rotates older. |

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