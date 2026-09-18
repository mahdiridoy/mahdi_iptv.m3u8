# Mahdi IPTV M3U8

> An automated pipeline that filters, decorates, and orders IPTV M3U playlists into a clean, consistently-numbered .m3u8 file ready for any player.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Why This Exists

Raw IPTV playlists are messy: they contain adult channels, duplicate entries, missing logos, inconsistent ordering, and no stable channel numbers. This pipeline takes a raw `scan.m3u` file and transforms it into a clean, player-ready `mahdi_iptv.m3u8` playlist through deterministic stages -- so your channel list looks professional and works reliably across every device.

## Pipeline Overview

```
scan.m3u                       Raw IPTV playlist (input)
    |
    v
+---------------------+
|  adult_filter.py    |  Remove adult/explicit channels
+----------+----------+
           |
           v
+---------------------+
|    logos.py         |  Attach channel logos from LOGO_DB
+----------+----------+
           |
           v
+---------------------+
|    config.py        |  Channel ordering + performance settings
+----------+----------+
           |
           v
+---------------------+
|  order_m3u.py       |  Sort channels, assign permanent numbers
+----------+----------+
           |
           v
mahdi_iptv.m3u8                 Clean, ordered playlist (output)
```

## Prerequisites

- **Python 3.10** or newer
- **pip** (Python package manager)
- No external dependencies -- the pipeline uses only the Python standard library

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/mahdi_iptv.m3u8.git
cd mahdi_iptv.m3u8
```

2. **Verify Python version**

```bash
python --version   # Should print 3.10 or higher
```

3. **Place your source playlist**

Copy or place your raw IPTV playlist as `scan.m3u` in the project root directory.

## Usage

### Manual Run

Execute the pipeline scripts in order from the project root:

```bash
# Step 1: Filter out adult channels
python adult_filter.py

# Step 2: Attach channel logos
python attach_logos.py

# Step 3: Order channels and assign permanent numbers
python order_m3u.py
```

The final output will be written to `mahdi_iptv.m3u8`.

### What Each Step Does

| Step | Script | Reads | Writes | Purpose |
|------|--------|-------|--------|---------|
| 1 | `adult_filter.py` | `scan.m3u` | `scan.m3u` | Removes adult channels in-place |
| 2 | `attach_logos.py` | `scan.m3u` | `scan.m3u` | Attaches logos from `LOGO_DB` |
| 3 | `order_m3u.py` | `scan.m3u` | `mahdi_iptv.m3u8` | Orders channels, assigns numbers |

### GitHub Actions

This pipeline can be automated via GitHub Actions. Create a workflow file (e.g., `.github/workflows/build.yml`) that:

1. Checks out the repository
2. Sets up Python 3.10+
3. Runs the three scripts in sequence
4. Commits the updated `mahdi_iptv.m3u8` back to the repository

Example workflow:

```yaml
name: Build IPTV Playlist

on:
  schedule:
    - cron: '0 */6 * * *'   # Every 6 hours
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Run pipeline
        run: |
          python adult_filter.py
          python attach_logos.py
          python order_m3u.py

      - name: Commit updated playlist
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add mahdi_iptv.m3u8
          git diff --cached --quiet || git commit -m "chore: update playlist $(date +'%Y-%m-%d %H:%M')"
          git push
```

## Configuration

All tunable settings live in **`config.py`**. You do not need to edit any other file to customize behavior.

### Channel Ordering (CHANNEL_ORDER)

The `CHANNEL_ORDER` list controls the **exact order** of channels in the output. Each entry is a keyword matched (case-insensitive, whole-word or phrase) against channel names.

```python
CHANNEL_ORDER = [
    "BTV",              # Position 1 -- all BTV channels
    "ATN",              # Position 2 -- all ATN channels
    "Channel i",        # Position 3
    "Jamuna",           # Position 4
    "Somoy",            # Position 5
    # ... Bangladesh channels ...
    "Star",             # India -- Star network
    "Zee",              # India -- Zee network
    "Sony",             # India -- Sony network
    # ... more Indian channels ...
    "Bangla",           # Generic (placed last to avoid false matches)
    "T Sports",         # Sports
    "ESPN",             # Sports
]
```

**How matching works:**

- A channel is placed under the **first** keyword that matches it
- Channels matching **no** keyword are appended after all listed channels (never dropped)
- Each keyword assigns a **permanent channel number** -- position N in the list = channel number N

### Performance Tuning

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_WORKERS` | `200` | Parallel threads for URL checking |
| `SOURCE_TIMEOUT` | `120` | Seconds to wait for a source playlist |
| `CHECK_TIMEOUT` | `3` | Max seconds per channel check |
| `SKIP_URL_CHECK` | `False` | Set `True` to skip live URL verification |
| `CHECK_RETRIES` | `0` | Retries on timeout before marking dead |
| `READ_WINDOW` | `2.0` | Seconds to measure real throughput |
| `MIN_THROUGHPUT_KBPS` | `50` | Minimum KB/s to consider a stream healthy |
| `BUFFER_THRESHOLD` | `2.0` | Max seconds latency to keep a channel |
| `SOURCE_RETRIES` | `1` | Retries for source playlist download |
| `MIN_OUTPUT_RATIO` | `0.5` | New run must keep 50% of previous channels |
| `MIN_OUTPUT_CHANNELS` | `20` | Never output fewer than this many channels |

### When to Adjust Settings

- **Playlist takes too long to build**: Increase `CHECK_TIMEOUT` or set `SKIP_URL_CHECK = True`
- **Good channels are being dropped**: Increase `BUFFER_THRESHOLD` or `MIN_THROUGHPUT_KBPS`
- **Too many dead links in output**: Decrease `BUFFER_THRESHOLD` or increase `MIN_THROUGHPUT_KBPS`
- **Source playlists frequently timeout**: Increase `SOURCE_TIMEOUT` and `SOURCE_RETRIES`

## Pipeline Steps Explained

### Step 1: Adult Content Filter (adult_filter.py)

Reads `scan.m3u` and removes every channel whose `#EXTINF` line or stream URL contains an adult keyword. The filtered file overwrites the input.

**Keyword list** (case-insensitive, 34 keywords):

```
adult, xxx, porn, sex, erotic, erotico, erotique, dorcel, penthouse,
playboy, hustler, brazzers, bangbros, mofos, wankz, vixen, blacked,
realitykings, reality kings, naughtyamerica, naughty america, xvideos,
xhamster, pornhub, onlyfans, boyxx, sextreme, hentai, nude, naked,
milf, fetish, hardcore, softcore, explicit, uncensored, redlight,
red light, taboo, 18+, for adults, adults only, hot movies
```

**Implementation detail:** All keywords are pre-compiled into a single regex pattern (`_ADULT_RE`) for fast scanning. Both the `#EXTINF` metadata line and the following stream URL line are checked for each channel entry. Any match causes the entire channel block (metadata + URL) to be removed.

### Step 2: Logo Attachment (logos.py / attach_logos.py)

Matches channel names against the `LOGO_DB` dictionary -- a mapping of channel names to logo image URLs. Each channel receives a `tvg-logo` attribute pointing to the matched logo.

**How matching works:**

- Channel names are compared against `LOGO_DB` keys using a clean/normalized form
- Multiple variants of the same channel name (e.g., "Deepto", "Deepto TV", "Deepto TV HD") all map to the same logo URL
- Channels with no match in `LOGO_DB` keep their existing logo or have no logo

The `LOGO_DB` dictionary currently contains **900+** logo mappings covering:

- Bangladeshi channels (BTV, ATN, Channel i, NTV, Jamuna, etc.)
- Indian channels (Star, Zee, Sony, Colors, DD, etc.)
- International sports (ESPN, Sky Sports, Sony Ten, etc.)
- Kids channels (Cartoon Network, Nickelodeon, POGO, etc.)
- News channels (CNN, Al Jazeera, NDTV, Republic, etc.)

### Step 3: Channel Ordering (order_m3u.py)

Reads `scan.m3u`, parses every channel entry, and outputs `mahdi_iptv.m3u8` with:

1. **Channels sorted** by their position in `CHANNEL_ORDER`
2. **Permanent channel numbers** assigned (`tvg-chno="N"`) based on the keyword slot
3. **`group-title` attributes removed** -- the output has no categories/groups
4. **Unlisted channels appended** -- anything not matching a keyword gets numbered after the last keyword

**Example output structure:**

```
#EXTM3U
#EXTINF:-1 tvg-chno="1" tvg-logo="...",BTV
http://...
#EXTINF:-1 tvg-chno="2" tvg-logo="...",ATN News
http://...
#EXTINF:-1 tvg-chno="3" tvg-logo="...",Channel i
http://...
```

**Key behaviors:**

- Channels are never dropped -- if a channel does not match any keyword, it is appended at the end with a continuing channel number
- Channel numbers are **permanent** -- they are tied to the keyword position, not to which channels survived previous steps
- The `group-title` attribute is stripped from all output entries for a clean, flat playlist

## Output Format

The output file `mahdi_iptv.m3u8` is a standard M3U8 playlist:

```
#EXTM3U
#EXTINF:-1 tvg-chno="1" tvg-logo="https://example.com/logo.png",Channel Name
http://stream-url.example.com/live/stream.m3u8
```

Each channel entry consists of:
- An `#EXTINF` line with `tvg-chno` (permanent channel number) and `tvg-logo` (channel logo URL)
- A stream URL on the following line

The file is UTF-8 encoded and compatible with all major IPTV players (VLC, Kodi, IPTV Smarters, TiviMate, etc.).

## Troubleshooting

### "scan.m3u not found"

Ensure `scan.m3u` exists in the project root directory before running any script. This file is your raw input playlist.

### Adult channels still appear in output

The filter only checks the `#EXTINF` line text and stream URL. If an adult channel uses a non-obvious name that does not match any keyword in the `ADULT_KEYWORDS` list, it will pass through. Add the new keyword to the list in `adult_filter.py`.

### Channels have no logo

The channel name may not match any entry in `LOGO_DB` (defined in `logos.py`). Add a new mapping:

```python
LOGO_DB["Your Channel Name"] = "https://example.com/logo.png"
```

### Channel order is wrong

Check the position of the matching keyword in `CHANNEL_ORDER` (defined in `config.py`). Channels are placed under the **first** matching keyword. If a channel matches an earlier keyword than intended, reorder or rename the keywords.

### Pipeline is slow

- Set `SKIP_URL_CHECK = True` in `config.py` to skip URL verification
- Reduce `MAX_WORKERS` if you are hitting rate limits
- Increase `CHECK_TIMEOUT` if many channels are timing out

### Output has too few channels

- Check that `MIN_OUTPUT_RATIO` and `MIN_OUTPUT_CHANNELS` are not too restrictive
- Verify source playlists are accessible (increase `SOURCE_TIMEOUT`)
- Review logs for connection errors or timeouts

## License

MIT License -- see [LICENSE](LICENSE) for details.
