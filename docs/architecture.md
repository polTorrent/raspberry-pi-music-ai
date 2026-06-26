# Architecture

## System Diagram

```
                          ┌──────────────────────────────┐
                          │        Telegram Cloud         │
                          │   (Bot API long-polling)      │
                          └──────────────┬───────────────┘
                                         │
                                         │ HTTPS (Telegram Bot API)
                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi (armv7l, 1 GB RAM)                   │
│                        Raspbian Bullseye (Linux 6.1)                     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    systemd services                               │   │
│  │                                                                   │   │
│  │  ┌─────────────────┐    ┌──────────────────────────────────┐     │   │
│  │  │  venice-proxy    │    │  picoclaw-gateway                 │     │   │
│  │  │  (Python :8899)  │    │  (Go binary, Telegram bot)        │     │   │
│  │  │                  │    │                                   │     │   │
│  │  │  Receives LLM    │    │  - Reads Telegram messages        │     │   │
│  │  │  requests from   │    │  - Loads system prompt + skills  │     │   │
│  │  │  PicoClaw        │    │  - Calls LLM via proxy            │     │   │
│  │  │  Injects API key │    │  - Executes tools (shell, files, │     │   │
│  │  │  Forwards to     │    │    web search, cron, etc.)       │     │   │
│  │  │  Venice.ai API   │    │  - Sends replies to Telegram      │     │   │
│  │  │                  │    │  - Runs scheduled cron jobs       │     │   │
│  │  └────────┬─────────┘    └───────────────┬──────────────────┘     │   │
│  │           │                              │                         │   │
│  │           │ HTTP localhost:8899         │ shell exec / file I/O  │   │
│  │           │                              │                         │   │
│  └───────────┼──────────────────────────────┼─────────────────────────┘   │
│              │                              │                             │
│              │                              ▼                             │
│              │              ┌───────────────────────────────────┐         │
│              │              │         PicoClaw Workspace          │         │
│              │              │     ~/.picoclaw/workspace/         │         │
│              │              │                                    │         │
│              │              │  memory/MEMORY.md  (long-term)     │         │
│              │              │  skills/             (13 skills)   │         │
│              │              │  ├── pi-maintenance/  (scripts)     │         │
│              │              │  ├── music-library/   (scripts)     │         │
│              │              │  ├── music-recommendations/ (py)   │         │
│              │              │  ├── soulseek-music/  (scripts)    │         │
│              │              │  └── ... 8 more skills              │         │
│              │              └───────────────────────────────────┘         │
│              │                                                          │
│              │                    │                                     │
│              │                    │ docker exec / API calls             │
│              │                    ▼                                     │
│              │    ┌──────────────────────────────────────┐              │
│              │    │       Docker Compose network          │              │
│              │    │                                       │              │
│              │    │  ┌────────────┐   ┌──────────────┐   │              │
│              │    │  │ Navidrome   │   │   slskd      │   │              │
│              │    │  │ :4533       │   │ :5030/:5031  │   │              │
│              │    │  │             │   │              │   │              │
│              │    │  │ Music       │   │ Soulseek     │   │              │
│              │    │  │ streaming   │   │ client +     │   │              │
│              │    │  │ SQLite DB   │   │ REST API     │   │              │
│              │    │  └──────┬─────┘   └──────┬───────┘   │              │
│              │    └─────────┼────────────────┼───────────┘              │
│              │              │                │                          │
│              │              │  /music:ro     │ /music + /downloads     │
│              │              │                │                          │
│              │              ▼                ▼                          │
│              │    ┌──────────────────────────────────────┐              │
│              │    │   External USB drive (1.8 TB, ext4)    │              │
│              │    │   /mnt/music                           │              │
│              │    │                                        │              │
│              │    │   Artist/Album/track.flac              │              │
│              │    │   Artist/Album/track.mp3              │              │
│              │    │   _downloads/ (Soulseek staging)     │              │
│              │    └──────────────────────────────────────┘              │
│              │                                                          │
│  ┌───────────▼──────────────────────────────────────────────┐           │
│  │                    Internet                              │           │
│  │                                                          │           │
│  │  ┌─────────────┐         ┌─────────────────────┐        │           │
│  │  │ Tailscale   │         │ Venice.ai API       │        │           │
│  │  │ (WireGuard) │         │ (LLM inference)     │        │           │
│  │  │             │         │                     │        │           │
│  │  │ Remote      │         │ GLM 5.2 model       │        │           │
│  │  │ access from │         │ via proxy :8899     │        │           │
│  │  │ any device  │         │                     │        │           │
│  │  └─────────────┘         └─────────────────────┘        │           │
│  └──────────────────────────────────────────────────────────┘           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User sends a message on Telegram

```
User → Telegram Cloud → PicoClaw gateway (long-poll) → System prompt + skills loaded
```

### 2. PicoClaw processes the message

```
PicoClaw → LLM call via Venice proxy (:8899) → Venice.ai API → GLM 5.2
         ← Response with tool calls (shell, file, web search, cron...)
```

### 3. Tool execution (example: "download an album")

```
PicoClaw → reads skill: soulseek-music/SKILL.md
         → executes: python3 slskd_search.py "query"
         → slskd REST API (:5030) → Soulseek network
         ← ranked JSON results
         → presents options to user on Telegram
         → user picks one
         → executes: python3 slskd_download.py --from-json results.json --rank 1
         → slskd downloads files → /mnt/music/_downloads/
         → PicoClaw organizes into Artist/Album structure
         → triggers Navidrome scan (15-min schedule or manual)
```

### 4. Weekly recommendations (cron job)

```
Cron (Monday 10:00) → PicoClaw activates music-recommendations skill
  → python3 analyze_listening.py (queries Navidrome SQLite DB)
  → python3 generate_recommendations.py (combines analysis + user profile)
  → web_search for new releases (Album of the Year, artist queries)
  → filters duplicates against library
  → sends formatted recommendations to Telegram
  → (optional) user asks to download → Soulseek pipeline
```

## Component Responsibilities

| Component | Role |
|---|---|
| **PicoClaw** | Orchestration. Reads messages, calls LLM, executes tools, manages skills, runs cron jobs |
| **Venice Proxy** | Security layer. Holds the API key, forwards requests to Venice.ai, keeps the key out of PicoClaw config |
| **Navidrome** | Music streaming server. SQLite DB stores scrobbles, ratings, library metadata. Scans every 15 min |
| **slskd** | Soulseek client. REST API for search/download. Downloads to staging folder |
| **Tailscale** | VPN. Enables remote access to Navidrome web UI, slskd web UI, and SSH from any device |
| **Skills** | Modular capability extensions. Each skill is a SKILL.md spec + scripts that PicoClaw reads on demand |

## Security Model

- **No ports exposed to the public internet.** All access is via Tailscale VPN or LAN.
- **Venice API key** is stored only in the proxy script, never in PicoClaw config or environment.
- **Telegram bot token** is passed via systemd `Environment=` directive, not hardcoded.
- **slskd API key** is stored in an environment file sourced before script execution.
- **PicoClaw workspace** is restricted — `allow_read_outside_workspace: false` prevents arbitrary file access.
- **Navidrome** mounts the music directory as read-only (`/music:ro`).