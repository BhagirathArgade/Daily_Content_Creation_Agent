"""Visual Director: understands the clip's meaning and plans the look of the reel.

With ANTHROPIC_API_KEY, Claude Sonnet 5.5 reads the lyrics and reasons about the feeling and
imagery of the clip. Without a key, the sound alone chooses palette and motion.
Output: {mood, meaning, palette[5], segments[3-8] with start/end/motion/motif, source}.
Author: Bhagirath Argade
"""
from __future__ import annotations

import re

import numpy as np

from . import claude_agents
from .visual_renderer import MOTIONS

MAX_SEGMENTS = 8
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

NEON = ["#0b0221", "#ff2e88", "#00f5d4", "#ffd166", "#f8f7ff"]
DUSK = ["#0b132b", "#1c2541", "#3a506b", "#5bc0be", "#e0fbfc"]
GOLD = ["#2b1d0e", "#7a4a1d", "#e09f3e", "#ffd6a5", "#fff3e0"]
ROSE = ["#1d0b1f", "#5e2750", "#c9184a", "#ff8fa3", "#fff0f3"]

DIRECTOR_SYSTEM = """You are the Visual Director for a daily Instagram music-reel page.
You receive a short song clip: its lyrics (may be empty), its length and a summary of its loudness.
1. Understand the meaning and feeling of the clip: its emotion, setting and imagery.
2. Choose 5 hex colours (dark to light) that fit that meaning.
3. Split the clip into 3 to 8 contiguous segments that cover 0 to the clip length exactly.
   Each segment gets one motion:
   "aurora" = flowing light bands (calm, dreamy, night),
   "particles" = drifting glowing dust (romantic, hopeful, nostalgic),
   "waves" = pulsing rings (powerful, dramatic, the peaks of the song),
   "orbs" = soft large light orbs (intimate, sad, tender).
   Give each segment a short "motif": the imagery in plain words, e.g. "lantern glow over still water".
The visuals must never contain text, letters, numbers or logos.
Return JSON: {"mood": "2-4 words", "meaning": "one sentence", "palette": ["#rrggbb" x5],
"segments": [{"start": number, "end": number, "motion": "aurora|particles|waves|orbs", "motif": "..."}]}"""


def _loudness_summary(feats: dict) -> str:
    rms = feats["rms"]
    return (f"average loudness {rms.mean():.2f}, peak {rms.max():.2f}, "
            f"tempo about {feats.get('bpm', 0):.0f} BPM, brightness {feats['centroid'].mean():.2f}")


def heuristic_plan(duration: float, feats: dict) -> dict:
    """Sound-only plan: palette from brightness, motion from each segment's loudness."""
    fps, rms = feats["fps"], feats["rms"]
    bright = float(feats["centroid"].mean())
    palette = NEON if bright > 0.5 else (GOLD if bright > 0.3 else DUSK)
    n = min(MAX_SEGMENTS, max(3, round(duration / 3.5)))
    edges = np.linspace(0.0, duration, n + 1)
    levels = []
    for i in range(n):
        k0, k1 = int(edges[i] * fps), max(int(edges[i + 1] * fps), int(edges[i] * fps) + 1)
        levels.append(float(rms[k0:k1].mean()))
    order = np.argsort(levels)  # quietest first
    motion = [None] * n
    for rank, idx in enumerate(order):
        third = rank / max(n - 1, 1)
        if third >= 0.66:
            motion[idx] = "waves"
        elif third >= 0.33:
            motion[idx] = "particles"
        else:
            motion[idx] = "aurora" if rank % 2 == 0 else "orbs"
    segments = [{"start": round(float(edges[i]), 3), "end": round(float(edges[i + 1]), 3),
                 "motion": motion[i], "motif": "sound-driven"} for i in range(n)]
    energy = "high energy" if bright > 0.5 else "calm and warm"
    return {"mood": energy, "meaning": "Mood read from the sound alone (no lyrics or API key).",
            "palette": palette, "segments": segments, "source": "heuristic (sound only)"}


def _validate(data: dict, duration: float) -> tuple[list[str], list[dict]]:
    palette = [str(c) for c in data.get("palette", [])]
    if len(palette) != 5 or not all(HEX.match(c) for c in palette):
        raise ValueError("palette must be 5 hex colours")
    segs = data.get("segments") or []
    if not (1 <= len(segs) <= MAX_SEGMENTS):
        raise ValueError(f"expected 1-{MAX_SEGMENTS} segments")
    out = []
    for s in segs:
        if s.get("motion") not in MOTIONS:
            raise ValueError(f"unknown motion {s.get('motion')!r}")
        out.append({"start": float(s["start"]), "end": float(s["end"]), "motion": s["motion"],
                    "motif": str(s.get("motif", ""))[:120]})
    if abs(out[0]["start"]) > 0.05 or abs(out[-1]["end"] - duration) > 0.25:
        raise ValueError("segments must cover the whole clip")
    for a, b in zip(out, out[1:]):
        if abs(a["end"] - b["start"]) > 0.05 or b["end"] <= b["start"]:
            raise ValueError("segments must be contiguous and forward in time")
    out[0]["start"], out[-1]["end"] = 0.0, duration
    for a, b in zip(out, out[1:]):
        b["start"] = a["end"]
    return palette, out


def plan_look(song: str, artist: str, lyrics_text: str, duration: float, feats: dict) -> dict:
    fallback = heuristic_plan(duration, feats)
    if not claude_agents.available():
        return fallback
    user = (f"Song: {song}\nArtist: {artist or 'unknown'}\nClip length: {duration:.1f}s\n"
            f"Sound: {_loudness_summary(feats)}\n"
            f"Lyrics of the clip (may be empty):\n{lyrics_text or '(none found)'}")
    try:
        data = claude_agents._ask_json(DIRECTOR_SYSTEM, user, 2500)
        palette, segments = _validate(data, duration)
        return {"mood": str(data.get("mood", "")), "meaning": str(data.get("meaning", "")),
                "palette": palette, "segments": segments, "source": claude_agents.MODEL}
    except Exception as e:
        fallback["source"] = f"heuristic (Claude failed: {type(e).__name__}: {str(e)[:90]})"
        return fallback
