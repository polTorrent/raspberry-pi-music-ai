# Venice Proxy

A lightweight HTTP proxy that injects the Venice.ai API key into LLM requests, keeping the key out of PicoClaw's configuration.

## Why?

PicoClaw needs to call an LLM API. If the API key were stored in PicoClaw's config, the AI itself could read it. This proxy solves that by holding the key and forwarding requests transparently.

## Setup

1. Copy the proxy script:
   ```bash
   sudo cp venice-proxy.py /usr/local/bin/venice-proxy.py
   ```

2. Set the API key. Choose one method:

   **Option A — systemd Environment (recommended):**
   ```ini
   # In the .service file:
   Environment="VENICE_API_KEY=your-key-here"
   ```

   **Option B — Environment file (more secure):**
   ```bash
   echo 'VENICE_API_KEY=your-key-here' | sudo tee /etc/venice-proxy.env
   sudo chmod 600 /etc/venice-proxy.env
   ```
   ```ini
   # In the .service file:
   EnvironmentFile=/etc/venice-proxy.env
   ```

3. Install the systemd service:
   ```bash
   sudo cp ../systemd/venice-proxy.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now venice-proxy
   ```

4. Verify:
   ```bash
   sudo systemctl status venice-proxy
   curl -s http://localhost:8899/  # should get a response from Venice API
   ```

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `VENICE_API_KEY` | (required) | Venice.ai API key |
| `VENICE_API_URL` | `https://api.venice.ai/api/v1` | Base URL for the API |
| `PROXY_HOST` | `127.0.0.1` | Bind address (keep localhost) |
| `PROXY_PORT` | `8899` | Listen port |

## Adapting for other providers

See [docs/venice-proxy.md](../docs/venice-proxy.md) for instructions on adapting the proxy for OpenAI, Ollama, or other OpenAI-compatible APIs.

## Security notes

- Binds to `127.0.0.1` only — not reachable from the network
- Suppresses request logging for privacy
- No external dependencies (pure Python stdlib)
- The API key never appears in PicoClaw's config or workspace