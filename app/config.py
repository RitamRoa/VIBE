"""
Central Vibedia / Wikipedia configuration.

Add a new magazine or Journey topic by appending one entry to WIKI_CATEGORIES,
then listing its id in HOME_SECTION_IDS and/or JOURNEY_TOPIC_IDS.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Wikipedia MediaWiki + REST endpoints
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
WIKI_REST_URL = "https://en.wikipedia.org/api/rest_v1"
WIKI_USER_AGENT = "VIBE-Vibedia/1.0 (https://github.com; educational news reader)"

# Default page size for category / topic listings
TOPIC_PAGE_SIZE = 20
HOME_SECTION_SIZE = 10
SEARCH_RESULT_LIMIT = 20
JOURNEY_DEFAULT_LIMIT = 20

# Cache TTLs (seconds)
ARTICLE_TTL = 24 * 60 * 60
SEARCH_TTL = 60 * 60
HOME_TTL = 6 * 60 * 60
JOURNEY_TTL = 30 * 60

# Upstream HTTP
WIKI_TIMEOUT_SECONDS = 12.0
WIKI_MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# Categories — single source of truth
# ---------------------------------------------------------------------------
# wikipedia_category: MediaWiki Category: title used for topic pagination.
# seeds: curated titles for the home magazine grid (quality over raw category dump).
# type: "category" | "random"

WIKI_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "finance": {
        "id": "finance",
        "label": "Finance",
        "type": "category",
        "wikipedia_category": "Finance",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Finance",
            "Stock market",
            "Investment",
            "Hedge fund",
            "Cryptocurrency",
            "Federal Reserve",
            "Bond (finance)",
            "Initial public offering",
            "Private equity",
            "Central bank",
        ],
    },
    "technology": {
        "id": "technology",
        "label": "Technology",
        "type": "category",
        "wikipedia_category": "Technology",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Technology",
            "Artificial intelligence",
            "Computer science",
            "Internet",
            "Smartphone",
            "Cloud computing",
            "Quantum computing",
            "Machine learning",
            "Semiconductor",
            "Software engineering",
        ],
    },
    "business": {
        "id": "business",
        "label": "Business",
        "type": "category",
        "wikipedia_category": "Business",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Business",
            "Entrepreneurship",
            "Marketing",
            "Startup company",
            "Supply chain",
            "Corporate finance",
            "Management",
            "E-commerce",
            "Brand",
            "Fortune Global 500",
        ],
    },
    "science": {
        "id": "science",
        "label": "Science",
        "type": "category",
        "wikipedia_category": "Science",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Science",
            "Physics",
            "Chemistry",
            "Biology",
            "Scientific method",
            "Genetics",
            "Evolution",
            "Neuroscience",
            "Climate change",
            "Astronomy",
        ],
    },
    "history": {
        "id": "history",
        "label": "History",
        "type": "category",
        "wikipedia_category": "History",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "History",
            "World War II",
            "Ancient Rome",
            "Industrial Revolution",
            "Renaissance",
            "Cold War",
            "Silk Road",
            "French Revolution",
            "Age of Discovery",
            "Archaeology",
        ],
    },
    "space": {
        "id": "space",
        "label": "Space",
        "type": "category",
        "wikipedia_category": "Space",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Outer space",
            "NASA",
            "Solar System",
            "Black hole",
            "International Space Station",
            "Mars",
            "Milky Way",
            "Space exploration",
            "Telescope",
            "Satellite",
        ],
    },
    "random": {
        "id": "random",
        "label": "Random",
        "type": "random",
        "wikipedia_category": None,
        "ttl_seconds": 60 * 60,
        "seeds": [],
    },
}

# Vibedia magazine home sections (order matters)
HOME_SECTION_IDS: List[str] = ["finance", "technology", "business", "random"]

# Journey topics — no "random"; Surprise Me mixes these intentionally
JOURNEY_TOPIC_IDS: List[str] = [
    "finance",
    "technology",
    "business",
    "science",
    "history",
    "space",
]


def get_category(topic: str) -> Optional[Dict[str, Any]]:
    """Return category config by id, or None if unknown."""
    return WIKI_CATEGORIES.get(topic.lower().strip())


def list_category_ids() -> list[str]:
    """Ordered category ids for the Vibedia home feed."""
    return [cid for cid in HOME_SECTION_IDS if cid in WIKI_CATEGORIES]


def list_journey_topic_ids() -> list[str]:
    """Ordered Journey topic ids (excludes random)."""
    return [cid for cid in JOURNEY_TOPIC_IDS if cid in WIKI_CATEGORIES]
