"""Pydantic models for Vibedia / Wikipedia API responses."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WikiArticleCard(BaseModel):
    """Compact card used in grids, search, and related lists."""

    title: str
    summary: str = ""
    thumbnail: Optional[str] = None
    url: str
    pageid: Optional[int] = None


class WikiArticleDetail(WikiArticleCard):
    """Full article view payload."""

    description: Optional[str] = None
    extract: str = ""
    related: List[WikiArticleCard] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)


class WikiHomeResponse(BaseModel):
    """Home magazine feed — one list per configured category."""

    sections: Dict[str, List[WikiArticleCard]]


class WikiTopicResponse(BaseModel):
    """Paginated topic listing."""

    topic: str
    label: str
    articles: List[WikiArticleCard]
    continue_token: Optional[str] = None
    has_more: bool = False


class WikiSearchResponse(BaseModel):
    """Search results."""

    query: str
    articles: List[WikiArticleCard]
