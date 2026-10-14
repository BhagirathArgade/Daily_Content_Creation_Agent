"""Agent 3 - Visual Reel Renderer: a high-resolution, text-free, sound-reactive 9:16 video.

Each plan segment has a motion style (aurora, particles, waves, orbs) and a palette.
Motion strength follows the clip's loudness, and flashes follow its beats, so the picture
moves with the sound. No captions, letters or logos are drawn.
Author: Bhagirath Argade
"""
from __future__ import annotations

import numpy as np

from PIL import Image

from .audio_analysis import analyze_audio

# Rendered at 432x768 for speed, then upscaled to the 1080x1920 output with a high-quality filter.
W, H = 432, 768
OUT_W, OUT_H = 1080, 1920
FPS = 30
XFADE = 0.6  # seconds of cross-fade between segments
MOTIONS = ("aurora", "particles", "waves", "orbs")


def hex_to_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def _box_blur(a: np.ndarray, r: int) -> np.ndarray:
    """Separable box blur with edge padding (numpy only)."""
    k = 2 * r + 1
    for axis in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r, r)
        p = np.pad(a, pad, mode="edge")
        c = np.cumsum(p, axis=axis, dtype=np.float64)
        zero_shape = list(c.shape)
        zero_shape[axis] = 1
        c = np.concatenate([np.zeros(zero_shape), c], axis=axis)
        if axis == 0:
            a = ((c[k:] - c[:-k]) / k).astype(np.float32)
        else:
            a = ((c[:, k:] - c[:, :-k]) / k).astype(np.float32)
    return a


def _glow(img: np.ndarray, r: int, factor: int = 4) -> np.ndarray:
    """Cheap large-radius glow: block-average down, blur, block-repeat up."""
    small_shape = (H // factor, factor, W // factor, factor) + img.shape[2:]
    small = img.reshape(small_shape).mean(axis=(1, 3))
    b = _box_blur(small, r)
    return np.repeat(np.repeat(b, factor, axis=0), factor, axis=1)


class _Scene:
    def __init__(self, palette: list[str], seed: int, feats: dict):
        self.pal = np.stack([hex_to_rgb(c) for c in palette])  # 5 x RGB
        self.feats = feats
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xn, self.yn = xx / W, yy / H
        self.base = self.pal[0] * (1 - self.yn[..., None]) + self.pal[1] * self.yn[..., None]
        self.vign = (1 - 0.45 * ((self.xn - 0.5) ** 2 * 1.4 + (self.yn - 0.5) ** 2))[..., None]
        n = 420
        self.px, self.py = rng.uniform(0, W, n), rng.uniform(0, H, n)
        self.pspeed, self.pph = rng.uniform(40, 140, n), rng.uniform(0, 6.28, n)
        self.pb = rng.uniform(0.4, 1.0, n)
        self.orb_ph = rng.uniform(0, 6.28, (4, 2))
        self.ring_off = float(rng.uniform(0, 1))
        self.noise = rng.normal(0, 0.015, (H, W, 1)).astype(np.float32)

    def _at(self, key: str, t: float) -> float:
        arr = self.feats[key]
        return float(arr[min(int(t * self.feats["fps"]), len(arr) - 1)])

    def render(self, t: float, motion: str, frame_idx: int) -> np.ndarray:
        level, beat, bright = self._at("rms", t), self._at("onset", t), self._at("centroid", t)
        img = self.base.copy()
        if motion == "aurora":
            w = np.sin(self.xn * 7 + 2 * np.sin(self.yn * 4 + 0.4 * t) + 0.8 * t)
            center = 0.35 + 0.2 * np.sin(0.3 * t + self.xn * 3)
            band = np.exp(-(((self.yn - center) / 0.12) ** 2)) * (0.35 + 0.9 * level)
            mix = (0.5 + 0.5 * w)[..., None]
            img += (self.pal[2] * mix + self.pal[3] * (1 - mix)) * band[..., None]
        elif motion == "particles":
            yi = ((self.py - self.pspeed * t) % H).astype(int)
            xi = ((self.px + 25 * np.sin(0.7 * t + self.pph)) % W).astype(int)
            buf = np.zeros((H, W), np.float32)
            np.add.at(buf, (yi, xi), self.pb * (0.4 + beat))
            img += self.pal[4] * (buf * 1.0 + _glow(buf, r=6) * 8.0)[..., None]
        elif motion == "waves":
            cy = 0.5 + 0.03 * np.sin(t)
            r = np.hypot(self.xn - 0.5, (self.yn - cy) * (H / W))
            rings = np.zeros((H, W), np.float32)
            for j in range(4):
                ph = (t * 0.22 + j * 0.25 + self.ring_off) % 1.0
                rings += np.exp(-(((r - ph * 0.9) / 0.012) ** 2)) * (1 - ph)
            img += self.pal[2] * (rings * (0.3 + 1.2 * beat + 0.3 * level))[..., None]
        else:  # orbs
            for i in range(4):
                cx = 0.5 + 0.3 * np.sin(0.21 * t + self.orb_ph[i, 0] + i)
                cy = 0.5 + 0.25 * np.cos(0.17 * t + self.orb_ph[i, 1])
                R = 0.18 + 0.12 * level
                blob = np.exp(-(((self.xn - cx) ** 2 + (self.yn - cy) ** 2) / R ** 2)) * 0.8
                img += self.pal[2 + i % 3] * blob[..., None]

        img = np.clip(img * self.vign, 0, 1)
        highlights = np.clip(img - 0.55, 0, None)
        img = 1 - (1 - img) * (1 - np.clip(_glow(highlights, r=8) * (1.4 + 0.6 * bright), 0, 1))
        grain = np.roll(self.noise, shift=((frame_idx * 37) % H, (frame_idx * 91) % W), axis=(0, 1))
        return (np.clip(img + grain, 0, 1) * 255).astype(np.uint8)


def _segment_at(segs: list[dict], t: float):
    for i, s in enumerate(segs):
        if t < s["end"] or i == len(segs) - 1:
            nxt = segs[i + 1] if i + 1 < len(segs) else None
            a = 0.0
            if nxt is not None and t > s["end"] - XFADE:
                a = (t - (s["end"] - XFADE)) / XFADE
            return s, nxt, a
    raise ValueError("empty plan")


def render_reel(clip_path: str, plan: dict, out_path: str, seed: int = 0, feats: dict | None = None) -> str:
    """Render the animated reel with the clip's own audio. Returns out_path."""
    from moviepy import AudioFileClip, VideoClip

    feats = feats or analyze_audio(clip_path)
    dur = feats["duration"]
    palette = list(plan["palette"])
    k = seed % len(palette)
    palette = palette[k:] + palette[:k]  # regeneration rotates the palette too
    scene = _Scene(palette, seed, feats)
    segs = plan["segments"]

    def make_frame(t: float):
        frame_idx = int(round(t * FPS))
        s, nxt, a = _segment_at(segs, t)
        img = scene.render(t, s["motion"], frame_idx).astype(np.float32)
        if a > 0 and nxt is not None:
            img = (1 - a) * img + a * scene.render(t, nxt["motion"], frame_idx).astype(np.float32)
        big = Image.fromarray(img.astype(np.uint8)).resize((OUT_W, OUT_H), Image.LANCZOS)
        return np.asarray(big)

    video = VideoClip(make_frame, duration=dur).with_fps(FPS)
    video = video.with_audio(AudioFileClip(clip_path).with_duration(dur))
    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac", bitrate="8000k", threads=2, logger=None)
    video.close()
    return out_path
