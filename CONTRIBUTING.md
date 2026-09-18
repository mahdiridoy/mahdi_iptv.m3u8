# Contributing to Mahdi IPTV M3U8

Thank you for your interest in contributing! This guide explains how to set up a development environment, run the pipeline, and make changes.

## Development Environment Setup

### Prerequisites

- Python 3.10 or newer
- Git

### Steps

1. **Fork and clone the repository**

```bash
git clone https://github.com/yourusername/mahdi_iptv.m3u8.git
cd mahdi_iptv.m3u8
```

2. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

3. **Verify Python is available**

```bash
python --version   # Should print 3.10 or higher
```

No `pip install` is needed -- the pipeline uses only the Python standard library.

4. **Place a test playlist**

Put a small test `scan.m3u` file in the project root. Use a subset of channels for fast iteration.

## Running the Pipeline

Execute the scripts in order:

```bash
python adult_filter.py      # Step 1: filter adult content
python attach_logos.py      # Step 2: attach logos
python order_m3u.py         # Step 3: order and number channels
```

The output is written to `mahdi_iptv.m3u8`.

### Running Individual Steps

Each script can be run independently for testing:

```bash
# Test only the adult filter
python adult_filter.py

# Test only the logo attachment
python attach_logos.py

# Test only the ordering step
python order_m3u.py
```

### Checking Output

After running the pipeline, inspect the output:

```bash
# Count channels in output
grep -c "^#EXTINF" mahdi_iptv.m3u8

# View first 20 lines
head -20 mahdi_iptv.m3u8

# Check for a specific channel
grep -i "channel name" mahdi_iptv.m3u8
```

## Code Style Guidelines

### General

- Use Python 3.10+ features (type hints, match statements, etc.)
- Keep scripts self-contained -- each script should work as a standalone entry point
- Use `logging` module for all output (not `print()`)
- Follow PEP 8 style conventions

### Logging Format

All scripts use the same logging format:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
```

### File Encoding

- All M3U files are read/written with `encoding="utf-8"` and `errors="ignore"` for input
- Output files use strict `encoding="utf-8"`

### Naming Conventions

- `SCREAMING_SNAKE_CASE` for module-level constants (`SOURCE_FILE`, `OUTPUT_FILE`, `LOGO_DB`)
- `snake_case` for functions and local variables
- Descriptive variable names -- prefer `channel_name` over `cn`

## How to Add New Channels to CHANNEL_ORDER

The `CHANNEL_ORDER` list in `config.py` defines the exact output order. Each entry is a keyword matched against channel names.

### Adding a Single Channel

1. Open `config.py`
2. Add the keyword in the correct position within `CHANNEL_ORDER`

```python
CHANNEL_ORDER = [
    "BTV",
    "ATN",
    "Channel i",
    # ... existing entries ...
    "Your New Channel",   # <-- add here
    # ... more entries ...
]
```

### Adding a Group of Channels

Add the common keyword that identifies the group:

```python
# Adding all "GTV" channels
CHANNEL_ORDER = [
    # ... existing entries ...
    "GTV",   # catches GTV, GTV HD, GTV News, etc.
    # ... more entries ...
]
```

### Important Rules

- **Position matters**: Channels are placed under the **first** matching keyword. If "Star" appears before "Star Sports", all Star channels (including Star Sports) go under "Star".
- **"Bangla" is last on purpose**: The generic "Bangla" keyword is placed after all Indian brand keywords so that "Zee Bangla" matches "Zee" first, not "Bangla".
- **Inserting shifts numbers**: Adding a keyword in position N renumbers all channels after it. This is by design -- channel numbers are tied to keyword positions.
- **Never drop channels**: Channels matching no keyword are appended at the end with continuing numbers.

### Testing Your Change

After modifying `CHANNEL_ORDER`:

1. Run `python order_m3u.py`
2. Check `mahdi_iptv.m3u8` for the new channel order
3. Verify channel numbers are correct and sequential

## How to Add New Logos to LOGO_DB

The `LOGO_DB` dictionary in `logos.py` maps channel names to logo image URLs.

### Adding a Single Logo

1. Open `logos.py`
2. Add a new entry to the `LOGO_DB` dictionary

```python
LOGO_DB = {
    # ... existing entries ...
    "Your Channel Name": "https://example.com/logo.png",
    # ... more entries ...
}
```

### Logo URL Requirements

- Must be a direct URL to an image file (PNG, JPG, or WebP)
- Should be a reasonably sized image (200-400px wide is ideal)
- HTTPS URLs are preferred
- Use a reliable hosting service (Imgur, Wikimedia, official CDN, etc.)

### Handling Channel Name Variants

If a channel has multiple name variants in different playlists, add all of them:

```python
LOGO_DB = {
    "Deepto": "https://example.com/deepto.png",
    "Deepto TV": "https://example.com/deepto.png",
    "Deepto TV HD": "https://example.com/deepto.png",
}
```

### Testing Your Change

1. Ensure the channel appears in `scan.m3u`
2. Run `python attach_logos.py`
3. Check that the `tvg-logo` attribute is added to the channel's `#EXTINF` line

## Making a Pull Request

1. **Commit your changes** with a clear message

```bash
git add config.py logos.py
git commit -m "feat: add GTV channels to CHANNEL_ORDER"
```

2. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

3. **Open a Pull Request** against the main branch with:

   - A description of what you changed and why
   - The affected files
   - Any testing you performed

### Pull Request Checklist

- [ ] Code follows the style guidelines above
- [ ] `CHANNEL_ORDER` changes maintain correct keyword ordering
- [ ] `LOGO_DB` entries use valid, accessible image URLs
- [ ] Scripts run without errors on your test playlist
- [ ] Commit messages are clear and descriptive

## Reporting Issues

If you find a bug or have a feature request:

1. Check existing issues to avoid duplicates
2. Open a new issue with:
   - A clear title
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Your Python version and operating system

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
