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
