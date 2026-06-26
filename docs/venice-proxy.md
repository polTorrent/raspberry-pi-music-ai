# Venice Proxy

## Why a proxy?

PicoClaw needs to call an LLM API to process user messages. By default, it would need the API key stored in its config file or environment. This creates two problems:

1. **Key exposure**: The API key would be visible in PicoClaw's config (`~/.picoclaw/config.json`), which the AI itself can read.
2. **Inflexibility**: Changing LLM providers would require editing PicoClaw's config and restarting the service.

The Venice proxy solves both: it's a tiny HTTP server that injects the API key transparently, so PicoClaw only needs to know `http://localhost:8899` as its API base.

## How it works

```
PicoClaw                    Venice Proxy (:8899)              Venice.ai API
   │                              │                                │
   │  POST /v1/chat/completions   │                                │
   │  (no API key)                │                                │
   ├─────────────────────────────►│                                │
   │                              │  POST /api/v1/chat/completions  │
   │                              │  Authorization: Bearer <KEY>    │
   │                              ├───────────────────────────────►│
   │                              │                                │
   │                              │  200 OK (JSON)                  │
   │                              │◄───────────────────────────────┤
   │  200 OK (JSON)               │                                │
   │◄─────────────────────────────┤                                │
```

The proxy:
1. Listens on `127.0.0.1:8899` (localhost only — not exposed to network)
2. Receives the request from PicoClaw as-is
3. Adds the `Authorization: Bearer <API_KEY>` header
4. Forwards to `https://api.venice.ai/api/v1`
5. Returns the response back to PicoClaw

## The script

The proxy is ~30 lines of Python using only the standard library (`http.server` + `urllib`). No dependencies, no frameworks.

```python
#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import os

VENICE_KEY = os.environ.get("VENICE_API_KEY", "")
VENICE_URL = "https://api.venice.ai/api/v1"

class Proxy(BaseHTTPRequestHandler):
    def _proxy(self, method):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len > 0 else None

        req = urllib.request.Request(VENICE_URL + self.path, data=body, method=method)
        req.add_header('Authorization', f'Bearer {VENICE_KEY}')
        req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)

    def do_POST(self): self._proxy('POST')
    def do_GET(self): self._proxy('GET')
    def log_message(self, *a): pass

print("Venice proxy a http://localhost:8899")
HTTPServer(('127.0.1', 8899), Proxy).serve_forever()
```

## Security considerations

- **Localhost only**: The proxy binds to `127.0.0.1`, so it's not reachable from the network or other machines (even on Tailscale).
- **Key via environment variable**: The API key should be loaded from `os.environ.get("VENICE_API_KEY")`, not hardcoded. Set it in the systemd unit or an environment file.
- **No logging**: The proxy suppresses request logs (`log_message` is a no-op) to avoid leaking request data.
- **PicoClaw can't see the key**: PicoClaw's config only references `http://localhost:8899` as the API base. It never has access to the actual Venice API key.

## Adapting for other LLM providers

The proxy pattern works with any OpenAI-compatible API. To use a different provider:

1. Change `VENICE_URL` to the provider's base URL (e.g., `https://api.openai.com/v1`).
2. Change the environment variable name (e.g., `OPENAI_API_KEY`).
3. Update the systemd service to set the new environment variable.

Example for OpenAI:
```python
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_URL = "https://api.openai.com/v1"
```

Example for a local LLM (Ollama):
```python
# No proxy needed — PicoClaw can call Ollama directly
# Just set api_base to http://localhost:11434/v1 in PicoClaw config
```

## Deployment

The proxy runs as a systemd service:

```ini
[Unit]
Description=Venice API Proxy
After=network.target

[Service]
Type=simple
User=pi
Environment="VENICE_API_KEY=your-key-here"
ExecStart=/usr/bin/python3 /usr/local/bin/venice-proxy.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **Tip**: For better security, use an `EnvironmentFile=` pointing to a file with restricted permissions (`chmod 600`) instead of hardcoding the key in the service file.

## PicoClaw configuration

In PicoClaw's `config.json`, the model entry points to the proxy:

```json
{
  "model_name": "venice-glm-5.2",
  "provider": "vllm",
  "api_base": "http://localhost:8899",
  "model": "your-model-id"
}
```

PicoClaw sends requests to `http://localhost:8899/v1/chat/completions`, the proxy forwards them to Venice.ai with the API key injected, and the response flows back.