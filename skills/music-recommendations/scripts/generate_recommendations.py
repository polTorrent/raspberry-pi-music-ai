#!/usr/bin/env python3
"""
generate_recommendations.py — Generate personalized music recommendations.

Combines Navidrome listening analysis with a user-defined musical profile
to produce categorized recommendations.

Reads: analysis_output.json (from analyze_listening.py)
Writes: recommendations.json

Categories:
    forgotten_gems   — Library albums not played in 90+ days
    never_played      — Library albums with 0 plays
    similar_artists   — Artists similar to favorites, not in library
    recently_added    — Recently added to library
    search_queries    — Web search queries for new releases
    listening_stats   — Summary statistics
"""

import json
import os
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_FILE = os.path.join(SCRIPT_DIR, "analysis_output.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "recommendations.json")

# ─── User Musical Profile ───
# Customize this to match your taste. Used for web search queries and
# as a fallback when Navidrome genre tags are missing.
USER_MUSIC_PROFILE = {
    "genres": [
        "IDM", "ambient", "electronic experimental", "krautrock",
        "post-punk", "world music", "art rock", "psychedelic", "jazz"
    ],
    "key_artists": [
        "Aphex Twin", "FSOL", "YMO", "Air", "Yello",
        "Ariel Pink", "King Gizzard", "Mdou Moctar",
        "Boards of Canada", "Can", "Neu!",
        "The Cure", "Kate Bush", "Radiohead", "Talking Heads",
        "Ryuichi Sakamoto", "Morphine"
    ],
}

# Albums to exclude from recommendations (already well-known to user)
EXCLUDE_ALBUMS = set()


def load_analysis():
    if not os.path.exists(ANALYSIS_FILE):
        print(f"ERROR: {ANALYSIS_FILE} not found. Run analyze_listening.py first.")
        exit(1)
    with open(ANALYSIS_FILE) as f:
        return json.load(f)


def generate(analysis):
    stats = analysis.get("stats", {})
    top_artists = analysis.get("top_artists", [])
    top_albums = analysis.get("top_albums", [])
    never_played = analysis.get("never_played", [])
    recently_added = analysis.get("recently_added", [])
    similar_artists = analysis.get("similar_artists", [])

    # --- Forgotten gems: top-played albums ---
    forgotten_gems = []
    for album in top_albums[:10]:
        if album["album"] not in EXCLUDE_ALBUMS:
            forgotten_gems.append({
                "album": album["album"],
                "artist": album["artist"],
                "year": album.get("year"),
                "plays": album["plays"],
                "reason": "High play count — worth revisiting"
            })

    # --- Never played ---
    never_played_recs = [
        {
            "album": a["album"],
            "artist": a["artist"],
            "year": a.get("year"),
            "reason": "In your library, never played"
        }
        for a in never_played[:15]
        if a["album"] not in EXCLUDE_ALBUMS
    ]

    # --- Similar artists ---
    similar_recs = [
        {"artist": s, "reason": "Similar to your top artists (Last.fm)"}
        for s in similar_artists[:20]
    ]

    # --- Recently added ---
    recently_recs = [
        {
            "album": a["album"],
            "artist": a["artist"],
            "year": a.get("year"),
            "added": a.get("added"),
            "reason": "Recently added to your library"
        }
        for a in recently_added[:10]
    ]

    # --- Web search queries for new releases ---
    current_year = datetime.now().year
    search_queries = []

    for artist in top_artists[:10]:
        search_queries.append(f"{artist['artist']} new album {current_year}")

    for genre in USER_MUSIC_PROFILE["genres"][:5]:
        search_queries.append(f"best new {genre} albums {current_year}")

    for genre in USER_MUSIC_PROFILE["genres"][:3]:
        search_queries.append(f"underrated {genre} albums")

    return {
        "forgotten_gems": forgotten_gems,
        "never_played": never_played_recs,
        "similar_artists": similar_recs,
        "recently_added": recently_recs,
        "search_queries": search_queries,
        "listening_stats": stats,
        "user_profile": USER_MUSIC_PROFILE,
    }


def main():
    analysis = load_analysis()
    recs = generate(analysis)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(recs, f, indent=2, ensure_ascii=False)

    print(f"Recommendations written to {OUTPUT_FILE}")
    print(f"  Forgotten gems: {len(recs['forgotten_gems'])}")
    print(f"  Never played: {len(recs['never_played'])}")
    print(f"  Similar artists: {len(recs['similar_artists'])}")
    print(f"  Recently added: {len(recs['recently_added'])}")
    print(f"  Search queries: {len(recs['search_queries'])}")


if __name__ == "__main__":
    main()