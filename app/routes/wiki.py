"""
Vibedia Wikipedia API routes.

All Wikipedia traffic is proxied through these endpoints.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import WIKI_CATEGORIES, get_category
from app.models.wiki import (
    WikiArticleDetail,
    WikiHomeResponse,
    WikiSearchResponse,
    WikiTopicResponse,
)
from app.services.wiki_service import WikiUpstreamError, wiki_service

router = APIRouter(prefix="/wiki", tags=["vibedia"])


@router.get("/home")
async def wiki_home():
    """
    Magazine home feed.

    Returns a flat map of category id → exactly ten cards, e.g.
    ``{ "finance": [...], "technology": [...], ... }``.
    Frontend should call this once — never fan out to Wikipedia.
    """
    try:
        home: WikiHomeResponse = await wiki_service.get_home()
        return {
            key: [card.model_dump() for card in cards]
            for key, cards in home.sections.items()
        }
    except WikiUpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/search", response_model=WikiSearchResponse)
async def wiki_search(
    q: str = Query("", min_length=0, max_length=200, description="Search query"),
) -> WikiSearchResponse:
    """Search Wikipedia articles."""
    try:
        return await wiki_service.search(q)
    except WikiUpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/topic/{topic}", response_model=WikiTopicResponse)
async def wiki_topic(
    topic: str,
    continue_token: Optional[str] = Query(
        None, alias="continue", description="Pagination continue token"
    ),
) -> WikiTopicResponse:
    """Paginated articles for a Vibedia topic (finance, technology, …)."""
    if not get_category(topic):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown topic. Valid: {', '.join(WIKI_CATEGORIES)}",
        )
    try:
        return await wiki_service.get_topic(topic, continue_token)
    except WikiUpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/article/{title:path}", response_model=WikiArticleDetail)
async def wiki_article(title: str) -> WikiArticleDetail:
    """Full article detail including related pages."""
    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    try:
        return await wiki_service.get_article(title)
    except WikiUpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/categories")
async def wiki_categories():
    """List configured Vibedia categories (for future-proof clients)."""
    return {
        "categories": [
            {
                "id": cfg["id"],
                "label": cfg["label"],
                "type": cfg["type"],
            }
            for cfg in WIKI_CATEGORIES.values()
        ]
    }
