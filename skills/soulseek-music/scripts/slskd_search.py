#!/usr/bin/env python3
"""
slskd_search.py — Search Soulseek via slskd REST API, group results, rank by quality.

Usage:
    python3 slskd_search.py "search query" [--max-wait 60] [--top 10]

Output: JSON to stdout with ranked results.

Environment variables:
    SLSKD_BASE     — slskd base URL (default: http://localhost:5030)
    SLSKD_API_KEY  — API key (required)
"""

import json
import sys
import time
import os
import urllib.request
import urllib.error

BASE = os.environ.get("SLSKD_BASE", "http://localhost:5030")
API_KEY = os.environ.get("SLSKD_API_KEY", "")

if not API_KEY:
    print(json.dumps({"error": "SLSKD_API_KEY not set"}))
    sys.exit(1)

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Quality scoring for file formats
FORMAT_SCORES = {
    "flac": 100, "wav": 95, "ape": 90,
    "m4a": 70, "mp3": 60, "ogg": 50, "opus": 55, "wma": 30,
}


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


def start_search(query):
    result = api_request("POST", "/api/v0/searches", {"SearchText": query})
    if "error" in result:
        return None
    search_id = result.get("id")
    return search_id


def wait_for_results(search_id, max_wait=60):
    for i in range(max_wait):
        time.sleep(2)
        state = api_request("GET", f"/api/v0/searches/{search_id}")
        if state.get("isComplete", False):
            break
        file_count = state.get("fileCount", 0)
        response_count = state.get("responseCount", 0)
        print(f"  Waiting... {response_count} responses, {file_count} files", file=sys.stderr)
    return True


def get_results(search_id):
    return api_request("GET", f"/api/v0/searches/{search_id}/responses")


def rank_results(results, query):
    """Group by username+directory, score, and rank."""
    groups = {}

    for r in results:
        username = r.get("username", "")
        for f in r.get("files", []):
            dirname = os.path.dirname(f.get("filename", ""))
            key = f"{username}|{dirname}"
            if key not in groups:
                groups[key] = {
                    "username": username,
                    "directory": dirname,
                    "files": [],
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "extensions": set(),
                    "bitrates": [],
                    "locked_count": 0,
                }
            g = groups[key]
            g["files"].append({
                "filename": f.get("filename", ""),
                "size": f.get("size", 0),
                "bitrate": f.get("bitRate", 0),
                "extension": os.path.splitext(f.get("filename", ""))[1].lower().lstrip("."),
            })
            g["file_count"] += 1
            g["total_size_bytes"] += f.get("size", 0)
            ext = os.path.splitext(f.get("filename", ""))[1].lower().lstrip(".")
            g["extensions"].add(ext)
            if f.get("bitRate"):
                g["bitrates"].append(f["bitRate"])
            if f.get("locked", False):
                g["locked_count"] += 1

    # Score each group
    scored = []
    for key, g in groups.items():
        score = 0

        # Format quality
        for ext in g["extensions"]:
            score += FORMAT_SCORES.get(ext, 10)

        # File count (more = better, complete album)
        score += min(g["file_count"] * 5, 50)

        # Bitrate
        if g["bitrates"]:
            avg_br = sum(g["bitrates"]) / len(g["bitrates"])
            score += min(int(avg_br / 10), 40)

        # Locked files penalty
        score -= g["locked_count"] * 15

        # Query terms in directory name
        query_lower = query.lower()
        dir_lower = g["directory"].lower()
        for term in query_lower.split():
            if term in dir_lower:
                score += 10

        # Size bonus
        size_mb = g["total_size_bytes"] / (1024 * 1024)
        score += min(int(size_mb / 10), 20)

        g["extensions"] = sorted(g["extensions"])
        g["avg_bitrate"] = int(sum(g["bitrates"]) / len(g["bitrates"])) if g["bitrates"] else 0
        g["total_size_mb"] = round(size_mb, 1)
        g["score"] = score
        scored.append(g)

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Add rank
    for i, g in enumerate(scored):
        g["rank"] = i + 1

    return scored


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 slskd_search.py \"query\" [--max-wait N] [--top N]", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    max_wait = 60
    top_n = 10

    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--max-wait" and i + 1 < len(sys.argv):
            max_wait = int(sys.argv[i + 1])
        elif arg == "--top" and i + 1 < len(sys.argv):
            top_n = int(sys.argv[i + 1])

    print(f"Searching: {query}", file=sys.stderr)
    search_id = start_search(query)
    if not search_id:
        print(json.dumps({"error": "Failed to start search"}))
        sys.exit(1)

    print(f"Search ID: {search_id}", file=sys.stderr)
    wait_for_results(search_id, max_wait)

    results = get_results(search_id)
    if isinstance(results, dict) and "error" in results:
        print(json.dumps(results))
        sys.exit(1)

    ranked = rank_results(results, query)
    output = {
        "query": query,
        "total_results": len(ranked),
        "results": ranked[:top_n],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()