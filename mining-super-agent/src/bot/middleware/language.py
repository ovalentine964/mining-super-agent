"""
Language Middleware
===================
Auto-detects language from user messages and manages language preferences.

Fallback chain: detected → preferred → Swahili (default)

Supported:
- Swahili (sw) — primary
- English (en)
- Luo (luo)

Detection uses keyword / pattern matching — fast and zero-cost.
For production, could optionally call a language detection API.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language detection patterns
# ---------------------------------------------------------------------------

# Common Swahili words/phrases
_SWAHILI_PATTERNS = [
    re.compile(r"\b(habari|hujambo|jambo|mambo|sasa|niaje|vipi)\b", re.I),
    re.compile(r"\b(nataka|nini|wapi|kwa|na|ya|la|za|wa|ni|si)\b", re.I),
    re.compile(r"\b(dhahabu|madini|shaba|mwamba|shamba|serikali)\b", re.I),
    re.compile(r"\b(tafadhali|asante|karibu|samahani|sawa)\b", re.I),
    re.compile(r"\b(bei|soko|leseni|ripoti|uchambuzi|sauti)\b", re.I),
    re.compile(r"\b(nitakusaidia|ninaweza|unataka|je,)\b", re.I),
    re.compile(r"\b(kwenye|kutoka|hapo|hapa|pale|huko)\b", re.I),
]

# Common English words/phrases
_ENGLISH_PATTERNS = [
    re.compile(r"\b(the|is|are|was|were|have|has|had|will|would|could|should)\b", re.I),
    re.compile(r"\b(what|where|when|how|why|who|which)\b", re.I),
    re.compile(r"\b(mineral|gold|copper|price|market|license|mining)\b", re.I),
    re.compile(r"\b(hello|hi|hey|please|thank|thanks|sorry)\b", re.I),
    re.compile(r"\b(I|you|we|they|this|that|there|here)\b", re.I),
    re.compile(r"\b(want|need|help|know|find|identify|analyze)\b", re.I),
]

# Common Luo words/phrases
_LUO_PATTERNS = [
    re.compile(r"\b(maribé|amos|inyalo|ka|gi|ne|ni|ma|wuod|min)\b", re.I),
    re.compile(r"\b(nang|in|ok|os|ose|wach|peny|nen|tich)\b", re.I),
    re.compile(r"\b(konyo|thur|dhok|dhi|biro|yudo|ng'eyo)\b", re.I),
    re.compile(r"\b(piny|shamba|minera|dhahabu|chiero)\b", re.I),
    re.compile(r"\b(munde|japiny|wuod|min|nyise|pwod|mor)\b", re.I),
]


class LanguageMiddleware:
    """
    Manages language detection and user preferences.

    Thread-safe for the single-threaded async bot.
    """

    def __init__(self):
        self._preferences: dict[int, str] = {}  # user_id → lang code

    def detect_language(self, text: str) -> str:
        """
        Detect the language of a text message.

        Returns: 'sw', 'en', or 'luo'
        Defaults to 'sw' if uncertain.
        """
        if not text or not text.strip():
            return "sw"

        text_clean = text.strip()

        # Score each language
        scores: dict[str, int] = {"sw": 0, "en": 0, "luo": 0}

        for pattern in _SWAHILI_PATTERNS:
            if pattern.search(text_clean):
                scores["sw"] += 1

        for pattern in _ENGLISH_PATTERNS:
            if pattern.search(text_clean):
                scores["en"] += 1

        for pattern in _LUO_PATTERNS:
            if pattern.search(text_clean):
                scores["luo"] += 1

        # If no patterns matched, default to Swahili
        if sum(scores.values()) == 0:
            return "sw"

        # Return the highest scoring language
        detected = max(scores, key=scores.get)  # type: ignore[arg-type]

        # Require a minimum score for English and Luo to avoid false positives
        # (Swahili is the safe default)
        if detected == "en" and scores["en"] < 2:
            return "sw"
        if detected == "luo" and scores["luo"] < 2:
            return "sw"

        return detected

    def set_language(self, user_id: int, lang: str) -> None:
        """Store a user's language preference."""
        if lang in ("sw", "en", "luo"):
            self._preferences[user_id] = lang
            logger.info("Language preference set for user %s: %s", user_id, lang)
        else:
            logger.warning("Invalid language code '%s' for user %s", lang, user_id)

    def get_language(self, user_id: int) -> str:
        """Get a user's stored language preference. Defaults to Swahili."""
        return self._preferences.get(user_id, "sw")

    def resolve_language(self, user_id: int, detected: str) -> str:
        """
        Resolve the final language using the fallback chain:
        1. If user has explicitly set a preference, use it
        2. Otherwise, use the detected language
        3. Fall back to Swahili

        Exception: If the user explicitly chose English or Luo, respect that
        even if the current message is in Swahili (code-switching is common).
        """
        preferred = self._preferences.get(user_id)

        # If user explicitly chose a language, stick with it
        if preferred:
            return preferred

        # Otherwise use detected
        if detected in ("sw", "en", "luo"):
            return detected

        return "sw"

    def clear_preference(self, user_id: int) -> None:
        """Clear a user's language preference (revert to auto-detect)."""
        if user_id in self._preferences:
            del self._preferences[user_id]

    def get_all_preferences(self) -> dict[int, str]:
        """Get all stored preferences (for admin)."""
        return dict(self._preferences)
