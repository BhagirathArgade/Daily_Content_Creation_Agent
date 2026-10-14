# Daily_Content_Creation_Agent 🎬

> Type a song name → pick the right YouTube upload → the agents find the most viral moment, cut it, and build an aesthetic 9:16 reel whose images match the lyrics. Don't like the visuals? Regenerate new images for the same lyrics in one click.

**Author:** [Bhagirath Argade](https://github.com/BhagirathArgade)

## How it works

```
song name ──► YouTube suggestions ──► pick one
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 │ Agent 1 · Viral Cutter  (Claude Sonnet 5.5) │
                 │  • downloads audio (yt-dlp)                 │
                 │  • fetches time-synced lyrics (lrclib.net)  │
                 │  • picks the most viral 15–30 s window      │
                 │  • cuts the exact clip                      │
                 └──────────────────────┬──────────────────────┘
                 ┌──────────────────────┴──────────────────────┐
                 │ Agent 2 · Aesthetic Storyboarder (Sonnet 5.5)│
                 │  • tokenizes the clip's lyrics into meaning- │
                 │    ful statements: at most 8 scenes total   │
                 │  • one image per statement, one shared style │
                 │    (same accent throughout the reel)        │
                 │  • 🔁 Regenerate: same scenes, new seed      │
                 ┌──────────────────────┴──────────────────────┐
                 │ Agent 3 · Composer                          │
                 │  • 9:16 MP4: images + captions + hook audio │
                 │  • caption + hashtags for posting           │
                 └─────────────────────────────────────────────┘
```

**Works without any API key.** Without `ANTHROPIC_API_KEY`, Agent 1 uses a chorus finder (lyric lines that repeat score higher) and Agent 2 uses a rule-based caption split. The web app shows which brain ran for each step.

## Quick start

```bash
git clone https://github.com/BhagirathArgade/Daily_Content_Creation_Agent.git
cd Daily_Content_Creation_Agent
pip install -r requirements.txt        # needs ffmpeg on your PATH
cp .env.example .env                   # optional: add ANTHROPIC_API_KEY
python run.py                          # open http://localhost:8000
```

Then type the song name, choose a suggestion, pick a vibe, and press **Generate**. When the reel is ready, press **Regenerate visuals** for new images with the same lyrics.

## Configuration

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Enables Claude Sonnet 5.5 for Agents 1 and 2 |
| `CLAUDE_MODEL` | Defaults to `claude-sonnet-5-5` |

`GET /api/health` reports which brains are active.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/search?q=` | YouTube suggestions |
| POST | `/api/process` | Server-Sent Events: progress, then `complete` with scenes, hook, reel URL and caption |
| POST | `/api/regenerate` | Same scene prompts, new seed → new images (and a re-rendered reel) |
| GET | `/api/health` | Active brains and model |

## Tests

```bash
python -m pytest -q tests      # 13 offline tests: no YouTube, lyrics, image or API calls
```

The tests cover the lyric parser, the chorus finder, Claude response validation (with stubbed replies, including the 8-scene cap and full word coverage), stable image seeds across processes, regeneration, a full MP4 render from synthetic audio, and the `/api/process` event stream.

## Honest limits

- **Copyright.** Downloading audio from YouTube and burning lyrics into videos may breach YouTube's terms and the rights holders' copyright. Use this for music you have the rights to, or check the rules before posting publicly.
- **Clip tokenization.** Statements come from the lyrics timed to the clip. If no lyrics are found, the clip is transcribed with faster-whisper when it is installed (`pip install faster-whisper`); otherwise the song title is used.
- **Lyric timing.** Time-synced lyrics come from lrclib.net when it has them. Otherwise the lines are spread evenly across the song, which is labelled "approximate" in the output.
- **Images.** Pollinations.ai generates them for free but is not guaranteed; if it fails, a procedural backdrop in the song's palette is used so the reel still renders.
- **Legacy `core/` + `server.py`.** An earlier simulation pipeline. The real pipeline is `backend/` (run via `run.py`).

## Repository structure

```
backend/
  app.py              FastAPI app: /api/search, /api/process, /api/regenerate
  claude_agents.py    Sonnet 5.5 for Agent 1 (hook) and Agent 2 (≤8 scenes), with heuristic fallbacks
  lyrics.py           lrclib.net lyrics, LRC parser, approximate timing
  agent1_extractor.py YouTube search, yt-dlp download, clip cutting
  agent2_visual.py    image generation, seeds, regeneration
  agent3_composer.py  9:16 MP4 composition and posting pack
web/                  interactive dashboard (index.html, app.js, style.css)
tests/                offline test suite
run.py                entry point
```

## License

MIT © Bhagirath Argade. See [LICENSE](LICENSE).
