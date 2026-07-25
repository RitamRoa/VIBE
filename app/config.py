"""
Central Vibedia / Wikipedia configuration.

Add a new magazine section by appending one entry to WIKI_CATEGORIES —
routes, cache TTLs, and the home feed pick it up automatically.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Wikipedia MediaWiki + REST endpoints
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
WIKI_REST_URL = "https://en.wikipedia.org/api/rest_v1"
WIKI_USER_AGENT = "VIBE-Vibedia/1.0 (https://github.com; educational news reader)"

# Default page size for category / topic listings
TOPIC_PAGE_SIZE = 20
HOME_SECTION_SIZE = 10
SEARCH_RESULT_LIMIT = 20

# Cache TTLs (seconds)
ARTICLE_TTL = 24 * 60 * 60
SEARCH_TTL = 60 * 60
HOME_TTL = 6 * 60 * 60

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
    "random": {
        "id": "random",
        "label": "Random",
        "type": "random",
        "wikipedia_category": None,
        "ttl_seconds": 60 * 60,
        "seeds": [],
    },
}


def get_category(topic: str) -> Optional[Dict[str, Any]]:
    """Return category config by id, or None if unknown."""
    return WIKI_CATEGORIES.get(topic.lower().strip())


def list_category_ids() -> list[str]:
    """Ordered category ids for the home feed."""
    return list(WIKI_CATEGORIES.keys())
