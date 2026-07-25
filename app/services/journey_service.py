"""
Journey service — finite curated reading sessions (~20 articles).

Reuses wiki_service for fetching/normalization and image resolution.
Never hits Wikipedia's random endpoint for Surprise Me.
Never builds an endless feed — one issue has a beginning, middle, and end.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from typing import List, Optional, Set

from app.config import (
    JOURNEY_DEFAULT_LIMIT,
    JOURNEY_LENGTH,
    get_category,
    journey_title,
    list_journey_topic_ids,
    resolve_explore_topics,
)
from app.models.wiki import JourneyArticle, JourneyResponse, WikiArticleCard
from app.services.wiki_service import wiki_service


def _article_id(card: WikiArticleCard) -> str:
    if card.pageid:
        return f"p{card.pageid}"
    return f"t:{card.title.strip().lower().replace(' ', '_')}"


def _normalize(card: WikiArticleCard, category_label: str) -> JourneyArticle:
    """Map a Vibedia card into the Journey article contract."""
    image = card.image
    image_type = image.image_type if image else "editorial"
    image_url = image.image_url if image else card.thumbnail
    if not image_url:
        image_type = "editorial"
    return JourneyArticle(
        id=_article_id(card),
        title=card.title,
        summary=card.summary or "",
        image=image_url,
        image_type=image_type,  # type: ignore[arg-type]
        category=(image.category if image and image.category else category_label),
        wikipedia_url=card.url,
        page_id=card.pageid,
    )


def _shuffle_key(seed: str, title: str) -> str:
    return hashlib.sha256(f"{seed}:{title}".encode("utf-8")).hexdigest()


def _interleave(
    buckets: dict[str, List[JourneyArticle]],
    topic_order: List[str],
    *,
    limit: int,
    exclude: Set[str],
) -> List[JourneyArticle]:
    """Round-robin merge preferring alternating categories."""
    queues: dict[str, List[JourneyArticle]] = {
        tid: list(items) for tid, items in buckets.items()
    }
    result: List[JourneyArticle] = []
    last_cat: Optional[str] = None

    while len(result) < limit:
        progressed = False
        ordered = sorted(
            topic_order,
            key=lambda t: 0 if (queues.get(t) and t != last_cat) else 1,
        )
        for tid in ordered:
            q = queues.get(tid) or []
            deferred: Optional[JourneyArticle] = None
            while q:
                article = q.pop(0)
                if article.id in exclude:
                    continue
                same_cat = last_cat and article.category == last_cat
                has_alt = any(
                    queues.get(other) for other in topic_order if other != tid
                )
                if same_cat and has_alt:
                    deferred = article
                    continue
                exclude.add(article.id)
                result.append(article)
                last_cat = article.category
                progressed = True
                if deferred:
                    q.append(deferred)
                break
            if deferred and not progressed:
                if deferred.id not in exclude:
                    exclude.add(deferred.id)
                    result.append(deferred)
                    last_cat = deferred.category
                    progressed = True
            if len(result) >= limit:
                break
        if not progressed:
            break

    return result


class JourneyService:
    """Builds one finite Journey issue via existing wiki_service."""

    async def _pool_for_topic(
        self, tid: str, *, variation_seed: str
    ) -> List[JourneyArticle]:
        """
        Prefer curated high-quality seeds (shuffled per session), then category pages.
        """
        cfg = get_category(tid)
        if not cfg:
            return []
        label = cfg["label"]
        seeds = list(cfg.get("seeds") or [])
        seeds.sort(key=lambda t: _shuffle_key(variation_seed, t))

        cards: List[WikiArticleCard] = []
        if seeds:
            cards = await wiki_service.fetch_cards_by_titles(seeds)
            cards = await wiki_service.images.attach_to_cards(cards, category=label)
        elif cfg.get("type") == "category" and cfg.get("wikipedia_category"):
            # Neighbour topics without seeds: one category page only
            try:
                page = await wiki_service.get_topic(tid, None)
                cards = list(page.articles)
            except Exception as exc:  # noqa: BLE001
                print(f"Journey category pool ({tid}): {exc}")

        # Stable per-session shuffle of the pool (vary Begin Again)
        cards = sorted(cards, key=lambda c: _shuffle_key(variation_seed, c.title))
        return [_normalize(c, label) for c in cards]

    async def get_journey(
        self,
        *,
        mode: str = "surprise",
        topics: Optional[List[str]] = None,
        limit: int = JOURNEY_LENGTH,
        exclude: Optional[List[str]] = None,
        variation: Optional[str] = None,
    ) -> JourneyResponse:
        """
        Return one finite Journey (~20 articles). No endless pagination.

        mode=surprise → balanced mix across Journey topics.
        mode=topics   → selected intro topics.
        mode=explore  → neighbouring knowledge areas (Continue Exploring).
        """
        limit = max(1, min(int(limit or JOURNEY_LENGTH), JOURNEY_LENGTH))
        seen: Set[str] = set(exclude or [])
        mode_norm = (mode or "surprise").strip().lower()
        if mode_norm not in {"surprise", "topics", "explore"}:
            mode_norm = "surprise"

        journey_ids = list_journey_topic_ids()
        source_topics = [
            str(t).strip().lower()
            for t in (topics or [])
            if str(t).strip()
        ]

        if mode_norm == "surprise":
            topic_ids = journey_ids
        elif mode_norm == "explore":
            bases = source_topics or journey_ids
            # Only expand from known journey roots
            bases = [t for t in bases if t in journey_ids or get_category(t)]
            topic_ids = resolve_explore_topics(bases)
            if not topic_ids:
                topic_ids = journey_ids
        else:
            topic_ids = []
            for tid in source_topics:
                cfg = get_category(tid)
                if cfg and cfg.get("type") != "random" and tid not in topic_ids:
                    topic_ids.append(tid)
            if not topic_ids:
                topic_ids = journey_ids

        # Variation salt so Begin Again / new sessions reorder selections
        salt = variation or str(random.randint(1, 10_000_000))

        pools = await asyncio.gather(
            *[self._pool_for_topic(tid, variation_seed=f"{salt}:{tid}") for tid in topic_ids]
        )
        buckets = {tid: pool for tid, pool in zip(topic_ids, pools)}

        mixed = _interleave(buckets, topic_ids, limit=limit, exclude=seen)
        title = journey_title(mode_norm, source_topics if mode_norm != "surprise" else topic_ids)

        return JourneyResponse(
            articles=mixed,
            next_cursor=None,  # finite issue — no endless feed
            title=title,
            total=len(mixed),
            mode=mode_norm,
            topics=topic_ids,
        )


journey_service = JourneyService()
