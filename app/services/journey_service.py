"""
Journey service — curated fullscreen reading sessions.

Reuses wiki_service for fetching/normalization and image resolution.
Never hits Wikipedia's random endpoint for Surprise Me.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Dict, List, Optional, Set

from app.config import (
    JOURNEY_DEFAULT_LIMIT,
    get_category,
    list_journey_topic_ids,
)
from app.models.wiki import JourneyArticle, JourneyResponse, WikiArticleCard
from app.services.wiki_service import wiki_service


def _encode_cursor(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: Optional[str]) -> Dict[str, Any]:
    if not cursor:
        return {}
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


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


def _interleave(
    buckets: Dict[str, List[JourneyArticle]],
    topic_order: List[str],
    *,
    limit: int,
    exclude: Set[str],
) -> List[JourneyArticle]:
    """
    Round-robin merge that prefers alternating categories.

    Avoids consecutive articles from the same category whenever possible.
    """
    queues: Dict[str, List[JourneyArticle]] = {
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
                # No alternative available — accept deferred
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
    """Builds Surprise / topic Journey batches via existing wiki_service."""

    async def _fetch_topic(
        self, tid: str, token: Optional[str]
    ) -> tuple[str, List[JourneyArticle], Optional[str]]:
        cfg = get_category(tid)
        label = cfg["label"] if cfg else tid.title()
        try:
            page = await wiki_service.get_topic(tid, token)
        except Exception as exc:  # noqa: BLE001
            print(f"Journey topic fetch error ({tid}): {exc}")
            return tid, [], token
        articles = [_normalize(card, label) for card in page.articles]
        return tid, articles, page.continue_token

    async def get_journey(
        self,
        *,
        mode: str = "surprise",
        topics: Optional[List[str]] = None,
        limit: int = JOURNEY_DEFAULT_LIMIT,
        cursor: Optional[str] = None,
        exclude: Optional[List[str]] = None,
    ) -> JourneyResponse:
        """
        Return up to ``limit`` normalized Journey articles.

        mode=surprise → balanced mix across all Journey topics.
        mode=topics   → only the selected topic ids.
        """
        limit = max(1, min(int(limit or JOURNEY_DEFAULT_LIMIT), 40))
        state = _decode_cursor(cursor)
        seen: Set[str] = set(exclude or [])
        seen.update(state.get("seen") or [])

        mode_norm = (mode or "surprise").strip().lower()
        if mode_norm not in {"surprise", "topics"}:
            mode_norm = "surprise"

        journey_ids = list_journey_topic_ids()

        if mode_norm == "surprise":
            topic_ids = journey_ids
        else:
            requested = topics or state.get("topics") or []
            topic_ids = []
            for raw in requested:
                tid = str(raw).strip().lower()
                cfg = get_category(tid)
                if not cfg or cfg.get("type") == "random":
                    continue
                if tid not in topic_ids and (
                    tid in journey_ids or cfg.get("type") == "category"
                ):
                    topic_ids.append(tid)
            if not topic_ids:
                topic_ids = journey_ids

        tokens: Dict[str, Optional[str]] = dict(state.get("tokens") or {})

        fetched = await asyncio.gather(
            *[self._fetch_topic(tid, tokens.get(tid)) for tid in topic_ids]
        )

        buckets: Dict[str, List[JourneyArticle]] = {}
        new_tokens: Dict[str, Optional[str]] = {}
        for tid, articles, cont in fetched:
            buckets[tid] = articles
            new_tokens[tid] = cont

        # Second page for topics exhausted by exclusions
        refill_ids = [
            tid
            for tid in topic_ids
            if new_tokens.get(tid)
            and not any(a.id not in seen for a in buckets.get(tid, []))
        ]
        if refill_ids:
            refilled = await asyncio.gather(
                *[self._fetch_topic(tid, new_tokens.get(tid)) for tid in refill_ids]
            )
            for tid, articles, cont in refilled:
                buckets[tid] = articles
                new_tokens[tid] = cont

        mixed = _interleave(buckets, topic_ids, limit=limit, exclude=seen)

        seen_list = list(seen)
        if len(seen_list) > 200:
            seen_list = seen_list[-200:]

        has_more = any(new_tokens.get(tid) for tid in topic_ids) or len(mixed) >= limit
        next_cursor = None
        if has_more and mixed:
            next_cursor = _encode_cursor(
                {
                    "mode": mode_norm,
                    "topics": topic_ids,
                    "tokens": new_tokens,
                    "seen": seen_list,
                }
            )

        return JourneyResponse(articles=mixed, next_cursor=next_cursor)


journey_service = JourneyService()
