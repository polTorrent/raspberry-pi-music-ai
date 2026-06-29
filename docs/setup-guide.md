# Setup Guide

A step-by-step guide to replicate this self-hosted music + AI system on a Raspberry Pi.

## Prerequisites

| Item | Recommendation |
|---|---|
| Board | Raspberry Pi 3B/3B+ or better (armv7l works, arm64 preferred) |
| microSD | 32 GB, Class 10 / A2 |
| USB drive | 1 TB+ external HDD/SSD (ext4 formatted) |
| Power supply | Official 5V 2.5A+ |
| Internet | Ethernet or WiFi |
| Accounts | Telegram bot token, Venice.ai API key, Tailscale account |

---

## Step 1: Base OS

1. Download [Raspberry Pi OS Lite (Bullseye)](https://www.raspberrypi.com/software/).
2. Flash to microSD using the Raspberry Pi Imager or `dd`.
3. Enable SSH: create an empty `ssh` file in the boot partition.
4. Boot the Pi, SSH in, and run:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   sudo raspi-config  # set locale, timezone, hostname
   ```

## Step 2: Mount the External Drive

1. Connect the USB drive and identify it:
   ```bash
   lsblk
   ```
2. Format as ext4 (if needed):
   ```bash
   sudo mkfs.ext4 /dev/sda1
   ```
3. Create mount point and add to fstab:
   ```bash
   sudo mkdir -p /mnt/music
   echo '/dev/sda1 /mnt/music ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
   sudo mount -a
   ```
   > The `nofail` flag ensures the Pi boots even if the drive is disconnected.

4. Verify:
   ```bash
   df -h /mnt/music
   ```

## Step 3: Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

Install Docker Compose:
```bash
sudo apt install -y docker-compose-plugin
# or:
sudo apt install -y python3-pip && pip3 install docker-compose
```

## Step 4: Deploy Navidrome + slskd

1. Create the project directory:
   ```bash
   mkdir -p ~/navidrome/data ~/navidrome/slskd-data
   ```

2. Copy the example compose file:
   ```bash
   cp config-examples/docker-compose.example.yml ~/navidrome/docker-compose.yml
   ```

3. Edit the compose file to match your paths:
   ```bash
   nano ~/navidrome/docker-compose.yml
   ```
   - Update volume paths if your music drive is mounted elsewhere
   - Set any Navidrome environment variables (scan schedule, log level)

4. Start the services:
   ```bash
   cd ~/navidrome
   docker compose up -d
   ```

5. Verify:
   ```bash
   docker ps
   # Navidrome should be running on :4533
   # slskd should be running on :5030/:5031
   ```

6. Configure Navidrome:
   - Open `http://<pi-ip>:4533` in your browser
   - Create an admin account
   - Navidrome will auto-scan `/music` (mapped to your USB drive)

7. Configure slskd:
   - Open `http://<pi-ip>:5031` for the web UI
   - Set your Soulseek credentials
   - Set the download folder to `/downloads` (mapped to `/mnt/music/_downloads`)
   - Generate an API key (save it — you'll need it for the Soulseek skill)

## Step 5: Install Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Authenticate with your Tailscale account. Your Pi will get a `100.x.x.x` IP address.

Verify:
```bash
tailscale status
```

You can now access the Pi remotely via the Tailscale IP from any device on your tailnet.

## Step 6: Install PicoClaw

1. Download the PicoClaw binary for arm:
   ```bash
   # Check the PicoClaw releases page for the latest version
   wget <picoclaw-release-url> -O /usr/local/bin/picoclaw
   chmod +x /usr/local/bin/picoclaw
   ```

2. Create the workspace:
   ```bash
   mkdir -p ~/.picoclaw/workspace/{memory,skills}
   ```

3. Copy the example config:
   ```bash
   cp config-examples/config.example.json ~/.picoclaw/config.json
   ```

4. Edit the config:
   ```bash
   nano ~/.picoclaw/config.json
   ```
   - Set your Telegram bot token
   - Set your Telegram chat ID (allowed user)
   - Set the model and API base (point to the Venice proxy at `http://localhost:8899`)

5. Create a Telegram bot:
   - Talk to [@BotFather](https://t.me/BotFather) on Telegram
   - Create a new bot → get the token
   - Find your chat ID (send a message to the bot, check `getUpdates` API)

## Step 7: Deploy the Venice Proxy

The proxy is a tiny Python script that injects the Venice API key into LLM requests, keeping it out of PicoClaw's config.

1. Copy the proxy script:
   ```bash
   sudo cp venice-proxy/venice-proxy.py /usr/local/bin/venice-proxy.py
   ```

2. Edit it to add your Venice API key:
   ```bash
   sudo nano /usr/local/bin/venice-proxy.py
   # Or better: set it via environment variable
   ```

3. Install the systemd service:
   ```bash
   sudo cp systemd/venice-proxy.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now venice-proxy
   ```

4. Verify:
   ```bash
   curl http://localhost:8899/health  # or just check the service
   sudo systemctl status venice-proxy
   ```

See [docs/venice-proxy.md](venice-proxy.md) for details.

## Step 8: Install Skills

Copy the skill directories into the PicoClaw workspace:

```bash
cp -r skills/* ~/.picoclaw/workspace/skills/
```

For the Soulseek skill, set the API key:
```bash
# Create an env file for the skill scripts
echo 'export SLSKD_API_KEY="your-slskd-api-key"' > ~/.picoclaw/workspace/skills/soulseek-music/scripts/env.sh
chmod 600 ~/.picoclaw/workspace/skills/soulseek-music/scripts/env.sh
```

## Step 9: Deploy PicoClaw as a Service

1. Copy the systemd unit:
   ```bash
   sudo cp systemd/picoclaw-gateway.service /etc/systemd/system/
   ```

2. Edit to set your Telegram token:
   ```bash
   sudo nano /etc/systemd/system/picoclaw-gateway.service
   # Replace the placeholder in Environment= with your actual token
   # Or use an EnvironmentFile= pointing to a secure file
   ```

3. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now picoclaw-gateway
   ```

4. Verify:
   ```bash
   sudo systemctl status picoclaw-gateway
   ```

## Step 10: Test the System

1. Send a message to your Telegram bot.
2. Try these commands:
   - "System status" — should report CPU, RAM, disk, Docker, Tailscale
   - "Search music: [artist] [album]" — should return Soulseek search results ranked by quality
   - "Music recommendations" — should generate personalized recommendations
   - "How is the library?" — should run a library health diagnostic

## Step 11: Set Up Cron Jobs (Optional)

PicoClaw supports scheduled tasks. Example:

- **Weekly recommendations**: every Monday at 10:00
- **Daily Navidrome backup**: every day at 04:00

These are configured through PicoClaw's cron system (not system crontab).

## Step 11: Connect a Music Client (Symfonium)

Now that Navidrome is running, you need a client app to actually listen to your music. Navidrome implements the Subsonic API, so any compatible client works.

### Recommended: Symfonium (Android)

1. Install [Symfonium](https://symfonium.app/) from the Play Store
2. Open the app → **Settings** → **Servers** → **Add server**
3. Configure:
   - **Server type**: Subsonic / Navidrome
   - **Server URL**: `http://<pi-ip>:4533` (LAN) or `http://<tailscale-ip>:4533` (remote)
   - **Username**: your Navidrome username
   - **Password**: your Navidrome password
4. Tap **Test connection** → should show "OK"
5. Symfonium will scan and index your library

Key features to enable:
- **Offline mode**: Pin albums for offline playback (downloads to phone storage)
- **Transcoding**: Set preferred format/quality for streaming over mobile data
- **Scrobbling**: Enabled by default — play counts sync back to Navidrome

### Other clients

| Client | Platform | Notes |
|---|---|---|
| DSub | Android | Free, open-source |
| Tempo | iOS | Modern, actively maintained |
| Feishin | Desktop (Electron) | Cross-platform |
| Jamstash | Web | Browser-based, no install needed |

> **Remote access**: Install Tailscale on your phone too. Connect to the Pi's Tailscale IP and your music streams securely from anywhere — no port forwarding needed.

## Post-Setup Checklist

- [ ] External drive auto-mounts on reboot (test with `sudo reboot`)
- [ ] Docker containers restart on reboot (`restart: unless-stopped`)
- [ ] Tailscale connects on boot
- [ ] PicoClaw starts on boot and responds on Telegram
- [ ] Venice proxy is running (`systemctl status venice-proxy`)
- [ ] Music library is organized in `Artist/Album` structure
- [ ] slskd API key is set for the Soulseek skill
- [ ] Telegram bot is restricted to your chat ID only
- [ ] Symfonium (or other Subsonic client) connects and plays music
- [ ] Remote playback works via Tailscale IP

## Troubleshooting

| Problem | Fix |
|---|---|
| Docker containers not starting | `docker compose logs` in `~/navidrome/` |
| PicoClaw not responding | `journalctl -u picoclaw-gateway -f` |
| Venice proxy errors | `journalctl -u venice-proxy -f`, check API key |
| Tailscale not connecting | `sudo tailscale status`, re-auth with `sudo tailscale up` |
| slskd can't connect to Soulseek | Check credentials in slskd web UI (:5031) |
| Navidrome not scanning | Check volume mount paths, verify `/music` has files |
| High temperature (>85°C) | Add a heatsink/fan, check `cat /sys/class/thermal/thermal_zone0/temp` |