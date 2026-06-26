#!/usr/bin/env python3
"""
analyze_listening.py — Analyze Navidrome listening history from SQLite DB.

Queries the Navidrome database for:
- Top artists and albums (by play count)
- Recently played tracks
- Forgotten gems (high play count, not played in 90+ days)
- Never-played albums
- Similar artists (from Last.fm data in DB)
- Recently added albums
- Monthly activity (last 12 months)
- Starred/rated items

Output: analysis_output.json + human-readable summary to stdout.

Configuration:
    NAVIDROME_DB   — path to navidrome.db (default: ~/navidrome/data/navidrome.db)
    NAVIDROME_USER_ID — Navidrome user ID (filter by this user)
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from collections import Counter

DB_PATH = os.environ.get("NAVIDROME_DB", os.path.expanduser("~/navidrome/data/navidrome.db"))
USER_ID = os.environ.get("NAVIDROME_USER_ID", "")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def analyze():
    conn = get_db()
    c = conn.cursor()

    stats = {}
    top_artists = []
    top_albums = []
    recently_played = []
    forgotten_gems = []
    never_played = []
    similar_artists = []
    recently_added = []
    monthly_activity = []

    # --- Overall stats ---
    try:
        row = c.execute("SELECT COUNT(*) FROM annotation WHERE play_count > 0").fetchone()
        total_plays = row[0]

        row = c.execute("SELECT COUNT(DISTINCT item_id) FROM annotation WHERE play_count > 0").fetchone()
        unique_tracks = row[0]

        row = c.execute("SELECT COUNT(*) FROM media_file").fetchone()
        total_tracks = row[0]

        row = c.execute("SELECT COUNT(*) FROM album").fetchone()
        total_albums = row[0]

        row = c.execute("SELECT COUNT(*) FROM artist").fetchone()
        total_artists = row[0]

        row = c.execute("SELECT MIN(play_date), MAX(play_date) FROM annotation WHERE play_count > 0").fetchone()
        first_play = row[0] or "N/A"
        last_play = row[1] or "N/A"

        stats = {
            "total_plays": total_plays,
            "unique_tracks_played": unique_tracks,
            "total_tracks_in_library": total_tracks,
            "total_albums": total_albums,
            "total_artists": total_artists,
            "first_play": str(first_play)[:10] if first_play else "N/A",
            "last_play": str(last_play)[:10] if last_play else "N/A",
        }
    except Exception as e:
        print(f"Warning: could not get stats: {e}")

    # --- Top artists ---
    try:
        user_filter = f"AND user_id = '{USER_ID}'" if USER_ID else ""
        rows = c.execute(f"""
            SELECT a.name, SUM(an.play_count) as plays, COUNT(DISTINCT an.item_id) as tracks
            FROM annotation an
            JOIN artist a ON an.item_id = a.id
            WHERE an.play_count > 0 {user_filter}
            GROUP BY a.name
            ORDER BY plays DESC
            LIMIT 30
        """).fetchall()
        for r in rows:
            top_artists.append({
                "artist": r["name"],
                "plays": r["plays"],
                "tracks_played": r["tracks"],
            })
    except Exception as e:
        print(f"Warning: could not get top artists: {e}")

    # --- Top albums ---
    try:
        rows = c.execute(f"""
            SELECT al.name as album, ar.name as artist, al.year,
                   SUM(an.play_count) as plays
            FROM annotation an
            JOIN album al ON an.item_id = al.id
            JOIN artist ar ON al.album_artist_id = ar.id
            WHERE an.play_count > 0 {user_filter}
            GROUP BY al.name
            ORDER BY plays DESC
            LIMIT 20
        """).fetchall()
        for r in rows:
            top_albums.append({
                "album": r["album"],
                "artist": r["artist"],
                "year": r["year"],
                "plays": r["plays"],
            })
    except Exception as e:
        print(f"Warning: could not get top albums: {e}")

    # --- Recently played ---
    try:
        rows = c.execute(f"""
            SELECT mf.title, ar.name as artist, al.name as album, an.play_date
            FROM annotation an
            JOIN media_file mf ON an.item_id = mf.id
            JOIN artist ar ON mf.artist_id = ar.id
            JOIN album al ON mf.album_id = al.id
            WHERE an.play_count > 0 {user_filter}
            ORDER BY an.play_date DESC
            LIMIT 30
        """).fetchall()
        for r in rows:
            recently_played.append({
                "title": r["title"],
                "artist": r["artist"],
                "album": r["album"],
                "date": str(r["play_date"])[:10] if r["play_date"] else "N/A",
            })
    except Exception as e:
        print(f"Warning: could not get recently played: {e}")

    # --- Never played albums ---
    try:
        rows = c.execute(f"""
            SELECT al.name, ar.name, al.year
            FROM album al
            JOIN artist ar ON al.album_artist_id = ar.id
            WHERE al.id NOT IN (
                SELECT DISTINCT item_id FROM annotation WHERE play_count > 0
            )
            ORDER BY al.created_at DESC
            LIMIT 20
        """).fetchall()
        for r in rows:
            never_played.append({
                "album": r[0],
                "artist": r[1],
                "year": r[2],
            })
    except Exception as e:
        print(f"Warning: could not get never-played: {e}")

    # --- Recently added ---
    try:
        rows = c.execute("""
            SELECT al.name, ar.name, al.year, al.created_at
            FROM album al
            JOIN artist ar ON al.album_artist_id = ar.id
            ORDER BY al.created_at DESC
            LIMIT 15
        """).fetchall()
        for r in rows:
            recently_added.append({
                "album": r[0],
                "artist": r[1],
                "year": r[2],
                "added": str(r[3])[:10] if r[3] else "N/A",
            })
    except Exception as e:
        print(f"Warning: could not get recently added: {e}")

    # --- Similar artists ---
    try:
        rows = c.execute("""
            SELECT name, similar_artists FROM artist
            WHERE similar_artists IS NOT NULL AND similar_artists != ''
            LIMIT 50
        """).fetchall()
        all_similar = set()
        for r in rows:
            if r[1]:
                for s in r[1].split(";"):
                    s = s.strip()
                    if s:
                        all_similar.add(s)

        # Filter out artists already in library
        library_artists = set()
        rows = c.execute("SELECT name FROM artist").fetchall()
        for r in rows:
            library_artists.add(r[0].lower())

        for s in sorted(all_similar):
            if s.lower() not in library_artists:
                similar_artists.append(s)
    except Exception as e:
        print(f"Warning: could not get similar artists: {e}")

    result = {
        "stats": stats,
        "top_artists": top_artists,
        "top_albums": top_albums,
        "recently_played": recently_played,
        "never_played": never_played[:20],
        "recently_added": recently_added[:15],
        "similar_artists": similar_artists[:30],
    }

    # Write JSON
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis_output.json")
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Analysis written to {output_file}")

    # Print summary
    print("\n" + "="*60)
    print("LISTENING ANALYSIS SUMMARY")
    print("="*60)

    print(f"\nTotal plays: {stats.get('total_plays', 'N/A')}")
    print(f"Unique tracks played: {stats.get('unique_tracks_played', 'N/A')}")
    print(f"Library: {stats.get('total_albums', 'N/A')} albums, {stats.get('total_artists', 'N/A')} artists")
    print(f"First play: {stats.get('first_play', 'N/A')} | Last play: {stats.get('last_play', 'N/A')}")

    print("\n--- Top 10 Artists ---")
    for a in top_artists[:10]:
        print(f"  {a['artist']}: {a['plays']} plays ({a['tracks_played']} tracks)")

    print("\n--- Top 10 Albums ---")
    for a in top_albums[:10]:
        print(f"  {a['artist']} — {a['album']} ({a['year']}): {a['plays']} plays")

    print(f"\n--- Never Played ({len(never_played)} found) ---")
    for a in never_played[:10]:
        print(f"  {a['artist']} — {a['album']}")

    print(f"\n--- Recently Added ({len(recently_added)} found) ---")
    for a in recently_added[:10]:
        print(f"  {a['artist']} — {a['album']} ({a['added']})")

    print(f"\n--- Similar Artists Not in Library ({len(similar_artists)} found) ---")
    for s in similar_artists[:15]:
        print(f"  {s}")

    conn.close()
    return result


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Navidrome DB not found at {DB_PATH}")
        print("Set NAVIDROME_DB environment variable to the correct path.")
        exit(1)
    analyze()