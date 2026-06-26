#!/usr/bin/env python3
"""
print_recs.py — Print recommendations in human-readable format.

Reads: recommendations.json (from generate_recommendations.py)
Output: formatted text to stdout, suitable for sending to the user.
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECS_FILE = os.path.join(SCRIPT_DIR, "recommendations.json")


def main():
    if not os.path.exists(RECS_FILE):
        print(f"ERROR: {RECS_FILE} not found. Run generate_recommendations.py first.")
        exit(1)

    with open(RECS_FILE) as f:
        recs = json.load(f)

    print("🎵 RECOMANACIONS MUSICALS SETMANALS\n")
    print("="*50 + "\n")

    # Forgotten gems
    gems = recs.get("forgotten_gems", [])
    if gems:
        print("🔄 JOIES OBLIDADES\n")
        for g in gems[:5]:
            year = f" ({g['year']})" if g.get("year") else ""
            print(f"  • {g['artist']} — {g['album']}{year}")
            print(f"    {g['plays']} reproduccions\n")

    # Never played
    never = recs.get("never_played", [])
    if never:
        print("💎 ÀLBUMS PER DESCobrir (sense escoltar)\n")
        for a in never[:10]:
            year = f" ({a['year']})" if a.get("year") else ""
            print(f"  • {a['artist']} — {a['album']}{year}")
        print()

    # Similar artists
    similar = recs.get("similar_artists", [])
    if similar:
        print("🎯 ARTISTES SIMILARS\n")
        for s in similar[:15]:
            print(f"  • {s['artist']}")
        print()

    # Recently added
    recent = recs.get("recently_added", [])
    if recent:
        print("🆕 AFEGITS RECENTMENT\n")
        for a in recent[:10]:
            year = f" ({a['year']})" if a.get("year") else ""
            print(f"  • {a['artist']} — {a['album']}{year}")
        print()

    # Search queries (for the agent to execute)
    queries = recs.get("search_queries", [])
    if queries:
        print("🔍 CERQUES WEB PENDENTS\n")
        print("L'agent ha de cercar novetats amb aquestes queries:")
        for q in queries:
            print(f"  • {q}")
        print()

    print("="*50)
    print("Per descarregar qualsevol recomanació, demana-ho!")


if __name__ == "__main__":
    main()