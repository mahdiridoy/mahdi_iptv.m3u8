"""
Tests for order_m3u.py
======================
Covers:
  - Channel number assignment based on CHANNEL_ORDER position
  - Unlisted channels appended after listed ones
  - group-title attribute removal
  - Preservation of tvg-id, tvg-logo, tvg-chno attributes
  - Correct M3U output format
"""

import os
import sys
import textwrap

import pytest

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import CHANNEL_ORDER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_m3u(path, lines):
    """Write an M3U file from a list of strings (newline-terminated)."""
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def _read_m3u(path):
    """Return the contents of an M3U file as a list of strings."""
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def _extract_entries(lines):
    """Parse M3U lines into a list of dicts: {name, attrs_dict, url, chno}."""
    entries = []
    current_extinf = None
    current_meta = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            if current_extinf is not None:
                entries.append({"extinf": current_extinf, "meta": current_meta, "url": None})
            current_extinf = line
            current_meta = []
        elif line.startswith("#"):
            current_meta.append(line)
        else:
            # URL line
            entries.append({
                "extinf": current_extinf,
                "meta": current_meta,
                "url": line,
            })
            current_extinf = None
            current_meta = []
    if current_extinf is not None:
        entries.append({"extinf": current_extinf, "meta": current_meta, "url": None})
    return entries


def _get_chno_from_extinf(extinf):
    """Extract tvg-chno value from an EXTINF line."""
    import re
    match = re.search(r'tvg-chno="(\d+)"', extinf)
    return int(match.group(1)) if match else None


def _get_name_from_extinf(extinf):
    """Extract display name from an EXTINF line."""
    comma = extinf.rfind(",")
    return extinf[comma + 1:].strip() if comma != -1 else "Unknown"


def _has_group_title(extinf):
    """Check if group-title is present in an EXTINF line."""
    return 'group-title="' in extinf


def _get_attr(extinf, attr_name):
    """Extract an attribute value from an EXTINF line."""
    import re
    match = re.search(rf'{attr_name}="([^"]*)"', extinf)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Fixture: run order_m3u.main() with temp paths
# ---------------------------------------------------------------------------

@pytest.fixture()
def run_order_m3u(tmp_path, monkeypatch):
    """Return a callable that runs order_m3u.main() with temp paths."""
    import order_m3u

    def _run(input_filename="scan.m3u", output_filename="mahdi_iptv.m3u8"):
        src = tmp_path / input_filename
        out = tmp_path / output_filename
        monkeypatch.setattr(order_m3u, "SOURCE_FILE", str(src))
        monkeypatch.setattr(order_m3u, "OUTPUT_FILE", str(out))
        return src, out

    return _run


# ---------------------------------------------------------------------------
# Tests: Channel number assignment
# ---------------------------------------------------------------------------

class TestChannelNumberAssignment:
    """Channels should get tvg-chno based on their position in CHANNEL_ORDER."""

    def test_first_keyword_channel_gets_chno_1(self, run_order_m3u, tmp_path):
        """The first keyword 'BTV' should produce tvg-chno=1."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"BTV\" tvg-logo=\"http://logo.png\",BTV",
            "http://example.com/btv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        assert len(entries) >= 1
        chno = _get_chno_from_extinf(entries[0]["extinf"])
        assert chno == 1

    def test_multiple_keywords_get_sequential_numbers(self, run_order_m3u, tmp_path):
        """Channels matching different keywords get sequential chno values."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            # BTV → index 0 → chno 1
            "#EXTINF:-1 tvg-name=\"BTV\",BTV",
            "http://example.com/btv.m3u8",
            # ATN → index 1 → chno 2
            "#EXTINF:-1 tvg-name=\"ATN News\",ATN News",
            "http://example.com/atn.m3u8",
            # Channel i → index 2 → chno 3
            "#EXTINF:-1 tvg-name=\"Channel I\",Channel I",
            "http://example.com/channeli.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        chnos = [_get_chno_from_extinf(e["extinf"]) for e in entries]
        assert 1 in chnos
        assert 2 in chnos
        assert 3 in chnos

    def test_same_keyword_channels_share_chno(self, run_order_m3u, tmp_path):
        """Multiple channels matching the same keyword get the same chno."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,NTV",
            "http://example.com/ntv1.m3u8",
            "#EXTINF:-1,NTV (720p)",
            "http://example.com/ntv2.m3u8",
            "#EXTINF:-1,NTV UK",
            "http://example.com/ntv3.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        # All NTV channels should have the same chno (NTV's rank in CHANNEL_ORDER)
        from utils import order_rank, clean_name
        ntv_rank = order_rank(clean_name("NTV"))
        expected_chno = ntv_rank + 1 if ntv_rank is not None else None
        assert expected_chno is not None

        for e in entries:
            chno = _get_chno_from_extinf(e["extinf"])
            assert chno == expected_chno


# ---------------------------------------------------------------------------
# Tests: Unlisted channels
# ---------------------------------------------------------------------------

class TestUnlistedChannels:
    """Channels not matching any keyword are appended after all listed channels."""

    def test_unlisted_channels_appended(self, run_order_m3u, tmp_path):
        """Channels not in CHANNEL_ORDER go to the end."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            # A listed channel
            "#EXTINF:-1 tvg-name=\"BTV\",BTV",
            "http://example.com/btv.m3u8",
            # An unlisted channel
            "#EXTINF:-1 tvg-name=\"XYZ Random\",XYZ Random",
            "http://example.com/xyz.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        names = [_get_name_from_extinf(e["extinf"]) for e in entries]
        assert names[0] == "BTV"
        assert names[-1] == "XYZ Random"

    def test_unlisted_channels_get_sequential_numbers(self, run_order_m3u, tmp_path):
        """Unlisted channels get chno = len(CHANNEL_ORDER) + position."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,BTV",
            "http://example.com/btv.m3u8",
            "#EXTINF:-1,RandomAlpha",
            "http://example.com/alpha.m3u8",
            "#EXTINF:-1,RandomBeta",
            "http://example.com/beta.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        unlisted_base = len(CHANNEL_ORDER) + 1

        # Find the random channels
        alpha = next(e for e in entries if "RandomAlpha" in _get_name_from_extinf(e["extinf"]))
        beta = next(e for e in entries if "RandomBeta" in _get_name_from_extinf(e["extinf"]))

        assert _get_chno_from_extinf(alpha["extinf"]) == unlisted_base
        assert _get_chno_from_extinf(beta["extinf"]) == unlisted_base + 1

    def test_no_channels_dropped(self, run_order_m3u, tmp_path):
        """All channels with URLs survive the ordering process."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,BTV",
            "http://example.com/btv.m3u8",
            "#EXTINF:-1,ZRandom1",
            "http://example.com/z1.m3u8",
            "#EXTINF:-1,ZRandom2",
            "http://example.com/z2.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        assert len(entries) == 3


# ---------------------------------------------------------------------------
# Tests: group-title removal
# ---------------------------------------------------------------------------

class TestGroupTitleRemoval:
    """group-title attributes should be stripped from the output."""

    def test_removes_group_title(self, run_order_m3u, tmp_path):
        """group-title attribute is not present in the output."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            '#EXTINF:-1 tvg-name="BTV" group-title="News",BTV',
            "http://example.com/btv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        assert len(entries) >= 1
        assert not _has_group_title(entries[0]["extinf"])

    def test_removes_multiple_group_titles(self, run_order_m3u, tmp_path):
        """All group-title attributes are removed across multiple channels."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            '#EXTINF:-1 tvg-name="BTV" group-title="Bangladesh",BTV',
            "http://example.com/btv.m3u8",
            '#EXTINF:-1 tvg-name="NTV" group-title="Entertainment",NTV',
            "http://example.com/ntv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        for e in entries:
            assert not _has_group_title(e["extinf"]), \
                f"group-title found in: {e['extinf']}"


# ---------------------------------------------------------------------------
# Tests: tvg attribute preservation
# ---------------------------------------------------------------------------

class TestTvgAttributePreservation:
    """tvg-id, tvg-logo, and tvg-name attributes should be preserved."""

    def test_preserves_tvg_id(self, run_order_m3u, tmp_path):
        """tvg-id attribute survives the reordering."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="btv.bd" tvg-name="BTV",BTV',
            "http://example.com/btv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        assert _get_attr(entries[0]["extinf"], "tvg-id") == "btv.bd"

    def test_preserves_tvg_logo(self, run_order_m3u, tmp_path):
        """tvg-logo attribute survives the reordering."""
        import order_m3u

        src, out = run_order_m3u()
        logo_url = "https://example.com/btv_logo.png"
        _write_m3u(src, [
            "#EXTM3U",
            f'#EXTINF:-1 tvg-logo="{logo_url}" tvg-name="BTV",BTV',
            "http://example.com/btv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        assert _get_attr(entries[0]["extinf"], "tvg-logo") == logo_url

    def test_preserves_tvg_name(self, run_order_m3u, tmp_path):
        """tvg-name attribute survives the reordering."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            '#EXTINF:-1 tvg-name="My BTV" tvg-id="btv.bd",BTV',
            "http://example.com/btv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        assert _get_attr(entries[0]["extinf"], "tvg-name") == "My BTV"

    def test_preserves_multiple_attributes(self, run_order_m3u, tmp_path):
        """All tvg-* attributes are preserved together."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            '#EXTINF:-1 tvg-id="ntv.bd" tvg-name="NTV" tvg-logo="https://ntv.png" tvg-chno="7",NTV',
            "http://example.com/ntv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        extinf = entries[0]["extinf"]
        assert _get_attr(extinf, "tvg-id") == "ntv.bd"
        assert _get_attr(extinf, "tvg-name") == "NTV"
        assert _get_attr(extinf, "tvg-logo") == "https://ntv.png"
        # tvg-chno is overwritten by the ordering system
        assert _get_chno_from_extinf(extinf) is not None


# ---------------------------------------------------------------------------
# Tests: Output format
# ---------------------------------------------------------------------------

class TestOutputFormat:
    """The output file must be a valid M3U playlist."""

    def test_starts_with_extm3u(self, run_order_m3u, tmp_path):
        """Output starts with #EXTM3U header."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,BTV",
            "http://example.com/btv.m3u8",
        ])

        order_m3u.main()

        content = _read_m3u(out)
        assert content[0].strip() == "#EXTM3U"

    def test_every_entry_has_extinf_and_url(self, run_order_m3u, tmp_path):
        """Every channel entry consists of an EXTINF line followed by a URL."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"BTV\",BTV",
            "http://example.com/btv.m3u8",
            "#EXTINF:-1 tvg-name=\"NTV\",NTV",
            "http://example.com/ntv.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        for e in entries:
            assert e["extinf"] is not None
            assert e["url"] is not None
            assert e["url"].startswith("http")

    def test_display_name_preserved(self, run_order_m3u, tmp_path):
        """The display name after the comma is preserved in output."""
        import order_m3u

        src, out = run_order_m3u()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,Channel X",
            "http://example.com/x.m3u8",
        ])

        order_m3u.main()

        entries = _extract_entries(_read_m3u(out))
        assert _get_name_from_extinf(entries[0]["extinf"]) == "Channel X"


# ---------------------------------------------------------------------------
# Tests: utils functions (parse_extinf_attrs, clean_name, order_rank)
# ---------------------------------------------------------------------------

class TestUtilsFunctions:
    """Test the utility functions imported by order_m3u."""

    def test_parse_extinf_attrs_basic(self):
        """Parse a simple EXTINF line."""
        from utils import parse_extinf_attrs
        extinf = '#EXTINF:-1 tvg-id="btv.bd" tvg-name="BTV",BTV'
        attrs = parse_extinf_attrs(extinf)
        assert attrs["tvg-id"] == "btv.bd"
        assert attrs["tvg-name"] == "BTV"
        assert attrs["name"] == "BTV"

    def test_parse_extinf_attrs_empty(self):
        """Parse an EXTINF line with no attributes."""
        from utils import parse_extinf_attrs
        extinf = "#EXTINF:-1,Unknown"
        attrs = parse_extinf_attrs(extinf)
        assert attrs["name"] == "Unknown"

    def test_clean_name_strips_quality(self):
        """clean_name removes quality tags."""
        from utils import clean_name
        assert clean_name("Channel (720p)") == "Channel"
        assert clean_name("Channel 1080p") == "Channel"
        assert clean_name("Channel (1080i)") == "Channel"

    def test_clean_name_strips_brackets(self):
        """clean_name removes bracket tags."""
        from utils import clean_name
        assert clean_name("[BD] BTV") == "BTV"
        assert clean_name("Channel [Geo-blocked]") == "Channel"
        assert clean_name("Channel [Not 24/7] (720p)") == "Channel"

    def test_order_rank_returns_index(self):
        """order_rank returns the correct index for a matching keyword."""
        from utils import order_rank, clean_name
        assert order_rank(clean_name("BTV")) == 0  # "BTV" is first
        assert order_rank(clean_name("ATN News")) == 1  # "ATN" is second
        assert order_rank(clean_name("Channel I")) == 2  # "Channel i" is third

    def test_order_rank_returns_none_for_unknown(self):
        """order_rank returns None for channels not matching any keyword."""
        from utils import order_rank
        assert order_rank("XYZ Random 999") is None
        assert order_rank("Completely Unknown") is None
