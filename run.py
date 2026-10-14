#!/usr/bin/env python
"""
Quick entry point to launch the Daily Content Creation Agent v2 Backend
Author: Bhagirath Argade
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    import uvicorn

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from backend.ffmpeg_setup import INSTALL_HELP, ensure_ffmpeg

    ffmpeg_dir = ensure_ffmpeg()
    print("ffmpeg:", ffmpeg_dir or "NOT FOUND")
    if not ffmpeg_dir:
        print(INSTALL_HELP)
    print("=" * 62)
    print("  Daily Content Creation Agent v2.0 -- Real AI Pipeline")
    print("  Author: Bhagirath Argade")
    print("  GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent")
    print("  Open browser at --> http://localhost:8000")
    print("=" * 62)
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
