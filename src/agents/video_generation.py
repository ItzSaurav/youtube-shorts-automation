# src/agents/video_generation.py
"""
Video Generation Agent — downloads HD stock footage from Pexels, then uses
ffmpeg DIRECTLY (via subprocess) to assemble the final MP4 video.

This is 10-20x faster than moviepy because ffmpeg handles all decoding,
scaling, and encoding in native C code without Python frame-by-frame overhead.
"""
import os
import subprocess
import logging
import tempfile

logger = logging.getLogger(__name__)


def _get_ffmpeg_path():
    """Find ffmpeg — try imageio_ffmpeg first, then system PATH."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


class VideoGenerationAgent:
    def __init__(self, stock_media_client=None, file_management=None):
        self.stock_media_client = stock_media_client
        self.file_management = file_management
        self.ffmpeg = _get_ffmpeg_path()
        logger.info("VideoGenerationAgent initialized.")

    def _build_search_queries(self, topic_data, script_data=None):
        """Build high-relevance, concrete cinematic search queries from topic and script."""
        queries = []
        
        # 1. Curated high-impact concrete cinematic lifestyle queries (abstract terms like 'wellness' fail on Pexels)
        cinematic_pool = [
            "waking up bedroom sunrise morning",
            "drinking glass water morning",
            "stretching outdoor sunrise park",
            "running jogging morning fitness",
            "healthy food salad fruit breakfast",
            "walking nature sunlight forest",
            "workout fitness gym exercise",
            "meditation sunrise peaceful nature",
            "making coffee morning kitchen",
            "sunlight window morning happy"
        ]

        title = (topic_data.get("title", "") if isinstance(topic_data, dict) else "").lower()
        script_text = ""
        if isinstance(script_data, dict):
            script_text = script_data.get("narration", "") or script_data.get("script", "")
        elif isinstance(script_data, str):
            script_text = script_data
        script_text = script_text.lower()

        # Match specific concrete themes from title/script to prioritize matching clips
        if "water" in title or "water" in script_text or "hydrate" in script_text or "drink" in script_text:
            queries.append("drinking water morning")
        if "walk" in title or "walk" in script_text or "step" in script_text or "run" in script_text:
            queries.append("running jogging morning fitness")
            queries.append("walking nature sunlight forest")
        if "stretch" in title or "stretch" in script_text or "exercise" in script_text or "workout" in script_text:
            queries.append("stretching outdoor sunrise park")
            queries.append("workout fitness gym exercise")
        if "food" in title or "eat" in script_text or "breakfast" in script_text or "diet" in script_text:
            queries.append("healthy food salad fruit breakfast")
        if "sleep" in title or "wake" in script_text or "morning" in title or "habit" in title:
            queries.append("waking up bedroom sunrise morning")
            queries.append("making coffee morning kitchen")

        # Fill the rest with our curated high-converting cinematic pool
        for q in cinematic_pool:
            if q not in queries:
                queries.append(q)

        return queries[:10]

    def _download_stock_clips(self, queries, target_count=8):
        """Download stock video clips from Pexels with high relevance filtering."""
        if not self.stock_media_client:
            logger.warning("No stock media client available.")
            return []

        download_dir = self.file_management.get_stock_media_dir() if self.file_management else "data/stock_media"
        os.makedirs(download_dir, exist_ok=True)

        downloaded = []
        seen_urls = set()

        for query in queries:
            if len(downloaded) >= target_count:
                break
            try:
                results = self.stock_media_client.search(query=query, media_type="videos", per_page=10)
                for clip in results:
                    if len(downloaded) >= target_count:
                        break
                    url = clip.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    # Skip very short clips if duration info available
                    dur = clip.get("duration", 10)
                    if dur < 4:
                        continue
                    seen_urls.add(url)
                    filename = f"clip_{len(downloaded):02d}.mp4"
                    output_path = os.path.join(download_dir, filename)
                    logger.info(f"Downloading clip {len(downloaded)+1}/{target_count} ({query}): {url} -> {output_path}")
                    self.stock_media_client.download(url, output_path)
                    downloaded.append(output_path)
            except Exception as e:
                logger.warning(f"Error searching/downloading for query '{query}': {e}")

        logger.info(f"Downloaded {len(downloaded)} high-relevance stock clips.")
        return downloaded

    def _get_duration(self, file_path):
        """Get duration of media file in seconds using ffmpeg CLI (no ffprobe dependency)."""
        import re, subprocess
        try:
            cmd = [self.ffmpeg, "-i", file_path]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
            if match:
                h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
                return h * 3600 + m * 60 + s
            match_cs = re.search(r"Duration:\s*(\d+):(\d+):(\d+),(\d+)", res.stderr)
            if match_cs:
                h, m, s, cs = float(match_cs.group(1)), float(match_cs.group(2)), float(match_cs.group(3)), float(match_cs.group(4))
                return h * 3600 + m * 60 + s + cs / 100.0
            return 0.0
        except Exception as e:
            logger.warning(f"Could not get duration for {file_path}: {e}")
            return 0.0

    def _assemble_video_ffmpeg(self, audio_path, clip_paths, output_path):
        """
        Assemble video using raw ffmpeg — MUCH faster than moviepy.
        Strategy: concatenate clips into a loop, overlay audio, trim to audio duration.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    def _assemble_video_ffmpeg(self, audio_path, clip_paths, output_path):
        """
        Assemble video using raw ffmpeg with White-Flash Impact Transitions on every cut.
        """
        import shutil
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        audio_duration = self._get_duration(audio_path)
        if audio_duration <= 0:
            logger.error("Could not determine audio duration.")
            return None
        logger.info(f"Audio duration: {audio_duration:.1f}s")

        # Step 1: Create agency-style White-Flash Impact Transitions on every 3.5s cut
        temp_cuts_dir = os.path.join(os.path.dirname(output_path), "temp_cuts")
        os.makedirs(temp_cuts_dir, exist_ok=True)
        cut_duration = 3.5  # Fast 3.5-second visual cuts
        num_cuts = int(audio_duration / cut_duration) + 2
        ts_files = []

        logger.info(f"Generating {num_cuts} cuts with White-Flash Impact Transitions...")
        for i in range(num_cuts):
            cp = clip_paths[i % len(clip_paths)]
            clip_dur = self._get_duration(cp)
            start_offset = 0.0
            if clip_dur >= cut_duration + 0.5:
                loop_round = i // len(clip_paths)
                start_offset = (loop_round * cut_duration) % max(1.0, clip_dur - cut_duration)

            ts_file = os.path.join(temp_cuts_dir, f"cut_{i:02d}.ts")
            # VF: 9:16 vertical crop + color grading + 150ms White Flash Impact Transition
            cut_vf = (
                f"scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
                f"fps=24,setsar=1,format=yuv420p,"
                f"eq=contrast=1.08:saturation=1.28:brightness=0.02,"
                f"fade=t=in:st=0:d=0.15:color=white"
            )
            cut_cmd = [
                self.ffmpeg, "-y", "-i", cp,
                "-ss", f"{start_offset:.2f}",
                "-t", f"{cut_duration:.2f}", "-vf", cut_vf,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
                "-preset", "ultrafast", "-crf", "23",
                "-g", "12", "-r", "24",
                "-an", ts_file
            ]
            subprocess.run(cut_cmd, capture_output=True, text=True, timeout=30)
            if os.path.exists(ts_file):
                ts_files.append(ts_file)

        if not ts_files:
            logger.error("Failed to generate cut segments.")
            return None

        # Step 2: Concat all .ts cut segments seamlessly (instant stream copy!)
        concat_ts = "concat:" + "|".join(ts_files)
        
        # Check subtitles
        ass_path = os.path.splitext(audio_path)[0] + ".ass"
        srt_path = os.path.splitext(audio_path)[0] + ".srt"
        sub_filter = ""
        if os.path.exists(ass_path):
            rel_ass = os.path.relpath(ass_path).replace("\\", "/").replace(":", "\\:")
            sub_filter = f"subtitles='{rel_ass}'"
            logger.info(f"Burning animated ASS subtitles from: {ass_path}")
        elif os.path.exists(srt_path):
            rel_srt = os.path.relpath(srt_path).replace("\\", "/").replace(":", "\\:")
            sub_filter = f"subtitles='{rel_srt}':force_style='FontName=Arial,FontSize=75,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=6,Shadow=4,Alignment=5'"
            logger.info(f"Burning SRT subtitles from: {srt_path}")

        # Final pass: overlay audio & burn captions (force yuv420p for 100% universal compatibility!)
        cmd = [
            self.ffmpeg, "-y",
            "-i", concat_ts,
            "-i", audio_path
        ]
        if sub_filter:
            cmd.extend(["-vf", sub_filter, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-preset", "ultrafast", "-crf", "23"])
        else:
            cmd.extend(["-c:v", "copy"])
        cmd.extend([
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(audio_duration), "-shortest",
            "-threads", "0", "-movflags", "+faststart", output_path
        ])

        logger.info("Running final ffmpeg assembly & subtitle burn...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute safe timeout
            )
            # Clean up temporary cut segments
            shutil.rmtree(temp_cuts_dir, ignore_errors=True)

            if result.returncode != 0:
                logger.error(f"ffmpeg failed: {result.stderr[-500:]}")
                return None

            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Video exported: {output_path} ({file_size_mb:.1f} MB)")
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("ffmpeg timed out after 120 seconds.")
            os.remove(concat_file)
            return None
        except Exception as e:
            logger.error(f"ffmpeg error: {e}")
            return None

    def run(self, audio_path, script_data=None, topic_data=None):
        """
        Full video generation pipeline:
        1. Download 3 HD stock clips from Pexels
        2. Assemble with ffmpeg directly (fast!)
        """
        logger.info("Running VideoGenerationAgent...")

        if not audio_path or not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return None

        queries = self._build_search_queries(topic_data or {}, script_data)
        logger.info(f"Stock footage search queries: {queries}")

        clip_paths = self._download_stock_clips(queries, target_count=8)

        if not clip_paths:
            logger.error("No clips downloaded. Cannot assemble video.")
            return None

        output_path = self.file_management.get_video_path("assembled_video.mp4") if self.file_management else "assembled_video.mp4"

        result = self._assemble_video_ffmpeg(audio_path, clip_paths, output_path)

        if result:
            logger.info(f"Video generation complete: {result}")
        else:
            logger.error("Video generation failed.")

        return result
