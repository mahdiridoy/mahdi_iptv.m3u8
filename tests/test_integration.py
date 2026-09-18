"""
Integration tests for the full M3U IPTV processing pipeline
============================================================
Tests that run adult_filter.py → order_m3u.py (with logos + config) in sequence
on a sample M3U file and validate the final output.

The pipeline is:
  scan.m3u → adult_filter.py → logos.py (LOGO_DB) → config.py (CHANNEL_ORDER)
          → order_m3u.py → mahdi_iptv.m3u8
"""

import os
import re
import shutil
import sys

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_m3u(path, lines):
    """Write an M3U file from a list of strings."""
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def _read_file(path):
    """Return file contents as a string."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_lines(path):
    """Return file contents as a list of lines."""
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


# ---------------------------------------------------------------------------
# Fixture: Set up a clean project directory with sample data
# ---------------------------------------------------------------------------

@pytest.fixture()
def pipeline_env(tmp_path, monkeypatch):
    """Set up a temporary project directory and run the full pipeline.

    Returns a dict with paths and metadata.
    """
    project_dir = tmp_path
    scan_file = project_dir / "scan.m3u"

    # Sample M3U with a mix of clean and adult channels
    sample_data = [
        "#EXTM3U",
        # Clean Bangladeshi channels
        '#EXTINF:-1 tvg-id="btv.bd" tvg-name="BTV" tvg-logo="https://example.com/btv.png",BTV',
        "http://example.com/btv/stream.m3u8",
        '#EXTINF:-1 tvg-id="atn.bd" tvg-name="ATN News" tvg-logo="https://example.com/atn.png",ATN News',
        "http://example.com/atn/stream.m3u8",
        '#EXTINF:-1 tvg-id="channeli.bd" tvg-name="Channel I" tvg-logo="https://example.com/channeli.png",Channel I',
        "http://example.com/channeli/stream.m3u8",
        '#EXTINF:-1 tvg-name="Jamuna TV" tvg-logo="https://example.com/jamuna.png",Jamuna TV',
        "http://example.com/jamuna/stream.m3u8",
        '#EXTINF:-1 tvg-name="NTV" tvg-logo="https://example.com/ntv.png",NTV',
        "http://example.com/ntv/stream.m3u8",
        # Clean generic channel
        '#EXTINF:-1 tvg-name="Clean Kids TV" tvg-logo="https://example.com/kids.png",Clean Kids TV',
        "http://example.com/kids/stream.m3u8",
        # Adult channels (should be removed by adult_filter)
        '#EXTINF:-1 tvg-name="XXX Adult Channel" tvg-logo="https://example.com/adult.png",XXX Adult Channel',
        "http://example.com/adult/stream.m3u8",
        '#EXTINF:-1 tvg-name="Porn Live TV",Porn Live TV',
        "http://example.com/porn/stream.m3u8",
        # Channel with group-title (should be stripped by order_m3u)
        '#EXTINF:-1 tvg-name="Drama Channel" group-title="Entertainment",Drama Channel',
        "http://example.com/drama/stream.m3u8",
        # Channel with quality tag (should work fine)
        '#EXTINF:-1 tvg-name="Sports Channel (720p)" tvg-logo="https://example.com/sports.png",Sports Channel (720p)',
        "http://example.com/sports/stream.m3u8",
    ]

    _write_m3u(scan_file, sample_data)

    # Monkeypatch the module constants to use the temp directory
    import adult_filter
    import order_m3u

    monkeypatch.setattr(adult_filter, "SOURCE_FILE", str(scan_file))
    monkeypatch.setattr(adult_filter, "OUTPUT_FILE", str(scan_file))  # in-place
    monkeypatch.setattr(order_m3u, "SOURCE_FILE", str(scan_file))
    monkeypatch.setattr(order_m3u, "OUTPUT_FILE", str(project_dir / "mahdi_iptv.m3u8"))

    return {
        "project_dir": project_dir,
        "scan_file": scan_file,
        "output_file": project_dir / "mahdi_iptv.m3u8",
    }


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """Run the complete pipeline and validate the output."""

    def test_full_pipeline_produces_output(self, pipeline_env):
        """Running adult_filter then order_m3u produces an output file."""
        import adult_filter
        import order_m3u

        # Step 1: Adult filter
        adult_filter.main()
        # Step 2: Order and write output
        order_m3u.main()

        assert pipeline_env["output_file"].exists()

    def test_output_starts_with_extm3u(self, pipeline_env):
        """The final output starts with #EXTM3U."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        assert content.startswith("#EXTM3U")

    def test_output_has_channels(self, pipeline_env):
        """The output contains at least one channel."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        extinf_count = content.count("#EXTINF")
        assert extinf_count > 0, "No channels found in output"

    def test_adult_channels_removed(self, pipeline_env):
        """Adult channels are not present in the final output."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        assert "XXX Adult Channel" not in content
        assert "Porn Live TV" not in content

    def test_clean_channels_preserved(self, pipeline_env):
        """All clean channels are present in the final output."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        for name in ["BTV", "ATN News", "Channel I", "Jamuna TV", "NTV"]:
            assert name in content, f"Channel '{name}' missing from output"

    def test_group_title_removed_in_output(self, pipeline_env):
        """group-title attributes are stripped in the final output."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        assert 'group-title=' not in content

    def test_channel_numbers_assigned(self, pipeline_env):
        """Every channel in the output has a tvg-chno attribute."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        extinf_lines = [l for l in content.split("\n") if l.startswith("#EXTINF")]
        for line in extinf_lines:
            assert re.search(r'tvg-chno="\d+"', line), \
                f"Missing tvg-chno in: {line}"

    def test_channel_numbers_sequential(self, pipeline_env):
        """Channel numbers are sequential starting from 1."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        extinf_lines = [l for l in content.split("\n") if l.startswith("#EXTINF")]
        chnos = []
        for line in extinf_lines:
            match = re.search(r'tvg-chno="(\d+)"', line)
            if match:
                chnos.append(int(match.group(1)))

        assert chnos == sorted(chnos), "Channel numbers not in ascending order"
        assert chnos[0] == 1, "First channel number should be 1"

    def test_output_is_valid_m3u_format(self, pipeline_env):
        """Output follows M3U format: header + alternating EXTINF/URL pairs."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        lines = _read_lines(pipeline_env["output_file"])
        non_empty = [l.strip() for l in lines if l.strip()]

        # First line must be #EXTM3U
        assert non_empty[0] == "#EXTM3U"

        # Remaining lines alternate: EXTINF, URL, EXTINF, URL, ...
        body = non_empty[1:]
        for i, line in enumerate(body):
            if i % 2 == 0:
                assert line.startswith("#EXTINF"), \
                    f"Expected EXTINF at position {i}, got: {line[:60]}"
            else:
                assert line.startswith("http"), \
                    f"Expected URL at position {i}, got: {line[:60]}"

    def test_display_names_preserved_through_pipeline(self, pipeline_env):
        """Channel display names survive the full pipeline intact."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        # Check that display names appear after commas
        assert ",BTV" in content
        assert ",ATN News" in content
        assert ",Channel I" in content
        assert ",NTV" in content

    def test_tvg_attributes_preserved(self, pipeline_env):
        """tvg-id and tvg-logo survive the full pipeline."""
        import adult_filter
        import order_m3u

        adult_filter.main()
        order_m3u.main()

        content = _read_file(pipeline_env["output_file"])
        assert 'tvg-id="btv.bd"' in content
        assert 'tvg-logo="https://example.com/btv.png"' in content


# ---------------------------------------------------------------------------
# Edge-case integration tests
# ---------------------------------------------------------------------------

class TestEdgeCasePipeline:
    """Pipeline behaviour with unusual inputs."""

    def test_pipeline_with_no_adult_channels(self, tmp_path, monkeypatch):
        """Pipeline works fine when there are zero adult channels."""
        import adult_filter
        import order_m3u

        scan = tmp_path / "scan.m3u"
        _write_m3u(scan, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"BTV\",BTV",
            "http://example.com/btv.m3u8",
            "#EXTINF:-1 tvg-name=\"NTV\",NTV",
            "http://example.com/ntv.m3u8",
        ])

        monkeypatch.setattr(adult_filter, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(adult_filter, "OUTPUT_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "OUTPUT_FILE", str(tmp_path / "out.m3u8"))

        adult_filter.main()
        order_m3u.main()

        output = tmp_path / "out.m3u8"
        assert output.exists()
        content = _read_file(output)
        assert content.count("#EXTINF") == 2

    def test_pipeline_with_all_adult_channels(self, tmp_path, monkeypatch):
        """When all channels are adult, output is just the header."""
        import adult_filter
        import order_m3u

        scan = tmp_path / "scan.m3u"
        _write_m3u(scan, [
            "#EXTM3U",
            "#EXTINF:-1,XXX Bad",
            "http://example.com/bad.m3u8",
            "#EXTINF:-1,Porn Worse",
            "http://example.com/worse.m3u8",
        ])

        monkeypatch.setattr(adult_filter, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(adult_filter, "OUTPUT_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "OUTPUT_FILE", str(tmp_path / "out.m3u8"))

        adult_filter.main()
        order_m3u.main()

        output = tmp_path / "out.m3u8"
        assert output.exists()
        content = _read_file(output)
        # Only the #EXTM3U header remains
        assert content.strip() == "#EXTM3U"

    def test_pipeline_with_single_channel(self, tmp_path, monkeypatch):
        """Pipeline handles a single-channel M3U correctly."""
        import adult_filter
        import order_m3u

        scan = tmp_path / "scan.m3u"
        _write_m3u(scan, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"BTV\",BTV",
            "http://example.com/btv.m3u8",
        ])

        monkeypatch.setattr(adult_filter, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(adult_filter, "OUTPUT_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "OUTPUT_FILE", str(tmp_path / "out.m3u8"))

        adult_filter.main()
        order_m3u.main()

        output = tmp_path / "out.m3u8"
        content = _read_file(output)
        assert content.count("#EXTINF") == 1
        assert 'tvg-chno="1"' in content

    def test_pipeline_with_unknown_channels(self, tmp_path, monkeypatch):
        """Channels not in CHANNEL_ORDER are appended with continuing numbers."""
        import adult_filter
        import order_m3u
        from config import CHANNEL_ORDER

        scan = tmp_path / "scan.m3u"
        _write_m3u(scan, [
            "#EXTM3U",
            "#EXTINF:-1 tvg-name=\"XYZ Random\",XYZ Random",
            "http://example.com/xyz.m3u8",
            "#EXTINF:-1 tvg-name=\"ABC Unknown\",ABC Unknown",
            "http://example.com/abc.m3u8",
        ])

        monkeypatch.setattr(adult_filter, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(adult_filter, "OUTPUT_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "SOURCE_FILE", str(scan))
        monkeypatch.setattr(order_m3u, "OUTPUT_FILE", str(tmp_path / "out.m3u8"))

        adult_filter.main()
        order_m3u.main()

        output = tmp_path / "out.m3u8"
        content = _read_file(output)
        base_chno = len(CHANNEL_ORDER) + 1
        assert f'tvg-chno="{base_chno}"' in content
        assert f'tvg-chno="{base_chno + 1}"' in content
