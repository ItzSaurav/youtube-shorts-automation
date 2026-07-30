# src/utils/thumbnail_creator.py
"""
Viral Cover Thumbnail Creator for YouTube Shorts (1080x1920)
Automatically extracts a high-contrast cover frame from the opening hook scene
where the bold animated captions and lifestyle visuals are most eye-catching.
"""
import os
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class ThumbnailCreator:
    def __init__(self, ffmpeg_path=None):
        if not ffmpeg_path:
            try:
                import imageio_ffmpeg
                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                ffmpeg_path = "ffmpeg"
        self.ffmpeg_path = ffmpeg_path
        logger.info(f"ThumbnailCreator initialized with ffmpeg: {self.ffmpeg_path}")

    def create_viral_cover(self, video_path, output_path=None, timestamp_sec=1.5):
        """
        Extracts an HD 1080x1920 cover image from the opening hook of the Short.
        
        Args:
            video_path (str): Path to the rendered MP4 Short.
            output_path (str): Optional destination path for the JPEG cover.
            timestamp_sec (float): Second to capture (default 1.5s for peak hook impact).
            
        Returns:
            str: Path to the generated cover thumbnail image, or None if failed.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found for thumbnail creation: {video_path}")
            return None

        if not output_path:
            out_dir = Path("data/video")
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / "cover_thumbnail.jpg")

        logger.info(f"Extracting viral Shorts cover thumbnail from '{video_path}' at {timestamp_sec}s...")

        cmd = [
            self.ffmpeg_path, "-y",
            "-ss", str(timestamp_sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Successfully generated viral cover thumbnail: {output_path}")
                return output_path
            else:
                logger.error(f"ffmpeg cover extraction failed: {res.stderr}")
                return None
        except Exception as e:
            logger.error(f"Exception during cover thumbnail creation: {e}")
            return None
