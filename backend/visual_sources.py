"""Free visual sources for the reel. Every call fails soft (returns None) so the reel always renders.

* Stock video: Pexels or Pixabay (free accounts; add PEXELS_API_KEY or PIXABAY_API_KEY to .env).
* Still images: Pollinations.ai (free, no key), animated with a slow camera move in the composer.

Author: Bhagirath Argade
"""
from __future__ import annotations

import os
from urllib.parse import quote

import httpx

MAX_DOWNLOAD_MB = 40


def _download(url: str, dest: str) -> str | None:
    try:
        with httpx.stream("GET", url, timeout=60, follow_redirects=True) as r:
            r.raise_for_status()
            size = 0
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes(1 << 16):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_MB * 1024 * 1024:
                        raise ValueError("file too large")
                    fh.write(chunk)
        return dest
    except Exception:
        try:
            os.remove(dest)
        except OSError:
            pass
        return None


def _pexels(query: str, dest_dir: str, index: int) -> str | None:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return None
    r = httpx.get("https://api.pexels.com/videos/search",
                  params={"query": query, "orientation": "portrait", "per_page": 8, "size": "medium"},
                  headers={"Authorization": key}, timeout=20)
    r.raise_for_status()
    options = []
    for v in r.json().get("videos", []):
        files = [f for f in v.get("video_files", []) if "mp4" in (f.get("file_type") or "") and f.get("height")]
        files = [f for f in files if 720 <= f["height"] <= 1920]
        if not files:
            continue
        files.sort(key=lambda f: (f["width"] > f["height"], -f["height"]))  # portrait first, then sharper
        options.append((v["id"], files[0]["link"]))
    if not options:
        return None
    vid, link = options[index % len(options)]
    return _download(link, os.path.join(dest_dir, f"pexels_{vid}.mp4"))


def _pixabay(query: str, dest_dir: str, index: int) -> str | None:
    key = os.getenv("PIXABAY_API_KEY")
    if not key:
        return None
    r = httpx.get("https://pixabay.com/api/videos/",
                  params={"key": key, "q": query, "per_page": 8, "safesearch": "true"}, timeout=20)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    if not hits:
        return None
    hit = hits[index % len(hits)]
    video = (hit.get("videos") or {}).get("medium") or (hit.get("videos") or {}).get("small") or {}
    if not video.get("url"):
        return None
    return _download(video["url"], os.path.join(dest_dir, f"pixabay_{hit['id']}.mp4"))


def find_stock_video(query: str, dest_dir: str, index: int = 0) -> str | None:
    os.makedirs(dest_dir, exist_ok=True)
    for source in (_pexels, _pixabay):
        try:
            path = source(query, dest_dir, index)
            if path:
                return path
        except Exception:
            continue
    return None


def generate_image(prompt: str, dest: str, seed: int = 0, timeout: float = 90) -> str | None:
    """Free AI still from Pollinations.ai, 1080x1920."""
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt[:700])}"
           f"?width=1080&height=1920&seed={seed}&nologo=true")
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            from io import BytesIO

            from PIL import Image

            Image.open(BytesIO(r.content)).convert("RGB").save(dest, quality=93)
            return dest
    except Exception:
        pass
    return None
