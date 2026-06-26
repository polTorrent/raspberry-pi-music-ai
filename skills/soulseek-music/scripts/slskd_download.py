#!/usr/bin/env python3
"""
slskd_download.py — Download music from Soulseek via slskd REST API.

Usage:
    # Download from search results (by rank)
    python3 slskd_download.py --from-json results.json --rank 1

    # Download specific files from a user
    python3 slskd_download.py --username "user" --files "path/to/file.flac"

    # Check download status
    python3 slskd_download.py --status

Environment variables:
    SLSKD_BASE     — slskd base URL (default: http://localhost:5030)
    SLSKD_API_KEY  — API key (required)
"""

import json
import sys
import os
import urllib.request
import urllib.error

BASE = os.environ.get("SLSKD_BASE", "http://localhost:5030")
API_KEY = os.environ.get("SLSKD_API_KEY", "")

if not API_KEY:
    print(json.dumps({"error": "SLSKD_API_KEY not set"}))
    sys.exit(1)

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def api_request(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}", "detail": error_body}
    except Exception as e:
        return {"error": str(e)}


def download_from_rank(json_file, rank):
    """Download files from a search results JSON by rank number."""
    with open(json_file) as f:
        data = json.load(f)

    results = data.get("results", [])
    if rank < 1 or rank > len(results):
        print(json.dumps({"error": f"Rank {rank} out of range (1-{len(results)})"}))
        sys.exit(1)

    selected = results[rank - 1]
    username = selected["username"]
    files = [f["filename"] for f in selected["files"]]

    print(f"Downloading {len(files)} files from {username}", file=sys.stderr)
    print(f"Directory: {selected['directory']}", file=sys.stderr)

    # Enqueue batch download
    batch = [{"username": username, "files": files}]
    result = api_request("POST", "/api/v0/transfers/downloads/batches", batch)

    if "error" in result:
        print(json.dumps(result))
        sys.exit(1)

    print(json.dumps({
        "status": "queued",
        "username": username,
        "file_count": len(files),
        "directory": selected["directory"]
    }, indent=2))


def download_specific(username, files):
    """Download specific files from a user."""
    print(f"Downloading {len(files)} files from {username}", file=sys.stderr)

    batch = [{"username": username, "files": files}]
    result = api_request("POST", "/api/v0/transfers/downloads/batches", batch)

    if "error" in result:
        print(json.dumps(result))
        sys.exit(1)

    print(json.dumps({
        "status": "queued",
        "username": username,
        "file_count": len(files)
    }, indent=2))


def check_status():
    """Check download status."""
    data = api_request("GET", "/api/v0/transfers/downloads")
    if "error" in data:
        print(json.dumps(data))
        sys.exit(1)

    downloads = []
    for user_group in data:
        username = user_group.get("username", "?")
        for d in user_group.get("directories", []):
            for f in d.get("files", []):
                pct = f.get("percentComplete", 0)
                state = f.get("state", "unknown")
                filename = f.get("filename", "?")
                downloads.append({
                    "username": username,
                    "filename": os.path.basename(filename),
                    "state": state,
                    "percent": pct,
                })

    if not downloads:
        print(json.dumps({"status": "no active downloads"}))
        return

    print(json.dumps({"downloads": downloads}, indent=2, ensure_ascii=False))


def main():
    if len(sys.argv) < 2:
        print("Usage:", file=sys.stderr)
        print("  python3 slskd_download.py --from-json results.json --rank N", file=sys.stderr)
        print("  python3 slskd_download.py --username \"user\" --files \"file1\" --files \"file2\"", file=sys.stderr)
        print("  python3 slskd_download.py --status", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--status":
        check_status()
        return

    if sys.argv[1] == "--from-json":
        json_file = sys.argv[2]
        rank = 1
        for i, arg in enumerate(sys.argv[3:], 3):
            if arg == "--rank" and i + 1 < len(sys.argv):
                rank = int(sys.argv[i + 1])
        download_from_rank(json_file, rank)
        return

    if sys.argv[1] == "--username":
        username = sys.argv[2]
        files = []
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--files" and i + 1 < len(sys.argv):
                files.append(sys.argv[i + 1])
                i += 2
            else:
                i += 1
        if not files:
            print("Error: no files specified", file=sys.stderr)
            sys.exit(1)
        download_specific(username, files)
        return

    print(f"Unknown command: {sys.argv[1]}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()