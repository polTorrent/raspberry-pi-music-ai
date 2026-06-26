# Skill: Soulseek Music (slskd)

## Description
Search and download music from Soulseek via the slskd REST API. Returns ranked results grouped by user/folder before downloading, so you can pick the best option.

## When to Use
- User asks to search for music on Soulseek
- User asks to download music/albums
- User wants to find the best quality version of an album
- User asks to check download status

## Prerequisites
- slskd running and connected to Soulseek (Docker container, port 5030)
- Environment variable `SLSKD_API_KEY` set (API key from slskd config)

## Configuration
The scripts read from environment variables:
- `SLSKD_BASE` — slskd base URL (default: `http://localhost:5030`)
- `SLSKD_API_KEY` — API key for authentication (required)

To set the API key for all commands, export it or add to the shell profile:
```bash
export SLSKD_API_KEY="your-api-key-here"
```

## Scripts

### `slskd_search.py` — Search & Rank
Searches Soulseek, waits for results, groups by user/folder, and ranks by quality.

```bash
python3 scripts/slskd_search.py "Aphex Twin Selected Ambient Works" [--max-wait 60] [--top 10]
```

Output: JSON with ranked results. Each result includes:
- `rank` — position in ranking
- `username` — Soulseek user sharing the files
- `directory` — shared folder path
- `file_count` — number of files in this group
- `total_size_mb` — total size
- `extensions` — file formats (flac, mp3, etc.)
- `avg_bitrate` — average bitrate (kbps)
- `locked_files` — number of locked/restricted files
- `score` — ranking score
- `files` — list of individual files with filename, size, bitrate

**Ranking criteria:**
- FLAC > WAV > APE > MP3 320 > MP3 192 > other
- More files = better (complete albums)
- Higher bitrate = better
- Fewer locked files = better
- Query terms in directory name = bonus
- Larger total size = bonus

### `slskd_download.py` — Download
Enqueues downloads via the slskd batch API.

```bash
# Download from search results (by rank)
python3 scripts/slskd_download.py --from-json results.json --rank 1

# Download specific files from a user
python3 scripts/slskd_download.py --username "user123" --files "path\\to\\file.flac" --files "path\\to\\file2.flac"

# Check download status
python3 scripts/slskd_download.py --status
```

Downloads go to the slskd configured download directory.
Use `--destination` to specify a subfolder within the download directory.

## API Reference
- `POST /api/v0/searches` — start search (body: `{"SearchText": "..."}`)
- `GET /api/v0/searches/{id}` — get search state
- `GET /api/v0/searches/{id}/responses` — get search results
- `POST /api/v0/transfers/downloads/batches` — enqueue batch download
- `GET /api/v0/transfers/downloads` — list all downloads
- `DELETE /api/v0/transfers/downloads/{username}/{id}` — cancel download
- `DELETE /api/v0/transfers/downloads/all/completed` — clear completed

All requests require header `X-API-Key: <key>`.

## Workflow
1. Run `slskd_search.py` with the search query → save output to JSON
2. Present ranked results to the user
3. User picks a rank number
4. Run `slskd_download.py --from-json <file> --rank <N>` to download
5. Monitor with `slskd_download.py --status` if needed