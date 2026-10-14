"""Find ffmpeg / ffprobe even when they are not on PATH (common on Windows).

Looks in: PATH, the FFMPEG_LOCATION env var, the winget install folder, C:\\ffmpeg\\bin.
When found, its folder is added to PATH so yt-dlp, moviepy and ffmpeg all see it.

Author: Bhagirath Argade
"""
from __future__ import annotations

import glob
import os
import shutil

INSTALL_HELP = (
    "ffmpeg was not found. Install it, then restart the app:\n"
    "  Windows: winget install --id Gyan.FFmpeg -e   (or set FFMPEG_LOCATION to its bin folder)\n"
    "  macOS:   brew install ffmpeg\n"
    "  Linux:   sudo apt install ffmpeg"
)


def _candidate_dirs():
    env = os.getenv("FFMPEG_LOCATION")
    if env:
        yield env
    local = os.getenv("LOCALAPPDATA")
    if local:
        yield from glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "*FFmpeg*", "**", "bin"), recursive=True)
    yield r"C:\ffmpeg\bin"
    yield r"C:\Program Files\ffmpeg\bin"


def ensure_ffmpeg() -> str | None:
    """Returns the folder holding ffmpeg and ffprobe, or None. Adds it to PATH when found outside PATH."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return os.path.dirname(shutil.which("ffmpeg"))
    for d in _candidate_dirs():
        folder = d if os.path.isdir(d) else os.path.dirname(d)
        if all(os.path.isfile(os.path.join(folder, n)) for n in ("ffmpeg.exe", "ffprobe.exe")) or all(
            os.path.isfile(os.path.join(folder, n)) for n in ("ffmpeg", "ffprobe")
        ):
            os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
            return folder
    return None
