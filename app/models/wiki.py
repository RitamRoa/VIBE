"""Resolved visual payload for Vibedia article cards."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ImageType = Literal["thumbnail", "article_image", "editorial"]


class ResolvedImage(BaseModel):
    """
    Final visual for a card/article.

    Frontend never distinguishes sources beyond rendering:
    - thumbnail / article_image → <img>
    - editorial → EditorialCover component (local, no URL)
    """

    image_type: ImageType
    image_url: Optional[str] = None
    title: str
    category: str = "Knowledge"


class WikiArticleCard(BaseModel):
    """Compact card used in grids, search, and related lists."""

    title: str
    summary: str = ""
    thumbnail: Optional[str] = None
    url: str
    pageid: Optional[int] = None
    image: Optional[ResolvedImage] = None


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


class JourneyArticle(BaseModel):
    """Normalized Journey slide — never a raw Wikipedia payload."""

    id: str
    title: str
    summary: str = ""
    image: Optional[str] = None
    image_type: ImageType = "editorial"
    category: str = "Knowledge"
    wikipedia_url: str
    page_id: Optional[int] = None


class JourneyResponse(BaseModel):
    """One finite Journey issue (~20 slides). next_cursor is unused for endless scroll."""

    articles: List[JourneyArticle]
    next_cursor: Optional[str] = None
    title: str = "Journey"
    total: int = 0
    mode: str = "surprise"
    topics: List[str] = Field(default_factory=list)


