import os
import json
import asyncio
import shutil
import logging
import httpx
import datetime
from pathlib import Path
import edge_tts

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.endpoint = os.environ.get("LLM_API_ENDPOINT", "http://localhost:20128/v1")
        self.model = os.environ.get("LLM_MODEL", "openrouter/auto")
        self.timeout = 60.0
        logger.info("LLMClient initialized.")

    def _call_api(self, user_prompt, system_prompt=None):
        """Make a raw API call and return the content string."""
        headers = {"Content-Type": "application/json"}
        api_key = os.environ.get("LLM_API_KEY", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant. Return valid JSON only, without markdown wrappers."})
        messages.append({"role": "user", "content": user_prompt})

        payload = {"model": self.model, "messages": messages}

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.endpoint}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return content.strip()

    def generate_raw(self, prompt, system_prompt=None):
        """Generate raw text from the LLM. Used by agents that parse JSON themselves."""
        return self._call_api(prompt, system_prompt)

    def generate_script(self, topic, tone, length, context=""):
        prompt = (
            f"Topic: {topic}\nTone: {tone}\nLength: {length}\nContext: {context}\n"
            "Generate a YouTube video script. Return ONLY a JSON object with keys: "
            "title, hook, introduction, body, call_to_action, outro, tags (list), description."
        )
        content = self._call_api(prompt)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "title": f"Script for {topic}",
                "hook": "Fallback Hook",
                "introduction": "Fallback Intro",
                "body": content,
                "call_to_action": "Subscribe!",
                "outro": "Thanks for watching.",
                "tags": ["fallback", "script"],
                "description": "Auto-generated fallback description due to JSON parsing error."
            }


class TtsClient:
    def __init__(self):
        self.voice = os.environ.get("TTS_VOICE", "en-US-GuyNeural")
        self.rate = os.environ.get("TTS_RATE", "+22%")  # Faster, energetic speech
        logger.info(f"TtsClient initialized: voice={self.voice}, rate={self.rate}")

    def _srt_to_animated_ass(self, srt_path, ass_path):
        import re
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
            ass_header = (
                "[Script Info]\n"
                "ScriptType: v4.00+\n"
                "PlayResX: 1080\n"
                "PlayResY: 1920\n"
                "ScaledBorderAndShadow: yes\n\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Default,Arial,75,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,4,5,40,40,40,1\n\n"
                "[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            )
            def srt_time_to_ms(t_str):
                m_obj = re.match(r"(\d+):(\d+):(\d+),(\d+)", t_str)
                if not m_obj:
                    return 0
                h, m, s, ms = m_obj.groups()
                return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)

            def ms_to_ass_time(ms):
                h = ms // 3600000
                ms %= 3600000
                m = ms // 60000
                ms %= 60000
                s = ms // 1000
                cs = (ms % 1000) // 10
                return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

            events = []
            # Primary Crisp White (&H00FFFFFF), Highlight Vibrant Yellow (&H0000FFFF), Highlight Neon Green (&H0000FF00)
            colors = ['&H00FFFFFF', '&H0000FFFF', '&H00FFFFFF', '&H0000FF00']
            color_idx = 0

            blocks = content.strip().split("\n\n")
            for b in blocks:
                lines = b.split("\n")
                if len(lines) >= 3:
                    time_match = re.search(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lines[1])
                    if time_match:
                        t1_str = f"{time_match.group(1)}:{time_match.group(2)}:{time_match.group(3)},{time_match.group(4)}"
                        t2_str = f"{time_match.group(5)}:{time_match.group(6)}:{time_match.group(7)},{time_match.group(8)}"
                        start_ms = srt_time_to_ms(t1_str)
                        end_ms = srt_time_to_ms(t2_str)
                        text = " ".join(lines[2:]).replace("\n", " ")
                        words = text.split()
                        if not words:
                            continue

                        # Break sentence into fast 2-word or 3-word chunks (viral TikTok style)
                        chunk_size = 3 if len(words) >= 5 else (2 if len(words) >= 2 else 1)
                        chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
                        
                        # Apportion chunk duration proportionally to character length = ZERO VOICE SYNC DRIFT!
                        total_chars = sum(len(c) for c in chunks)
                        if total_chars == 0:
                            total_chars = 1
                        
                        curr_ms = start_ms
                        for idx, chunk in enumerate(chunks):
                            chunk_dur = int((end_ms - start_ms) * (len(chunk) / total_chars))
                            chunk_dur = max(chunk_dur, 250)
                            c_start = curr_ms
                            c_end = min(end_ms, c_start + chunk_dur)
                            if idx == len(chunks) - 1:
                                c_end = end_ms
                            curr_ms = c_end

                            color = colors[color_idx % len(colors)]
                            color_idx += 1
                            # Agency-grade sleek punch-in (88% -> 104% -> 100%) so text is instantly readable
                            anim = r"{\fscx88\fscy88\t(0,70,\fscx104\fscy104)\t(70,140,\fscx100\fscy100)\c" + color + "}"
                            events.append(f"Dialogue: 0,{ms_to_ass_time(c_start)},{ms_to_ass_time(c_end)},Default,,0,0,0,,{anim}{chunk}")

            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(ass_header + "\n".join(events))
            logger.info(f"Animated ASS subtitles (zero-drift sync & sleek punch-in) saved to {ass_path}")
        except Exception as e:
            logger.warning(f"Failed to generate ASS subtitles: {e}")

    def synthesize(self, text, output_filename):
        """Generate audio + SRT and animated ASS subtitle files with word-level timing."""
        Path(output_filename).parent.mkdir(parents=True, exist_ok=True)
        srt_path = str(Path(output_filename).with_suffix(".srt"))
        ass_path = str(Path(output_filename).with_suffix(".ass"))

        async def _synthesize():
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
            submaker = edge_tts.SubMaker()

            with open(output_filename, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif "Boundary" in chunk["type"]:
                        submaker.feed(chunk)

            # Generate SRT subtitles
            srt_content = submaker.get_srt()
            if srt_content:
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                logger.info(f"Subtitles saved to {srt_path}")
                self._srt_to_animated_ass(srt_path, ass_path)

        asyncio.run(_synthesize())
        return output_filename


class StockMediaClient:
    def __init__(self):
        self.api_key = os.environ.get("PEXELS_API_KEY", "")
        if self.api_key:
            logger.info("StockMediaClient initialized with Pexels API key.")
        else:
            logger.warning("StockMediaClient: PEXELS_API_KEY not set. Stock footage disabled.")

    def search(self, query, media_type="videos", per_page=5):
        if not self.api_key:
            logger.warning("PEXELS_API_KEY not set. Returning empty list.")
            return []
            
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": self.api_key}
        params = {"query": query, "per_page": per_page, "orientation": "portrait"}
        
        with httpx.Client() as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for video in data.get("videos", []):
                video_files = video.get("video_files", [])
                if not video_files:
                    continue

                # Prefer ~1080p HD files (much faster to encode than 4K UHD)
                hd_files = [f for f in video_files if 720 <= f.get("height", 0) <= 1080]
                if hd_files:
                    best_file = sorted(hd_files, key=lambda x: x.get("width", 0), reverse=True)[0]
                else:
                    # Fallback to smallest available if no HD
                    best_file = sorted(video_files, key=lambda x: x.get("width", 0))[0]

                results.append({
                    "url": best_file.get("link"),
                    "width": best_file.get("width"),
                    "height": best_file.get("height"),
                    "duration": video.get("duration")
                })

            return results

    def download(self, url, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with httpx.Client(timeout=120.0) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        return output_path


class YouTubeClient:
    def __init__(self):
        logger.info("YouTubeClient initialized (API auto-publish + SEO + Cover Thumbnail mode).")

    def search_videos(self, query, max_results=5):
        return [{"title": f"Video {i} for {query}", "description": "Mock description"} for i in range(max_results)]

    def upload_video(self, video_path, title, description, tags=None, category_id="22"):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir = Path("output/ready_for_upload")
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        filename = Path(video_path).stem
        dest_path = dest_dir / f"{timestamp}_{filename}.mp4"
        cover_path = dest_dir / f"{timestamp}_{filename}_cover.jpg"
        seo_path = dest_dir / f"{timestamp}_{filename}_seo.json"

        # 1. Copy video to output queue
        shutil.copy2(video_path, dest_path)

        # 2. Extract HD Viral Cover Thumbnail from Hook (1.5s)
        try:
            from .thumbnail_creator import ThumbnailCreator
            ThumbnailCreator().create_viral_cover(str(dest_path), str(cover_path), timestamp_sec=1.5)
        except Exception as e:
            logger.warning(f"Could not generate cover thumbnail: {e}")

        # 3. Generate Click-Optimized SEO Metadata & Hashtags
        try:
            from .youtube_seo import YouTubeSEOGenerator
            seo_data = YouTubeSEOGenerator().generate_seo_metadata(title, description, category_id=category_id)
        except Exception as e:
            logger.warning(f"Using default metadata due to SEO error: {e}")
            seo_data = {
                "title": f"{title} #shorts",
                "description": description,
                "tags": tags or ["shorts", "viral"],
                "category_id": category_id
            }

        with open(seo_path, "w", encoding="utf-8") as f:
            json.dump(seo_data, f, indent=4)

        logger.info(f"Saved video: {dest_path}")
        logger.info(f"Saved viral cover thumbnail: {cover_path}")
        logger.info(f"Saved SEO metadata: {seo_path}")

        # 4. Attempt Direct YouTube API v3 Publishing if token.json exists
        token_file = Path("token.json")
        if token_file.exists():
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaFileUpload

                logger.info("🔑 Found token.json! Uploading directly to YouTube channel via Data API v3...")
                creds = Credentials.from_authorized_user_file(str(token_file), ['https://www.googleapis.com/auth/youtube.upload'])
                youtube = build("youtube", "v3", credentials=creds)

                body = {
                    "snippet": {
                        "title": seo_data["title"],
                        "description": seo_data["description"],
                        "tags": seo_data["tags"],
                        "categoryId": seo_data["category_id"]
                    },
                    "status": {
                        "privacyStatus": "public",
                        "selfDeclaredMadeForKids": False
                    }
                }
                media = MediaFileUpload(str(dest_path), chunksize=-1, resumable=True)
                request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
                response = request.execute()
                yt_url = f"https://www.youtube.com/shorts/{response['id']}"
                logger.info(f"🎉 SUCCESS! Video auto-published to YouTube: {yt_url}")
                return yt_url
            except Exception as e:
                logger.error(f"YouTube API upload failed ({e}). Video is ready in {dest_path}")
        else:
            logger.info("💡 YouTube OAuth token (token.json) not found — saved video, cover thumbnail, and SEO metadata locally to output/ready_for_upload/.")
            logger.info("💡 To enable automated API publishing, run: python src/setup_youtube_auth.py")

        return str(dest_path)


def get_youtube_client():
    return YouTubeClient()

def get_tts_client():
    return TtsClient()

def get_stock_media_client():
    return StockMediaClient()

def get_llm_client():
    return LLMClient()
