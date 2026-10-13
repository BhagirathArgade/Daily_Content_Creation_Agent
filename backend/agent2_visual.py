"""
Agent 2: Real Lyrics Fetcher & AI Image Generator
Author: Bhagirath Argade

Capabilities:
- Fetches real lyrics via lyrics.ovh (free, no API key needed)
- Parses lyrics into timed micro-sentence chunks
- Generates real aesthetic images using Pollinations.ai (free, no API key needed)
- Supports full regeneration with new images for same lyrics
"""

import os
import re
import sys
import time
import uuid
import hashlib
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)


# Aesthetic Vibe DNA presets
VIBE_PRESETS = {
    "moody_monsoon": {
        "name": "Moody Monsoon 35mm Film",
        "style_suffix": "cinematic 35mm film grain, rain-soaked neon street, emotional longing, Wong Kar-wai color grading, dark blue and amber tones, shallow depth of field, anamorphic lens flare, 9:16 vertical portrait, photorealistic, 8k",
    },
    "golden_hour": {
        "name": "Golden Hour Nostalgia",
        "style_suffix": "golden hour sunburst, Kodak Portra 400 warm tones, soft hazy bokeh, romantic dreamy, 9:16 vertical portrait, cinematic still, 8k",
    },
    "cyber_lofi": {
        "name": "Cyber Lofi Midnight",
        "style_suffix": "cyberpunk lofi Tokyo midnight neon, purple and cyan electric glow, rain-damp streets, moody 9:16 vertical portrait, synthwave atmosphere, 8k",
    },
    "dark_academia": {
        "name": "Dark Academia Vintage",
        "style_suffix": "dark academia aesthetic, candlelit antique library, sepia and warm mahogany tones, vintage solitude, 9:16 vertical portrait, Chiaroscuro lighting, 8k",
    },
    "anime_sky": {
        "name": "Makoto Shinkai Anime Sky",
        "style_suffix": "Makoto Shinkai anime background art, hyper-detailed twilight clouds, shooting stars, radiant gradient sky, Your Name aesthetic, 9:16 vertical, 8k",
    },
    "bollywood_drama": {
        "name": "Bollywood Cinematic Drama",
        "style_suffix": "Bollywood epic cinematic still, dramatic Indian landscape, vibrant marigold and crimson tones, soulful emotion, backlighting, 9:16 vertical, 8k, photorealistic",
    },
}


def fetch_lyrics(song_title: str, artist: str = "") -> Dict[str, Any]:
    """
    Fetches real lyrics from lyrics.ovh (free public API, no key needed).
    Falls back to chunked placeholder lyrics on failure.
    """
    clean_song = re.sub(r"[^\w\s]", "", song_title).strip()
    clean_artist = re.sub(r"[^\w\s]", "", artist).strip() if artist else "unknown"

    if clean_artist and clean_artist.lower() != "unknown":
        url = f"https://api.lyrics.ovh/v1/{quote(clean_artist)}/{quote(clean_song)}"
    else:
        # Try a second source: lrclib.net (also free, no key)
        url = f"https://lrclib.net/api/search?q={quote(clean_song)}"

    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if "lyrics" in data and data["lyrics"]:
                return {"lyrics": data["lyrics"], "source": "lyrics.ovh", "success": True}
            elif isinstance(data, list) and len(data) > 0:
                # lrclib format
                entry = data[0]
                lyrics = entry.get("plainLyrics") or entry.get("syncedLyrics") or ""
                if lyrics:
                    return {"lyrics": lyrics, "source": "lrclib.net", "success": True}
    except Exception:
        pass

    # Fallback: Try lrclib directly with full search
    try:
        url2 = f"https://lrclib.net/api/search?q={quote(clean_song + ' ' + clean_artist)}"
        resp2 = requests.get(url2, timeout=8)
        if resp2.status_code == 200:
            data2 = resp2.json()
            if isinstance(data2, list) and len(data2) > 0:
                entry = data2[0]
                lyrics = entry.get("plainLyrics") or entry.get("syncedLyrics") or ""
                if lyrics:
                    return {"lyrics": lyrics, "source": "lrclib.net", "success": True}
    except Exception:
        pass

    # Intelligent placeholder when no lyrics available online
    placeholder = (
        f"The melody of {song_title} begins softly\n"
        f"Notes rising like heartbeats in the silence\n"
        f"Every word carries the weight of emotion\n"
        f"The chorus soars high and fills the soul\n"
        f"Memories painted in sound and feeling\n"
        f"The final note echoes into forever"
    )
    return {"lyrics": placeholder, "source": "generated_placeholder", "success": False}


def parse_lyrics_to_chunks(lyrics_text: str, clip_duration: float, max_chunks: int = 6) -> List[Dict]:
    """
    Splits raw lyrics into 4-6 meaningful, evenly-timed scene chunks.
    Each chunk gets a precise start/end timestamp for video sync.
    """
    # Clean: remove timestamps like [00:23.45], empty lines
    cleaned = re.sub(r"\[\d+:\d+\.\d+\]", "", lyrics_text)
    lines = [l.strip() for l in cleaned.split("\n") if l.strip() and len(l.strip()) > 3]

    if len(lines) == 0:
        lines = ["The melody rises with emotion", "Every lyric a heartbeat", "The chorus fills the soul"]

    # Group lines into chunks if too many
    while len(lines) > max_chunks:
        merged = []
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                merged.append(lines[i] + ", " + lines[i + 1])
            else:
                merged.append(lines[i])
        lines = merged

    time_per_chunk = clip_duration / len(lines)
    chunks = []
    for idx, line in enumerate(lines):
        start = round(idx * time_per_chunk, 2)
        end = round((idx + 1) * time_per_chunk, 2)
        if idx == len(lines) - 1:
            end = round(clip_duration, 2)
        chunks.append({
            "id": idx + 1,
            "text": line,
            "start": start,
            "end": end,
            "duration": round(end - start, 2),
        })
    return chunks


def generate_image_for_chunk(chunk_text: str, vibe_key: str, song_title: str, regenerate_seed: int = 0) -> str:
    """
    Generates a real aesthetic image using Pollinations.ai (completely free, no API key).
    The seed parameter allows regenerating different images for the same lyric.
    Returns the local file path of the downloaded image.
    """
    preset = VIBE_PRESETS.get(vibe_key, VIBE_PRESETS["bollywood_drama"])
    style_suffix = preset["style_suffix"]

    # Build scene-specific prompt
    prompt = f"{chunk_text}, {style_suffix}"

    # Unique filename per lyric+seed combo
    seed = abs(hash(chunk_text + str(regenerate_seed))) % 999999
    safe_chunk = re.sub(r"[^\w]", "_", chunk_text[:30]).strip("_")
    filename = f"{safe_chunk}_{vibe_key}_{seed}.jpg"
    local_path = os.path.join(IMAGES_DIR, filename)

    if os.path.exists(local_path) and regenerate_seed == 0:
        return local_path

    # Pollinations.ai API - completely free, generates real AI images
    encoded_prompt = quote(prompt)
    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1080&height=1920&seed={seed}&nologo=true&enhance=true"
    )

    try:
        resp = requests.get(image_url, timeout=30, stream=True)
        if resp.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return local_path
    except Exception:
        pass

    # Fallback: Unsplash themed image
    themes = ["cinematic night city", "dramatic sky", "golden sunset", "emotional portrait", "aesthetic minimal"]
    theme = themes[regenerate_seed % len(themes)]
    fallback_url = f"https://source.unsplash.com/1080x1920/?{quote(theme)}&sig={seed}"
    try:
        r = requests.get(fallback_url, timeout=15, stream=True)
        if r.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return local_path
    except Exception:
        pass

    return ""


def generate_storyboard(
    chunks: List[Dict],
    vibe_key: str,
    song_title: str,
    regenerate_seed: int = 0,
    on_progress=None,
) -> List[Dict]:
    """
    For each chunk, generate a matching aesthetic image.
    Supports regeneration via a new seed integer.
    """
    scenes = []
    for i, chunk in enumerate(chunks):
        if on_progress:
            on_progress(f"Generating image {i+1}/{len(chunks)}: '{chunk['text'][:40]}...'")
        image_path = generate_image_for_chunk(
            chunk["text"], vibe_key, song_title, regenerate_seed=regenerate_seed
        )
        scenes.append({
            **chunk,
            "image_path": image_path,
            "vibe": vibe_key,
            "vibe_name": VIBE_PRESETS.get(vibe_key, {}).get("name", vibe_key),
        })
    return scenes
