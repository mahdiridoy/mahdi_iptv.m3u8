"""
Tests for logos.py
==================
Covers:
  - Attaching a logo to a known channel via LOGO_DB lookup
  - Skipping unknown channels (no logo found)
  - Preserving existing attributes when adding a logo
  - Structural integrity of the LOGO_DB dictionary
"""

import pytest


# ---------------------------------------------------------------------------
# Tests: LOGO_DB structure
# ---------------------------------------------------------------------------

class TestLogoDBStructure:
    """Validate that LOGO_DB is well-formed."""

    def test_logo_db_is_dict(self):
        """LOGO_DB must be a dictionary."""
        from logos import LOGO_DB
        assert isinstance(LOGO_DB, dict)

    def test_logo_db_not_empty(self):
        """LOGO_DB should contain at least one entry."""
        from logos import LOGO_DB
        assert len(LOGO_DB) > 0

    def test_all_keys_are_strings(self):
        """Every key in LOGO_DB must be a string."""
        from logos import LOGO_DB
        for key in LOGO_DB:
            assert isinstance(key, str), f"Non-string key: {key!r}"

    def test_all_values_are_urls(self):
        """Every value in LOGO_DB must be a URL string."""
        from logos import LOGO_DB
        for key, url in LOGO_DB.items():
            assert isinstance(url, str), f"Non-string value for {key!r}"
            assert url.startswith("http"), f"Value for {key!r} is not a URL: {url!r}"

    def test_known_channels_present(self):
        """Well-known channels like BTV, NTV, CNN should have logos."""
        from logos import LOGO_DB
        known = ["BTV", "NTV", "CNN", "Al Jazeera", "Star Plus HD"]
        for ch in known:
            # Case-insensitive check
            found = any(ch.lower() == k.lower() for k in LOGO_DB)
            assert found, f"Expected channel '{ch}' not found in LOGO_DB"


# ---------------------------------------------------------------------------
# Tests: Logo lookup logic
# ---------------------------------------------------------------------------

class TestLogoLookup:
    """Simulate how the pipeline matches channel names to logos."""

    def test_exact_match(self):
        """An exact key match returns the correct logo URL."""
        from logos import LOGO_DB
        name = "BTV"
        logo = LOGO_DB.get(name)
        assert logo is not None
        assert logo.startswith("http")

    def test_case_insensitive_lookup(self):
        """Lookup should work with different casing."""
        from logos import LOGO_DB
        # Find a logo by iterating (simulates case-insensitive matching)
        target = None
        for key in LOGO_DB:
            if key.lower() == "btv":
                target = LOGO_DB[key]
                break
        assert target is not None

    def test_unknown_channel_returns_none(self):
        """A channel not in LOGO_DB returns None via dict.get()."""
        from logos import LOGO_DB
        logo = LOGO_DB.get("NonExistentChannel XYZ 999")
        assert logo is None

    def test_partial_name_match(self):
        """A channel name that is a substring of a key can be found with iteration."""
        from logos import LOGO_DB
        # "NTV" is a key; "NTV (720p)" would need iteration/fuzzy matching
        matches = [v for k, v in LOGO_DB.items() if "ntv" in k.lower()]
        assert len(matches) > 0

    def test_logo_for_star_plus(self):
        """StarPlus HD should have a logo entry."""
        from logos import LOGO_DB
        logo = LOGO_DB.get("StarPlus HD")
        assert logo is not None
        assert "starplus" in logo.lower() or "star" in logo.lower()


# ---------------------------------------------------------------------------
# Tests: Logo attachment behaviour (simulated)
# ---------------------------------------------------------------------------

class TestAttachLogo:
    """Simulate the logo-attaching logic the pipeline would use."""

    def _build_extinf(self, name, existing_attrs=None):
        """Helper to construct an #EXTINF line."""
        attr_str = ""
        if existing_attrs:
            attr_str = " ".join(f'{k}="{v}"' for k, v in existing_attrs.items())
            attr_str = " " + attr_str
        return f"#EXTINF:-1{attr_str},{name}"

    def _attach_logo(self, extinf_line, logo_url):
        """Simulate adding tvg-logo to an EXTINF line if not present."""
        if 'tvg-logo="' in extinf_line:
            return extinf_line  # already has logo
        # Insert before the comma + name
        comma_pos = extinf_line.rfind(",")
        before = extinf_line[:comma_pos]
        after = extinf_line[comma_pos:]
        return f'{before} tvg-logo="{logo_url}"{after}'

    def test_attaches_logo_to_known_channel(self):
        """A channel in LOGO_DB gets its logo attached."""
        from logos import LOGO_DB

        name = "BTV"
        logo = LOGO_DB.get(name)
        assert logo is not None

        extinf = self._build_extinf(name)
        result = self._attach_logo(extinf, logo)
        assert f'tvg-logo="{logo}"' in result
        assert result.endswith(f",{name}")

    def test_skips_unknown_channel(self):
        """A channel not in LOGO_DB gets no logo (None → skip)."""
        from logos import LOGO_DB

        name = "RandomXYZ Unknown"
        logo = LOGO_DB.get(name)
        assert logo is None

    def test_preserves_existing_logo(self):
        """If an EXTINF line already has tvg-logo, it is not overwritten."""
        name = "BTV"
        existing_logo = "https://existing.com/logo.png"

        extinf = self._build_extinf(name, {"tvg-logo": existing_logo})
        assert 'tvg-logo="' in extinf

        from logos import LOGO_DB
        new_logo = LOGO_DB.get(name)
        result = self._attach_logo(extinf, new_logo)

        # Should keep the original logo
        assert existing_logo in result
        assert new_logo not in result

    def test_preserves_existing_tvg_id(self):
        """When adding a logo, existing tvg-id and tvg-name attributes stay."""
        name = "NTV"
        extinf = self._build_extinf(name, {
            "tvg-id": "ntv.bd",
            "tvg-name": "NTV",
        })

        from logos import LOGO_DB
        logo = LOGO_DB.get(name)
        result = self._attach_logo(extinf, logo)

        assert 'tvg-id="ntv.bd"' in result
        assert 'tvg-name="NTV"' in result
        assert f'tvg-logo="{logo}"' in result
        assert result.endswith(f",{name}")

    def test_preserves_chno_attribute(self):
        """tvg-chno is preserved when logo is attached."""
        name = "CNN"
        extinf = self._build_extinf(name, {
            "tvg-id": "cnn.us",
            "tvg-chno": "42",
        })

        from logos import LOGO_DB
        logo = LOGO_DB.get(name)
        result = self._attach_logo(extinf, logo)

        assert 'tvg-chno="42"' in result
        assert f'tvg-logo="{logo}"' in result
