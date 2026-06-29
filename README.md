# 🦞 Raspberry Pi Music AI

A self-hosted music server powered by a Raspberry Pi, an AI assistant on Telegram, and a Soulseek download pipeline — all running on a single board.

## What is this?

This project turns a humble Raspberry Pi into a complete, AI-assisted music ecosystem:

- **🎵 Navidrome** — a self-hosted streaming server (like Spotify, but yours)
- **📱 Symfonium** — a Subsonic-compatible Android client for streaming your library anywhere
- **📥 slskd** — a Soulseek client for discovering and downloading music
- **🤖 PicoClaw** — a lightweight AI assistant (Go) that runs on Telegram, manages the server, searches for music, generates weekly recommendations, and maintains library health
- **🔐 Tailscale** — zero-config VPN for secure remote access from anywhere

The AI assistant can:
- Search and download albums from Soulseek with quality ranking (FLAC > MP3 320 > MP3 192)
- Automatically process downloads: rename, tag, organize into `Artist/YYYY - Album/NN - Song.ext`, and trigger a Navidrome scan — all on a daily cron, no manual intervention
- Generate weekly personalized recommendations by analyzing your listening history + web searches for new releases
- Monitor system health (CPU, temperature, RAM, disk, Docker containers, VPN)
- Monitor memory usage every 6 hours with automatic alerts if RAM < 150 MB or swap > 500 MB
- Clean up junk files, detect duplicates, and diagnose library issues
- Normalize library structure: reorganize folders, fix artist/album tags, embed cover art
- Restart services, apply updates, and perform system maintenance

All controlled via natural language through a Telegram chat.

## Why is this interesting?

- **Fully self-hosted**: No subscription, no cloud dependency, no tracking. Your music, your data, your server.
- **AI-native**: The assistant doesn't just respond — it actively manages the system. It runs shell scripts, queries databases, searches the web, and orchestrates multi-step workflows.
- **Runs on a $35 board**: The entire stack (streaming server, download client, AI assistant, VPN) runs on a Raspberry Pi with 1 GB RAM.
- **Skill-based architecture**: PicoClaw extends its capabilities through modular "skills" — Markdown spec files + Python/Bash scripts that the AI reads and executes on demand.
- **Privacy-first**: The Venice AI proxy routes LLM requests through a private, uncensored inference API. No data is shared with big tech.

## Architecture Overview

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

For a detailed architecture diagram, see [docs/architecture.md](docs/architecture.md).

## Security & Privacy

### ProtonVPN WireGuard via Gluetun

- **Gluetun** is a lightweight VPN client container that establishes a WireGuard tunnel to ProtonVPN.
- **slskd** uses `network_mode: "service:gluetun"`, so all its traffic (Soulseek peer connections, downloads) goes through the VPN tunnel.
- **Navidrome** runs on the host network directly — it is NOT routed through the VPN, ensuring fast local and remote streaming via Tailscale.
- The VPN exit IP is the only IP visible to Soulseek peers.

### Kill switch

- Gluetun includes a built-in **kill switch**: if the VPN tunnel drops, all outbound traffic from the container is blocked.
- This prevents slskd from leaking your real IP address if the VPN connection is interrupted.

### Secrets Management

All secrets are kept out of the repository. None are hardcoded in any committed file.

| Secret | Where it lives | In repo? |
|---|---|---|
| VPN WireGuard private key | `.env` (gitignored, loaded by Docker Compose) | ❌ No |
| Venice API key | systemd drop-in override (`systemctl edit venice-proxy.service`) | ❌ No |
| Telegram bot token | systemd drop-in override (`systemctl edit picoclaw-gateway.service`) | ❌ No |
| slskd API key | `env.sh` (gitignored, sourced by skill scripts) | ❌ No |
| Navidrome credentials | Navidrome's own database (not in repo) | ❌ No |
| PicoClaw config | `~/.picoclaw/config.json` (outside repo) | ❌ No |

The committed service files contain only comments with instructions on how to set up the overrides. See [`.env.example`](config-examples/.env.example) for the full list of environment variables.

## Tech Stack

| Layer | Technology |
|---|---|
| Hardware | Raspberry Pi (armv7l, 1 GB RAM) |
| OS | Raspbian Bullseye (Linux 6.1) |
| Container runtime | Docker + Docker Compose |
| Music server | Navidrome (port 4533) |
| Download client | slskd / Soulseek (ports 5030/5031) |
| AI assistant | PicoClaw 0.2.x (Go, Telegram bot) |
| LLM provider | Venice.ai (GLM 5.2) via local proxy |
| VPN (Soulseek) | ProtonVPN WireGuard via Gluetun (Docker) |
| VPN (remote access) | Tailscale (zero-config WireGuard) |
| Mobile client | Symfonium (Android, Subsonic API) |
| Storage | 30 GB microSD (OS) + 1.8 TB USB drive (music, ext4) |
| Scripting | Python 3.9, Bash |

## Repository Structure

```
raspberry-pi-music-ai/
├── README.md                  ← You are here
├── LICENSE                    ← MIT
├── docs/
│   ├── architecture.md        ← System diagram + data flow
│   ├── setup-guide.md         ← Step-by-step replication guide
│   ├── system-overview.md     ← Current system state & optimizations
│   ├── venice-proxy.md        ← Why and how the LLM proxy works
│   └── picoclaw-skills.md     ← Skill pattern explained
├── venice-proxy/
│   ├── venice-proxy.py        ← Proxy script (sanitized)
│   └── README.md              ← Proxy setup instructions
├── systemd/
│   ├── venice-proxy.service   ← systemd unit for the proxy
│   └── picoclaw-gateway.service ← systemd unit for PicoClaw
├── scripts/
│   ├── mem-monitor.sh         ← RAM alert (every 6h)
│   └── mem-weekly.sh          ← Weekly memory summary (Sundays 9am)
├── skills/
│   ├── pi-maintenance/        ← System monitoring & maintenance
│   ├── music-library/         ← Library health, duplicates, cleanup, normalization
│   ├── music-recommendations/ ← Weekly AI-powered recommendations
│   └── soulseek-music/        ← Soulseek search & download
├── config-examples/
│   ├── config.example.json    ← PicoClaw config (placeholders only)
│   └── docker-compose.example.yml ← Navidrome + slskd + Gluetun VPN compose file
```

## Documentation

- 📖 [Setup Guide](docs/setup-guide.md) — Replicate the entire system from scratch
- 🏗️ [Architecture](docs/architecture.md) — How the pieces fit together
- 📊 [System Overview](docs/system-overview.md) — Current system state, optimizations & cron jobs
- 🔌 [Venice Proxy](docs/venice-proxy.md) — The LLM proxy layer explained
- 🧩 [PicoClaw Skills](docs/picoclaw-skills.md) — The skill pattern and how to write your own

## Subsonic API & Clients

Navidrome implements the [Subsonic API](https://www.subsonic.org/pages/api.jsp) (and [OpenSubsonic](https://opensubsonic.netlify.app/) extensions), so any compatible client can connect. No extra API key is needed — clients authenticate with your Navidrome username + password using the Subsonic salt/token method.

### Recommended: Symfonium (Android)

[Symfonium](https://symfonium.app/) is the most feature-complete Subsonic client for Android:

- **Offline cache**: Download albums for offline playback
- **Transcoding**: On-the-fly format conversion (e.g., FLAC → MP3) for limited bandwidth
- **Scrobbling**: Play counts sync back to Navidrome
- **Gapless playback**: For continuous albums
- **Material Design UI**: Clean, modern interface

### Other compatible clients

| Client | Platform | Notes |
|---|---|---|
| DSub | Android | Classic, open-source |
| Tempo | iOS | Modern, actively maintained |
| Feishin | Desktop (Electron) | Cross-platform, full-featured |
| Jamstash | Web | Browser-based, no install |
| substreamer | iOS/Android | Solid alternative |

### Connecting a client

1. Open your Subsonic client of choice
2. Add a new server with these details:
   - **Server URL (LAN)**: `http://<pi-ip>:4533`
   - **Server URL (remote)**: `http://<tailscale-ip>:4533`
   - **Username**: your Navidrome username
   - **Password**: your Navidrome password
3. The client will test the connection and start scanning your library

> **Tip**: For remote access, make sure Tailscale is running on both your Pi and your phone/computer. The Subsonic traffic stays encrypted inside the WireGuard tunnel.

### Subsonic API for developers

If you want to build custom integrations, the API is available at:
```
http://<pi-ip>:4533/rest/
```
Example endpoint:
```
GET /rest/search3.view?u=<user>&p=<password>&v=1.16.1&c=myapp&f=json&query=aphex+twin
```

## Automation & Optimization

### Download Processing Pipeline (fully automated)

Soulseek downloads are processed and available in Navidrome without any manual intervention:

```
slskd downloads → 03:00 process & organize → 03:20 Navidrome scan → available in Symfonium
```

| Time | Cron Job | Description |
|---|---|---|
| 03:00 daily | `auto-process-downloads.sh` | Checks download folder, runs `process-downloads.py --confirm` to rename, tag, and move files to `Artist/YYYY - Album/NN - Song.ext` |
| 03:20 daily | Navidrome scan trigger | Scans the music library for new content, making it available to all clients |

The `process-downloads.py` script:
- Reads audio tags with mutagen (artist, album, date, track number, title)
- Creates standardized `Artist/YYYY - Album/` folder structure
- Renames files to `NN - Title.ext`
- Handles multi-disc albums (Disc 1, Disc 2, etc.)
- Merges split CDs into a single album folder
- Deletes junk files (.cue, .m3u, .log, .sfv, .nfo, .accurip, .lrc)
- Moves `cover.jpg` to the album folder
- Changes ownership (chown) so Navidrome can read them

### Memory Optimization

The Raspberry Pi has limited RAM (1 GB). The following optimizations are recommended:

| Setting | Before | After | Impact |
|---|---|---|---|
| Swap size | 100 MB | 1024 MB | More breathing room under memory pressure |
| Swappiness | 60 (default) | 10 | Prefer RAM over swap, only swap when necessary |

Persistent configuration:
- Swap: `/etc/dphys-swapfile` (CONF_SWAPSIZE=1024)
- Swappiness: `/etc/sysctl.d/99-swappiness.conf` (vm.swappiness=10)

> **Note**: Docker memory limits (`mem_limit: 256m`, `memswap_limit: 512m`) in the compose file are **not enforced** on 32-bit kernels without cgroups memory support. They are kept for future use on 64-bit kernels.

### Memory Monitoring

| Schedule | Job | Description |
|---|---|---|
| Every 6 hours | `scripts/mem-monitor.sh` | Alerts only if RAM available < 150 MB, swap used > 500 MB, or slskd container > 200 MB |
| Sundays 09:00 | `scripts/mem-weekly.sh` | Weekly summary with current values + reminder about inactive Docker limits |

### Library Normalization

The bot can clean up and standardize your music library through these phases:

| Phase | What it does |
|---|---|
| Phase 1 | Delete junk files (.m3u, .log, .cue, .sfv, .bmp, Thumbs.db) |
| Phase 2 | Reorganize albums to `Artist/YYYY - Album/` format |
| Phase 3 | Fix disguised artists, merge duplicates, rename subfolders |
| Phase 4 | Tag audit (artist, album, date, track, title, genre) |
| Phase 5 | Fix tags A–M and N–Z |
| Phase 6 | Embed cover art |
| Phase 7 | Final cleanup |

## Quick Start

1. **Flash Raspbian Bullseye** on a microSD card and boot your Pi.
2. **Mount an external USB drive** for music storage (ext4 recommended).
3. **Install Docker and Docker Compose.**
4. **Deploy Navidrome + slskd + Gluetun VPN** using the example compose file:
   ```bash
   cp config-examples/docker-compose.example.yml ~/navidrome/docker-compose.yml
   # Edit paths and add your VPN configuration
   cd ~/navidrome && docker compose up -d
   ```
5. **Install Tailscale** and authenticate your Pi.
6. **Install PicoClaw** and configure it with the example config:
   ```bash
   cp config-examples/config.example.json ~/.picoclaw/config.json
   # Edit model, token, and chat ID
   ```
7. **Deploy the Venice proxy** as a systemd service:
   ```bash
   sudo cp venice-proxy/venice-proxy.py /usr/local/bin/
   sudo cp systemd/venice-proxy.service /etc/systemd/system/
   sudo systemctl enable --now venice-proxy
   ```
8. **Install skills** into the PicoClaw workspace:
   ```bash
   cp -r skills/* ~/.picoclaw/workspace/skills/
   ```
9. **Start PicoClaw** as a systemd service and talk to it on Telegram.

See the [full setup guide](docs/setup-guide.md) for detailed instructions.

## Library Stats (example deployment)

| Metric | Example Value |
|---|---|
| Audio files | ~10,000+ |
| Albums | ~1,000+ |
| Artists | ~300+ |
| Total size | ~150 GB+ |
| Scrobbles tracked | ~1,500+ |

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [Navidrome](https://github.com/navidrome/navidrome) — the music server
- [slskd](https://github.com/slskd/slskd) — the Soulseek client
- [Gluetun](https://github.com/qdm12/gluetun) — the VPN client container
- [ProtonVPN](https://protonvpn.com/) — the WireGuard VPN provider
- [Tailscale](https://tailscale.com/) — the remote-access VPN
- [PicoClaw](https://picoclaw.io/) — the AI assistant framework
- [Venice.ai](https://venice.ai/) — the LLM inference provider
- [Symfonium](https://symfonium.app/) — the Subsonic client for Android
- [Subsonic API](https://www.subsonic.org/pages/api.jsp) — the streaming protocol standard
