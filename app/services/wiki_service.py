"""
Wikipedia service — all upstream communication lives here.

Frontend never talks to Wikipedia; routes call this service only.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from app.cache.wiki_cache import wiki_cache
from app.config import (
    ARTICLE_TTL,
    HOME_SECTION_SIZE,
    HOME_TTL,
    SEARCH_RESULT_LIMIT,
    SEARCH_TTL,
    TOPIC_PAGE_SIZE,
    WIKI_API_URL,
    WIKI_CATEGORIES,
    WIKI_REST_URL,
    WIKI_TIMEOUT_SECONDS,
    WIKI_USER_AGENT,
    get_category,
    list_category_ids,
)
from app.models.wiki import (
    ResolvedImage,
    WikiArticleCard,
    WikiArticleDetail,
    WikiHomeResponse,
    WikiSearchResponse,
    WikiTopicResponse,
)
from app.services.image_service import ImageService


class WikiUpstreamError(Exception):
    """Raised when Wikipedia is unavailable, rate-limited, or times out."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class WikiService:
    """Async Wikipedia client with caching and request coalescing."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.images = ImageService(self._mediawiki)

    async def _get_client(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        if (
            self._client is None
            or self._client.is_closed
            or self._loop is not loop
        ):
            if self._client is not None and not self._client.is_closed:
                try:
                    await self._client.aclose()
                except Exception:  # noqa: BLE001
                    pass
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(WIKI_TIMEOUT_SECONDS),
                headers={
                    "User-Agent": WIKI_USER_AGENT,
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
            self._loop = loop
        return self._client

    async def close(self) -> None:
        """Close the shared HTTP client."""
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception:  # noqa: BLE001
                pass
            self._client = None
            self._loop = None

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    async def _mediawiki(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """GET MediaWiki Action API."""
        client = await self._get_client()
        query = {"format": "json", "formatversion": "2", **params}
        try:
            response = await client.get(WIKI_API_URL, params=query)
            if response.status_code == 429:
                raise WikiUpstreamError("Wikipedia rate limit exceeded", 429)
            if response.status_code >= 500:
                raise WikiUpstreamError("Wikipedia unavailable", 502)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise WikiUpstreamError("Wikipedia request timed out", 504) from exc
        except httpx.HTTPError as exc:
            raise WikiUpstreamError(f"Wikipedia request failed: {exc}", 502) from exc

    async def _rest_get(self, path: str) -> Dict[str, Any]:
        """GET Wikipedia REST API path (without base)."""
        client = await self._get_client()
        url = f"{WIKI_REST_URL}{path}"
        try:
            response = await client.get(url)
            if response.status_code == 404:
                return {}
            if response.status_code == 403:
                # Some REST endpoints reject certain clients; callers may fall back.
                return {}
            if response.status_code == 429:
                raise WikiUpstreamError("Wikipedia rate limit exceeded", 429)
            if response.status_code >= 500:
                raise WikiUpstreamError("Wikipedia unavailable", 502)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise WikiUpstreamError("Wikipedia request timed out", 504) from exc
        except httpx.HTTPError as exc:
            raise WikiUpstreamError(f"Wikipedia request failed: {exc}", 502) from exc

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _one_line(text: Optional[str], fallback: str = "") -> str:
        if not text:
            return fallback
        cleaned = " ".join(text.replace("\n", " ").split())
        if len(cleaned) > 160:
            return cleaned[:157].rstrip() + "…"
        return cleaned

    @staticmethod
    def _page_url(title: str) -> str:
        return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

    def _card_from_page(self, page: Dict[str, Any]) -> Optional[WikiArticleCard]:
        """Build a card from a MediaWiki page object."""
        title = page.get("title")
        if not title or page.get("missing"):
            return None
        thumb = None
        thumbnail = page.get("thumbnail") or {}
        if isinstance(thumbnail, dict):
            thumb = thumbnail.get("source")
        if not thumb:
            original = page.get("original") or {}
            if isinstance(original, dict):
                thumb = original.get("source")
        extract = page.get("extract") or page.get("description") or ""
        return WikiArticleCard(
            title=title,
            summary=self._one_line(extract),
            thumbnail=thumb,
            url=page.get("fullurl") or self._page_url(title),
            pageid=page.get("pageid"),
        )

    def _card_from_summary(self, data: Dict[str, Any]) -> Optional[WikiArticleCard]:
        """Build a card from REST page summary JSON."""
        title = data.get("title")
        if not title or data.get("type") == "disambiguation" and not data.get("extract"):
            if not title:
                return None
        thumb = None
        original = data.get("originalimage") or data.get("thumbnail") or {}
        if isinstance(original, dict):
            thumb = original.get("source")
        extract = data.get("extract") or data.get("description") or ""
        content_urls = data.get("content_urls") or {}
        desktop = content_urls.get("desktop") or {}
        return WikiArticleCard(
            title=title,
            summary=self._one_line(extract),
            thumbnail=thumb,
            url=desktop.get("page") or self._page_url(title),
            pageid=data.get("pageid"),
        )

    def _cache_cards(self, cards: List[WikiArticleCard], ttl: int) -> None:
        """Warm individual card cache entries (separate from full article cache)."""
        for card in cards:
            key = wiki_cache.card_key(card.title)
            if wiki_cache.get(key) is None:
                wiki_cache.set(key, card.model_dump(), ttl)

    # ------------------------------------------------------------------
    # Batch fetch by titles (reuses article cache)
    # ------------------------------------------------------------------

    async def fetch_cards_by_titles(
        self, titles: List[str], *, ttl: int = ARTICLE_TTL
    ) -> List[WikiArticleCard]:
        """
        Resolve titles to cards, reusing cached articles and batching the rest.
        """
        if not titles:
            return []

        results: Dict[str, WikiArticleCard] = {}
        missing: List[str] = []

        for title in titles:
            # Prefer card cache; fall back to full article cache
            cached = wiki_cache.get(wiki_cache.card_key(title))
            if not cached:
                detail = wiki_cache.get(wiki_cache.article_key(title))
                if isinstance(detail, dict) and detail.get("title"):
                    cached = {
                        "title": detail["title"],
                        "summary": detail.get("summary")
                        or self._one_line(detail.get("extract")),
                        "thumbnail": detail.get("thumbnail"),
                        "url": detail.get("url") or self._page_url(detail["title"]),
                        "pageid": detail.get("pageid"),
                    }
            if cached and isinstance(cached, dict) and cached.get("title"):
                results[title] = WikiArticleCard(**cached)
                continue
            missing.append(title)

        if missing:
            # MediaWiki allows | joined titles; chunk to stay under URL limits
            chunk_size = 20
            for i in range(0, len(missing), chunk_size):
                chunk = missing[i : i + chunk_size]
                joined = "|".join(chunk)
                data = await self._mediawiki(
                    {
                        "action": "query",
                        "prop": "extracts|pageimages|info",
                        "exintro": 1,
                        "explaintext": 1,
                        "piprop": "thumbnail|original",
                        "pithumbsize": 640,
                        "pilicense": "any",
                        "inprop": "url",
                        "titles": joined,
                    }
                )
                pages = (data.get("query") or {}).get("pages") or []
                for page in pages:
                    card = self._card_from_page(page)
                    if card:
                        results[card.title] = card
                        wiki_cache.set(
                            wiki_cache.card_key(card.title),
                            card.model_dump(),
                            ttl,
                        )

        # Preserve requested order where possible
        ordered: List[WikiArticleCard] = []
        seen = set()
        for title in titles:
            card = results.get(title)
            if not card:
                # Case-insensitive fallback
                for key, value in results.items():
                    if key.lower() == title.lower():
                        card = value
                        break
            if card and card.title not in seen:
                ordered.append(card)
                seen.add(card.title)
        # Append any extras from results not in order list
        for card in results.values():
            if card.title not in seen:
                ordered.append(card)
                seen.add(card.title)
        return ordered

    # ------------------------------------------------------------------
    # Public endpoints logic
    # ------------------------------------------------------------------

    async def get_home(self) -> WikiHomeResponse:
        """Fetch all home sections concurrently (one upstream wave)."""

        async def build() -> Dict[str, List[dict]]:
            ids = list_category_ids()
            tasks = [self._home_section(cat_id) for cat_id in ids]
            sections_list = await asyncio.gather(*tasks, return_exceptions=True)
            payload: Dict[str, List[dict]] = {}
            for cat_id, section in zip(ids, sections_list):
                if isinstance(section, Exception):
                    print(f"Home section error ({cat_id}): {section}")
                    payload[cat_id] = []
                else:
                    payload[cat_id] = [c.model_dump() for c in section]
            return payload

        raw = await wiki_cache.get_or_fetch(wiki_cache.home_key(), HOME_TTL, build)
        return WikiHomeResponse(
            sections={
                key: [WikiArticleCard(**item) for item in items]
                for key, items in raw.items()
            }
        )

    async def _home_section(self, topic: str) -> List[WikiArticleCard]:
        """Load one home section with its own TTL / dedup key."""
        config = get_category(topic)
        if not config:
            return []

        ttl = int(config["ttl_seconds"])

        async def build() -> List[dict]:
            if config["type"] == "random":
                cards = await self._fetch_random(HOME_SECTION_SIZE)
            else:
                seeds = list(config.get("seeds") or [])[:HOME_SECTION_SIZE]
                cards = await self.fetch_cards_by_titles(seeds, ttl=ARTICLE_TTL)
                # Backfill from category if seeds under-deliver
                if len(cards) < HOME_SECTION_SIZE:
                    extra = await self._fetch_category_members(
                        config["wikipedia_category"],
                        limit=HOME_SECTION_SIZE,
                    )
                    seen = {c.title for c in cards}
                    for card in extra:
                        if card.title not in seen:
                            cards.append(card)
                            seen.add(card.title)
                        if len(cards) >= HOME_SECTION_SIZE:
                            break
            cards = cards[:HOME_SECTION_SIZE]
            cards = await self.images.attach_to_cards(
                cards, category=config["label"]
            )
            self._cache_cards(cards, ARTICLE_TTL)
            return [c.model_dump() for c in cards]

        raw = await wiki_cache.get_or_fetch(
            wiki_cache.category_home_key(topic), ttl, build
        )
        return [WikiArticleCard(**item) for item in raw]

    async def _fetch_random(self, limit: int) -> List[WikiArticleCard]:
        """Fetch random main-namespace articles with extracts."""
        data = await self._mediawiki(
            {
                "action": "query",
                "generator": "random",
                "grnnamespace": 0,
                "grnlimit": limit,
                "prop": "extracts|pageimages|info",
                "exintro": 1,
                "explaintext": 1,
                "piprop": "thumbnail|original",
                "pithumbsize": 640,
                "pilicense": "any",
                "inprop": "url",
            }
        )
        pages = (data.get("query") or {}).get("pages") or []
        cards: List[WikiArticleCard] = []
        for page in pages:
            card = self._card_from_page(page)
            if card:
                cards.append(card)
        return cards

    async def _fetch_category_members(
        self,
        category_name: str,
        *,
        limit: int = TOPIC_PAGE_SIZE,
        continue_token: Optional[str] = None,
    ) -> List[WikiArticleCard]:
        """
        Fetch category member pages and hydrate cards concurrently via titles.
        Returns cards only; continue token handled by caller via raw API.
        """
        params: Dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category_name}",
            "cmtype": "page",
            "cmlimit": limit,
        }
        if continue_token:
            params["cmcontinue"] = continue_token

        data = await self._mediawiki(params)
        members = (data.get("query") or {}).get("categorymembers") or []
        titles = [m["title"] for m in members if m.get("title")]
        return await self.fetch_cards_by_titles(titles, ttl=ARTICLE_TTL)

    async def get_topic(
        self, topic: str, continue_token: Optional[str] = None
    ) -> WikiTopicResponse:
        """Paginated topic listing with caching per page token."""
        config = get_category(topic)
        if not config:
            raise ValueError(f"Unknown topic: {topic}")

        ttl = int(config["ttl_seconds"])
        cache_key = wiki_cache.topic_key(topic, continue_token)

        async def build() -> dict:
            if config["type"] == "random":
                cards = await self._fetch_random(TOPIC_PAGE_SIZE)
                cards = await self.images.attach_to_cards(
                    cards, category=config["label"]
                )
                self._cache_cards(cards, ARTICLE_TTL)
                return {
                    "articles": [c.model_dump() for c in cards],
                    "continue_token": None,
                    "has_more": True,  # random always offers another roll
                }

            params: Dict[str, Any] = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{config['wikipedia_category']}",
                "cmtype": "page",
                "cmlimit": TOPIC_PAGE_SIZE,
            }
            if continue_token:
                params["cmcontinue"] = continue_token

            data = await self._mediawiki(params)
            members = (data.get("query") or {}).get("categorymembers") or []
            titles = [m["title"] for m in members if m.get("title")]
            cards = await self.fetch_cards_by_titles(titles, ttl=ARTICLE_TTL)
            cards = await self.images.attach_to_cards(
                cards, category=config["label"]
            )
            self._cache_cards(cards, ARTICLE_TTL)

            cont = (data.get("continue") or {}).get("cmcontinue")
            return {
                "articles": [c.model_dump() for c in cards],
                "continue_token": cont,
                "has_more": bool(cont),
            }

        raw = await wiki_cache.get_or_fetch(cache_key, ttl, build)
        return WikiTopicResponse(
            topic=config["id"],
            label=config["label"],
            articles=[WikiArticleCard(**a) for a in raw["articles"]],
            continue_token=raw.get("continue_token"),
            has_more=bool(raw.get("has_more")),
        )

    async def search(self, query: str) -> WikiSearchResponse:
        """Search Wikipedia and return card results."""
        q = (query or "").strip()
        if not q:
            return WikiSearchResponse(query=q, articles=[])

        cache_key = wiki_cache.search_key(q)

        async def build() -> List[dict]:
            data = await self._mediawiki(
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": q,
                    "srlimit": SEARCH_RESULT_LIMIT,
                    "srnamespace": 0,
                }
            )
            hits = (data.get("query") or {}).get("search") or []
            titles = [h["title"] for h in hits if h.get("title")]
            cards = await self.fetch_cards_by_titles(titles, ttl=ARTICLE_TTL)
            cards = await self.images.attach_to_cards(
                cards, category="Knowledge"
            )
            self._cache_cards(cards, ARTICLE_TTL)
            return [c.model_dump() for c in cards]

        raw = await wiki_cache.get_or_fetch(cache_key, SEARCH_TTL, build)
        return WikiSearchResponse(
            query=q, articles=[WikiArticleCard(**item) for item in raw]
        )

    async def get_article(self, title: str) -> WikiArticleDetail:
        """
        Full article detail with related pages.
        Reuses cached article data when still fresh.
        """
        normalized = title.replace("_", " ").strip()
        cache_key = wiki_cache.article_key(normalized)

        async def build() -> dict:
            encoded = quote(normalized.replace(" ", "_"), safe="")
            summary_task = self._rest_get(f"/page/summary/{encoded}")
            related_task = self._rest_get(f"/page/related/{encoded}")
            summary, related_payload = await asyncio.gather(
                summary_task, related_task, return_exceptions=True
            )

            if isinstance(summary, Exception) or not summary:
                # Fallback to MediaWiki extracts
                cards = await self.fetch_cards_by_titles([normalized], ttl=ARTICLE_TTL)
                if not cards:
                    raise WikiUpstreamError("Article not found", 404)
                card = cards[0]
                resolved = card.image or await self.images.resolve(
                    card.title,
                    thumbnail=card.thumbnail,
                    category="Knowledge",
                )
                return {
                    "title": card.title,
                    "summary": card.summary,
                    "thumbnail": resolved.image_url,
                    "url": card.url,
                    "pageid": card.pageid,
                    "description": None,
                    "extract": card.summary,
                    "related": [],
                    "sections": [],
                    "image": resolved.model_dump()
                    if hasattr(resolved, "model_dump")
                    else resolved,
                }

            assert isinstance(summary, dict)
            thumb = None
            original = summary.get("originalimage") or summary.get("thumbnail") or {}
            if isinstance(original, dict):
                thumb = original.get("source")

            content_urls = summary.get("content_urls") or {}
            desktop = content_urls.get("desktop") or {}
            extract = summary.get("extract") or ""

            related_cards: List[dict] = []
            related_titles: List[str] = []

            if isinstance(related_payload, dict):
                pages = related_payload.get("pages") or []
                related_titles = [
                    (p.get("titles") or {}).get("normalized")
                    or (p.get("titles") or {}).get("display")
                    or p.get("title")
                    for p in pages[:8]
                ]
                related_titles = [t for t in related_titles if t]

            # Fallback when REST /page/related is unavailable (403/empty)
            if not related_titles:
                try:
                    more = await self._mediawiki(
                        {
                            "action": "query",
                            "list": "search",
                            "srsearch": f"morelike:{normalized}",
                            "srlimit": 8,
                            "srnamespace": 0,
                        }
                    )
                    hits = (more.get("query") or {}).get("search") or []
                    related_titles = [
                        h["title"]
                        for h in hits
                        if h.get("title") and h["title"].lower() != normalized.lower()
                    ]
                except WikiUpstreamError:
                    related_titles = []

            if related_titles:
                cards = await self.fetch_cards_by_titles(
                    related_titles, ttl=ARTICLE_TTL
                )
                cards = await self.images.attach_to_cards(
                    cards, category="Knowledge"
                )
                related_cards = [c.model_dump() for c in cards]

            # Resolve primary article visual (cached after first time)
            resolved = await self.images.resolve(
                summary.get("title") or normalized,
                thumbnail=thumb,
                category="Knowledge",
            )

            return {
                "title": summary.get("title") or normalized,
                "summary": self._one_line(extract),
                "thumbnail": resolved.image_url,
                "url": desktop.get("page") or self._page_url(normalized),
                "pageid": summary.get("pageid"),
                "description": summary.get("description"),
                "extract": extract,
                "related": related_cards,
                "sections": [],
                "image": resolved.model_dump(),
            }

        raw = await wiki_cache.get_or_fetch(cache_key, ARTICLE_TTL, build)
        # Ensure image is always present even for older cache entries
        if not raw.get("image"):
            resolved = await self.images.resolve(
                raw.get("title") or normalized,
                thumbnail=raw.get("thumbnail"),
                category="Knowledge",
            )
            raw["image"] = resolved.model_dump()
            raw["thumbnail"] = resolved.image_url
            wiki_cache.set(cache_key, raw, ARTICLE_TTL)

        detail = WikiArticleDetail(**raw)
        # Keep card cache in sync for search / grids
        wiki_cache.set(
            wiki_cache.card_key(detail.title),
            WikiArticleCard(
                title=detail.title,
                summary=detail.summary,
                thumbnail=detail.thumbnail,
                url=detail.url,
                pageid=detail.pageid,
                image=detail.image,
            ).model_dump(),
            ARTICLE_TTL,
        )
        return detail


wiki_service = WikiService()
