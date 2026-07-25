"""
Wikipedia image resolution pipeline.

Priority:
  1. Lead thumbnail (if usable)
  2. Best suitable on-page article image
  3. Editorial cover marker (rendered locally by the frontend)

Resolved results are cached so resolution never repeats for the same article.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from app.cache.wiki_cache import wiki_cache
from app.config import ARTICLE_TTL
from app.models.wiki import ResolvedImage, WikiArticleCard

# Minimum edge length for Priority-2 images
MIN_IMAGE_EDGE = 250

# Filename / URL hints that are never suitable magazine art
_SKIP_NAME_RE = re.compile(
    r"(logo|icon|wordmark|disambig|stub|ambox|padlock|symbol|badge|"
    r"commons-logo|edit[-_]?clear|question_book|crystal_|"
    r"wikimedia|wikipedia[-_]?logo|red[_-]?pencil|semi[_-]?protect|"
    r"featured[_-]?article|speaker[_-]?icon|sound[_-]?icon|"
    r"portal[_-]?|template_|nuvola|gnome-mime|file[_-]?icon)",
    re.IGNORECASE,
)

MediaWikiFn = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


class ImageService:
    """Resolves a visual for every Vibedia article exactly once (per TTL)."""

    def __init__(self, mediawiki: MediaWikiFn, *, concurrency: int = 6) -> None:
        self._mediawiki = mediawiki
        self._sem = asyncio.Semaphore(concurrency)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve(
        self,
        title: str,
        *,
        thumbnail: Optional[str] = None,
        category: str = "Knowledge",
    ) -> ResolvedImage:
        """
        Resolve image for a title.

        Cached results are returned immediately — no re-fetch.
        """
        cache_key = wiki_cache.image_key(title)
        cached = wiki_cache.get(cache_key)
        if isinstance(cached, dict) and cached.get("image_type"):
            # Keep category fresh for display context when reusing cache
            cached = {**cached, "title": cached.get("title") or title}
            if category and category != "Knowledge":
                cached["category"] = category
            return ResolvedImage(**cached)

        async with self._sem:
            # Re-check after waiting for the semaphore (dedupe bursts)
            cached = wiki_cache.get(cache_key)
            if isinstance(cached, dict) and cached.get("image_type"):
                if category and category != "Knowledge":
                    cached = {**cached, "category": category}
                return ResolvedImage(**cached)

            result = await self._resolve_uncached(
                title, thumbnail=thumbnail, category=category
            )
            wiki_cache.set(cache_key, result.model_dump(), ARTICLE_TTL)
            return result

    async def attach_to_cards(
        self,
        cards: Sequence[WikiArticleCard],
        *,
        category: str = "Knowledge",
    ) -> List[WikiArticleCard]:
        """Attach resolved images to a list of cards (concurrent)."""
        if not cards:
            return []

        async def one(card: WikiArticleCard) -> WikiArticleCard:
            # Already fully resolved in this payload
            if (
                card.image
                and card.image.image_type
                and (
                    card.image.image_type == "editorial"
                    or card.image.image_url
                )
            ):
                # Refresh category label for section context
                img = card.image.model_copy(
                    update={"category": category or card.image.category}
                )
                return card.model_copy(
                    update={
                        "image": img,
                        "thumbnail": img.image_url,
                    }
                )

            resolved = await self.resolve(
                card.title,
                thumbnail=card.thumbnail,
                category=category,
            )
            return card.model_copy(
                update={
                    "image": resolved,
                    "thumbnail": resolved.image_url,
                }
            )

        return list(await asyncio.gather(*[one(c) for c in cards]))

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    async def _resolve_uncached(
        self,
        title: str,
        *,
        thumbnail: Optional[str],
        category: str,
    ) -> ResolvedImage:
        # Priority 1 — lead thumbnail
        if self._is_usable_url(thumbnail):
            return ResolvedImage(
                image_type="thumbnail",
                image_url=thumbnail,
                title=title,
                category=category,
            )

        # Priority 2 — scan article images
        best = await self._best_article_image(title)
        if best:
            return ResolvedImage(
                image_type="article_image",
                image_url=best,
                title=title,
                category=category,
            )

        # Priority 3 — editorial cover (frontend-rendered)
        return ResolvedImage(
            image_type="editorial",
            image_url=None,
            title=title,
            category=category or "Knowledge",
        )

    async def _best_article_image(self, title: str) -> Optional[str]:
        """Pick the largest suitable raster image from the article page."""
        try:
            listed = await self._mediawiki(
                {
                    "action": "query",
                    "titles": title,
                    "prop": "images",
                    "imlimit": 40,
                }
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Image list error ({title}): {exc}")
            return None

        pages = (listed.get("query") or {}).get("pages") or []
        if not pages:
            return None

        files: List[str] = []
        for page in pages:
            for img in page.get("images") or []:
                name = img.get("title") or ""
                if not name.startswith("File:"):
                    continue
                if not self._is_candidate_filename(name):
                    continue
                files.append(name)

        if not files:
            return None

        # Cap upstream fan-out
        files = files[:25]
        best_url: Optional[str] = None
        best_area = 0

        # Batch imageinfo in chunks
        chunk_size = 10
        for i in range(0, len(files), chunk_size):
            chunk = files[i : i + chunk_size]
            try:
                info = await self._mediawiki(
                    {
                        "action": "query",
                        "titles": "|".join(chunk),
                        "prop": "imageinfo",
                        "iiprop": "url|size|mime",
                        "iiurlwidth": 800,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                print(f"Imageinfo error ({title}): {exc}")
                continue

            for page in (info.get("query") or {}).get("pages") or []:
                ii_list = page.get("imageinfo") or []
                if not ii_list:
                    continue
                ii = ii_list[0]
                mime = (ii.get("mime") or "").lower()
                if mime.startswith("image/svg") or "svg" in mime:
                    continue
                if not mime.startswith("image/"):
                    continue

                width = int(ii.get("width") or 0)
                height = int(ii.get("height") or 0)
                if width < MIN_IMAGE_EDGE or height < MIN_IMAGE_EDGE:
                    continue

                # Prefer scaled thumb URL when present, else original
                url = ii.get("thumburl") or ii.get("url")
                if not self._is_usable_url(url):
                    continue

                area = width * height
                if area > best_area:
                    best_area = area
                    best_url = url

        return best_url

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    @staticmethod
    def _is_usable_url(url: Optional[str]) -> bool:
        if not url or not isinstance(url, str):
            return False
        lower = url.lower().split("?", 1)[0]
        if not lower.startswith("http"):
            return False
        if lower.endswith(".svg") or ".svg/" in lower:
            return False
        # Filter by filename only — never the CDN host (upload.wikimedia.org)
        filename = lower.rsplit("/", 1)[-1]
        if _SKIP_NAME_RE.search(filename):
            return False
        return True

    @staticmethod
    def _is_candidate_filename(name: str) -> bool:
        # name like "File:Something.png"
        bare = name.split(":", 1)[-1]
        lower = bare.lower()
        if lower.endswith(".svg"):
            return False
        if not lower.endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff")
        ):
            if "." in lower:
                return False
        if _SKIP_NAME_RE.search(lower):
            return False
        return True


# Module-level instance is wired from WikiService (needs mediawiki binding)
image_service: Optional[ImageService] = None
