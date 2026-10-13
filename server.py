"""
Lightweight Web Server & API for Daily Content Creation Agent
Author: Bhagirath Argade
GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent
"""

import os
import sys
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# Reconfigure Windows console UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.orchestrator import DailyContentCreationOrchestrator

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class AgentDashboardHandler(SimpleHTTPRequestHandler):
    """Handles static web dashboard requests and API endpoints for multi-agent execution."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_body.decode("utf-8"))
            except Exception:
                payload = {}

            song = payload.get("song_name", "Kesariya")
            movie = payload.get("movie_or_artist", "Brahmastra")
            vibe = payload.get("vibe_theme", "moody_monsoon")
            sub = payload.get("subtitle_style", "Karaoke Highlight")

            orchestrator = DailyContentCreationOrchestrator()
            result = orchestrator.run_pipeline(
                song_name=song,
                movie_or_artist=movie,
                vibe_theme=vibe,
                subtitle_style=sub
            )

            response_data = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        else:
            self.send_error(404, "Endpoint Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_server(port=PORT):
    server_address = ("", port)
    httpd = HTTPServer(server_address, AgentDashboardHandler)
    print("==================================================================")
    print(f"🚀 Daily Content Creation Agent - Web Dashboard Server")
    print(f"👑 Author: Bhagirath Argade")
    print(f"🌐 Serving Interactive Webpage at: http://localhost:{port}")
    print(f"⚡ Press Ctrl+C to stop the server.")
    print("==================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped gracefully.")


if __name__ == "__main__":
    run_server()
