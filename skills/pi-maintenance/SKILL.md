---
name: pi-maintenance
description: >
  Monitor and maintain a Raspberry Pi running a self-hosted music server
  (Navidrome + slskd + Tailscale via Docker Compose). Use when the user asks
  to check system status, monitor CPU/temperature/RAM/disk, verify services
  are running, clean up temporary files, check or apply system updates, view
  resource-hungry processes, or restart services. Covers: system health,
  Docker containers (Navidrome port 4533, slskd ports 5030/5031), Tailscale
  VPN, disk space on SD card and external music drive, apt updates, and
  cleanup of cache/tmp/old downloads.
---

# Pi Maintenance

Skill for monitoring and maintaining the Raspberry Pi music server.

## System Overview

- **Hardware**: Raspberry Pi (armv7l 32-bit), Raspbian Bullseye
- **User**: pi
- **Docker Compose**: `~/navidrome/` (Navidrome + slskd)
- **Music disk**: external USB drive mounted at `/mnt/music` (ext4)
- **Tailscale**: remote access VPN

## Scripts

All scripts are in `scripts/`. Run them with `bash scripts/<script>.sh`.

### pi-status.sh — Full System Report

```bash
bash scripts/pi-status.sh          # Human-readable report
bash scripts/pi-status.sh --json   # JSON output for programmatic use
```

Shows: CPU model, load, uptime, temperature, RAM, swap, disk usage (SD + music),
Docker containers, Tailscale, top processes by CPU, pending updates, cache sizes.

**Temperature thresholds**: >75°C warning, >85°C critical.

### pi-services.sh — Service Management

```bash
bash scripts/pi-services.sh status              # Check all services
bash scripts/pi-services.sh restart             # Restart all
bash scripts/pi-services.sh navidrome           # Restart Navidrome only
bash scripts/pi-services.sh slskd               # Restart slskd only
bash scripts/pi-services.sh tailscale           # Restart Tailscale only
```

Containers monitored:
- `navidrome-navidrome-1` (Navidrome, port 4533)
- `navidrome-slskd-1` (slskd, ports 5030/5031)

### pi-cleanup.sh — System Cleanup

```bash
bash scripts/pi-cleanup.sh --dry-run   # Preview what would be cleaned
bash scripts/pi-cleanup.sh             # Actually clean
```

Cleans:
- APT cache (`apt-get clean`)
- Unused packages (`apt-get autoremove`)
- Journal logs older than 7 days
- `/tmp` files older than 7 days
- Docker dangling images and build cache
- slskd incomplete downloads older than 30 days

### pi-updates.sh — System Updates

```bash
bash scripts/pi-updates.sh check    # List pending updates
bash scripts/pi-updates.sh apply    # Apply all updates
```

## Quick Health Check

For a fast overview, run:

```bash
bash scripts/pi-status.sh && bash scripts/pi-services.sh status
```

## Alerts

When reporting status to the user, flag:
- Temperature > 75°C (warning) or > 85°C (critical)
- Swap heavily used (Pi has limited RAM)
- Disk usage > 80% on either drive
- Any Docker container not running or unhealthy
- Tailscale not connected
- Many pending updates (especially security-related: openssl, libssl, sudo)