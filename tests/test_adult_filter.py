"""
Tests for adult_filter.py
=========================
Covers:
  - Removing channels with adult keywords in EXTINF lines or URLs
  - Preserving clean (non-adult) channels
  - Handling malformed / edge-case input
  - Preserving the #EXTM3U header after filtering
"""

import os
import shutil
import textwrap

import pytest


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


def _extract_extinf_names(lines):
    """Return the display names from all #EXTINF lines."""
    names = []
    for line in lines:
        if line.startswith("#EXTINF"):
            comma = line.rfind(",")
            if comma != -1:
                names.append(line[comma + 1 :].strip())
    return names


# ---------------------------------------------------------------------------
# Fixture: patch SOURCE_FILE / OUTPUT_FILE to point at tmp_path
# ---------------------------------------------------------------------------

@pytest.fixture()
def patched_adult_filter(tmp_path, monkeypatch):
    """Return a callable that runs adult_filter.main() with temp paths."""
    import adult_filter

    def _run(input_filename="scan.m3u", output_filename="scan.m3u"):
        src = tmp_path / input_filename
        out = tmp_path / output_filename
        monkeypatch.setattr(adult_filter, "SOURCE_FILE", str(src))
        monkeypatch.setattr(adult_filter, "OUTPUT_FILE", str(out))
        return src, out

    return _run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRemoveAdultContent:
    """Channels with adult keywords in EXTINF or URL should be removed."""

    def test_removes_adult_keyword_in_extinf(self, patched_adult_filter, tmp_path):
        """An EXTINF line containing an adult keyword is dropped."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"XXX Hot Channel\",XXX Hot Channel",
            "http://example.com/clean1.m3u8",
            "#EXTINF:-1 tvg-name=\"Normal News\",Normal News",
            "http://example.com/clean2.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert "Normal News" in result
        assert "XXX Hot Channel" not in result

    def test_removes_adult_keyword_in_url(self, patched_adult_filter, tmp_path):
        """A URL containing an adult keyword causes the channel to be dropped."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"Some Channel\",Some Channel",
            "http://example.com/porn/stream.m3u8",
            "#EXTINF:-1 tvg-name=\"Clean TV\",Clean TV",
            "http://example.com/clean.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert "Clean TV" in result
        assert "Some Channel" not in result

    def test_removes_multiple_adult_channels(self, patched_adult_filter, tmp_path):
        """Multiple adult channels are all removed in one pass."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,XXX Channel",
            "http://a.com/1.m3u8",
            "#EXTINF:-1,Adult Films",
            "http://a.com/2.m3u8",
            "#EXTINF:-1,Porn Hub Live",
            "http://a.com/3.m3u8",
            "#EXTINF:-1,Clean Channel",
            "http://a.com/4.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert result == ["Clean Channel"]

    def test_removes_channel_with_hentai_in_name(self, patched_adult_filter, tmp_path):
        """The keyword 'hentai' triggers removal."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,Hentai Stream",
            "http://a.com/1.m3u8",
            "#EXTINF:-1,Safe Stream",
            "http://a.com/2.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert "Safe Stream" in result
        assert "Hentai Stream" not in result


class TestPreservesCleanContent:
    """Non-adult channels should be kept intact."""

    def test_preserves_clean_channels(self, patched_adult_filter, tmp_path):
        """Channels without adult keywords are all preserved."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"BTV\" tvg-logo=\"http://logo.png\",BTV",
            "http://example.com/btv.m3u8",
            "#EXTINF:-1 tvg-name=\"NTV\" tvg-logo=\"http://logo2.png\",NTV",
            "http://example.com/ntv.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert "BTV" in result
        assert "NTV" in result
        assert len(result) == 2

    def test_preserves_channel_count(self, patched_adult_filter, tmp_path):
        """The number of clean channels matches expected count."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,Channel A",
            "http://a.com/1.m3u8",
            "#EXTINF:-1,Channel B",
            "http://a.com/2.m3u8",
            "#EXTINF:-1,Channel C",
            "http://a.com/3.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert len(result) == 3

    def test_all_keyword_variations(self, patched_adult_filter, tmp_path):
        """Every keyword in ADULT_KEYWORDS triggers removal."""
        import adult_filter

        # Test a representative subset of keywords
        keywords = ["xxx", "porn", "sex", "erotic", "hentai", "nude", "naked",
                     "milf", "fetish", "hardcore", "18+", "playboy"]
        for kw in keywords:
            src, out = patched_adult_filter()
            _write_m3u(src, [
                "#EXTM3U",
                f"#EXTINF:-1,Channel {kw}",
                f"http://a.com/{kw}.m3u8",
            ])
            adult_filter.main()
            result = _extract_extinf_names(_read_m3u(out))
            assert result == [], f"Keyword '{kw}' was not caught"


class TestHandlesMalformedInput:
    """Edge cases and unusual input formats."""

    def test_empty_file(self, patched_adult_filter, tmp_path):
        """An empty input file produces an empty output file."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [])

        adult_filter.main()

        assert _read_m3u(out) == []

    def test_only_extm3u_header(self, patched_adult_filter, tmp_path):
        """A file with only the #EXTM3U header is preserved."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, ["#EXTM3U"])

        adult_filter.main()

        content = _read_m3u(out)
        assert len(content) == 1
        assert content[0].strip() == "#EXTM3U"

    def test_odd_line_count(self, patched_adult_filter, tmp_path):
        """An EXTINF line without a following URL line is handled gracefully."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,Orphan Channel",
            "#EXTINF:-1,Normal Channel",
            "http://example.com/normal.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert "Normal Channel" in result

    def test_blank_lines_between_entries(self, patched_adult_filter, tmp_path):
        """Blank lines interspersed between entries do not cause errors."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "",
            "#EXTINF:-1,Channel A",
            "http://a.com/1.m3u8",
            "",
            "#EXTINF:-1,Channel B",
            "http://a.com/2.m3u8",
            "",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert "Channel A" in result
        assert "Channel B" in result

    def test_case_insensitive_matching(self, patched_adult_filter, tmp_path):
        """Adult keywords are matched case-insensitively."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,XXX Upper Case",
            "http://a.com/1.m3u8",
            "#EXTINF:-1,xxx lower case",
            "http://a.com/2.m3u8",
            "#EXTINF:-1,XxX mixed case",
            "http://a.com/3.m3u8",
            "#EXTINF:-1,Safe Channel",
            "http://a.com/4.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(out))
        assert result == ["Safe Channel"]


class TestPreservesHeader:
    """The #EXTM3U header should survive the filtering process."""

    def test_extm3u_header_present(self, patched_adult_filter, tmp_path):
        """The output file starts with #EXTM3U."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,Clean Channel",
            "http://a.com/1.m3u8",
        ])

        adult_filter.main()

        content = _read_m3u(out)
        assert content[0].strip() == "#EXTM3U"

    def test_header_survives_when_all_channels_removed(self, patched_adult_filter, tmp_path):
        """The header remains even when every channel is adult."""
        import adult_filter

        src, out = patched_adult_filter()
        _write_m3u(src, [
            "#EXTM3U",
            "#EXTINF:-1,XXX Bad",
            "http://a.com/1.m3u8",
        ])

        adult_filter.main()

        content = _read_m3u(out)
        assert content[0].strip() == "#EXTM3U"


class TestInputOutputBehavior:
    """adult_filter reads from SOURCE_FILE and writes to OUTPUT_FILE."""

    def test_in_place_overwrite(self, tmp_path, monkeypatch):
        """When SOURCE_FILE == OUTPUT_FILE the file is overwritten in-place."""
        import adult_filter

        m3u = tmp_path / "scan.m3u"
        monkeypatch.setattr(adult_filter, "SOURCE_FILE", str(m3u))
        monkeypatch.setattr(adult_filter, "OUTPUT_FILE", str(m3u))

        _write_m3u(m3u, [
            "#EXTM3U",
            "#EXTINF:-1,XXX Adult",
            "http://a.com/1.m3u8",
            "#EXTINF:-1,Clean",
            "http://a.com/2.m3u8",
        ])

        adult_filter.main()

        result = _extract_extinf_names(_read_m3u(m3u))
        assert result == ["Clean"]
