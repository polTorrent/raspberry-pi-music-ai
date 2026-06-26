# 🦞 Raspberry Pi Music AI

A self-hosted music server powered by a Raspberry Pi, an AI assistant on Telegram, and a Soulseek download pipeline — all running on a single board.

## What is this?

This project turns a humble Raspberry Pi into a complete, AI-assisted music ecosystem:

- **🎵 Navidrome** — a self-hosted streaming server (like Spotify, but yours)
- **📥 slskd** — a Soulseek client for discovering and downloading music
- **🤖 PicoClaw** — a lightweight AI assistant (Go) that runs on Telegram, manages the server, searches for music, generates weekly recommendations, and maintains library health
- **🔐 Tailscale** — zero-config VPN for secure remote access from anywhere

The AI assistant can:
- Search and download albums from Soulseek with quality ranking (FLAC > MP3 320 > MP3 192)
- Organize downloaded music into a clean `Artist/Album` folder structure
- Generate weekly personalized recommendations by analyzing your listening history + web searches for new releases
- Monitor system health (CPU, temperature, RAM, disk, Docker containers, VPN)
- Clean up junk files, detect duplicates, and diagnose library issues
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
┌─────────────────────────────────────────────────────────┐
│                     Telegram Chat                        │
│                    (you ↔ PicoClaw)                       │
└──────────────────────────┬──────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PicoClaw   │  Go binary, Telegram bot
                    │  (gateway)  │  13 skills, 2 cron jobs
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐    │     ┌──────▼──────┐
       │ Venice Proxy│    │     │  Shell/Py   │
       │ (Python)    │    │     │  Scripts    │
       │ :8899       │    │     │ (skills)    │
       └──────┬──────┘    │     └──────┬──────┘
              │            │            │
       ┌──────▼──────┐    │     ┌──────▼──────┐
       │ Venice.ai   │    │     │ Docker      │
       │ API (LLM)   │    │     │ Navidrome   │
       │ GLM 5.2     │    │     │ slskd       │
       └─────────────┘    │     └─────────────┘
                          │
                   ┌──────▼──────┐
                   │ Tailscale   │
                   │ VPN         │
                   └─────────────┘
```

For a detailed architecture diagram, see [docs/architecture.md](docs/architecture.md).

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
| VPN | Tailscale (zero-config WireGuard) |
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
│   ├── venice-proxy.md        ← Why and how the LLM proxy works
│   └── picoclaw-skills.md     ← Skill pattern explained
├── venice-proxy/
│   ├── venice-proxy.py        ← Proxy script (sanitized)
│   └── README.md              ← Proxy setup instructions
├── systemd/
│   ├── venice-proxy.service   ← systemd unit for the proxy
│   └── picoclaw-gateway.service ← systemd unit for PicoClaw
├── skills/
│   ├── pi-maintenance/        ← System monitoring & maintenance
│   ├── music-library/         ← Library health, duplicates, cleanup
│   ├── music-recommendations/ ← Weekly AI-powered recommendations
│   └── soulseek-music/        ← Soulseek search & download
├── config-examples/
│   ├── config.example.json    ← PicoClaw config (placeholders only)
│   └── docker-compose.example.yml ← Navidrome + slskd compose file
```

## Documentation

- 📖 [Setup Guide](docs/setup-guide.md) — Replicate the entire system from scratch
- 🏗️ [Architecture](docs/architecture.md) — How the pieces fit together
- 🔌 [Venice Proxy](docs/venice-proxy.md) — The LLM proxy layer explained
- 🧩 [PicoClaw Skills](docs/picoclaw-skills.md) — The skill pattern and how to write your own

## Quick Start

1. **Flash Raspbian Bullseye** on a microSD card and boot your Pi.
2. **Mount an external USB drive** for music storage (ext4 recommended).
3. **Install Docker and Docker Compose.**
4. **Deploy Navidrome + slskd** using the example compose file:
   ```bash
   cp config-examples/docker-compose.example.yml ~/navidrome/docker-compose.yml
   # Edit paths and credentials, then:
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

| Metric | Value |
|---|---|
| Audio files | ~11,500 |
| Albums | ~1,500 |
| Artists | ~1,700 |
| Total size | ~170 GB |
| Scrobbles tracked | ~2,000 |

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [Navidrome](https://github.com/navidrome/navidrome) — the music server
- [slskd](https://github.com/slskd/slskd) — the Soulseek client
- [Tailscale](https://tailscale.com/) — the VPN
- [PicoClaw](https://github.com/nicobailon/picoclaw) — the AI assistant framework
- [Venice.ai](https://venice.ai/) — the LLM inference provider