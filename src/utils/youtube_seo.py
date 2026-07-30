# src/utils/youtube_seo.py
"""
YouTube Shorts SEO & Viral Metadata Generator
Produces click-optimized titles, high-retention descriptions, and 20+ targeted search tags.
"""
import logging
import re

logger = logging.getLogger(__name__)


class YouTubeSEOGenerator:
    def __init__(self):
        logger.info("YouTubeSEOGenerator initialized.")

    def generate_seo_metadata(self, title, script_text=None, niche="Health & Wellness", category_id="22"):
        """
        Generate complete YouTube Shorts SEO metadata package.
        
        Args:
            title (str): Base topic title.
            script_text (str): Optional script narration text for context.
            niche (str): Content category/niche.
            category_id (str): YouTube Category ID (22 = People & Blogs, 27 = Education, 26 = Howto & Style).
            
        Returns:
            dict: Package containing 'title', 'description', 'tags', 'category_id', and 'hashtags'.
        """
        # 1. Click-Optimized Short Title (under 65 chars with #shorts)
        clean_title = re.sub(r'[#@\n\r]', '', title).strip()
        seo_title = f"{clean_title} #shorts"
        if len(seo_title) > 65:
            seo_title = f"{clean_title[:54]}... #shorts"

        # 2. Viral Hashtags
        base_hashtags = ["#shorts", "#viral", "#fyp", "#trending", "#habits"]
        niche_tags = {
            "Health & Wellness": ["#health", "#wellness", "#selfimprovement", "#morningroutine"],
            "Tech": ["#tech", "#gadgets", "#ai", "#innovation"],
            "Finance": ["#money", "#investing", "#wealth", "#success"]
        }
        hashtags = base_hashtags + niche_tags.get(niche, ["#motivation", "#mindset", "#lifehacks"])

        # 3. Targeted Search Tags (20+ keywords for algorithm ranking)
        seo_tags = [
            "shorts", "viral", "fyp", "trending", "youtube shorts",
            "morning routine", "habits that change your life", "self improvement",
            "productivity", "health and wellness", "daily habits", "life hacks",
            "personal growth", "motivation", "success mindset", "healthy lifestyle",
            "mindfulness", "wellness tips", "morning habits", "better habits"
        ]

        # 4. High-Retention Description
        desc_lines = [
            f"🔥 {clean_title} — Start applying these powerful daily habits today!",
            "",
            "📌 IN THIS SHORT:",
            "• Simple actionable habits you can start tomorrow morning",
            "• Proven routines to boost energy, focus, and productivity",
            "• Upgrade your daily mindset in under 60 seconds",
            "",
            "⏱️ TIMESTAMPS:",
            "0:00 - The Hook",
            "0:05 - Key Habits That Change Your Life",
            "0:50 - Final Takeaway & Challenge",
            "",
            "💡 Like and Subscribe for more daily high-performance & wellness routines!",
            "",
            " ".join(hashtags)
        ]
        description = "\n".join(desc_lines)

        logger.info(f"Generated SEO Metadata for: {seo_title}")
        return {
            "title": seo_title,
            "description": description,
            "tags": seo_tags,
            "hashtags": hashtags,
            "category_id": category_id
        }
