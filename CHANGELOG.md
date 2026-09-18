# Changelog

All notable changes to the Mahdi IPTV M3U8 project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2024-01-01

### Initial Release

The first stable release of the Mahdi IPTV M3U8 pipeline -- a four-stage processing system that transforms raw IPTV M3U playlists into clean, ordered, player-ready output.

### Pipeline Overview

```
scan.m3u -> adult_filter.py -> logos.py -> config.py -> order_m3u.py -> mahdi_iptv.m3u8
```

### Added

#### adult_filter.py

- Reads `scan.m3u` and removes channels containing adult/explicit content
- 34 keyword patterns matched via pre-compiled regex for fast scanning
- Checks both the `#EXTINF` metadata line and the stream URL for each channel
- Keywords include: adult, xxx, porn, sex, erotic, hentai, nude, milf, hardcore, and many more
- Removed channels are logged with counts for removed vs kept channels
- Operates in-place -- overwrites `scan.m3u` with the cleaned result

#### logos.py

- Contains `LOGO_DB` dictionary mapping 900+ channel names to logo image URLs
- Covers Bangladeshi channels (BTV, ATN, Channel i, NTV, Jamuna, etc.)
- Covers Indian channels (Star, Zee, Sony, Colors, DD, etc.)
- Covers international sports (ESPN, Sky Sports, Sony Ten, etc.)
- Covers kids channels (Cartoon Network, Nickelodeon, POGO, etc.)
- Supports multiple name variants per channel for reliable matching

#### config.py

- `CHANNEL_ORDER` list defining the exact output channel sequence (170+ keywords)
- Bangladesh channels listed first, followed by Indian channels, then generic categories
- Performance tuning parameters:
  - `MAX_WORKERS` (200) for parallel URL checking
  - `SOURCE_TIMEOUT` (120s) for source playlist fetching
  - `CHECK_TIMEOUT` (3s) for per-channel health checks
  - `SKIP_URL_CHECK` toggle for fast mode vs verified mode
  - `CHECK_RETRIES`, `READ_WINDOW`, `MIN_THROUGHPUT_KBPS` for stream quality validation
  - `BUFFER_THRESHOLD` for latency-based filtering
- Safety parameters:
  - `MIN_OUTPUT_RATIO` (0.5) prevents overwriting good playlists with broken ones
  - `MIN_OUTPUT_CHANNELS` (20) ensures minimum channel count
  - `SOURCE_RETRIES` with exponential backoff for source playlist resilience

#### order_m3u.py

- Reads `scan.m3u` and outputs `mahdi_iptv.m3u8`
- Parses M3U entries into (extinf, metadata, url) blocks
- Sorts channels by position in `CHANNEL_ORDER`
- Assigns permanent `tvg-chno` numbers based on keyword slot position
- Removes `group-title` attributes for a clean flat playlist
- Appends unlisted channels (no keyword match) after all listed channels
- Never drops channels -- every entry in the input appears in the output

### How Channel Numbers Work

- Channel number N corresponds to position N in `CHANNEL_ORDER`
- Numbers are permanent -- tied to the keyword list, not to surviving channels
- Inserting a keyword shifts all subsequent numbers
- Unlisted channels receive numbers starting after the last keyword position

### Configuration Highlights

#### CHANNEL_ORDER Structure

```python
CHANNEL_ORDER = [
    # Bangladesh (positions 1-59)
    "BTV", "ATN", "Channel i", "Jamuna", "Somoy", "Ekattor",
    "NTV", "Boishakhi", "Desh", "Gazi", "DBC", "MyTV", "SA TV",
    "RTV", "Maasranga", "Independent TV", "News24", "Channel 24",
    "Mohona", "Bijoy", "BanglaVision", "Asian TV", "Duronto TV",
    "Ananda TV", "Deepto TV", "Bangla TV", "Global TV", "Channel S",
    "Green TV", "Ruposhi Bangla", "Movie Bangla", "Music Bangla",
    "Bangla Plus", "Channel 9",

    # India (positions 60-165)
    "Star", "Zee", "Sony", "Colors", "Republic", "Sun", "DD",
    "Aaj Tak", "India TV", "NDTV", "TV9", "ABP", "Asianet",
    "&TV", "Dangal", "Big Magic", "News18", "Times Now",
    "CNBC", "Eurosport", "B4U", "9XM", "MTV", "Cartoon Network",
    "Discovery", "Nick", "Disney", "National Geographic",
    "Travel XP", "Zee Bangla", "Colors Bangla", "Sun Bangla",

    # Generic (position 165)
    "Bangla",

    # Sports (positions 166-170)
    "T Sports", "ESPN",
]
```

### Requirements

- Python 3.10+
- No external dependencies (standard library only)

### Documentation

- README.md with pipeline overview, installation, usage, and configuration
- CONTRIBUTING.md with development setup and contribution guidelines
- This CHANGELOG.md
- MIT License
