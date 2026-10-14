"""Story planner: works out what the clip is about and plans a realistic shot for each segment.

The reel has no text, so the picture has to tell the song's meaning. With ANTHROPIC_API_KEY,
Claude Sonnet 5.5 writes a plain-language shot for each part of the clip. Without a key,
keywords from the lyrics pick the shots and the sound picks the look.
Output: {mood, meaning, look, palette, segments[{start,end,concept,query,prompt,motion,shot}], suggestions, source}
Author: Bhagirath Argade
"""
from __future__ import annotations

import re

from . import claude_agents, visual_director
from .visual_renderer import MOTIONS

LOOK_LABELS = {
    "cinematic_warm": "Cinematic warm",
    "moody_blue": "Moody blue",
    "soft_pastel": "Soft pastel",
    "bw_film": "Black & white film",
}
SHOT_STYLES = ("slow push-in", "slow pan left", "slow pan right", "static")
SUFFIX = ", photorealistic cinematic footage, vertical 9:16, shallow depth of field, no text, no logos"

# (keywords, what the viewer sees, free-stock search words, image prompt)
CONCEPTS = [
    (("rain", "monsoon", "storm", "thunder", "drizzle"), "rain falling on a quiet street at night",
     "rain street night", "rain falling on a quiet street at night, soft streetlights"),
    (("fire", "flame", "burn", "burning", "candle"), "a candle flame glowing in a dark room",
     "candle flame dark room", "a candle flame glowing in a dark room, warm light"),
    (("sea", "ocean", "wave", "waves", "water", "river", "lake", "shore"), "waves rolling onto a beach at sunset",
     "ocean waves sunset", "waves rolling onto a beach at sunset, golden light"),
    (("sun", "sunrise", "sunset", "morning", "dawn", "golden", "shine", "light"), "the sun rising over quiet hills",
     "sunrise hills", "the sun rising over quiet hills, warm morning light"),
    (("moon", "stars", "starry", "midnight", "night", "sky"), "a moonlit night sky over a still landscape",
     "moon night sky", "a moonlit night sky over a still landscape, stars"),
    (("love", "heart", "kiss", "hold", "hands", "together", "pyaar", "dil"), "two people holding hands in a warm place",
     "couple holding hands", "two people holding hands in a warm place, tender mood"),
    (("dance", "dancing", "groove", "party", "music", "sing", "song", "dhol", "beat"), "a silhouette dancing in warm stage light",
     "dancing silhouette stage light", "a silhouette dancing in warm stage light, energetic"),
    (("alone", "lonely", "cry", "tears", "sad", "miss", "gone", "broken", "pain"), "a lone figure walking down an empty road",
     "lonely figure empty road", "a lone figure walking down an empty road, melancholy"),
    (("run", "road", "journey", "travel", "walk", "way", "highway", "away"), "a road stretching into the distance",
     "empty road distance", "a road stretching into the distance at dusk"),
    (("flower", "flowers", "rose", "bloom", "garden", "spring"), "flowers opening in soft sunlight",
     "flowers blooming sunlight", "flowers opening in soft sunlight, shallow focus"),
    (("mountain", "mountains", "hill", "peak", "himalaya", "snow"), "snowy mountain peaks at dawn",
     "snowy mountain dawn", "snowy mountain peaks at dawn, cold clear air"),
    (("wind", "breeze", "fly", "wings", "free"), "leaves swept up by the wind",
     "leaves wind autumn", "leaves swept up by the wind, soft motion"),
    (("forest", "tree", "trees", "jungle", "leaf"), "sunlight through a misty forest",
     "misty forest sunlight", "sunlight through a misty forest, morning haze"),
    (("temple", "god", "shiva", "prayer", "pray", "bhakti", "divine", "lord", "devotion"), "a lit oil lamp glowing in a temple at dusk",
     "oil lamp temple dusk", "a lit oil lamp glowing in a temple at dusk, devotional"),
    (("city", "street", "lights", "crowd", "town"), "city lights blurring at night",
     "city lights night bokeh", "city lights blurring at night, bokeh"),
]
DEFAULT_CONCEPT = ("a slow cinematic landscape at golden hour", "cinematic landscape golden hour",
                   "a slow cinematic landscape at golden hour, soft light")


def _concept_for(text: str) -> tuple[str, str, str]:
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    best, best_score = DEFAULT_CONCEPT, 0
    for kws, concept, query, prompt in CONCEPTS:
        score = sum(1 for k in kws if k in words)
        if score > best_score:
            best, best_score = (concept, query, prompt), score
    return best


def _suggestions(segs: list[dict], look: str, mood: str) -> list[dict]:
    concepts: list[str] = []
    for s in segs:
        if s["concept"] not in concepts:
            concepts.append(s["concept"])
    avg = sum(s["end"] - s["start"] for s in segs) / max(len(segs), 1)
    others = ", ".join(v for k, v in LOOK_LABELS.items() if k != look)
    return [
        {"title": "Realistic shots", "detail": "Each part of the song is shown as real footage: " + "; ".join(concepts[:4]) + "."},
        {"title": "Camera motion", "detail": "Slow push-ins and gentle pans, so every shot moves with the song. Cuts land on the strongest beats."},
        {"title": "Colour look", "detail": f"'{LOOK_LABELS[look]}' grade keeps every shot in one colour world. Alternatives: {others}."},
        {"title": "Pacing", "detail": f"{len(segs)} shots of about {avg:.1f} s each, so the reel is easy to follow without any text."},
        {"title": "Mood", "detail": f"Feel: {mood or 'calm'}. Keep the reel to the hook so people stay for the chorus."},
    ]


def heuristic_story(duration: float, feats: dict, lines=(), lyrics_text: str = "") -> dict:
    base = visual_director.heuristic_plan(duration, feats)
    for s in base["segments"]:
        seg_text = " ".join(l.text for l in lines if l.end > s["start"] and l.start < s["end"]) or lyrics_text
        concept, query, prompt = _concept_for(seg_text)
        s.update(concept=concept, query=query, prompt=prompt + SUFFIX, shot=SHOT_STYLES[0] if s["motion"] != "waves" else SHOT_STYLES[1])
    look = "moody_blue" if float(feats["centroid"].mean()) < 0.4 else "cinematic_warm"
    return {
        "mood": base["mood"], "meaning": "Read from the clip's words and sound (no AI key).",
        "look": look, "palette": base["palette"], "segments": base["segments"],
        "suggestions": _suggestions(base["segments"], look, base["mood"]), "source": "heuristic (keywords + sound)",
    }


STORY_SYSTEM = """You are the creative director for a daily Instagram music-reel page.
The reel has NO text on screen, and someone who has never heard the song must understand it from the picture.
So the picture shows, in realistic footage, what the song is about.
You get the lyrics for this clip (may be empty), its length and a loudness summary.
1. Understand the meaning and feeling: what is happening, where, who, what emotion.
2. Split the clip into 3 to 8 contiguous segments that cover 0 to the clip length exactly. Each segment shows one
   literal moment matching its lyrics (for example "I miss you in the rain" becomes a lone person standing in the rain under a streetlight).
   For each segment give:
   "concept": plain-language description of what the viewer sees,
   "query": 2-4 concrete words for searching free stock video (no names, no brands),
   "prompt": one sentence photorealistic image prompt for that moment, vertical 9:16, no text,
   "motion": one of aurora, particles, waves, orbs (used only if no footage is found),
   "shot": one of "slow push-in", "slow pan left", "slow pan right", "static".
3. Choose "look" from: cinematic_warm, moody_blue, soft_pastel, bw_film.
4. Give 3 to 5 "suggestions": short edit advice as {"title", "detail"} about the visual style, the kind of
   realistic footage or animation that suits the song, camera motion, colour and pacing.
Return JSON: {"mood": "2-4 words", "meaning": "one sentence", "look": "...",
"segments": [{"start": number, "end": number, "concept": "...", "query": "...", "prompt": "...", "motion": "...", "shot": "..."}],
"suggestions": [{"title": "...", "detail": "..."}]}"""


def _validate_segments(raw, duration: float) -> list[dict]:
    if not isinstance(raw, list) or not (1 <= len(raw) <= 8):
        raise ValueError("expected 1-8 segments")
    out = []
    for s in raw:
        motion = s.get("motion") if s.get("motion") in MOTIONS else "particles"
        shot = s.get("shot") if s.get("shot") in SHOT_STYLES else SHOT_STYLES[0]
        concept = str(s.get("concept", "")).strip()
        query = str(s.get("query", "")).strip()
        prompt = str(s.get("prompt", "")).strip()
        if not concept or not query:
            raise ValueError("every segment needs a concept and a search query")
        out.append({"start": float(s["start"]), "end": float(s["end"]), "motion": motion, "shot": shot,
                    "concept": concept[:160], "query": query[:80], "prompt": (prompt or concept)[:400] + SUFFIX})
    if abs(out[0]["start"]) > 0.05 or abs(out[-1]["end"] - duration) > 0.25:
        raise ValueError("segments must cover the whole clip")
    for a, b in zip(out, out[1:]):
        if abs(a["end"] - b["start"]) > 0.05 or b["end"] <= b["start"]:
            raise ValueError("segments must be contiguous and forward in time")
    out[0]["start"], out[-1]["end"] = 0.0, duration
    for a, b in zip(out, out[1:]):
        b["start"] = a["end"]
    return out


def plan_story(song: str, artist: str, lyrics_text: str, duration: float, feats: dict, lines=()) -> dict:
    fb = heuristic_story(duration, feats, lines, lyrics_text)
    if not claude_agents.available():
        return fb
    user = (f"Song: {song}\nArtist: {artist or 'unknown'}\nClip length: {duration:.1f}s\n"
            f"Sound: {visual_director._loudness_summary(feats)}\n"
            f"Lyrics of this clip (may be empty):\n{lyrics_text or '(none found)'}")
    try:
        data = claude_agents._ask_json(STORY_SYSTEM, user, 3500)
        segs = _validate_segments(data.get("segments"), duration)
        look = data.get("look") if data.get("look") in LOOK_LABELS else fb["look"]
        sugg = [{"title": str(x.get("title", ""))[:60], "detail": str(x.get("detail", ""))[:300]}
                for x in (data.get("suggestions") or []) if isinstance(x, dict)][:5] or fb["suggestions"]
        return {"mood": str(data.get("mood", "")), "meaning": str(data.get("meaning", "")), "look": look,
                "palette": fb["palette"], "segments": segs, "suggestions": sugg, "source": claude_agents.MODEL}
    except Exception as e:
        fb["source"] = f"heuristic (Claude failed: {type(e).__name__}: {str(e)[:90]})"
        return fb
