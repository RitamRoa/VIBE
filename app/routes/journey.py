"""
Journey API routes — curated reading sessions.

Mounted under /wiki so the frontend keeps a single Wikipedia proxy surface.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import JOURNEY_DEFAULT_LIMIT, list_journey_topic_ids
from app.models.wiki import JourneyResponse
from app.services.journey_service import journey_service
from app.services.wiki_service import WikiUpstreamError

router = APIRouter(tags=["journey"])


@router.get("/wiki/journey", response_model=JourneyResponse)
async def get_journey(
    mode: str = Query(
        "surprise",
        description="surprise | topics",
    ),
    topics: Optional[str] = Query(
        None,
        description="Comma-separated topic ids when mode=topics",
    ),
    limit: int = Query(JOURNEY_DEFAULT_LIMIT, ge=1, le=40),
    cursor: Optional[str] = Query(
        None, description="Opaque next_cursor from a previous batch"
    ),
    exclude: Optional[str] = Query(
        None, description="Comma-separated article ids already shown"
    ),
) -> JourneyResponse:
    """
    Fetch a Journey batch.

    Examples:
      /wiki/journey?mode=surprise&limit=20
      /wiki/journey?mode=topics&topics=finance,technology&limit=20
    """
    topic_list: Optional[List[str]] = None
    if topics:
        topic_list = [t.strip() for t in topics.split(",") if t.strip()]

    exclude_list: Optional[List[str]] = None
    if exclude:
        exclude_list = [e.strip() for e in exclude.split(",") if e.strip()]

    try:
        return await journey_service.get_journey(
            mode=mode,
            topics=topic_list,
            limit=limit,
            cursor=cursor,
            exclude=exclude_list,
        )
    except WikiUpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wiki/journey/topics")
async def journey_topics():
    """List Journey-selectable topics (excludes random)."""
    from app.config import get_category

    return {
        "topics": [
            {"id": tid, "label": (get_category(tid) or {}).get("label", tid.title())}
            for tid in list_journey_topic_ids()
        ]
    }
