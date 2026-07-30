# src/utils/file_management.py
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class FileManagement:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Working directories
        self.scripts_dir = self.base_dir / "scripts"
        self.audio_dir = self.base_dir / "audio"
        self.video_dir = self.base_dir / "video"
        self.stock_media_dir = self.base_dir / "stock_media"
        self.thumbnails_dir = self.base_dir / "thumbnails"

        # Output directory for finished videos ready for YouTube upload
        self.output_dir = Path("output") / "ready_for_upload"

        # Create all directories
        for d in [
            self.scripts_dir, self.audio_dir, self.video_dir,
            self.stock_media_dir, self.thumbnails_dir, self.output_dir
        ]:
            d.mkdir(parents=True, exist_ok=True)

        logger.info(f"FileManagement initialized at {self.base_dir}")

    def save_script(self, script_data, filename="script.json"):
        """Save a script dict to JSON."""
        path = self.scripts_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved script to {path}")
        return str(path)

    def get_audio_path(self, filename="narration.mp3"):
        """Return the path for an audio file."""
        return str(self.audio_dir / filename)

    def get_video_path(self, filename="video.mp4"):
        """Return the path for a video file."""
        return str(self.video_dir / filename)

    def get_stock_media_dir(self):
        """Return the stock media download directory path."""
        return str(self.stock_media_dir)

    def get_output_path(self, title="video"):
        """Return a timestamped output path for the final video."""
        safe_title = "".join(c if c.isalnum() or c in " _-" else "" for c in title)
        safe_title = safe_title.strip().replace(" ", "_")[:60]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_title}.mp4"
        return str(self.output_dir / filename)

    def save_metadata(self, metadata, video_path):
        """Save title/description/tags JSON alongside the final video."""
        meta_path = Path(video_path).with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved metadata to {meta_path}")
        return str(meta_path)

    def cleanup_temp(self):
        """Remove intermediate files from working directories."""
        cleaned = 0
        for d in [self.stock_media_dir, self.audio_dir]:
            if d.exists():
                for f in d.iterdir():
                    if f.is_file():
                        try:
                            f.unlink()
                            cleaned += 1
                        except OSError as e:
                            logger.warning(f"Could not delete {f}: {e}")
        logger.info(f"Cleaned up {cleaned} temporary files.")
        return cleaned

    def save_content_to_file(self, content, filename, directory=None):
        """Save raw content (bytes or str) to a file in base_dir or a subdirectory."""
        if directory:
            target_dir = self.base_dir / directory
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = self.base_dir
        path = target_dir / filename
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(path, mode) as f:
            f.write(content)
        logger.info(f"Saved content to {path}")
        return str(path)

    def create_temp_dir(self, prefix="temp"):
        """Create a temporary directory inside data/."""
        temp_dir = self.base_dir / f"{prefix}_{datetime.now().strftime('%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created temp dir: {temp_dir}")
        return str(temp_dir)

    def cleanup_directory(self, path):
        """Remove a directory and all its contents."""
        try:
            shutil.rmtree(path)
            logger.info(f"Removed directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove directory {path}: {e}")
            return False
