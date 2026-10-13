"""
Multi-Agent AI Pipeline Orchestrator
Daily Content Creation Agent
Author: Bhagirath Argade
GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent

Coordinates:
- Agent 1: Viral Audio & Hook Extractor
- Agent 2: Lyrical Breakdown & Aesthetic Storyboarder
- Agent 3: Kinetic Video Compositor & Content Publisher
"""

import sys
import os
import json
import argparse
from typing import Dict, Any, Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.models import AudioClipMetadata, StoryboardPlan, InstagramPublishingPack
from core.agent1_viral_cutter import ViralAudioCutterAgent
from core.agent2_aesthetic_storyboarder import AestheticStoryboarderAgent
from core.agent3_video_compositor import VideoCompositorAgent


class DailyContentCreationOrchestrator:
    """Master Orchestrator managing multi-agent pipeline workflow."""

    def __init__(self):
        self.creator = "Bhagirath Argade"
        self.agent1 = ViralAudioCutterAgent()
        self.agent2 = AestheticStoryboarderAgent()
        self.agent3 = VideoCompositorAgent()

    def run_pipeline(
        self,
        song_name: str,
        movie_or_artist: str = "",
        vibe_theme: str = "moody_monsoon",
        subtitle_style: str = "Karaoke Highlight"
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-agent execution pipeline.
        """
        print(f"\n==================================================================")
        print(f"🎬 DAILY CONTENT CREATION AGENT - MULTI-AGENT PIPELINE")
        print(f"👑 Author: {self.creator}")
        print(f"🎵 Input: '{song_name}' | Movie/Artist: '{movie_or_artist}'")
        print(f"🎨 Aesthetic Theme: {vibe_theme}")
        print(f"==================================================================\n")

        # STEP 1: Agent 1 (Viral Audio & Hook Extractor)
        print("▶ [Step 1/3] Agent 1 is analyzing track virality & cutting peak hook...")
        clip_meta = self.agent1.detect_viral_hook(song_name, movie_or_artist)
        clip_meta = self.agent1.extract_clip(clip_meta)
        print(f"   ✔ Viral Hook Located: {clip_meta.start_sec}s -> {clip_meta.end_sec}s ({clip_meta.duration_sec}s)")
        print(f"   ✔ Virality Score: {clip_meta.virality_score}/100 | BPM: {clip_meta.bpm} | Energy: {clip_meta.energy_level}")
        print(f"   ✔ Hook Excerpt: \"{clip_meta.key_hook_line}\"\n")

        # STEP 2: Agent 2 (Lyrical Breakdown & Aesthetic Storyboarder)
        print("▶ [Step 2/3] Agent 2 is segmenting lyrics & curating consistent aesthetic visual assets...")
        storyboard = self.agent2.generate_storyboard(clip_meta, selected_vibe=vibe_theme)
        print(f"   ✔ Parsed into {len(storyboard.scenes)} rhythmic micro-scenes")
        print(f"   ✔ Enforced Aesthetic DNA: {storyboard.vibe_theme}")
        for scene in storyboard.scenes:
            print(f"     • Scene #{scene.scene_id} [{scene.chunk.start_time}s - {scene.chunk.end_time}s]: \"{scene.chunk.text}\"")
        print()

        # STEP 3: Agent 3 (Kinetic Video Compositor & Content Ready Engine)
        print("▶ [Step 3/3] Agent 3 is compositing 9:16 vertical video & generating viral Instagram pack...")
        insta_pack = self.agent3.compose_content_package(clip_meta, storyboard, subtitle_style=subtitle_style)
        print(f"   ✔ Instagram Reel Video Path: {insta_pack.video_output_path}")
        print(f"   ✔ Viral Hook Caption Ready: \"{insta_pack.caption_hook}\"")
        print(f"   ✔ Generated {len(insta_pack.hashtags)} targeted hashtags")
        print(f"   ✔ Optimal Posting Window: {insta_pack.recommended_post_time}\n")

        print("==================================================================")
        print("🎉 PIPELINE COMPLETE: Content is ready to publish on Instagram!")
        print("==================================================================\n")

        return {
            "author": self.creator,
            "agent1_output": clip_meta.model_dump(),
            "agent2_output": storyboard.model_dump(),
            "agent3_output": insta_pack.model_dump()
        }


def main():
    parser = argparse.ArgumentParser(description="Daily Content Creation Multi-Agent AI System")
    parser.add_argument("--song", type=str, default="Tum Hi Ho", help="Song name")
    parser.add_argument("--movie", type=str, default="Aashiqui 2", help="Movie or artist name")
    parser.add_argument("--vibe", type=str, default="moody_monsoon", help="Aesthetic vibe preset")
    parser.add_argument("--subtitle", type=str, default="Karaoke Highlight", help="Subtitle animation style")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    orchestrator = DailyContentCreationOrchestrator()
    result = orchestrator.run_pipeline(
        song_name=args.song,
        movie_or_artist=args.movie,
        vibe_theme=args.vibe,
        subtitle_style=args.subtitle
    )

    if args.json:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
