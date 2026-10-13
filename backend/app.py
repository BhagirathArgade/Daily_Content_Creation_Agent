"""
FastAPI Backend — Daily Content Creation Agent
Author: Bhagirath Argade
GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent

Endpoints:
  GET  /                           → Serve the web dashboard
  GET  /api/search?q=<song>        → YouTube search suggestions
  POST /api/process                → Full pipeline: download + lyrics + images + video
  POST /api/regenerate             → Regenerate images for same lyrics (new seed)
  GET  /outputs/<type>/<filename>  → Serve generated files
"""

import os
import sys
import json
import asyncio
from typing import Optional, List
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# UTF-8 Windows fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Import agents
sys.path.insert(0, BASE_DIR)
from backend.agent1_extractor import RealAudioExtractorAgent
from backend.agent2_visual import fetch_lyrics, parse_lyrics_to_chunks, generate_storyboard, VIBE_PRESETS
from backend.agent3_composer import build_video, generate_instagram_pack

app = FastAPI(title="Daily Content Creation Agent", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static outputs
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# Serve frontend
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))

@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(WEB_DIR, "app.js"))

@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(WEB_DIR, "style.css"))


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 1: YouTube Song Search Suggestions
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/search")
async def search_songs(q: str = Query(..., min_length=1)):
    """Returns YouTube search suggestions for a song query."""
    agent1 = RealAudioExtractorAgent()
    results = agent1.search_songs(q, max_results=8)
    return JSONResponse(content={"results": results})


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 2: Process Full Pipeline (SSE streaming progress)
# ─────────────────────────────────────────────────────────────────────────────
class ProcessRequest(BaseModel):
    youtube_url: str
    song_title: str
    artist: str = ""
    vibe: str = "bollywood_drama"
    subtitle_style: str = "Karaoke Highlight"


@app.post("/api/process")
async def process_pipeline(req: ProcessRequest):
    """
    Runs the complete 3-agent pipeline and returns SSE stream of progress + final result JSON.
    """
    async def event_stream():
        def send(msg: str, data: dict = None, event: str = "progress"):
            payload = json.dumps({"message": msg, "data": data or {}})
            return f"event: {event}\ndata: {payload}\n\n"

        try:
            agent1 = RealAudioExtractorAgent()

            # AGENT 1: Download Audio
            yield send("[Agent 1] Downloading real audio from YouTube...", event="progress")
            await asyncio.sleep(0.1)

            dl_result = await asyncio.to_thread(agent1.download_audio, req.youtube_url, req.song_title)
            if dl_result["status"] == "error" or not dl_result.get("path"):
                yield send(f"[Agent 1] Error: {dl_result.get('error', 'Download failed')}", event="error")
                return

            full_audio_path = dl_result["path"]
            full_duration = dl_result.get("duration", 200)
            actual_artist = dl_result.get("uploader", req.artist) or req.artist or "Unknown Artist"
            yield send(f"[Agent 1] Audio downloaded: {dl_result['title']} ({full_duration}s)", event="progress")

            # AGENT 1: Detect & Extract Hook
            hook_info = agent1.detect_viral_hook(full_audio_path, full_duration)
            yield send(f"[Agent 1] Viral hook detected: {hook_info['start_sec']}s → {hook_info['end_sec']}s (Virality: {hook_info['virality_score']}/100)", event="progress")

            clip_path = await asyncio.to_thread(
                agent1.extract_clip,
                full_audio_path,
                hook_info["start_sec"],
                hook_info["end_sec"],
                req.song_title,
            )
            yield send(f"[Agent 1] Audio hook clip extracted: {os.path.basename(clip_path)}", event="progress")

            # AGENT 2: Fetch Lyrics
            yield send("[Agent 2] Fetching real lyrics from the internet...", event="progress")
            lyrics_result = await asyncio.to_thread(fetch_lyrics, req.song_title, actual_artist)
            yield send(f"[Agent 2] Lyrics fetched (source: {lyrics_result['source']})", event="progress")

            chunks = parse_lyrics_to_chunks(lyrics_result["lyrics"], hook_info["duration_sec"], max_chunks=5)
            yield send(f"[Agent 2] Parsed into {len(chunks)} rhythmic scenes", event="progress")

            # AGENT 2: Generate Real AI Images
            scenes = []
            for i, chunk in enumerate(chunks):
                yield send(f"[Agent 2] Generating AI image {i+1}/{len(chunks)}: \"{chunk['text'][:45]}\"", event="progress")
                scene_list = await asyncio.to_thread(
                    generate_storyboard, [chunk], req.vibe, req.song_title, 0
                )
                scenes.extend(scene_list)

            yield send(f"[Agent 2] All {len(scenes)} aesthetic images generated!", event="progress")

            # AGENT 3: Compose Real Video
            yield send("[Agent 3] Compositing final 9:16 vertical video with audio + scenes...", event="progress")
            video_path = await asyncio.to_thread(build_video, scenes, clip_path, req.song_title)

            if video_path.startswith("error:"):
                yield send(f"[Agent 3] Composition warning: {video_path[6:]} — delivering image slideshow", event="progress")
                video_path = ""

            # AGENT 3: Instagram Pack
            # Pick the best hook line from lyrics
            hook_line = chunks[0]["text"] if chunks else req.song_title
            insta_pack = generate_instagram_pack(
                req.song_title, actual_artist,
                VIBE_PRESETS.get(req.vibe, {}).get("name", req.vibe),
                hook_line, video_path,
            )

            # Build response payload
            result = {
                "agent1": {
                    "title": dl_result["title"],
                    "artist": actual_artist,
                    "hook_start": hook_info["start_sec"],
                    "hook_end": hook_info["end_sec"],
                    "hook_duration": hook_info["duration_sec"],
                    "virality_score": hook_info["virality_score"],
                    "audio_clip": f"/outputs/audio/{os.path.basename(clip_path)}",
                },
                "agent2": {
                    "lyrics_source": lyrics_result["source"],
                    "scenes": [
                        {
                            "id": s["id"],
                            "text": s["text"],
                            "start": s["start"],
                            "end": s["end"],
                            "image_url": f"/outputs/images/{os.path.basename(s['image_path'])}" if s.get("image_path") else "",
                            "vibe_name": s.get("vibe_name", ""),
                        }
                        for s in scenes
                    ],
                },
                "agent3": {
                    "video_url": f"/outputs/videos/{os.path.basename(video_path)}" if video_path else "",
                    **insta_pack,
                },
            }

            yield send("[Pipeline Complete] Your Instagram Reel is ready!", data=result, event="complete")

        except Exception as e:
            yield send(f"Pipeline error: {str(e)}", event="error")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 3: Regenerate images for same lyrics (new visuals, same audio)
# ─────────────────────────────────────────────────────────────────────────────
class RegenerateRequest(BaseModel):
    scenes: List[dict]         # List of {id, text, start, end} from previous run
    vibe: str = "bollywood_drama"
    song_title: str = ""
    seed: int = 1              # Increment seed for new images


@app.post("/api/regenerate")
async def regenerate_visuals(req: RegenerateRequest):
    """Regenerates new aesthetic images for the same lyrics/scenes."""
    async def regen_stream():
        def send(msg, data=None, event="progress"):
            return f"event: {event}\ndata: {json.dumps({'message': msg, 'data': data or {}})}\n\n"

        try:
            scenes = []
            for i, chunk in enumerate(req.scenes):
                yield send(f"[Agent 2] Regenerating image {i+1}/{len(req.scenes)}: \"{chunk.get('text','')[:45]}\"", event="progress")
                scene_list = await asyncio.to_thread(
                    generate_storyboard, [chunk], req.vibe, req.song_title, req.seed
                )
                for s in scene_list:
                    scenes.append({
                        "id": s["id"],
                        "text": s["text"],
                        "start": s["start"],
                        "end": s["end"],
                        "image_url": f"/outputs/images/{os.path.basename(s['image_path'])}" if s.get("image_path") else "",
                        "vibe_name": s.get("vibe_name", ""),
                    })

            yield send("Regeneration complete — new images ready!", data={"scenes": scenes}, event="complete")
        except Exception as e:
            yield send(f"Regeneration error: {str(e)}", event="error")

    return StreamingResponse(regen_stream(), media_type="text/event-stream")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Daily Content Creation Agent v2.0 — Backend Server")
    print("Author: Bhagirath Argade")
    print("Dashboard: http://localhost:8000")
    print("=" * 60)
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
