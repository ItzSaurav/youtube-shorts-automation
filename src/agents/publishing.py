# src/agents/publishing.py
"""
Publishing Agent — saves the finished video + metadata to the
output/ready_for_upload/ folder for manual YouTube upload.
(Auto-upload via YouTube API will be added in a future step.)
"""
import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PublishingAgent:
    def __init__(self, youtube_client=None, file_management=None):
        self.youtube_client = youtube_client
        self.file_management = file_management
        logger.info("PublishingAgent initialized.")

    def run(self, video_path, title, description, tags=None):
        """
        Copy the finished video to output/ready_for_upload/ with a
        timestamped filename, and save a metadata JSON alongside it.
        """
        logger.info(f"Publishing video '{title}' from {video_path}")

        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        # Use the youtube_client's upload (which saves to disk for now)
        if self.youtube_client:
            try:
                result = self.youtube_client.upload_video(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags or []
                )
                return result
            except Exception as e:
                logger.error(f"Publishing failed: {e}")

        # Fallback: manual copy to output folder
        try:
            output_dir = os.path.join("output", "ready_for_upload")
            os.makedirs(output_dir, exist_ok=True)

            safe_title = "".join(c if c.isalnum() or c in " _-" else "" for c in title)
            safe_title = safe_title.strip().replace(" ", "_")[:60]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{timestamp}_{safe_title}.mp4"
            output_path = os.path.join(output_dir, output_filename)

            shutil.copy2(video_path, output_path)
            logger.info(f"Video saved to: {output_path}")

            # Save metadata alongside
            if self.file_management:
                self.file_management.save_metadata(
                    {"title": title, "description": description, "tags": tags or []},
                    output_path
                )

            return output_path
        except Exception as e:
            logger.error(f"Fallback publishing failed: {e}")
            return None
