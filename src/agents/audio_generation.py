# src/agents/audio_generation.py
"""
Audio Generation Agent — uses edge-tts (free Microsoft Neural voices) to
convert a script into a real, human-sounding voiceover MP3 file.
"""
import os
import asyncio
import logging

logger = logging.getLogger(__name__)


class AudioGenerationAgent:
    def __init__(self, tts_client=None, file_management=None):
        self.tts_client = tts_client
        self.file_management = file_management
        logger.info("AudioGenerationAgent initialized.")

    def _build_narration_text(self, script_data):
        """
        Combine all script sections into a single narration string
        with natural pauses between sections.
        """
        sections = []
        for key in ["hook", "introduction", "body", "call_to_action", "outro"]:
            text = script_data.get(key, "")
            if text:
                sections.append(text.strip())

        # Join sections with a single space so speech flows continuously without dead pauses
        full_text = " ".join(sections)

        # Clean up any problematic characters or extra punctuation that cause edge-tts to pause awkwardly
        import re
        full_text = re.sub(r'[\n\r]+', ' ', full_text)
        full_text = re.sub(r'\.{2,}', '.', full_text)  # Remove ellipses (...)
        full_text = re.sub(r'—|--', ',', full_text)    # Replace long dashes with brief comma
        full_text = re.sub(r'\s{2,}', ' ', full_text).strip()

        word_count = len(full_text.split())
        est_duration = word_count / 2.5  # ~150 words per minute
        logger.info(f"Narration text: {word_count} words, ~{est_duration:.0f}s estimated duration")

        return full_text

    def run(self, script_data):
        """
        Generate voiceover audio from the script using edge-tts.
        Returns the path to the generated MP3 file.
        """
        logger.info("Running AudioGenerationAgent...")

        # Build the narration text
        narration = self._build_narration_text(script_data)

        if not narration:
            logger.error("No narration text available. Cannot generate audio.")
            return None

        # Determine output path
        if self.file_management:
            output_path = self.file_management.get_audio_path("narration.mp3")
        else:
            output_path = "narration.mp3"

        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Use the TTS client (edge-tts)
        if self.tts_client:
            try:
                result = self.tts_client.synthesize(text=narration, output_filename=output_path)
                file_size = os.path.getsize(result)
                logger.info(f"Generated voiceover: {result} ({file_size / 1024:.1f} KB)")
                return result
            except Exception as e:
                logger.error(f"TTS synthesis failed: {e}")
                return None
        else:
            # Fallback: write a minimal WAV placeholder
            logger.warning("No TTS client available, generating placeholder audio.")
            output_path = output_path.replace(".mp3", ".wav")
            with open(output_path, "wb") as f:
                f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
                        b"\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00"
                        b"\x02\x00\x10\x00data\x00\x00\x00\x00")
            return output_path
