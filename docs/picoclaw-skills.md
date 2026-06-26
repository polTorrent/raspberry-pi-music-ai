# PicoClaw Skills

## The Skill Pattern

PicoClaw extends its capabilities through **skills** — modular packages that combine a Markdown specification (`SKILL.md`) with executable scripts (Python/Bash). The AI reads the spec on demand and executes the scripts as needed.

This pattern is powerful because:

1. **No code changes needed**: Adding a new capability is just dropping a folder into `~/.picoclaw/workspace/skills/`. No recompilation, no restart.
2. **AI-readable specs**: The `SKILL.md` file uses YAML frontmatter + Markdown, which the LLM parses naturally to understand what the skill does and when to use it.
3. **Human-editable**: Skills are plain text. Anyone can read, audit, and modify them without understanding the PicoClaw codebase.
4. **Composable**: Skills can reference each other (e.g., the music-recommendations skill can trigger the soulseek-music skill to download recommendations).

## Skill structure

```
skills/
└── my-skill/
    ├── SKILL.md          ← Required: spec file (YAML frontmatter + Markdown)
    ├── scripts/           ← Optional: executable scripts
    │   ├── do_thing.py
    │   └── do_thing.sh
    └── references/        ← Optional: reference docs, configs
        └── api-spec.json
```

## SKILL.md format

```yaml
---
name: my-skill
description: >
  One-paragraph description of what the skill does and when to use it.
  This is what the AI reads to decide whether to activate the skill.
---

# My Skill

## When to Use
- Trigger conditions

## Scripts

### `do_thing.py` — Does a thing
```bash
python3 scripts/do_thing.py --arg value
```

## Configuration
- Environment variables needed
- Prerequisites

## Notes
- Caveats, limitations
```

## Bypassing the safety guard

PicoClaw has a **safety guard** that restricts shell commands to the workspace directory. This prevents the AI from accidentally modifying system files or accessing sensitive paths.

The skills in this repository **bypass the safety guard** through a simple technique: they use **curated wrapper scripts** that run from the workspace but operate on system resources.

### The problem

When PicoClaw tries to run:
```bash
docker ps
```
The safety guard blocks it because the command doesn't explicitly stay within the workspace.

### The solution

Each skill includes wrapper scripts that:
1. Are stored in the workspace (`skills/my-skill/scripts/`)
2. Contain hardcoded, audited commands
3. Are executed by PicoClaw via `bash scripts/my-skill/scripts/do_thing.sh`
4. Operate on system resources (Docker, `/mnt/music`, etc.) safely

The AI doesn't compose arbitrary shell commands — it runs pre-written, reviewed scripts. This is safer than allowing free-form shell execution.

### Example: pi-maintenance

The `pi-status.sh` script checks system health:

```bash
#!/bin/bash
# Hardcoded, audited commands — no user input injection possible
echo "CPU: $(cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2)"
echo "Temp: $(cat /sys/class/thermal/thermal_zone0/temp)"
echo "RAM: $(free -h | grep Mem)"
echo "Disk: $(df -h | grep -vE 'tmpfs|devtmpfs')"
docker ps --format 'table {{.Names}}\t{{.Status}}'
tailscale status 2>&1 | head -5
```

PicoClaw calls it with:
```bash
bash skills/pi-maintenance/scripts/pi-status.sh
```

The safety guard allows this because the script is inside the workspace. The script itself handles system access safely.

## Skills in this repository

### pi-maintenance

**Purpose**: Monitor and maintain the Raspberry Pi.

**Scripts**:
| Script | Function |
|---|---|
| `pi-status.sh` | Full system report (CPU, temp, RAM, disk, Docker, Tailscale) |
| `pi-services.sh` | Start/stop/restart Docker containers and services |
| `pi-cleanup.sh` | Clean APT cache, old journal logs, tmp files, Docker images |
| `pi-updates.sh` | Check and apply system updates |

**Key design**: All scripts support `--dry-run` or `--json` flags. Destructive operations require explicit flags.

### music-library

**Purpose**: Analyze and maintain the health of the music library on disk.

**Scripts**:
| Script | Function |
|---|---|
| `library-health.sh` | Full diagnostic report (duplicates, junk, incomplete albums, cover art) |
| `verify-duplicates.sh` | MD5-verify suspected duplicates before deletion |
| `clean-junk.sh` | Remove DS_Store, __MACOSX, and other junk files |

**Key design**: `library-health.sh` is read-only by default. Cleanup scripts require `--confirm` flag.

### music-recommendations

**Purpose**: Generate weekly personalized music recommendations.

**Scripts**:
| Script | Function |
|---|---|
| `analyze_listening.py` | Query Navidrome SQLite DB for listening history, top artists, forgotten gems |
| `generate_recommendations.py` | Combine analysis + user profile → structured JSON |
| `print_recs.py` | Human-readable summary of recommendations |

**Key design**: The analysis is local (SQLite queries), but the "new releases" discovery uses web search (executed by the AI agent, not a script). This separation lets the AI reason about web results before presenting them.

### soulseek-music

**Purpose**: Search and download music from Soulseek via slskd REST API.

**Scripts**:
| Script | Function |
|---|---|
| `slskd_search.py` | Search Soulseek, group results by user/folder, rank by quality |
| `slskd_download.py` | Enqueue downloads by rank or specific files |

**Key design**: Ranking algorithm prioritizes lossless (FLAC > WAV > APE > MP3 320 > MP3 192), complete albums (more files = better), and accessible files (fewer locked = better). The AI presents ranked options to the user, who picks before download.

## Writing your own skill

1. Create a directory: `~/.picoclaw/workspace/skills/my-skill/`
2. Write `SKILL.md` with YAML frontmatter and clear instructions
3. Add scripts in `scripts/` (keep them simple, audited, and safe)
4. Test by asking PicoClaw to use the skill
5. PicoClaw will read `SKILL.md` on demand — no restart needed

### Tips

- **Keep scripts small**: One script per concern. Easy to audit.
- **Use flags for safety**: `--dry-run`, `--confirm`, `--json` make scripts safer and more flexible.
- **Document everything**: The AI relies on the SKILL.md to understand the skill. Clear docs = better execution.
- **Avoid user input in scripts**: Hardcode paths and commands. If you need parameters, pass them as script arguments, not shell injection.
- **Handle errors gracefully**: Scripts should exit with non-zero on failure and print clear error messages.