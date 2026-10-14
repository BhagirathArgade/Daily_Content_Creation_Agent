"""Offline tests - no YouTube, lyrics or image network calls, no API key needed.
Run:  python -m pytest -q tests
Author: Bhagirath Argade
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend import agent2_visual, claude_agents  # noqa: E402
from backend.lyrics import Line, approximate_timing, clean_title, parse_lrc  # noqa: E402

SONG = [
    Line(0, 4, "midnight rain on an empty street"),
    Line(4, 8, "streetlights hum a quiet tune"),
    Line(8, 12, "stay with me, stay with me"),
    Line(12, 16, "I carry your name like a little light"),
    Line(16, 20, "stay with me, stay with me"),
    Line(20, 24, "the night is soft and the city is slow"),
    Line(24, 28, "stay with me, stay with me"),
    Line(28, 32, "morning will find us dreaming still"),
]


def test_parse_lrc_handles_multi_stamp_and_gaps():
    lines = parse_lrc("[00:12.50] first\n[00:16.00][00:50.00] chorus\n[00:18.00]\n[00:20.00] last")
    assert [l.text for l in lines] == ["first", "chorus", "last", "chorus"]
    assert lines[0].start == 12.5 and lines[0].end == 16.0
    assert lines[3].start == 50.0


def test_approximate_timing_covers_duration():
    lines = approximate_timing("a\nb\nc", 30)
    assert lines[0].start > 0 and lines[-1].end == pytest.approx(30)


def test_clean_title_strips_noise():
    assert clean_title("Parvati (Official Video) | Song [HD]") == "Parvati | Song"


def test_heuristic_hook_prefers_repeated_chorus_and_respects_limits():
    h = claude_agents.heuristic_hook(SONG, 40, target=20, min_len=12, max_len=24)
    assert h["source"] == "heuristic"
    assert 12 <= h["end"] - h["start"] <= 24
    assert "stay with me" in " ".join(l.text for l in SONG[h["first_line"]: h["last_line"] + 1])


def test_hook_without_lyrics_uses_chorus_position():
    h = claude_agents.heuristic_hook([], 200, target=25, min_len=15, max_len=30)
    assert h["start"] == pytest.approx(72.0) and h["end"] - h["start"] == pytest.approx(25)


def test_scenes_tile_clip_and_match_lyrics_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    clip = [Line(l.start, l.end, l.text) for l in SONG[:4]]
    plan = claude_agents.plan_scenes("T", "", clip, 16, "Golden", "warm film", ["#000000"])
    sc = plan["scenes"]
    assert plan["source"].startswith("heuristic")
    assert sc[0]["start"] == 0 and sc[-1]["end"] == 16
    assert all(a["end"] == b["start"] for a, b in zip(sc, sc[1:]))
    assert all(s["duration"] >= 1.0 for s in sc) or len(sc) == 1
    joined = " ".join(s["text"] for s in sc).replace(",", "")
    assert "midnight rain" in joined and "little light" in joined


def test_claude_scenes_are_used_when_they_cover_the_lyrics(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    reply = {
        "style": {"name": "Rain", "palette": ["#112233"], "grade": "teal", "lighting": "neon", "subject_style": "street photo", "texture": "grain", "mood": "lonely"},
        "scenes": [{"text": "midnight rain", "prompt": "wet street at midnight"},
                   {"text": "on an empty street", "prompt": "empty city road"}],
    }
    monkeypatch.setattr(claude_agents, "_ask_json", lambda *a, **k: reply)
    plan = claude_agents.plan_scenes("T", "", [Line(0, 4, "midnight rain on an empty street")], 4, "Golden", "x", ["#000"])
    assert plan["source"] == claude_agents.MODEL
    assert [s["text"] for s in plan["scenes"]] == ["midnight rain", "on an empty street"]
    assert plan["scenes"][0]["prompt"].startswith("wet street at midnight")
    assert plan["style"]["name"] == "Rain"


def test_claude_scenes_that_drop_words_are_rejected_for_heuristic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    bad = {"style": {}, "scenes": [{"text": "midnight", "prompt": "x"}]}
    monkeypatch.setattr(claude_agents, "_ask_json", lambda *a, **k: bad)
    plan = claude_agents.plan_scenes("T", "", [Line(0, 4, "midnight rain on an empty street")], 4, "G", "suffix", ["#000"])
    assert plan["source"].startswith("heuristic (Claude failed")
    assert "".join(s["text"] for s in plan["scenes"]).replace(" ", "") == "midnightrainonanemptystreet"


def test_claude_reply_with_more_than_eight_scenes_is_rejected(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]
    many = {"style": {}, "scenes": [{"text": w, "prompt": w} for w in words]}
    monkeypatch.setattr(claude_agents, "_ask_json", lambda *a, **k: many)
    lines = [Line(0, 10, " ".join(words))]
    plan = claude_agents.plan_scenes("T", "", lines, 10, "G", "suffix", ["#000"])
    assert plan["source"].startswith("heuristic (Claude failed")
    assert len(plan["scenes"]) <= claude_agents.MAX_SCENES


@pytest.mark.parametrize("n_lines,clip_len", [(3, 11), (8, 32), (14, 30), (40, 30)])
def test_never_more_than_eight_scenes_and_full_coverage(monkeypatch, n_lines, clip_len):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    step = clip_len / n_lines
    lines = [Line(i * step, (i + 1) * step, f"word{i} lyric line number {i} here") for i in range(n_lines)]
    plan = claude_agents.plan_scenes("T", "", lines, clip_len, "G", "suffix", ["#000"])
    sc = plan["scenes"]
    assert 1 <= len(sc) <= 8
    assert sc[0]["start"] == 0 and sc[-1]["end"] == pytest.approx(clip_len)
    assert all(a["end"] == b["start"] for a, b in zip(sc, sc[1:]))
    text = "".join(s["text"] for s in sc).replace(" ", "")
    assert text == "".join(l.text for l in lines).replace(" ", "")


def test_typical_clip_gets_seven_or_eight_scenes(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    lines = [Line(i * 2.5, i * 2.5 + 2.5, f"this is lyric line number {i} of the chorus") for i in range(10)]
    plan = claude_agents.plan_scenes("T", "", lines, 25, "G", "suffix", ["#000"])
    assert len(plan["scenes"]) in (7, 8)


def test_claude_failure_is_reported_not_raised(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(claude_agents, "_ask_json", boom)
    plan = claude_agents.plan_scenes("T", "", SONG[:2], 8, "G", "suffix", ["#000"])
    assert "RuntimeError" in plan["source"] and plan["scenes"]


def test_image_seed_is_stable_across_processes():
    code = "import sys; sys.path.insert(0, %r); from backend.agent2_visual import image_seed; print(image_seed('stay with me', 3))" % ROOT
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env={**os.environ, "PYTHONHASHSEED": str(k)}).stdout.strip() for k in (1, 2)}
    assert len(outs) == 1 and outs.pop()


def test_regenerate_changes_images_not_prompts(tmp_path, monkeypatch):
    monkeypatch.setattr(agent2_visual, "generate_image", lambda p, d, s, pal, timeout=60: (agent2_visual.procedural_backdrop(p, pal, d), "procedural")[1])
    scenes = [{"id": 1, "text": "stay", "start": 0, "end": 2, "prompt": "a lone lamp in fog"}]
    a = agent2_visual.render_scenes(scenes, ["#101010", "#f0c040"], str(tmp_path), seed=1)[0]
    b = agent2_visual.regenerate_storyboard(scenes, ["#101010", "#f0c040"], str(tmp_path), seed=2)[0]
    assert a["prompt"] == b["prompt"] and a["start"] == b["start"]
    assert a["image_path"] != b["image_path"] and os.path.exists(b["image_path"])


def test_end_to_end_reel_renders(tmp_path, monkeypatch):
    """Synthetic 60 s tone -> cut hook -> storyboard -> MP4 (offline)."""
    from backend.agent1_extractor import RealAudioExtractorAgent
    from backend.agent3_composer import build_video
    monkeypatch.setattr(agent2_visual, "generate_image",
                        lambda p, d, s, pal, timeout=60: (agent2_visual.procedural_backdrop(p, pal, d), "procedural")[1])
    src = tmp_path / "tone.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=60",
                    "-c:a", "libmp3lame", str(src)], check=True)
    agent1 = RealAudioExtractorAgent()
    hook = claude_agents.pick_hook("Test Song", "", SONG, 60, target=12, min_len=8, max_len=16)
    clip = agent1.extract_clip(str(src), hook["start"], hook["end"], "e2e test")
    clip_len = hook["end"] - hook["start"]
    lines = [Line(max(0, l.start - hook["start"]), min(clip_len, l.end - hook["start"]), l.text)
             for l in SONG if l.end > hook["start"] and l.start < hook["end"]]
    board = agent2_visual.build_storyboard("Test Song", "", lines, clip_len, "golden_hour", str(tmp_path / "img"))
    video = build_video(board["scenes"], clip, "Test Song", None, "_pytest")
    assert not video.startswith("error:"), video
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout)
    assert dur == pytest.approx(clip_len, abs=1.0)


def test_process_stream_runs_all_three_agents(tmp_path, monkeypatch):
    """The /api/process SSE flow, with only the YouTube download and lyrics lookup stubbed."""
    from fastapi.testclient import TestClient
    import backend.app as app_mod

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(agent2_visual, "generate_image",
                        lambda p, d, s, pal, timeout=60: (agent2_visual.procedural_backdrop(p, pal, d), "procedural")[1])
    src = tmp_path / "tone.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=60",
                    "-c:a", "libmp3lame", str(src)], check=True)
    monkeypatch.setattr(app_mod.RealAudioExtractorAgent, "download_audio",
                        lambda self, url, title: {"path": str(src), "status": "downloaded", "title": "Test Song",
                                                  "duration": 60, "uploader": "Test Channel"})
    monkeypatch.setattr(app_mod, "fetch_lyrics", lambda t, a="": {"lines": SONG, "plain": "", "synced": True, "source": "test"})

    r = TestClient(app_mod.app).post("/api/process", json={
        "youtube_url": "https://www.youtube.com/watch?v=x", "song_title": "Test Song",
        "vibe": "golden_hour", "target_len": 12})
    assert "event: error" not in r.text, r.text[:500]
    assert "event: complete" in r.text
    import json as _json
    payload = _json.loads([l for l in r.text.split("\n") if l.startswith("data:") and '"agent3"' in l][-1][5:])["data"]
    assert payload["agent1"]["lyrics"]["synced"] is True
    assert payload["agent2"]["scenes"] and payload["agent2"]["scenes"][0]["image_url"].startswith("/outputs/images/")
    assert payload["agent3"]["video_url"].startswith("/outputs/videos/")


def test_search_endpoint_reports_errors_and_returns_items(monkeypatch):
    from fastapi.testclient import TestClient
    import backend.app as app_mod
    client = TestClient(app_mod.app)
    monkeypatch.setattr(app_mod.RealAudioExtractorAgent, "search_songs",
                        lambda self, q, max_results=8: [{"error": "network blocked", "title": q, "video_id": "", "url": "", "channel": ""}])
    r = client.get("/api/search", params={"q": "parvati"})
    assert r.status_code == 502 and "network blocked" in r.json()["error"]
    monkeypatch.setattr(app_mod.RealAudioExtractorAgent, "search_songs",
                        lambda self, q, max_results=8: [{"title": "Parvati", "channel": "C", "duration": 200, "url": "u", "video_id": "abc", "thumbnail": ""}])
    r = client.get("/api/search", params={"q": "parvati"})
    assert r.status_code == 200 and r.json()["results"][0]["video_id"] == "abc"


def test_bundled_ffmpeg_converts_audio_to_mp3(tmp_path):
    """No system ffmpeg needed: the imageio-ffmpeg binary converts the downloaded audio to MP3."""
    from backend import ffmpeg_setup
    src = tmp_path / "raw.wav"
    subprocess.run([ffmpeg_setup.ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    str(src)], check=True)
    dst = tmp_path / "out.mp3"
    ffmpeg_setup.convert_to_mp3(str(src), str(dst))
    assert dst.exists() and dst.stat().st_size > 1000
