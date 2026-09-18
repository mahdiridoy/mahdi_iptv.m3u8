"""Tests for config.py"""
from config import CHANNEL_ORDER


class TestChannelOrder:
    """Test the CHANNEL_ORDER configuration."""

    def test_channel_order_is_list(self):
        assert isinstance(CHANNEL_ORDER, list)

    def test_channel_order_not_empty(self):
        assert len(CHANNEL_ORDER) > 0

    def test_no_duplicate_first_entries(self):
        """First few entries should be unique (BTV, ATN, etc.)."""
        first_ten = CHANNEL_ORDER[:10]
        assert len(first_ten) == len(set(first_ten))

    def test_btv_is_first(self):
        """BTV should be the first channel in order."""
        assert CHANNEL_ORDER[0] == "BTV"

    def test_all_strings(self):
        """Every entry in CHANNEL_ORDER should be a string."""
        for entry in CHANNEL_ORDER:
            assert isinstance(entry, str), f"Non-string entry found: {entry}"

    def test_no_empty_strings(self):
        """No empty strings in CHANNEL_ORDER."""
        for entry in CHANNEL_ORDER:
            assert len(entry.strip()) > 0, "Empty string found in CHANNEL_ORDER"
