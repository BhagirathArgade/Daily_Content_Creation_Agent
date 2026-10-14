"""ffmpeg for the app - no separate install needed.

Uses the ffmpeg binary bundled by the `imageio-ffmpeg` pip package (moviepy already depends on it),
so it works on Windows, macOS and Linux without PATH or winget. Falls back to a system ffmpeg.

Author: Bhagirath Argade
"""
from __future__ import annotations

import shutil
import subprocess

INSTALL_HELP = "ffmpeg is missing. Run: pip install -r requirements.txt  (it installs ffmpeg through imageio-ffmpeg)"


def ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def ensure_ffmpeg() -> str | None:
    """Path to a working ffmpeg executable, or None."""
    return ffmpeg_exe()


def convert_to_mp3(src: str, dst: str, bitrate: str = "192k") -> str:
    exe = ffmpeg_exe()
    if not exe:
        raise RuntimeError(INSTALL_HELP)
    subprocess.run([exe, "-y", "-v", "error", "-i", src, "-vn", "-b:a", bitrate, dst], check=True)
    return dst
