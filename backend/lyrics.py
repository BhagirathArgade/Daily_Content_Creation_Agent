"""Lyrics lookup with timing (free, no API key) via lrclib.net.

* Prefers time-synced lyrics (LRC) so every caption lands on the right second.
* Falls back to plain lyrics with APPROXIMATE timing (lines spread over the song),
  and says so in the output - it never invents lyrics.

Author: Bhagirath Argade
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import requests

LRCLIB_SEARCH = "https://lrclib.net/api/search"
HEADERS = {"User-Agent": "Daily_Content_Creation_Agent (https://github.com/BhagirathArgade)"}
_TAG = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


@dataclass
class Line:
    start: float
    end: float
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_lrc(text: str) -> list[Line]:
    """Parse '[mm:ss.xx] words' lines. A line lasts until the next time stamp."""
    stamps: list[tuple[float, str]] = []
    for row in (text or "").splitlines():
        tags = list(_TAG.finditer(row))
        if not tags:
            continue
        words = row[tags[-1].end():].strip()
        for t in tags:
            stamps.append((int(t.group(1)) * 60 + float(t.group(2)), words))
    stamps.sort(key=lambda s: s[0])
    out: list[Line] = []
    for i, (t, words) in enumerate(stamps):
        if not words:
            continue
        end = stamps[i + 1][0] if i + 1 < len(stamps) else t + 4.0
        out.append(Line(round(t, 2), round(max(end, t + 0.8), 2), words))
    return out


def approximate_timing(plain: str, duration: float, intro: float = 0.05) -> list[Line]:
    """Spread plain lyric lines evenly over the song. Approximate - used only without LRC."""
    rows = [r.strip() for r in (plain or "").splitlines() if r.strip()]
    if not rows or duration <= 0:
        return []
    start_at = duration * intro
    slot = (duration - start_at) / len(rows)
    return [Line(round(start_at + i * slot, 2), round(start_at + (i + 1) * slot, 2), r) for i, r in enumerate(rows)]


_NOISE = re.compile(
    r"\((official|lyrics?|video|audio|hd|4k|remaster)[^)]*\)|\[(official|lyrics?|video|audio|hd|4k)[^\]]*\]"
    r"|\b(official (music )?video|official audio|lyrics?|full song|hd|4k)\b",
    re.I,
)


def clean_title(s: str) -> str:
    s = _NOISE.sub("", s or "")
    return re.sub(r"\s+", " ", s).strip(" -|•")


def fetch_lyrics(title: str, artist: str = "", timeout: float = 10) -> dict:
    """Returns {'lines': [Line], 'plain': str, 'synced': bool, 'source': str}."""
    empty = {"lines": [], "plain": "", "synced": False, "source": "none"}
    results: list[dict] = []
    try:
        params = {"track_name": clean_title(title)}
        if artist:
            params["artist_name"] = clean_title(artist)
        r = requests.get(LRCLIB_SEARCH, params=params, headers=HEADERS, timeout=timeout)
        results = r.json() if r.ok and isinstance(r.json(), list) else []
        if not results:
            q = f"{clean_title(title)} {clean_title(artist)}".strip()
            r = requests.get(LRCLIB_SEARCH, params={"q": q}, headers=HEADERS, timeout=timeout)
            results = r.json() if r.ok and isinstance(r.json(), list) else []
    except Exception:
        return empty

    for e in results:  # best case: time-synced lyrics
        if e.get("syncedLyrics"):
            lines = parse_lrc(e["syncedLyrics"])
            if lines:
                return {"lines": lines, "plain": e.get("plainLyrics") or "", "synced": True, "source": "lrclib.net"}
    for e in results:  # plain lyrics only
        if (e.get("plainLyrics") or "").strip():
            return {"lines": [], "plain": e["plainLyrics"], "synced": False, "source": "lrclib.net"}
    return empty
