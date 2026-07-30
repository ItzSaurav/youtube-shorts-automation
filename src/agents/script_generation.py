# src/agents/script_generation.py
"""
Script Generation Agent — uses the LLM to produce structured YouTube video
scripts with hook, body, CTA, and outro sections.
"""
import json
import logging

logger = logging.getLogger(__name__)

# System prompt for script generation
SCRIPT_SYSTEM_PROMPT = """You are an expert YouTube scriptwriter specializing in Health & Wellness content.
Write scripts that are engaging, fact-based, and optimized for viewer retention.

RULES:
- Use a conversational, friendly tone (as if talking to a friend)
- Start with a SCROLL-STOPPING VIRAL HOOK in the first 5 seconds (use curiosity gap, bold statement, or pattern interrupt)
- Include surprising facts and statistics where relevant
- Keep sentences short and punchy for fast-paced voiceover narration
- End with a clear call-to-action

Return ONLY valid JSON with these exact keys:
{{
  "title": "The final video title",
  "hook": "First 5 seconds - grab attention immediately with a bold pattern-interrupt hook (e.g. 'Stop doing X immediately...' or '99% of people ruin their morning before 8 AM...') (1-2 sentences)",
  "introduction": "Set up the topic and why it matters (2-3 sentences)",
  "body": "The main content with 3-5 key points, each separated by a newline (8-15 sentences total)",
  "call_to_action": "Ask viewers to like, subscribe, comment (1-2 sentences)",
  "outro": "Closing line and tease next video (1 sentence)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "description": "YouTube video description (2-3 sentences with keywords)"
}}"""

SCRIPT_USER_PROMPT = """Write a {length} YouTube {format_type} script about:

Topic: {topic}
Tone: {tone}
Target audience: {audience}

{context}

Remember: Return ONLY the JSON object, no markdown formatting or extra text."""


class ScriptGenerationAgent:
    def __init__(self, llm_client=None, file_management=None):
        self.llm_client = llm_client
        self.file_management = file_management
        logger.info("ScriptGenerationAgent initialized.")

    def run(self, topic_data, tone="casual and friendly", video_format="regular",
            audience="general health-conscious viewers"):
        """
        Generate a structured video script from a topic dict.
        Falls back to a template if the LLM is unavailable.
        """
        title = topic_data.get("title", "Untitled Video")
        description = topic_data.get("description", "")
        tags = topic_data.get("tags", [])

        logger.info(f"Generating script for topic: {title}")

        # Determine target length based on format
        if video_format == "shorts":
            length = "short (under 60 seconds of narration, roughly 120-150 words)"
            format_type = "Shorts"
        else:
            length = "medium (3-5 minutes of narration, roughly 500-800 words)"
            format_type = "video"

        # Try LLM-powered script generation
        if self.llm_client:
            try:
                prompt = SCRIPT_USER_PROMPT.format(
                    topic=title,
                    tone=tone,
                    length=length,
                    format_type=format_type,
                    audience=audience,
                    context=f"Topic description: {description}" if description else ""
                )
                response = self.llm_client.generate_raw(
                    prompt,
                    system_prompt=SCRIPT_SYSTEM_PROMPT
                )
                script = json.loads(response)

                # Ensure all required keys exist
                required_keys = ["title", "hook", "introduction", "body",
                                 "call_to_action", "outro", "tags", "description"]
                if all(k in script for k in required_keys):
                    logger.info(f"LLM generated script for: {script['title']}")
                    if self.file_management:
                        self.file_management.save_script(script, filename="latest_script.json")
                    return script
                else:
                    logger.warning("LLM script missing required keys, using fallback.")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"LLM script generation failed: {e}. Using fallback.")

        # Smart Fact-Specific Script Generator (Daily Rotation)
        title_lower = title.lower()
        if any(w in title_lower for w in ["procrastination", "mental", "procrastinate", "focus", "study"]):
            hook = f"Stop calling yourself lazy. Your brain is not procrastinating, it is protecting you from stress. Here is the 60-second trick to fix it."
            intro = f"Neuroscientists discovered that procrastination is an emotional regulation problem, not a time management problem."
            body = (
                f"Fact number one. When you face a task, your amygdala interprets it as a threat and triggers a fight-or-flight freeze response.\n\n"
                f"Fact number two. The five second rule bypasses your emotional brain by forcing your prefrontal cortex to activate before self doubt kicks in.\n\n"
                f"Fact number three. Starting a task for just two minutes breaks the dopamine freeze, and eighty percent of the time you will finish the entire job."
            )
        elif any(w in title_lower for w in ["phone", "screen", "waking", "morning"]):
            hook = f"If you check your phone within 15 minutes of waking up, you are accidentally sabotaging your brain for the rest of the day."
            intro = f"Here is the shocking neurological reason why morning screen light makes you feel exhausted by noon."
            body = (
                f"Fact number one. When you wake up, your brain is transitioning from alpha waves to beta waves. Checking notifications forces instant stress into a relaxed brain.\n\n"
                f"Fact number two. High contrast blue light floods your dopamine receptors before you even get out of bed, making normal tasks feel boring all day.\n\n"
                f"Fact number three. Waiting just thirty minutes before checking your screen doubles your natural cortisol awakening response and morning energy."
            )
        elif any(w in title_lower for w in ["sleep", "bed", "insomnia", "energy"]):
            hook = f"Stop counting sheep. If you wake up tired every single morning, your bedtime habits are secretly destroying your deep sleep."
            intro = f"Here are three sleep facts most doctors wish you knew about resetting your circadian rhythm."
            body = (
                f"Fact number one. Your body temperature must drop by two degrees Fahrenheit to enter deep REM sleep. A warm room literally traps you in light sleep.\n\n"
                f"Fact number two. Caffeine has a quarter-life of twelve hours, meaning a coffee at noon is still stimulating your brain at midnight.\n\n"
                f"Fact number three. The ten three two one zero rule clears melatonin blockers so you fall asleep in under three minutes naturally."
            )
        elif any(w in title_lower for w in ["psychology", "iq", "brain", "memory", "forget", "room"]):
            hook = f"Have you ever walked into a room and instantly forgotten why you went in there? You are not losing your memory, your brain did it on purpose."
            intro = f"Here are three mind blowing psychological facts about how your subconscious brain works."
            body = (
                f"Fact number one. The doorway effect happens because walking through a physical door forces your brain to archive short term memory to save cognitive space.\n\n"
                f"Fact number two. Your brain cannot tell the difference between vivid imagination and real events, which is why mental rehearsal builds physical neural pathways.\n\n"
                f"Fact number three. Chewing flavored gum while learning and chewing the same flavor later increases recall memory by thirty percent."
            )
        else:
            hook = f"Stop what you are doing right now. Ninety five percent of people ignore these daily body signals until it is too late."
            intro = f"Here are three science backed facts about {title.lower()} that will change how you live."
            body = (
                f"Fact number one. Consistency beats intensity every single time. Small daily habits compound faster than massive willpower bursts.\n\n"
                f"Fact number two. Your body signals nutrient and hydration deficits through afternoon brain fog hours before you feel thirsty.\n\n"
                f"Fact number three. Adjusting your morning routine by just fifteen minutes resets your biological clock and doubles daily focus."
            )

        script = {
            "title": title,
            "hook": hook,
            "introduction": intro,
            "body": body,
            "call_to_action": "If you love learning daily brain and body facts, smash that like button and subscribe for new videos every day!",
            "outro": "Thanks for watching, and I will see you tomorrow!",
            "tags": tags if tags else ["facts", "psychology", "science facts", "self improvement", "daily habits"],
            "description": description if description else f"Discover mind-blowing facts about {title.lower()}. Science-backed habits and psychology."
        }

        if self.file_management:
            self.file_management.save_script(script, filename="latest_script.json")

        logger.info(f"Generated smart fact-specific script for topic: '{title}'")
        return script
