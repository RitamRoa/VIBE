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

# One Journey issue is finite (~20 slides). Never an endless feed.
JOURNEY_LENGTH = 20

# Continue Exploring — neighbouring knowledge paths per root topic.
# Add new neighbours here only; no other files need hardcoding.
JOURNEY_NEIGHBORS: Dict[str, List[str]] = {
    "finance": [
        "economics",
        "investment_banking",
        "accounting",
        "financial_markets",
        "behavioral_finance",
    ],
    "technology": [
        "computer_science",
        "artificial_intelligence",
        "operating_systems",
        "programming_languages",
        "cybersecurity",
    ],
    "business": [
        "management",
        "marketing",
        "entrepreneurship",
        "corporate_finance",
        "supply_chain",
    ],
    "science": [
        "physics",
        "biology",
        "chemistry",
        "astronomy",
        "climate_change",
    ],
    "history": [
        "ancient_civilizations",
        "empires",
        "archaeology",
        "historical_figures",
        "political_history",
    ],
    "space": [
        "astronomy",
        "solar_system",
        "space_exploration",
        "nasa",
        "planets",
    ],
}

# Lightweight neighbour category definitions (not shown on Vibedia home / intro)
JOURNEY_NEIGHBOR_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "economics": {
        "id": "economics",
        "label": "Economics",
        "type": "category",
        "wikipedia_category": "Economics",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Economics",
            "Macroeconomics",
            "Microeconomics",
            "Supply and demand",
            "Inflation",
            "Gross domestic product",
            "Keynesian economics",
            "Market (economics)",
            "Trade",
            "Monetary policy",
        ],
    },
    "investment_banking": {
        "id": "investment_banking",
        "label": "Investment Banking",
        "type": "category",
        "wikipedia_category": "Investment banking",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Investment banking",
            "Goldman Sachs",
            "Mergers and acquisitions",
            "Initial public offering",
            "Underwriting",
            "Leveraged buyout",
            "Equity (finance)",
            "Debt capital markets",
            "Financial analyst",
            "Wall Street",
        ],
    },
    "accounting": {
        "id": "accounting",
        "label": "Accounting",
        "type": "category",
        "wikipedia_category": "Accounting",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Accounting",
            "Financial statement",
            "Balance sheet",
            "Audit",
            "Bookkeeping",
            "Generally Accepted Accounting Principles",
            "Cash flow statement",
            "Depreciation",
            "Double-entry bookkeeping",
            "Taxation",
        ],
    },
    "financial_markets": {
        "id": "financial_markets",
        "label": "Financial Markets",
        "type": "category",
        "wikipedia_category": "Financial markets",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Financial market",
            "Stock exchange",
            "Bond market",
            "Foreign exchange market",
            "Derivatives market",
            "New York Stock Exchange",
            "Nasdaq",
            "Commodity market",
            "Market liquidity",
            "Bull market",
        ],
    },
    "behavioral_finance": {
        "id": "behavioral_finance",
        "label": "Behavioral Finance",
        "type": "category",
        "wikipedia_category": "Behavioral economics",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Behavioral economics",
            "Cognitive bias",
            "Prospect theory",
            "Loss aversion",
            "Herd behavior",
            "Daniel Kahneman",
            "Anchoring (cognitive bias)",
            "Confirmation bias",
            "Nudge theory",
            "Irrational exuberance",
        ],
    },
    "computer_science": {
        "id": "computer_science",
        "label": "Computer Science",
        "type": "category",
        "wikipedia_category": "Computer science",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Computer science",
            "Algorithm",
            "Data structure",
            "Computational complexity theory",
            "Alan Turing",
            "Programming language",
            "Computer network",
            "Database",
            "Operating system",
            "Software engineering",
        ],
    },
    "artificial_intelligence": {
        "id": "artificial_intelligence",
        "label": "Artificial Intelligence",
        "type": "category",
        "wikipedia_category": "Artificial intelligence",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Artificial intelligence",
            "Machine learning",
            "Neural network (machine learning)",
            "Natural language processing",
            "Computer vision",
            "Deep learning",
            "Large language model",
            "Expert system",
            "Robotics",
            "Turing test",
        ],
    },
    "operating_systems": {
        "id": "operating_systems",
        "label": "Operating Systems",
        "type": "category",
        "wikipedia_category": "Operating systems",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Operating system",
            "Linux",
            "Microsoft Windows",
            "Unix",
            "Kernel (operating system)",
            "Process (computing)",
            "File system",
            "Virtual memory",
            "macOS",
            "Android (operating system)",
        ],
    },
    "programming_languages": {
        "id": "programming_languages",
        "label": "Programming Languages",
        "type": "category",
        "wikipedia_category": "Programming languages",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Programming language",
            "Python (programming language)",
            "JavaScript",
            "C (programming language)",
            "Java (programming language)",
            "Rust (programming language)",
            "Type system",
            "Compiler",
            "Functional programming",
            "Object-oriented programming",
        ],
    },
    "cybersecurity": {
        "id": "cybersecurity",
        "label": "Cybersecurity",
        "type": "category",
        "wikipedia_category": "Computer security",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Computer security",
            "Encryption",
            "Malware",
            "Firewall (computing)",
            "Phishing",
            "Public-key cryptography",
            "Vulnerability (computer security)",
            "Zero-day (computing)",
            "Authentication",
            "Transport Layer Security",
        ],
    },
    "management": {
        "id": "management",
        "label": "Management",
        "type": "category",
        "wikipedia_category": "Management",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Management",
            "Leadership",
            "Strategic management",
            "Project management",
            "Organizational culture",
            "Human resource management",
            "Operations management",
            "Decision-making",
            "Peter Drucker",
            "Business administration",
        ],
    },
    "marketing": {
        "id": "marketing",
        "label": "Marketing",
        "type": "category",
        "wikipedia_category": "Marketing",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Marketing",
            "Brand",
            "Advertising",
            "Digital marketing",
            "Market segmentation",
            "Consumer behaviour",
            "Product (business)",
            "Pricing",
            "Public relations",
            "Content marketing",
        ],
    },
    "entrepreneurship": {
        "id": "entrepreneurship",
        "label": "Entrepreneurship",
        "type": "category",
        "wikipedia_category": "Entrepreneurship",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Entrepreneurship",
            "Startup company",
            "Venture capital",
            "Business plan",
            "Lean startup",
            "Angel investor",
            "Bootstrapping (business)",
            "Innovation",
            "Small business",
            "Unicorn (finance)",
        ],
    },
    "corporate_finance": {
        "id": "corporate_finance",
        "label": "Corporate Finance",
        "type": "category",
        "wikipedia_category": "Corporate finance",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Corporate finance",
            "Capital structure",
            "Dividend",
            "Working capital",
            "Valuation (finance)",
            "Cost of capital",
            "Cash flow",
            "Leverage (finance)",
            "Shareholder",
            "Mergers and acquisitions",
        ],
    },
    "supply_chain": {
        "id": "supply_chain",
        "label": "Supply Chain",
        "type": "category",
        "wikipedia_category": "Supply chain management",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Supply chain",
            "Logistics",
            "Inventory",
            "Procurement",
            "Just-in-time manufacturing",
            "Warehouse",
            "Distribution (marketing)",
            "Outsourcing",
            "Global supply chain",
            "Demand forecasting",
        ],
    },
    "physics": {
        "id": "physics",
        "label": "Physics",
        "type": "category",
        "wikipedia_category": "Physics",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Physics",
            "Quantum mechanics",
            "Relativity",
            "Thermodynamics",
            "Electromagnetism",
            "Particle physics",
            "Newton's laws of motion",
            "Energy",
            "Optics",
            "Condensed matter physics",
        ],
    },
    "biology": {
        "id": "biology",
        "label": "Biology",
        "type": "category",
        "wikipedia_category": "Biology",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Biology",
            "Cell (biology)",
            "DNA",
            "Evolution",
            "Genetics",
            "Ecology",
            "Photosynthesis",
            "Protein",
            "Species",
            "Microbiology",
        ],
    },
    "chemistry": {
        "id": "chemistry",
        "label": "Chemistry",
        "type": "category",
        "wikipedia_category": "Chemistry",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Chemistry",
            "Periodic table",
            "Chemical bond",
            "Organic chemistry",
            "Molecule",
            "Acid",
            "Chemical reaction",
            "Atom",
            "Catalysis",
            "Inorganic chemistry",
        ],
    },
    "astronomy": {
        "id": "astronomy",
        "label": "Astronomy",
        "type": "category",
        "wikipedia_category": "Astronomy",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Astronomy",
            "Galaxy",
            "Star",
            "Telescope",
            "Cosmology",
            "Exoplanet",
            "Nebula",
            "Big Bang",
            "Observatory",
            "Astrophysics",
        ],
    },
    "climate_change": {
        "id": "climate_change",
        "label": "Climate Change",
        "type": "category",
        "wikipedia_category": "Climate change",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Climate change",
            "Global warming",
            "Greenhouse effect",
            "Carbon dioxide",
            "Renewable energy",
            "Sea level rise",
            "Paris Agreement",
            "Fossil fuel",
            "Climate",
            "Intergovernmental Panel on Climate Change",
        ],
    },
    "ancient_civilizations": {
        "id": "ancient_civilizations",
        "label": "Ancient Civilizations",
        "type": "category",
        "wikipedia_category": "Ancient history",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Ancient history",
            "Ancient Egypt",
            "Mesopotamia",
            "Ancient Greece",
            "Indus Valley Civilisation",
            "Maya civilization",
            "Ancient Rome",
            "Chinese civilization",
            "Bronze Age",
            "Sumer",
        ],
    },
    "empires": {
        "id": "empires",
        "label": "Empires",
        "type": "category",
        "wikipedia_category": "Empires",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Empire",
            "Roman Empire",
            "British Empire",
            "Ottoman Empire",
            "Mongol Empire",
            "Byzantine Empire",
            "Persian Empire",
            "Spanish Empire",
            "Holy Roman Empire",
            "Imperialism",
        ],
    },
    "archaeology": {
        "id": "archaeology",
        "label": "Archaeology",
        "type": "category",
        "wikipedia_category": "Archaeology",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Archaeology",
            "Excavation (archaeology)",
            "Artifact (archaeology)",
            "Radiocarbon dating",
            "Pompeii",
            "Tutankhamun",
            "Stonehenge",
            "Paleolithic",
            "Underwater archaeology",
            "Archaeological site",
        ],
    },
    "historical_figures": {
        "id": "historical_figures",
        "label": "Historical Figures",
        "type": "category",
        "wikipedia_category": "People by century",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Cleopatra",
            "Alexander the Great",
            "Julius Caesar",
            "Napoleon",
            "Abraham Lincoln",
            "Mahatma Gandhi",
            "Winston Churchill",
            "Queen Victoria",
            "Genghis Khan",
            "Leonardo da Vinci",
        ],
    },
    "political_history": {
        "id": "political_history",
        "label": "Political History",
        "type": "category",
        "wikipedia_category": "Political history",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Political history",
            "Democracy",
            "Revolution",
            "Cold War",
            "United Nations",
            "Constitution",
            "Diplomacy",
            "Treaty",
            "Nation state",
            "French Revolution",
        ],
    },
    "solar_system": {
        "id": "solar_system",
        "label": "Solar System",
        "type": "category",
        "wikipedia_category": "Solar System",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Solar System",
            "Sun",
            "Earth",
            "Mars",
            "Jupiter",
            "Saturn",
            "Moon",
            "Asteroid",
            "Comet",
            "Kuiper belt",
        ],
    },
    "space_exploration": {
        "id": "space_exploration",
        "label": "Space Exploration",
        "type": "category",
        "wikipedia_category": "Space exploration",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Space exploration",
            "Apollo program",
            "Space Shuttle",
            "Voyager program",
            "Human spaceflight",
            "SpaceX",
            "Moon landing",
            "Mars rover",
            "International Space Station",
            "Satellite",
        ],
    },
    "nasa": {
        "id": "nasa",
        "label": "NASA",
        "type": "category",
        "wikipedia_category": "NASA",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "NASA",
            "Kennedy Space Center",
            "Jet Propulsion Laboratory",
            "Hubble Space Telescope",
            "James Webb Space Telescope",
            "Artemis program",
            "Mercury (project)",
            "Gemini (NASA)",
            "Apollo 11",
            "Johnson Space Center",
        ],
    },
    "planets": {
        "id": "planets",
        "label": "Planets",
        "type": "category",
        "wikipedia_category": "Planets",
        "ttl_seconds": 6 * 60 * 60,
        "seeds": [
            "Planet",
            "Mercury (planet)",
            "Venus",
            "Earth",
            "Mars",
            "Jupiter",
            "Saturn",
            "Uranus",
            "Neptune",
            "Dwarf planet",
        ],
    },
}


def get_category(topic: str) -> Optional[Dict[str, Any]]:
    """Return category config by id (home, journey, or neighbour), or None."""
    key = topic.lower().strip()
    if key in WIKI_CATEGORIES:
        return WIKI_CATEGORIES[key]
    return JOURNEY_NEIGHBOR_CATEGORIES.get(key)


def list_category_ids() -> list[str]:
    """Ordered category ids for the Vibedia home feed."""
    return [cid for cid in HOME_SECTION_IDS if cid in WIKI_CATEGORIES]


def list_journey_topic_ids() -> list[str]:
    """Ordered Journey topic ids (excludes random)."""
    return [cid for cid in JOURNEY_TOPIC_IDS if cid in WIKI_CATEGORIES]


def resolve_explore_topics(source_topics: List[str]) -> List[str]:
    """
    Expand selected topics into neighbouring knowledge areas.

    Used by Continue Exploring — the next chapter of the magazine.
    """
    expanded: List[str] = []
    for tid in source_topics:
        key = tid.lower().strip()
        for neighbor in JOURNEY_NEIGHBORS.get(key, []):
            if neighbor not in expanded and get_category(neighbor):
                expanded.append(neighbor)
    # Fallback: if nothing mapped, reuse sources themselves
    if not expanded:
        expanded = [t for t in source_topics if get_category(t)]
    return expanded


def journey_title(mode: str, topics: List[str]) -> str:
    """Human label for the completion screen (e.g. Finance Journey)."""
    mode_n = (mode or "").lower()
    if mode_n == "surprise":
        return "Surprise Journey"
    if mode_n == "explore":
        return "Further Reading"
    if len(topics) == 1:
        cfg = get_category(topics[0])
        label = cfg["label"] if cfg else topics[0].replace("_", " ").title()
        return f"{label} Journey"
    if len(topics) > 1:
        return "Curated Journey"
    return "Journey"
