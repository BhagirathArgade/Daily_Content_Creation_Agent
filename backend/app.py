"""
FastAPI backend - Daily Content Creation Agent (the real pipeline)
Author: Bhagirath Argade
GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent

Endpoints:
  GET  /                      → web dashboard
  GET  /api/health            → which brains are active (Claude / sound-only heuristics)
  GET  /api/search?q=<song>   → YouTube suggestions for a song name
  POST /api/process           → SSE: download → lyrics → Agent 1 hook → Agent 2 visual plan → Agent 3 reel
  POST /api/regenerate        → SSE: same clip and plan, new seed → re-rendered reel
  GET  /outputs/...           → generated audio / videos
"""

import asyncio
import json
import os
import random
import re
import sys
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

sys.path.insert(0, BASE_DIR)
from backend import claude_agents, reel_composer, story_planner, visual_renderer  # noqa: E402
from backend import visual_sources  # noqa: E402
from backend.agent1_extractor import RealAudioExtractorAgent  # noqa: E402
from backend.agent3_composer import VIDEOS_DIR, generate_instagram_pack  # noqa: E402
from backend.audio_analysis import analyze_audio  # noqa: E402
from backend.ffmpeg_setup import INSTALL_HELP, ensure_ffmpeg  # noqa: E402
from backend.lyrics import Line, approximate_timing, fetch_lyrics, transcribe_clip  # noqa: E402

app = FastAPI(title="Daily Content Creation Agent", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# Last visual plan per clip file, so Regenerate keeps the same look and only changes the seed.
LAST_PLANS: dict[str, dict] = {}
MEDIA_DIR = os.path.join(OUTPUTS_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)


def _url(path: str) -> str:
    """Filesystem path under outputs/ → public /outputs/... URL."""
    return "/outputs/" + os.path.relpath(path, OUTPUTS_DIR).replace(os.sep, "/")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:40] or "song"


def _sse(event: str, message: str, data: Optional[dict] = None) -> str:
    return f"event: {event}\ndata: {json.dumps({'message': message, 'data': data or {}})}\n\n"


def _scenes_for_gallery(plan: dict) -> list[dict]:
    return [
        {"id": i + 1, "text": s.get("concept", f"Segment {i + 1}"), "start": s["start"], "end": s["end"],
         "duration": round(s["end"] - s["start"], 3), "prompt": s.get("query", ""),
         "image_url": "", "image_source": "", "vibe_name": plan.get("mood", "")}
        for i, s in enumerate(plan["segments"])
    ]


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(WEB_DIR, "app.js"))


@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(WEB_DIR, "style.css"))


@app.get("/api/health")
def health():
    return {
        "claude_enabled": claude_agents.available(),
        "model": claude_agents.MODEL,
        "render": f"{visual_renderer.OUT_W}x{visual_renderer.OUT_H} @ {visual_renderer.FPS}fps, text-free, Instagram-ready MP4",
        "stock_video": "Pexels" if os.getenv("PEXELS_API_KEY") else ("Pixabay" if os.getenv("PIXABAY_API_KEY") else "none (add PEXELS_API_KEY or PIXABAY_API_KEY)"),
        "images": "Pollinations.ai (free, no key)",
        "ffmpeg": bool(ensure_ffmpeg()),
        "author": "Bhagirath Argade",
    }


@app.get("/api/search")
async def search_songs(q: str = Query(..., min_length=1)):
    """YouTube suggestions for a song name."""
    results = await asyncio.to_thread(RealAudioExtractorAgent().search_songs, q, 8)
    if results and results[0].get("error"):
        return JSONResponse(status_code=502, content={"results": [], "error": results[0]["error"][:300]})
    return JSONResponse(content={"results": [r for r in results if r.get("video_id")]})


class ProcessRequest(BaseModel):
    youtube_url: str
    song_title: str
    artist: str = ""
    vibe: str = "bollywood_drama"
    subtitle_style: str = "Karaoke Highlight"
    target_len: float = 25.0


@app.post("/api/process")
async def process_pipeline(req: ProcessRequest):
    """Full pipeline, streamed as Server-Sent Events."""
    target = max(10.0, min(45.0, req.target_len))
    min_len, max_len = max(8.0, target * 0.6), target * 1.2

    async def event_stream():
        try:
            if ensure_ffmpeg() is None:
                yield _sse("error", INSTALL_HELP)
                return
            agent1 = RealAudioExtractorAgent()

            yield _sse("progress", "[Agent 1] Downloading the song's audio from YouTube…")
            dl = await asyncio.to_thread(agent1.download_audio, req.youtube_url, req.song_title)
            if dl.get("status") == "error" or not dl.get("path"):
                yield _sse("error", f"[Agent 1] {dl.get('error', 'Download failed')}")
                return
            full_path = dl["path"]
            full_duration = float(dl.get("duration") or 200)
            artist = req.artist or dl.get("uploader") or ""
            yield _sse("progress", f"[Agent 1] Audio ready: {dl.get('title', req.song_title)} ({full_duration:.0f}s)")

            yield _sse("progress", "[Agent 1] Looking up lyrics (time-synced when available)…")
            lyr = await asyncio.to_thread(fetch_lyrics, req.song_title, artist)
            lines: List[Line] = lyr["lines"]
            if lyr["synced"]:
                yield _sse("progress", f"[Agent 1] Time-synced lyrics found: {len(lines)} lines ({lyr['source']})")
            elif lyr["plain"]:
                lines = approximate_timing(lyr["plain"], full_duration)
                yield _sse("progress", f"[Agent 1] Plain lyrics found ({lyr['source']}) - timing is approximate")
            else:
                yield _sse("progress", "[Agent 1] No lyrics found online - the sound alone will guide the visuals")

            mode = "Claude Sonnet 5.5" if claude_agents.available() else "heuristic (no ANTHROPIC_API_KEY)"
            yield _sse("progress", f"[Agent 1] Choosing the most viral window with {mode}…")
            hook = await asyncio.to_thread(claude_agents.pick_hook, req.song_title, artist, lines, full_duration, target, min_len, max_len)
            yield _sse("progress", f"[Agent 1] Hook {hook['start']:.1f}s → {hook['end']:.1f}s · virality {hook['virality_score']}/100")

            clip_path = await asyncio.to_thread(agent1.extract_clip, full_path, hook["start"], hook["end"], req.song_title)
            clip_len = round(hook["end"] - hook["start"], 2)
            yield _sse("progress", f"[Agent 1] Clip cut: {os.path.basename(clip_path)}")

            clip_lines = [
                Line(max(0.0, l.start - hook["start"]), min(clip_len, l.end - hook["start"]), l.text)
                for l in lines if l.end > hook["start"] and l.start < hook["end"]
            ]
            if not clip_lines:
                clip_lines = await asyncio.to_thread(transcribe_clip, clip_path)
            lyrics_text = " / ".join(l.text for l in clip_lines)

            yield _sse("progress", "[Agent 2] Analysing the clip's sound: loudness, beats and brightness…")
            feats = await asyncio.to_thread(analyze_audio, clip_path)
            yield _sse("progress", f"[Agent 2] Tempo about {feats['bpm']:.0f} BPM · {feats['duration']:.1f}s")

            yield _sse("progress", f"[Agent 2] Understanding the clip's meaning and planning realistic shots with {mode}…")
            plan = await asyncio.to_thread(story_planner.plan_story, req.song_title, artist, lyrics_text, feats["duration"], feats, lines=clip_lines)
            LAST_PLANS[os.path.basename(clip_path)] = plan
            yield _sse("progress", f"[Agent 2] Mood: {plan.get('mood', '')} · {len(plan['segments'])} shots · look: {plan['look']} ({plan['source']})")

            slug = _slug(req.song_title)
            yield _sse("progress", "[Agent 3] Finding realistic footage for each shot and composing the 1080×1920 reel (a few minutes)…")
            rendered = await asyncio.to_thread(
                reel_composer.compose_reel, clip_path, plan, os.path.join(VIDEOS_DIR, f"{slug}_reel.mp4"), 0, feats, None, MEDIA_DIR
            )
            video_path = rendered["path"]
            yield _sse("progress", f"[Agent 3] Reel ready · shot sources: {', '.join(sorted(set(rendered['sources'])))}")

            hook_line = lines[hook["first_line"]].text if hook.get("first_line") is not None and lines else req.song_title
            pack = generate_instagram_pack(req.song_title, artist, plan.get("mood", ""), hook_line, video_path)

            result = {
                "agent1": {
                    "title": dl.get("title", req.song_title),
                    "artist": artist,
                    "hook_start": hook["start"],
                    "hook_end": hook["end"],
                    "hook_duration": clip_len,
                    "virality_score": hook["virality_score"],
                    "why": hook.get("why", ""),
                    "mood": hook.get("mood", ""),
                    "source": hook.get("source", ""),
                    "lyrics": {"source": lyr["source"], "synced": lyr["synced"], "lines": len(lines)},
                    "audio_clip": _url(clip_path),
                },
                "agent2": {
                    "mood": plan.get("mood", ""),
                    "meaning": plan.get("meaning", ""),
                    "style": {"palette": plan["palette"], "mood": plan.get("mood", ""), "look": plan["look"]},
                    "look": plan["look"],
                    "suggestions": plan["suggestions"],
                    "sources": rendered["sources"],
                    "source": plan["source"],
                    "bpm": feats["bpm"],
                    "scenes": _scenes_for_gallery(plan),
                },
                "agent3": {"video_url": _url(video_path), "resolution": "1080x1920", "fps": visual_renderer.FPS, "look": plan["look"], **pack},
            }
            yield _sse("complete", "[Pipeline Complete] Your Instagram Reel is ready!", result)
        except Exception as e:
            yield _sse("error", f"Pipeline error: {type(e).__name__}: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class RegenerateRequest(BaseModel):
    scenes: List[dict] = []     # accepted for compatibility; the plan comes from the last run
    vibe: str = "bollywood_drama"
    song_title: str = ""
    seed: int = 0               # 0 = pick a new random seed
    audio_clip: str = ""        # agent1.audio_clip from the last run
    look: str = ""              # optional colour look from the Suggest Edits section


@app.post("/api/regenerate")
async def regenerate_visuals(req: RegenerateRequest):
    """Same clip and look, new seed: particles, rings and light paths change, and the reel is re-rendered."""

    async def regen_stream():
        try:
            clip_file = os.path.join(OUTPUTS_DIR, "audio", os.path.basename(req.audio_clip)) if req.audio_clip else ""
            if not clip_file or not os.path.exists(clip_file):
                yield _sse("error", "Regeneration error: the clip for this reel is no longer available - process the song again.")
                return
            seed = req.seed if req.seed > 0 else random.randint(1, 999_999)
            yield _sse("progress", f"[Agent 3] New visual variation (seed {seed}) for the same clip and mood…")
            feats = await asyncio.to_thread(analyze_audio, clip_file)
            plan = LAST_PLANS.get(os.path.basename(clip_file)) or story_planner.heuristic_story(feats["duration"], feats)
            if req.look in reel_composer.LOOKS:
                plan = {**plan, "look": req.look}
                LAST_PLANS[os.path.basename(clip_file)] = plan
            out = os.path.join(VIDEOS_DIR, f"{_slug(req.song_title)}_reel_s{seed}.mp4")
            rendered = await asyncio.to_thread(reel_composer.compose_reel, clip_file, plan, out, seed, feats, plan["look"], MEDIA_DIR)
            video_path = rendered["path"]
            yield _sse("complete", "Regeneration complete - new visuals ready!", {
                "seed": seed,
                "scenes": _scenes_for_gallery(plan),
                "video_url": _url(video_path),
                "look": plan["look"],
                "sources": rendered["sources"],
            })
        except Exception as e:
            yield _sse("error", f"Regeneration error: {type(e).__name__}: {e}")

    return StreamingResponse(regen_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
