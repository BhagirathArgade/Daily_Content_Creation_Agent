"""
FastAPI backend - Daily Content Creation Agent (the real pipeline)
Author: Bhagirath Argade
GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent

Endpoints:
  GET  /                      → web dashboard
  GET  /api/health            → which brains are active (Claude / heuristics)
  GET  /api/search?q=<song>   → YouTube suggestions for a song name
  POST /api/process           → SSE: download → lyrics → Agent 1 hook → Agent 2 scenes/images → Agent 3 reel
  POST /api/regenerate        → SSE: same lyrics & prompts, NEW images (+ re-rendered reel)
  GET  /outputs/...           → generated audio / images / videos
"""

import asyncio
import json
import os
import random
import re
import sys
import uuid
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
from backend import agent2_visual, claude_agents  # noqa: E402
from backend.agent1_extractor import RealAudioExtractorAgent  # noqa: E402
from backend.agent3_composer import VIDEOS_DIR, build_video, generate_instagram_pack  # noqa: E402
from backend.lyrics import Line, approximate_timing, fetch_lyrics  # noqa: E402

app = FastAPI(title="Daily Content Creation Agent", version="2.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


def _url(path: str) -> str:
    """Filesystem path under outputs/ → public /outputs/... URL."""
    return "/outputs/" + os.path.relpath(path, OUTPUTS_DIR).replace(os.sep, "/")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:40] or "song"


def _sse(event: str, message: str, data: Optional[dict] = None) -> str:
    return f"event: {event}\ndata: {json.dumps({'message': message, 'data': data or {}})}\n\n"


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
        "image_source": "Pollinations.ai (free) with an offline procedural fallback",
        "author": "Bhagirath Argade",
    }


@app.get("/api/search")
async def search_songs(q: str = Query(..., min_length=1)):
    """YouTube suggestions for a song name."""
    results = await asyncio.to_thread(RealAudioExtractorAgent().search_songs, q, 8)
    return JSONResponse(content={"results": results})


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
    preset = agent2_visual.VIBE_PRESETS.get(req.vibe, agent2_visual.VIBE_PRESETS[agent2_visual.DEFAULT_VIBE])
    target = max(10.0, min(45.0, req.target_len))
    min_len, max_len = max(8.0, target * 0.6), target * 1.2

    async def event_stream():
        try:
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
                yield _sse("progress", "[Agent 1] No lyrics found online - captions will use the song title")

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
            yield _sse("progress", f"[Agent 2] {len(clip_lines)} lyric lines fall inside the clip - splitting into caption phrases…")
            plan = await asyncio.to_thread(
                claude_agents.plan_scenes, req.song_title, artist, clip_lines, clip_len,
                preset["name"], preset["style_suffix"], preset["palette"], "",
            )
            palette = plan["style"].get("palette") or preset["palette"]
            yield _sse("progress", f"[Agent 2] {len(plan['scenes'])} scenes planned in one style ({plan['source']})")

            out_dir = os.path.join(agent2_visual.IMAGES_DIR, _slug(req.song_title))
            scenes = []
            for sc in plan["scenes"]:
                yield _sse("progress", f"[Agent 2] Generating image {sc['id']}/{len(plan['scenes'])}: \"{sc['text'][:45]}\"")
                rendered = await asyncio.to_thread(agent2_visual.render_scenes, [sc], palette, out_dir, 0)
                scenes.extend(rendered)

            yield _sse("progress", "[Agent 3] Compositing the 9:16 reel: scenes + hook audio…")
            video_path = await asyncio.to_thread(build_video, scenes, clip_path, req.song_title, None, "")
            if video_path.startswith("error:"):
                yield _sse("progress", f"[Agent 3] Reel render failed ({video_path[6:]}); images are still available")
                video_path = ""

            hook_line = lines[hook["first_line"]].text if hook.get("first_line") is not None else scenes[0]["text"]
            pack = generate_instagram_pack(req.song_title, artist, preset["name"], hook_line, video_path)

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
                    "style": plan["style"],
                    "source": plan["source"],
                    "scenes": [
                        {
                            "id": s["id"], "text": s["text"], "start": s["start"], "end": s["end"],
                            "duration": s["duration"], "prompt": s["prompt"],
                            "image_url": _url(s["image_path"]), "image_source": s["image_source"],
                            "vibe_name": preset["name"],
                        }
                        for s in scenes
                    ],
                },
                "agent3": {"video_url": _url(video_path) if video_path else "", **pack},
            }
            yield _sse("complete", "[Pipeline Complete] Your Instagram Reel is ready!", result)
        except Exception as e:
            yield _sse("error", f"Pipeline error: {type(e).__name__}: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class RegenerateRequest(BaseModel):
    scenes: List[dict]          # from the last run: id, text, start, end, prompt
    vibe: str = "bollywood_drama"
    song_title: str = ""
    seed: int = 0               # 0 = pick a new random seed
    audio_clip: str = ""        # agent1.audio_clip from the last run, to re-render the reel


@app.post("/api/regenerate")
async def regenerate_visuals(req: RegenerateRequest):
    """Same lyrics, same prompts, brand-new images (new seed), reel re-rendered."""
    preset = agent2_visual.VIBE_PRESETS.get(req.vibe, agent2_visual.VIBE_PRESETS[agent2_visual.DEFAULT_VIBE])

    async def regen_stream():
        try:
            seed = req.seed if req.seed > 0 else random.randint(1, 999_999)
            scenes_in = []
            for i, s in enumerate(req.scenes):
                text = str(s.get("text", ""))
                scenes_in.append({
                    "id": int(s.get("id", i + 1)), "text": text,
                    "start": float(s["start"]), "end": float(s["end"]),
                    "prompt": s.get("prompt") or f"{text}, {preset['style_suffix']}",
                })
            out_dir = os.path.join(agent2_visual.IMAGES_DIR, _slug(req.song_title))
            scenes = []
            for sc in scenes_in:
                yield _sse("progress", f"[Agent 2] New image for \"{sc['text'][:45]}\" (seed {seed})")
                scenes.extend(await asyncio.to_thread(agent2_visual.regenerate_storyboard, [sc], preset["palette"], out_dir, seed))

            video_url = ""
            clip_file = os.path.join(OUTPUTS_DIR, "audio", os.path.basename(req.audio_clip)) if req.audio_clip else ""
            if clip_file and os.path.exists(clip_file):
                yield _sse("progress", "[Agent 3] Re-rendering the reel with the new visuals…")
                out = await asyncio.to_thread(build_video, scenes, clip_file, req.song_title, None, f"_s{seed}")
                if out.startswith("error:"):
                    yield _sse("progress", f"[Agent 3] Reel render failed ({out[6:]})")
                else:
                    video_url = _url(out)

            yield _sse("complete", "Regeneration complete - new visuals ready!", {
                "seed": seed,
                "scenes": [{"id": s["id"], "text": s["text"], "start": s["start"], "end": s["end"],
                            "duration": s["duration"], "prompt": s["prompt"], "image_url": _url(s["image_path"]),
                            "image_source": s["image_source"], "vibe_name": preset["name"]} for s in scenes],
                "video_url": video_url,
            })
        except Exception as e:
            yield _sse("error", f"Regeneration error: {type(e).__name__}: {e}")

    return StreamingResponse(regen_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
