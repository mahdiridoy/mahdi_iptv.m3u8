"""
utils.py
--------
Shared helper functions used by order_m3u.py and the rest of the pipeline.
"""

import re
from typing import Any

from config import CHANNEL_ORDER

_RES_RE = re.compile(
    r"\s*\(?[\d]+[ip]?\)?\s*$",
)
_BRACKET_RE = re.compile(
    r"\[[^\]]*\]",
)
_VIP_RE = re.compile(
    r"\bVIP\b",
    re.IGNORECASE,
)
_MULTI_PAREN_RE = re.compile(
    r"\s*\((?:\d+\s*){2,}\)\s*$",
)
_MULTI_SUFFIX_RE = re.compile(
    r"(?:\s*\(?\d+\)?){2,}\s*$",
)
_WHITESPACE_RE = re.compile(r"\s+")
_ATTR_RE = re.compile(r'(\S+)="([^"]*)"')


def clean_name(name: str) -> str:
    s = name.strip()
    s = _VIP_RE.sub("", s)
    s = _BRACKET_RE.sub("", s)
    s = _MULTI_SUFFIX_RE.sub("", s)
    s = _RES_RE.sub("", s)
    s = s.strip(" -")
    s = _WHITESPACE_RE.sub(" ", s)
    return s.strip()


def parse_extinf_attrs(extinf: str) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    parts = extinf.split(",", 1)
    header = parts[0]
    attrs["name"] = parts[1].strip() if len(parts) > 1 else "Unknown"
    for m in _ATTR_RE.finditer(header):
        attrs[m.group(1)] = m.group(2)
    return attrs


def order_rank(channel_name: str) -> int | None:
    lower = channel_name.lower()
    for idx, keyword in enumerate(CHANNEL_ORDER):
        kw = keyword.lower()
        pattern = r"(?:^|[\s\-\[&])(?:" + re.escape(kw) + r")(?:[\s\-\]&]|$)"
        if re.search(pattern, lower):
            return idx
    return None
