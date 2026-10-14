"""Frame-by-frame audio features for the reel: loudness, beats and brightness.

Decodes the clip with the bundled ffmpeg and uses numpy only (no librosa).
Author: Bhagirath Argade
"""
from __future__ import annotations

import subprocess

import numpy as np

from .ffmpeg_setup import ffmpeg_exe

SR = 22050
FPS = 30


def decode_mono(path: str) -> np.ndarray:
    raw = subprocess.run(
        [ffmpeg_exe(), "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def analyze_audio(path: str, fps: int = FPS) -> dict:
    """Returns per-video-frame arrays (all normalized 0..1) plus duration and a tempo estimate."""
    x = decode_mono(path)
    hop = SR // fps
    n = max(1, len(x) // hop)
    frames = x[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    rms = rms / (rms.max() + 1e-9)

    onset = np.clip(np.diff(rms, prepend=rms[0]), 0, None)
    onset = onset / (onset.max() + 1e-9)

    win = 2048
    xpad = np.pad(x, (win // 2, win // 2))
    idx = (np.arange(n) * hop + hop // 2)[:, None] + np.arange(win)[None, :]
    mag = np.abs(np.fft.rfft(xpad[idx] * np.hanning(win), axis=1))
    freqs = np.fft.rfftfreq(win, 1 / SR)
    cent = (mag * freqs).sum(axis=1) / (mag.sum(axis=1) + 1e-9)
    cent = (cent - cent.min()) / (cent.max() - cent.min() + 1e-9)

    bpm = 0.0
    lo, hi = int(0.3 * fps), int(1.0 * fps)
    if n > hi + 2:
        o = onset - onset.mean()
        ac = np.correlate(o, o, mode="full")[len(o) - 1 :]
        lag = lo + int(np.argmax(ac[lo:hi]))
        bpm = 60.0 * fps / lag

    return {"fps": fps, "duration": n / fps, "rms": rms, "onset": onset, "centroid": cent, "bpm": round(bpm, 1)}
