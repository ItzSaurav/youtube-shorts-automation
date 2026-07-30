# run_workflow.py
"""Standalone script to execute the YouTube automation workflow sequentially.

This script avoids external dependencies (like the `langgraph` library) and
uses mock client implementations so it can be run as a dry‑run in any
environment, including the sandbox used by Claude Code.

It sequentially invokes the agents that were implemented in the `src/`
package:

1.  TopicResearchAgent – discovers topics for a given niche.
2.  ScriptGenerationAgent – generates a script using a mock LLM.
3.  AudioGenerationAgent – synthesises audio via a mock TTS client.
4.  VideoGenerationAgent – assembles a video using mock stock media and ffmpeg.
5.  PublishingAgent – pretends to upload the video to YouTube.

All temporary files are written under the project's `data/` directory and are
cleaned up at the end of the run.
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Configure the import path so that `src` can be imported as a package.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))  # Allows `import agents` etc.

# ---------------------------------------------------------------------------
# Logging setup – log both to console and to a file for inspection.
# ---------------------------------------------------------------------------
log_file = PROJECT_ROOT / "run_workflow.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import the agent classes and the shared FileManagement utility.
# ---------------------------------------------------------------------------
try:
    from agents.topic_research import TopicResearchAgent
    from agents.script_generation import ScriptGenerationAgent
    from agents.audio_generation import AudioGenerationAgent
    from agents.video_generation import VideoGenerationAgent
    from agents.publishing import PublishingAgent
    from utils.file_management import FileManagement
except Exception as e:
    logger.critical(f"Failed to import project modules: {e}")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Mock client implementations – these replace the real API clients used in
# production. They only log actions and return dummy data that satisfies the
# agents' expectations.
# ---------------------------------------------------------------------------
class MockYouTubeClient:
    def __init__(self):
        logger.info("MockYouTubeClient initialized.")

    def search_videos(self, query, max_results=5):
        logger.info(f"MockYouTubeClient.search_videos called with query='{query}'")
        # Return a simple list with one mock video entry.
        return [{
            "title": f"Mock video about {query}",
            "id": "mock123",
            "channel_title": "Mock Channel",
            "published_at": "2023-01-01",
            "tags": ["mock", query]
        }]

    def upload_video(self, video_path, title, description, tags=None):
        logger.info(f"MockYouTubeClient.upload_video called with video_path={video_path}, title={title}")
        # Simulate a successful upload by returning a fake YouTube URL.
        fake_id = os.urandom(4).hex()
        return f"https://www.youtube.com/watch?v={fake_id}"

class MockTtsClient:
    def __init__(self):
        logger.info("MockTtsClient initialized.")

    def synthesize(self, text, output_filename):
        logger.info(f"MockTtsClient.synthesize called – writing dummy audio to {output_filename}")
        # Write a small placeholder file so downstream agents can read it.
        with open(output_filename, "wb") as f:
            f.write(b"\x00\x01\x02mock audio data")
        return output_filename

class MockStockMediaClient:
    def __init__(self):
        logger.info("MockStockMediaClient initialized.")

    def search(self, query, media_type, per_page):
        logger.info(f"MockStockMediaClient.search called – query='{query}', media_type='{media_type}'")
        # Return a single mock media entry (URL string only – the downloader will
        # create a dummy file.)
        dummy_url = f"http://example.com/{query.replace(' ', '_')}_{media_type}.bin"
        return [{"url": dummy_url, "sourceUrl": dummy_url, "thumbnail": "", "description": "Mock media"}]

class MockLLMClient:
    def __init__(self):
        logger.info("MockLLMClient initialized.")

    def generate_script(self, topic, tone, length, context=""):
        logger.info(f"MockLLMClient.generate_script called for topic='{topic}'")
        # Return a simple script structure.
        return {
            "title": f"Script for {topic}",
            "hook": "Welcome to the video!",
            "introduction": f"This video explores {topic}.",
            "body": "Here is the main content of the script.",
            "call_to_action": "Please like and subscribe.",
            "outro": "Thanks for watching!",
            "tags": [topic.lower().replace(' ', '_'), "mock"],
            "description": f"A mock script about {topic}."
        }

# ---------------------------------------------------------------------------
# Helper to clean up temporary directories created during the run.
# ---------------------------------------------------------------------------
def cleanup_temp_dirs(root_path: Path):
    """Remove any directories inside `root_path` that start with 'mock_temp_'."""
    for entry in root_path.iterdir():
        if entry.is_dir() and entry.name.startswith("mock_temp_"):
            try:
                shutil.rmtree(entry)
                logger.info(f"Cleaned up temporary directory: {entry}")
            except Exception as e:
                logger.warning(f"Failed to remove temp dir {entry}: {e}")

# ---------------------------------------------------------------------------
# Main sequential workflow
# ---------------------------------------------------------------------------
def run_sequential_workflow():
    logger.info("=== Starting sequential YouTube automation workflow (dry-run) ===")

    # Initialize shared FileManagement (writes into ./data)
    fm = FileManagement()

    # Instantiate mock clients
    mock_youtube = MockYouTubeClient()
    mock_tts = MockTtsClient()
    mock_stock = MockStockMediaClient()
    mock_llm = MockLLMClient()

    # 1. Topic research
    topic_agent = TopicResearchAgent(youtube_client=mock_youtube)
    niche = os.getenv("YOUTUBE_NICHE", "AI in Education")
    topics = topic_agent.run(niche)
    if not topics:
        logger.error("TopicResearchAgent returned no topics. Aborting.")
        return
    selected_topic = topics[0]
    logger.info(f"Selected topic: {selected_topic.get('title')}")

    # 2. Script generation
    script_agent = ScriptGenerationAgent(llm_client=mock_llm, file_management=fm)
    script = script_agent.run(topic_data=selected_topic)
    if not script:
        logger.error("ScriptGenerationAgent failed to produce a script. Aborting.")
        return
    logger.info("Script generation completed.")

    # 3. Audio generation
    audio_agent = AudioGenerationAgent(tts_client=mock_tts, file_management=fm)
    audio_path = audio_agent.run(script_data=script)
    if not audio_path:
        logger.error("AudioGenerationAgent failed to generate audio. Aborting.")
        return
    logger.info(f"Audio file generated at: {audio_path}")

    # 4. Video generation
    video_agent = VideoGenerationAgent(stock_media_client=mock_stock, file_management=fm)
    video_path = video_agent.run(audio_path=audio_path, script_data=script, topic_data=selected_topic)
    if not video_path:
        logger.error("VideoGenerationAgent failed to produce a video. Aborting.")
        return
    logger.info(f"Video file generated at: {video_path}")

    # 5. Publishing (mock)
    publishing_agent = PublishingAgent(youtube_client=mock_youtube, file_management=fm)
    youtube_url = publishing_agent.run(
        video_path=video_path,
        title=selected_topic.get("title", "Untitled Video"),
        description=selected_topic.get("description", ""),
        tags=selected_topic.get("tags", [])
    )
    if youtube_url:
        logger.info(f"Mock publish succeeded - video URL: {youtube_url}")
        print("\n=== Dry-run completed successfully ===")
        print(f"Published video URL (mock): {youtube_url}")
    else:
        logger.error("PublishingAgent failed to return a URL.")
        print("\n=== Dry-run completed with publishing failure ===")

    # -------------------------------------------------------------------
    # Perform cleanup of any temporary directories that were created.
    # -------------------------------------------------------------------
    cleanup_temp_dirs(PROJECT_ROOT)
    logger.info("All done.")

if __name__ == "__main__":
    run_sequential_workflow()
