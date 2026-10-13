"""Agent 2 - Aesthetic Storyboarder: caption scenes + one matching image per scene.

Flow: lyric lines of the clip -> claude_agents.plan_scenes() (Sonnet 5.5, or heuristics)
      -> one image per scene (Pollinations.ai, free, no key; procedural backdrop if offline)
Regeneration keeps the SAME lyric scenes and prompts, only the image seed changes.

Author: Bhagirath Argade
"""
from __future__ import annotations

import hashlib
import os
import random
from io import BytesIO
from urllib.parse import quote

import requests
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import claude_agents

W, H = 1080, 1920
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
IMAGES_DIR = os.path.join(OUTPUTS_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

VIBE_PRESETS = {
    "moody_monsoon": {
        "name": "Moody Monsoon 35mm Film",
        "style_suffix": "cinematic 35mm film grain, rain-soaked neon street, emotional longing, Wong Kar-wai color grading, dark blue and amber tones, shallow depth of field, anamorphic lens flare, 9:16 vertical portrait, photorealistic, 8k",
        "palette": ["#0b1a2a", "#1f3b57", "#c98a3b", "#f2d6a2", "#2b1d2e"],
    },
    "golden_hour": {
        "name": "Golden Hour Nostalgia",
        "style_suffix": "golden hour sunburst, Kodak Portra 400 warm tones, soft hazy bokeh, romantic dreamy, 9:16 vertical portrait, cinematic still, 8k",
        "palette": ["#ffd6a5", "#f4a261", "#e76f51", "#8d5a97", "#fff1d6"],
    },
    "cyber_lofi": {
        "name": "Cyber Lofi Midnight",
        "style_suffix": "cyberpunk lofi Tokyo midnight neon, purple and cyan electric glow, rain-damp streets, moody 9:16 vertical portrait, synthwave atmosphere, 8k",
        "palette": ["#0d0221", "#5b2a86", "#00f5d4", "#ff2e88", "#1b1f3b"],
    },
    "dark_academia": {
        "name": "Dark Academia Vintage",
        "style_suffix": "dark academia aesthetic, candlelit antique library, sepia and warm mahogany tones, vintage solitude, 9:16 vertical portrait, Chiaroscuro lighting, 8k",
        "palette": ["#1c1410", "#4a2f1d", "#a0692e", "#d8b483", "#2e2a26"],
    },
    "anime_sky": {
        "name": "Makoto Shinkai Anime Sky",
        "style_suffix": "Makoto Shinkai anime background art, hyper-detailed twilight clouds, shooting stars, radiant gradient sky, 9:16 vertical, 8k",
        "palette": ["#1d2b64", "#3a6ea5", "#8ecae6", "#ffb703", "#f8f7ff"],
    },
    "bollywood_drama": {
        "name": "Bollywood Cinematic Drama",
        "style_suffix": "Bollywood epic cinematic still, dramatic Indian landscape, vibrant marigold and crimson tones, soulful emotion, backlighting, 9:16 vertical, 8k, photorealistic",
        "palette": ["#7a0c0c", "#c1121f", "#f77f00", "#fcbf49", "#2d0a31"],
    },
}
DEFAULT_VIBE = "bollywood_drama"


def image_seed(prompt: str, seed: int) -> int:
    """Stable across runs and machines (Python's hash() is not)."""
    return int(hashlib.md5(f"{prompt}|{seed}".encode("utf-8")).hexdigest()[:8], 16) % 999_999


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def procedural_backdrop(seed_text: str, palette: list[str], dest: str) -> str:
    """Offline fallback: vertical gradient + blurred light blobs in the palette."""
    rnd = random.Random(image_seed(seed_text, 0))
    cols = [_hex(c) for c in (palette or ["#1b1b2f", "#e94560", "#f6c177"])]
    a, b = rnd.sample(cols, 2) if len(cols) > 1 else (cols[0], cols[0])
    base = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(base)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a[k] * (1 - t) + b[k] * t) for k in range(3)))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for _ in range(rnd.randint(3, 5)):
        r = rnd.randint(260, 520)
        cx, cy = rnd.randint(0, W), rnd.randint(int(H * 0.1), int(H * 0.9))
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rnd.choice(cols))
    img = ImageChops.screen(base, glow.filter(ImageFilter.GaussianBlur(160)))
    img.save(dest, quality=92)
    return dest


def generate_image(prompt: str, dest: str, seed: int, palette: list[str], timeout: float = 60) -> str:
    """Returns the source used: 'pollinations.ai' or 'procedural'."""
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt[:900])}"
           f"?width={W}&height={H}&seed={image_seed(prompt, seed)}&nologo=true")
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            Image.open(BytesIO(r.content)).convert("RGB").save(dest, quality=92)
            return "pollinations.ai"
    except Exception:
        pass
    procedural_backdrop(prompt, palette, dest)
    return "procedural"


def render_scenes(scenes: list[dict], palette: list[str], out_dir: str, seed: int, on_progress=None) -> list[dict]:
    """Adds image_path / image_source / seed to each scene (prompts and timings untouched)."""
    os.makedirs(out_dir, exist_ok=True)
    rendered = []
    for n, sc in enumerate(scenes):
        if on_progress:
            on_progress(n, len(scenes), sc["text"])
        dest = os.path.join(out_dir, f"scene_{int(sc['id']):02d}_seed{seed}.jpg")
        src = generate_image(sc["prompt"], dest, seed, palette)
        rendered.append({**sc, "image_path": dest, "image_source": src, "seed": seed,
                         "duration": round(max(0.1, float(sc["end"]) - float(sc["start"])), 3)})
    return rendered


def build_storyboard(song: str, artist: str, clip_lines, clip_len: float, vibe_key: str,
                     out_dir: str, vibe_hint: str = "", on_progress=None) -> dict:
    """Agent 2 end-to-end. Returns {'style', 'scenes', 'source'}."""
    preset = VIBE_PRESETS.get(vibe_key, VIBE_PRESETS[DEFAULT_VIBE])
    plan = claude_agents.plan_scenes(
        song, artist, clip_lines, clip_len,
        vibe_name=preset["name"], style_suffix=preset["style_suffix"],
        fallback_palette=preset["palette"], vibe_hint=vibe_hint,
    )
    palette = plan["style"].get("palette") or preset["palette"]
    plan["scenes"] = render_scenes(plan["scenes"], palette, out_dir, seed=0, on_progress=on_progress)
    return plan


def regenerate_storyboard(scenes: list[dict], palette: list[str], out_dir: str, seed: int, on_progress=None) -> list[dict]:
    """Same lyrics, same prompts, new images: only the seed changes."""
    return render_scenes(scenes, palette, out_dir, seed=seed, on_progress=on_progress)
