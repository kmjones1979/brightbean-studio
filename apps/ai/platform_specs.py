"""Per-platform constraints used by the AI generation engine.

Frozen at module level — pure data, easy to update.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class PlatformSpec:
    name: str
    label: str
    char_limit: int
    soft_buffer: int = 20  # Always stay this far below char_limit
    hashtag_style: str = "inline"  # inline | first-comment | none
    link_handling: str = "raw"  # raw | shortened | hidden
    line_break_style: str = "double"  # double | single | hard
    typical_tone: str = "professional"
    emoji_default: str = "sparingly"
    notes: str = ""

    @property
    def effective_limit(self) -> int:
        return max(1, self.char_limit - self.soft_buffer)


SPECS: dict[str, PlatformSpec] = {
    "twitter": PlatformSpec(
        name="twitter",
        label="X (Twitter)",
        char_limit=280,
        hashtag_style="inline",
        line_break_style="single",
        typical_tone="punchy, opinionated",
        emoji_default="optional",
        notes="Threads OK if numbered (1/, 2/). Hooks in first 200 chars.",
    ),
    "linkedin_personal": PlatformSpec(
        name="linkedin_personal",
        label="LinkedIn (Personal)",
        char_limit=3000,
        hashtag_style="inline",
        line_break_style="double",
        typical_tone="thoughtful, narrative",
        emoji_default="sparingly",
        notes="3-5 hashtags at the end. First two lines must hook before 'see more'.",
    ),
    "linkedin_company": PlatformSpec(
        name="linkedin_company",
        label="LinkedIn (Company)",
        char_limit=3000,
        hashtag_style="inline",
        line_break_style="double",
        typical_tone="professional, brand-voiced",
        emoji_default="rarely",
        notes="Brand-safe. Avoid first-person 'I' — use 'we' or company name.",
    ),
    "instagram": PlatformSpec(
        name="instagram",
        label="Instagram (Caption)",
        char_limit=2200,
        hashtag_style="first-comment",
        line_break_style="single",
        typical_tone="warm, visual",
        emoji_default="frequent",
        notes="First 125 chars show before truncation. Up to 30 hashtags in first comment.",
    ),
    "instagram_reels": PlatformSpec(
        name="instagram_reels",
        label="Instagram Reels",
        char_limit=2200,
        hashtag_style="inline",
        line_break_style="single",
        typical_tone="energetic",
        emoji_default="frequent",
        notes="Hook in first 3 words. 5-10 hashtags max for reels reach.",
    ),
    "tiktok": PlatformSpec(
        name="tiktok",
        label="TikTok",
        char_limit=2200,
        hashtag_style="inline",
        line_break_style="single",
        typical_tone="casual, native",
        emoji_default="frequent",
        notes="Hook < 2s. Use 3-5 trending hashtags relevant to the niche.",
    ),
    "youtube_short": PlatformSpec(
        name="youtube_short",
        label="YouTube Short (description)",
        char_limit=5000,
        hashtag_style="inline",
        line_break_style="double",
        typical_tone="instructive",
        emoji_default="rarely",
        notes="3 hashtags max appear above title. #Shorts recommended.",
    ),
    "youtube_long": PlatformSpec(
        name="youtube_long",
        label="YouTube (long-form description)",
        char_limit=5000,
        hashtag_style="inline",
        line_break_style="double",
        typical_tone="informative",
        emoji_default="rarely",
        notes="First 2-3 lines drive CTR. Include chapter timestamps if relevant.",
    ),
    "pinterest": PlatformSpec(
        name="pinterest",
        label="Pinterest (pin)",
        char_limit=500,
        hashtag_style="inline",
        line_break_style="single",
        typical_tone="aspirational, descriptive",
        emoji_default="rarely",
        notes="Optimize for search intent. Include the keyword in the first sentence.",
    ),
    "threads": PlatformSpec(
        name="threads",
        label="Threads",
        char_limit=500,
        hashtag_style="none",
        line_break_style="single",
        typical_tone="conversational",
        emoji_default="optional",
        notes="No hashtags. Keep it punchier than X.",
    ),
    "bluesky": PlatformSpec(
        name="bluesky",
        label="Bluesky",
        char_limit=300,
        hashtag_style="inline",
        line_break_style="single",
        typical_tone="dev/builder, sincere",
        emoji_default="rarely",
        notes="Audience is technical. Threading via reply chains is the norm.",
    ),
    "mastodon": PlatformSpec(
        name="mastodon",
        label="Mastodon",
        char_limit=500,
        hashtag_style="inline",
        line_break_style="single",
        typical_tone="builder, sincere",
        emoji_default="rarely",
        notes="Hashtags are critical for discovery. Use CamelCase tags.",
    ),
    "google_business": PlatformSpec(
        name="google_business",
        label="Google Business Profile",
        char_limit=1500,
        hashtag_style="none",
        line_break_style="double",
        typical_tone="local, helpful",
        emoji_default="rarely",
        notes="No hashtags. Include a clear CTA (Visit, Call, Learn more).",
    ),
}


# Public, immutable view
PLATFORM_SPECS = MappingProxyType(SPECS)


def get_spec(platform: str) -> PlatformSpec | None:
    return PLATFORM_SPECS.get(platform)


def supported_platforms() -> list[str]:
    return list(PLATFORM_SPECS.keys())
