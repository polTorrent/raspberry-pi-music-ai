#!/usr/bin/env python3
"""
Venice API Proxy — lightweight HTTP proxy that injects the Venice API key
into LLM requests so PicoClaw doesn't need to store it.

Binds to 127.0.0.1:8899 (localhost only — not exposed to network).

Set the API key via environment variable:
    export VENICE_API_KEY="your-key-here"
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
import os

VENICE_KEY = os.environ.get("VENICE_API_KEY", "")
VENICE_URL = os.environ.get("VENICE_API_URL", "https://api.venice.ai/api/v1")

if not VENICE_KEY:
    print("WARNING: VENICE_API_KEY not set — proxy will forward without auth")


class Proxy(BaseHTTPRequestHandler):
    def _proxy(self, method):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len > 0 else None

        url = VENICE_URL + self.path
        req = urllib.request.Request(url, data=body, method=method)
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
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(f'{{"error": "proxy error: {str(e)}"}}'.encode())

    def do_POST(self):
        self._proxy('POST')

    def do_GET(self):
        self._proxy('GET')

    def log_message(self, *args):
        """Suppress request logging for privacy."""
        pass


if __name__ == '__main__':
    HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
    PORT = int(os.environ.get("PROXY_PORT", 8899))
    print(f"Venice proxy listening on http://{HOST}:{PORT}")
    HTTPServer((HOST, PORT), Proxy).serve_forever()