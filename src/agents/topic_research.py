# src/agents/topic_research.py
"""
Topic Research Agent — uses the LLM to brainstorm SEO-optimized video topic ideas
for the configured niche, then picks the best one.
"""
import os
import json
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Prompt template for topic brainstorming
TOPIC_BRAINSTORM_PROMPT = """You are a YouTube content strategist specializing in the "{niche}" niche.

Generate exactly 5 unique, trending video topic ideas that will get high views and engagement.

For EACH topic, provide:
- title: A click-worthy, SEO-optimized YouTube title (under 60 characters)
- description: A compelling 1-sentence video description for YouTube
- tags: A list of 5-8 relevant YouTube search tags
- search_volume_hint: "high", "medium", or "low" (your best estimate)

Target audience: {audience}
Video format: {video_format}

Return ONLY valid JSON — an array of 5 objects. No markdown, no explanation.
Example format:
[
  {{"title": "...", "description": "...", "tags": ["...", "..."], "search_volume_hint": "high"}}
]"""


class TopicResearchAgent:
    def __init__(self, youtube_client=None, llm_client=None):
        self.youtube_client = youtube_client
        self.llm_client = llm_client
        logger.info("TopicResearchAgent initialized.")

    def run(self, niche="Health & Wellness", audience="general", video_format="both"):
        """
        Brainstorm video topics using the LLM, falling back to template-based
        topics if the LLM is unavailable.
        """
        logger.info(f"Researching topics for niche: {niche}")

        # Try LLM-powered brainstorming first
        # Try LLM-powered brainstorming first
        if self.llm_client:
            try:
                prompt = TOPIC_BRAINSTORM_PROMPT.format(
                    niche=niche,
                    audience=audience,
                    video_format=video_format
                )
                response = self.llm_client.generate_raw(prompt)
                topics = json.loads(response)
                if isinstance(topics, list) and len(topics) > 0:
                    logger.info(f"LLM generated {len(topics)} topic ideas.")
                    return self._deduplicate_and_select(topics)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"LLM topic brainstorm failed: {e}. Using fallback.")

        # Fallback & Daily Rotation: 20-Topic Viral Facts, Psychology & Habits Library
        all_topics = [
            # Daily Habits & Routines
            {"title": "5 Morning Habits That Change Your Life", "description": "Science-backed morning routines for better health and energy.", "tags": ["morning routine", "healthy habits", "wellness", "self improvement"]},
            {"title": "3 Bedtime Habits That Give You Unlimited Energy", "description": "How small evening tweaks double your morning energy.", "tags": ["sleep hacks", "energy tips", "bedtime routine", "health"]},
            {"title": "Why Walking 30 Minutes Daily Changes Everything", "description": "The surprising science behind the simplest daily exercise.", "tags": ["walking benefits", "fitness", "health tips", "daily habits"]},
            {"title": "3 Breathing Techniques to Reduce Stress Instantly", "description": "Calm your nervous system in under 60 seconds with these methods.", "tags": ["stress relief", "breathing exercises", "anxiety", "mental health"]},
            {"title": "The 2-Minute Shower Habit That Boosts Your Immune System", "description": "Why cold showers transform your metabolism and focus.", "tags": ["cold shower", "immune boost", "wellness hacks", "health"]},
            # Psychology & Mindset Facts
            {"title": "3 Psychology Facts About Sleep Most People Ignore", "description": "What your sleeping habits reveal about your brain.", "tags": ["psychology facts", "sleep psychology", "mindset", "brain facts"]},
            {"title": "Why Your Brain Secretly Rejects Multitasking", "description": "The shocking truth about how task-switching destroys memory.", "tags": ["brain facts", "productivity", "psychology", "focus"]},
            {"title": "The 60-Second Mental Trick To Beat Procrastination", "description": "How the 5-second rule rewires your dopamine response.", "tags": ["procrastination", "mindset hacks", "productivity", "self improvement"]},
            {"title": "4 Subtle Signs You Have A High IQ", "description": "Surprising psychological traits of highly intelligent people.", "tags": ["iq signs", "psychology facts", "human brain", "intelligence"]},
            {"title": "Why Listening To Music While Studying Is Actually Hurting You", "description": "How background noise affects deep memory retention.", "tags": ["study tips", "brain science", "psychology facts", "memory"]},
            # Human Body & Health Facts
            {"title": "Foods You Should Never Eat Before Bed", "description": "These common foods are secretly ruining your sleep quality.", "tags": ["sleep tips", "healthy eating", "nutrition", "wellness facts"]},
            {"title": "Signs Your Body Needs More Water Right Now", "description": "Dehydration symptoms most people ignore until it's too late.", "tags": ["hydration", "health facts", "body signals", "wellness"]},
            {"title": "Why Sleeping On Your Right Side Could Be Hurting Your Stomach", "description": "The digestive science behind why sleeping position matters.", "tags": ["sleep posture", "stomach health", "body facts", "wellness"]},
            {"title": "What Happens To Your Body 1 Hour After Drinking Sugar", "description": "The insulin rollercoaster that drains your afternoon energy.", "tags": ["sugar crash", "nutrition facts", "health tips", "metabolism"]},
            {"title": "3 Hidden Signs Your Magnesium Levels Are Too Low", "description": "Why muscle cramps and fatigue mean you need this mineral.", "tags": ["magnesium", "health symptoms", "vitamins", "wellness facts"]},
            # Science & Surprising Hacks
            {"title": "Why You Should Never Check Your Phone Within 15 Minutes Of Waking Up", "description": "How morning screen light destroys your dopamine baseline.", "tags": ["screen time", "morning routine", "dopamine detox", "brain health"]},
            {"title": "The Science Of Why You Forget Why You Entered A Room", "description": "The 'doorway effect' and how your brain clears short-term memory.", "tags": ["brain facts", "memory hacks", "psychology", "science facts"]},
            {"title": "Why Chewing Gum Makes You Smarter Under Pressure", "description": "The blood flow boost that improves cognitive test scores.", "tags": ["chewing gum", "brain boost", "cognitive hacks", "science facts"]},
            {"title": "What Your Eye Twitching Is Actually Trying To Tell You", "description": "The stress and electrolyte signals behind eyelid spasms.", "tags": ["body symptoms", "eye twitching", "health facts", "wellness"]},
            {"title": "The 10-3-2-1-0 Sleep Rule That Will Cure Your Insomnia", "description": "The doctor-recommended countdown for perfect sleep.", "tags": ["sleep hack", "insomnia cure", "bedtime routine", "wellness"]}
        ]
        return self._deduplicate_and_select(all_topics)

    def _deduplicate_and_select(self, topics):
        import random
        used_file = Path("data/scripts/used_topics.json")
        used_file.parent.mkdir(parents=True, exist_ok=True)
        used_titles = []
        if used_file.exists():
            try:
                with open(used_file, "r", encoding="utf-8") as f:
                    used_titles = json.load(f)
            except Exception:
                used_titles = []

        fresh_topics = [t for t in topics if t["title"] not in used_titles]
        if not fresh_topics:
            logger.info("All topics in current pool have been used! Resetting rotation history.")
            used_titles = []
            fresh_topics = topics

        selected_topic = random.choice(fresh_topics)
        used_titles.append(selected_topic["title"])
        with open(used_file, "w", encoding="utf-8") as f:
            json.dump(used_titles, f, indent=4)

        logger.info(f"✨ Selected unique daily topic: '{selected_topic['title']}' ({len(used_titles)}/{len(topics)} used so far)")
        return [selected_topic] + [t for t in fresh_topics if t != selected_topic]
