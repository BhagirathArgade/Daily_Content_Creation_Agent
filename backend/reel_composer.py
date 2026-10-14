"""Agent 3 - Reel Composer: realistic footage for each segment, cut to the clip's audio.

Per segment, in order: free stock video (Pexels / Pixabay) → free AI still with a slow camera
move (Pollinations) → sound-reactive animation. Every shot gets the same colour look. No text.
Exports 1080x1920, 30 fps, H.264 + AAC, fast-start, ready to upload to Instagram Reels.
Author: Bhagirath Argade
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image

from . import visual_sources
from .audio_analysis import analyze_audio
from .visual_renderer import FPS, OUT_H, OUT_W, _Scene

LOOKS = {
    "cinematic_warm": {"gain": (1.05, 1.0, 0.92), "contrast": 1.08, "sat": 1.05},
    "moody_blue": {"gain": (0.92, 0.99, 1.08), "contrast": 1.12, "sat": 0.9},
    "soft_pastel": {"gain": (1.04, 1.0, 1.02), "contrast": 0.95, "sat": 0.8},
    "bw_film": {"gain": (1.0, 1.0, 1.0), "contrast": 1.15, "sat": 0.0},
}
DEFAULT_LOOK = "cinematic_warm"


def grade(frame: np.ndarray, look: dict) -> np.ndarray:
    f = frame.astype(np.float32) / 255.0
    grey = f.mean(axis=-1, keepdims=True)
    f = grey + (f - grey) * look["sat"]
    f = (f - 0.5) * look["contrast"] + 0.5
    f = f * np.array(look["gain"], dtype=np.float32)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def _cover(clip):
    """Scale and centre-crop any clip to exactly 1080x1920."""
    scale = max(OUT_W / clip.w, OUT_H / clip.h)
    c = clip.resized(scale)
    return c.cropped(x_center=c.w / 2, y_center=c.h / 2, width=OUT_W, height=OUT_H)


def _still_with_move(path: str, duration: float, move: str):
    """A still image with a slow camera move: push-in, or pan left/right."""
    from moviepy import VideoClip

    pad = 1.15
    base = Image.open(path).convert("RGB").resize((int(OUT_W * pad), int(OUT_H * pad)), Image.LANCZOS)
    bw, bh = base.size

    def frame(tau: float):
        p = min(max(tau / max(duration, 0.01), 0.0), 1.0)
        zoom = 1.0 if move == "static" else 1.0 + 0.10 * p
        cw, ch = bw / zoom, bh / zoom
        if move == "slow pan left":
            x0 = (bw - cw) * (1 - p)
        elif move == "slow pan right":
            x0 = (bw - cw) * p
        else:
            x0 = (bw - cw) / 2
        y0 = (bh - ch) / 2
        crop = base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
        return np.asarray(crop.resize((OUT_W, OUT_H), Image.LANCZOS))

    return VideoClip(frame, duration=duration).with_fps(FPS)


def _procedural(seg: dict, t0: float, duration: float, feats: dict, palette: list[str], seed: int):
    from moviepy import VideoClip

    scene = _Scene(palette, seed, feats)

    def frame(tau: float):
        t = t0 + tau
        img = scene.render(t, seg["motion"], int(round(t * FPS)))
        return np.asarray(Image.fromarray(img).resize((OUT_W, OUT_H), Image.LANCZOS))

    return VideoClip(frame, duration=duration).with_fps(FPS)


def _segment_clip(seg: dict, idx: int, seed: int, work: str, feats: dict, palette: list[str], look: dict):
    """Returns (clip, source_label)."""
    from moviepy import VideoFileClip, concatenate_videoclips

    d = max(0.2, seg["end"] - seg["start"])
    try:
        stock = visual_sources.find_stock_video(seg["query"], os.path.join(work, "stock"), index=seed + idx)
        if stock:
            v = _cover(VideoFileClip(stock, audio=False))
            if v.duration < d:
                reps = int(np.ceil(d / max(v.duration, 0.1)))
                v = concatenate_videoclips([v] * reps)
            span = max(0.0, v.duration - d)
            start = ((seed * 7 + idx * 3) % 10) / 10.0 * span
            return v.subclipped(start, start + d).image_transform(lambda f: grade(f, look)), "stock video"
    except Exception:
        pass
    try:
        img = visual_sources.generate_image(seg["prompt"], os.path.join(work, f"still_{idx}_{seed}.jpg"), seed=seed * 31 + idx)
        if img:
            return _still_with_move(img, d, seg["shot"]).image_transform(lambda f: grade(f, look)), "AI still"
    except Exception:
        pass
    return _procedural(seg, seg["start"], d, feats, palette, seed).image_transform(lambda f: grade(f, look)), "sound animation"


def compose_reel(clip_path: str, plan: dict, out_path: str, seed: int = 0, feats: dict | None = None,
                 look_name: str | None = None, work_dir: str | None = None) -> dict:
    """Render the Instagram-ready reel. Returns {'path', 'sources': [...], 'look'}."""
    from moviepy import AudioFileClip, concatenate_videoclips

    feats = feats or analyze_audio(clip_path)
    look_key = look_name if look_name in LOOKS else plan.get("look", DEFAULT_LOOK)
    look = LOOKS.get(look_key, LOOKS[DEFAULT_LOOK])
    work = work_dir or os.path.join(os.path.dirname(out_path), "media")
    os.makedirs(work, exist_ok=True)
    palette = plan.get("palette") or ["#0b132b", "#1c2541", "#3a506b", "#5bc0be", "#e0fbfc"]

    parts, sources = [], []
    for i, seg in enumerate(plan["segments"]):
        clip, label = _segment_clip(seg, i, seed, work, feats, palette, look)
        parts.append(clip)
        sources.append(label)

    final = concatenate_videoclips(parts, method="compose")
    dur = feats["duration"]
    final = final.subclipped(0, min(dur, final.duration))
    final = final.with_audio(AudioFileClip(clip_path).subclipped(0, final.duration))
    final.write_videofile(
        out_path, fps=FPS, codec="libx264", audio_codec="aac", bitrate="8000k", threads=2, logger=None,
        ffmpeg_params=["-movflags", "+faststart", "-pix_fmt", "yuv420p", "-profile:v", "high"],
    )
    final.close()
    return {"path": out_path, "sources": sources, "look": look_key}
