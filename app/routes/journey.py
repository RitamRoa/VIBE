"""
Journey API routes — finite curated reading sessions.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import JOURNEY_LENGTH, list_journey_topic_ids
from app.models.wiki import JourneyResponse
from app.services.journey_service import journey_service
from app.services.wiki_service import WikiUpstreamError

router = APIRouter(tags=["journey"])


@router.get("/wiki/journey", response_model=JourneyResponse)
async def get_journey(
    mode: str = Query(
        "surprise",
        description="surprise | topics | explore",
    ),
    topics: Optional[str] = Query(
        None,
        description="Comma-separated topic ids (topics / explore source)",
    ),
    limit: int = Query(JOURNEY_LENGTH, ge=1, le=JOURNEY_LENGTH),
    exclude: Optional[str] = Query(
        None, description="Comma-separated article ids already shown"
    ),
    variation: Optional[str] = Query(
        None, description="Salt to vary ordering on Begin Again"
    ),
) -> JourneyResponse:
    """
    Fetch one finite Journey issue (~20 articles).

    Examples:
      /wiki/journey?mode=surprise&limit=20
      /wiki/journey?mode=topics&topics=finance,technology&limit=20
      /wiki/journey?mode=explore&topics=finance&limit=20
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
            exclude=exclude_list,
            variation=variation,
        )
    except WikiUpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wiki/journey/topics")
async def journey_topics():
    """List Journey-selectable intro topics (excludes random / neighbours)."""
    from app.config import get_category

    return {
        "topics": [
            {"id": tid, "label": (get_category(tid) or {}).get("label", tid.title())}
            for tid in list_journey_topic_ids()
        ]
    }
