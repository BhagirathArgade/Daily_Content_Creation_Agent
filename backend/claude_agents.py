"""Claude Sonnet 5.5 brains for Agent 1 (Viral Cutter) and Agent 2 (Storyboarder).

Agent 1 - pick_hook(): reads the timed lyrics of the whole song and chooses the most
          viral continuous span (chorus / quotable / peak).
Agent 2 - plan_scenes(): tokenizes the clip's lyrics into at most 8 meaningful statements,
          one scene (image) each, with ONE style bible so every image shares
          the same vibe.

Both work WITHOUT a key (deterministic heuristics) - the response says which one ran.
Set ANTHROPIC_API_KEY (and optionally CLAUDE_MODEL) to use Claude.

Author: Bhagirath Argade
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any

from .lyrics import Line

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def extract_json(text: str) -> Any:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model reply")
    return json.loads(text[start : end + 1])


def _ask_json(system: str, user: str, max_tokens: int) -> Any:
    import anthropic

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system + "\n\nReply with one valid JSON object and nothing else.",
        messages=[{"role": "user", "content": user}],
    )
    return extract_json("".join(b.text for b in msg.content if getattr(b, "type", "") == "text"))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# ───────────────────────── Agent 1: Viral Cutter ─────────────────────────

HOOK_SYSTEM = """You are the Viral Cutter agent for a daily Instagram Reels page that posts song moments.
You receive the timed lyrics of a full song as: line_no, start_s, end_s, text.
Choose the ONE continuous span most likely to go viral as a short reel:
the chorus hook or most quotable line, an emotional or melodic peak, lines people lip-sync,
a span that makes sense without context, a clean start and a clean end. Prefer chorus material.
Rules: use whole lines only. Span length must be between {min_len} and {max_len} seconds (ideal {target} s).
Return JSON: {{"first_line": int, "last_line": int, "virality_score": int 0-100,
"why": "one or two sentences", "mood": "2-4 words", "vibe_keywords": ["..."]}}"""


def heuristic_hook(lines: list[Line], duration: float, target: float, min_len: float, max_len: float) -> dict:
    """Chorus finder: lyric lines that repeat across the song score higher; fits the target length."""
    if not lines:
        start = round(0.36 * duration, 2) if duration > 90 else 0.0
        end = round(min(duration, start + target), 2)
        return {
            "start": start, "end": end, "first_line": None, "last_line": None,
            "virality_score": 50, "mood": "", "vibe_keywords": [], "source": "heuristic",
            "why": "No lyrics found, so the clip starts at the usual chorus position (~36% into the song).",
        }
    counts = Counter(_norm(l.text) for l in lines)
    best = None
    for i in range(len(lines)):
        for j in range(i, len(lines)):
            span = lines[j].end - lines[i].start
            if span > max_len:
                break
            if span < min_len:
                continue
            rep = sum(max(0, counts[_norm(l.text)] - 1) for l in lines[i : j + 1])
            density = sum(len(l.text.split()) for l in lines[i : j + 1]) / span
            fit = 1 - abs(span - target) / max(target, 1)
            score = rep * 2.0 + density + fit * 3.0
            if best is None or score > best[0]:
                best = (score, i, j, rep)
    if best is None:
        i, j, rep = 0, len(lines) - 1, 0
    else:
        _, i, j, rep = best
    return {
        "start": lines[i].start, "end": lines[j].end, "first_line": i, "last_line": j,
        "virality_score": min(90, 50 + 6 * rep), "mood": "", "vibe_keywords": ["chorus"] if rep else [],
        "source": "heuristic",
        "why": "Repeated (chorus-like) lyric block that fits the target length.",
    }


def pick_hook(song: str, artist: str, lines: list[Line], duration: float,
              target: float = 25.0, min_len: float = 15.0, max_len: float = 30.0) -> dict:
    fallback = heuristic_hook(lines, duration, target, min_len, max_len)
    if not lines or not available():
        fallback["why"] += "" if available() else " (No ANTHROPIC_API_KEY, so the heuristic ran.)"
        return fallback
    numbered = "\n".join(f"{i}\t{l.start:.2f}\t{l.end:.2f}\t{l.text}" for i, l in enumerate(lines))
    user = (f"Song: {song}\nArtist: {artist or 'unknown'}\nFull length: {duration:.0f}s\n"
            f"Lines (line_no, start_s, end_s, text):\n{numbered}")
    try:
        d = _ask_json(HOOK_SYSTEM.format(min_len=min_len, max_len=max_len, target=target), user, 1200)
        fi, la = int(d["first_line"]), int(d["last_line"])
        if not (0 <= fi <= la < len(lines)):
            raise ValueError("line numbers out of range")
        start, end = lines[fi].start, lines[la].end
        if not (min_len - 2 <= end - start <= max_len + 2):
            raise ValueError(f"span {end - start:.1f}s outside limits")
        return {
            "start": start, "end": end, "first_line": fi, "last_line": la,
            "virality_score": max(0, min(100, int(d.get("virality_score", 80)))),
            "why": str(d.get("why", "")), "mood": str(d.get("mood", "")),
            "vibe_keywords": [str(x) for x in d.get("vibe_keywords", [])][:8],
            "source": MODEL,
        }
    except Exception as e:  # network, auth, parse, limits
        fallback["why"] = f"Claude hook pick failed ({type(e).__name__}: {e}); heuristic used. " + fallback["why"]
        return fallback


# ─────────────────────── Agent 2: Aesthetic Storyboarder ───────────────────────

MAX_SCENES = 8  # hard cap for the whole clip: one image per statement, never more than 8

SCENE_SYSTEM = """You are the Aesthetic Storyboarder for a daily Instagram music-edit page.
You get the lyrics of ONE short clip as numbered lines with timings. Tokenize the clip into meaningful statements.
1. Split the clip into 7 or 8 scenes, never more than {max_scenes}. Each scene is one meaningful word group or
   statement (usually 3-10 words) that reads as one idea on screen.
   The scenes must cover the whole clip in order: joining all scene "text" values gives back the lyric words exactly,
   with nothing added, dropped or reordered. Split at natural phrase boundaries.
2. Define ONE style bible shared by every image: 4-5 hex palette colours, colour grade, lighting, subject style,
   texture and mood, derived from the song's mood, the vibe request and the lyrics.
3. For each scene write "prompt": one sentence image-generation prompt that shows the scene's meaning in the
   style bible. Concrete visual nouns only. No text or lyrics inside the image, no real people's names,
   no brands, no film titles.
Every image must share one colour world and one kind of subject, so the whole reel has one accent.
Return JSON: {{"style": {{"name": str, "palette": [hex...], "grade": str, "lighting": str,
"subject_style": str, "texture": str, "mood": str}},
"scenes": [{{"text": str, "prompt": str}}]}}"""


class _Timeline:
    """Maps the normalized character positions of the lyrics to clip time (linear inside each line)."""

    def __init__(self, lines: list[Line]):
        self.lines = lines
        self.starts: list[int] = []
        total = 0
        for l in lines:
            self.starts.append(total)
            total += len(_norm(l.text))
        self.total = total

    def time_at(self, g: int) -> float:
        if g >= self.total:
            return self.lines[-1].end
        for i, l in enumerate(self.lines):
            n = len(_norm(l.text))
            if n and self.starts[i] <= g < self.starts[i] + n:
                return l.start + (g - self.starts[i]) / n * (l.end - l.start)
        return self.lines[-1].end


def _heuristic_pieces(lines: list[Line], k: int) -> list[str]:
    """Split the lyric words into k chunks of roughly equal length.

    Cuts are preferred at the end of a phrase (punctuation or a line end) and only
    fall back to any word boundary when no phrase end comes soon enough.
    """
    words: list[tuple[str, bool]] = []
    for l in lines:
        toks = [w for w in l.text.split() if _norm(w)]
        for j, w in enumerate(toks):
            words.append((w, j == len(toks) - 1 or w[-1] in ",;:.!?"))
    if not words:
        return []
    k = max(1, min(k, MAX_SCENES, len(words)))
    total = sum(len(_norm(w)) for w, _ in words)
    target = total / k
    pieces: list[list[str]] = []
    cur: list[str] = []
    acc = 0
    for w, phrase_end in words:
        cur.append(w)
        acc += len(_norm(w))
        due = len(pieces) < k - 1 and acc >= target * (len(pieces) + 1)
        overdue = acc >= target * (len(pieces) + 1) * 1.3
        if due and (phrase_end or overdue):
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    return [" ".join(p) for p in pieces]


def _valid_claude_scenes(raw: Any, lines: list[Line]) -> list[tuple[str, str]]:
    if not isinstance(raw, list) or not (1 <= len(raw) <= MAX_SCENES):
        raise ValueError(f"expected 1-{MAX_SCENES} scenes, got {len(raw) if isinstance(raw, list) else 'none'}")
    out = []
    for sc in raw:
        text = str(sc.get("text", "")).strip()
        if not _norm(text):
            raise ValueError("empty scene text")
        out.append((text, str(sc.get("prompt") or text).strip()))
    if _norm("".join(t for t, _ in out)) != _norm("".join(l.text for l in lines)):
        raise ValueError("scenes do not cover the lyrics exactly")
    return out


def _scenes_from_pieces(pieces: list[tuple[str, str]], lines: list[Line], clip_len: float) -> list[dict]:
    tl = _Timeline(lines)
    scenes, g = [], 0
    for text, prompt in pieces:
        n = len(_norm(text))
        start, end = tl.time_at(g), tl.time_at(g + n)
        scenes.append({"text": text, "start": round(start, 3), "end": round(max(start, end), 3), "prompt": prompt})
        g += n
    scenes[0]["start"] = 0.0
    scenes[-1]["end"] = round(clip_len, 3)
    for a, b in zip(scenes, scenes[1:]):  # neighbours share one boundary, so scenes tile the clip
        b["start"] = a["end"] = round(min(max(a["end"], a["start"]), clip_len), 3)
    return scenes


def _merge_short(scenes: list[dict], min_dur: float = 1.2) -> list[dict]:
    """Fold scenes shorter than min_dur into a neighbour so the reel never flickers."""
    out: list[dict] = []
    for sc in scenes:
        if out and sc["end"] - sc["start"] < min_dur:
            out[-1] = {**out[-1], "text": f"{out[-1]['text']} {sc['text']}", "end": sc["end"]}
        else:
            out.append(dict(sc))
    if len(out) > 1 and out[0]["end"] - out[0]["start"] < min_dur:
        first, second = out[0], out.pop(1)
        out[0] = {**first, "text": f"{first['text']} {second['text']}", "end": second["end"]}
    return out


def plan_scenes(song: str, artist: str, clip_lines: list[Line], clip_len: float,
                vibe_name: str, style_suffix: str, fallback_palette: list[str],
                vibe_hint: str = "") -> dict:
    """Tokenize the clip into at most MAX_SCENES statements, one image each, one shared style.

    clip_lines are clip-relative (0 .. clip_len). Returns {'style', 'scenes', 'source'}.
    Each scene: {id, text, start, end, duration, prompt}; scenes tile the whole clip.
    """
    lines = clip_lines or [Line(0.0, clip_len, song)]
    style: dict = {"name": vibe_name, "palette": fallback_palette, "subject_style": style_suffix}
    source = "heuristic"
    pieces: list[tuple[str, str]] | None = None
    claude_suffix = ""

    if available():
        numbered = "\n".join(f"{i}\t{l.start:.2f}\t{l.end:.2f}\t{l.text}" for i, l in enumerate(lines))
        user = (f"Song: {song}\nArtist: {artist or 'unknown'}\nVibe preset: {vibe_name}\n"
                f"Vibe request: {vibe_hint or 'none - choose what suits the song'}\n"
                f"Clip length: {clip_len:.1f}s\nLines (line_no, start_s, end_s, text):\n{numbered}")
        try:
            data = _ask_json(SCENE_SYSTEM.format(max_scenes=MAX_SCENES), user, 4000)
            style.update({k: v for k, v in (data.get("style") or {}).items() if v})
            pieces = _valid_claude_scenes(data.get("scenes"), lines)
            claude_suffix = ", ".join(str(style[k]) for k in ("subject_style", "grade", "lighting", "texture", "mood") if style.get(k))
            claude_suffix += ", 9:16 vertical portrait, photorealistic, 8k"
            source = MODEL
        except Exception as e:  # invalid JSON, wrong coverage, too many scenes, network...
            pieces = None
            source = f"heuristic (Claude failed: {type(e).__name__}: {str(e)[:90]})"
    elif not os.getenv("ANTHROPIC_API_KEY"):
        source = "heuristic (no ANTHROPIC_API_KEY)"

    if pieces is not None:
        pieces = [(t, f"{p}, {claude_suffix}") for t, p in pieces]
    else:
        k = min(MAX_SCENES, max(7, round(clip_len / 3.2)))
        pieces = [(t, f"{t.strip(' ,;:')}, {style_suffix}") for t in _heuristic_pieces(lines, k)]

    scenes = _merge_short(_scenes_from_pieces(pieces, lines, clip_len))
    for n, sc in enumerate(scenes, start=1):
        sc["id"] = n
        sc["duration"] = round(max(0.1, sc["end"] - sc["start"]), 3)
    return {"style": style, "scenes": scenes, "source": source}
