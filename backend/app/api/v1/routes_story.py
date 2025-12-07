"""Story chapter API routes (read-only public endpoints)."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.story import StoryChapter
from app.schemas.news import NewsItemBrief
from app.schemas.story import (
    GenerateStoryResponse,
    StoryArchiveItem,
    StoryArchiveResponse,
    StoryChapterResponse,
    StoryContextResponse,
)
from app.services.context_builder import ContextBuilder
from app.services.story_engine import StoryEngine, TemplateStoryGenerator
from app.services.llm_story_generator import LLMStoryGeneratorWithFallback

router = APIRouter()
settings = get_settings()


def get_story_generator():
    """Get the appropriate story generator based on configuration."""
    fallback = TemplateStoryGenerator()

    if settings.use_llm_for_stories and settings.anthropic_api_key:
        return LLMStoryGeneratorWithFallback(
            api_key=settings.anthropic_api_key,
            fallback_generator=fallback,
            model=settings.llm_model,
        )

    return fallback


@router.get("/latest", response_model=Optional[StoryChapterResponse])
async def get_latest_story(
    db: AsyncSession = Depends(get_db),
) -> Optional[StoryChapterResponse]:
    """Get the most recent story chapter."""
    result = await db.execute(
        select(StoryChapter).order_by(desc(StoryChapter.chapter_date)).limit(1)
    )
    chapter = result.scalar_one_or_none()

    if not chapter:
        return None

    # Get news items that were used
    context_builder = ContextBuilder(db)
    news_items = None
    if chapter.used_news_item_ids:
        news_items = await context_builder.get_news_items_by_ids(
            chapter.used_news_item_ids
        )

    return StoryChapterResponse(
        id=chapter.id,
        chapter_date=chapter.chapter_date,
        title=chapter.title,
        body=chapter.body,
        weather_summary=chapter.weather_summary,
        tide_state=chapter.tide_state,
        season=chapter.season,
        month_name=chapter.month_name,
        day_of_week=chapter.day_of_week,
        used_news_item_ids=chapter.used_news_item_ids,
        created_at=chapter.created_at,
        news_items=news_items,
    )


@router.get("/date/{chapter_date}", response_model=StoryChapterResponse)
async def get_story_by_date(
    chapter_date: date,
    db: AsyncSession = Depends(get_db),
) -> StoryChapterResponse:
    """Get the story chapter for a specific date."""
    result = await db.execute(
        select(StoryChapter).where(StoryChapter.chapter_date == chapter_date)
    )
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(status_code=404, detail="No story found for this date")

    # Get news items that were used
    context_builder = ContextBuilder(db)
    news_items = None
    if chapter.used_news_item_ids:
        news_items = await context_builder.get_news_items_by_ids(
            chapter.used_news_item_ids
        )

    return StoryChapterResponse(
        id=chapter.id,
        chapter_date=chapter.chapter_date,
        title=chapter.title,
        body=chapter.body,
        weather_summary=chapter.weather_summary,
        tide_state=chapter.tide_state,
        season=chapter.season,
        month_name=chapter.month_name,
        day_of_week=chapter.day_of_week,
        used_news_item_ids=chapter.used_news_item_ids,
        created_at=chapter.created_at,
        news_items=news_items,
    )


@router.get("/archive", response_model=StoryArchiveResponse)
async def get_story_archive(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> StoryArchiveResponse:
    """Get paginated list of story chapters."""
    # Get total count
    count_result = await db.execute(select(func.count(StoryChapter.id)))
    total = count_result.scalar() or 0

    # Get paginated chapters
    offset = (page - 1) * page_size
    result = await db.execute(
        select(StoryChapter)
        .order_by(desc(StoryChapter.chapter_date))
        .offset(offset)
        .limit(page_size)
    )
    chapters = result.scalars().all()

    # Convert to archive items
    items = [
        StoryArchiveItem(
            id=ch.id,
            chapter_date=ch.chapter_date,
            title=ch.title,
            snippet=ch.body[:100] + "..." if len(ch.body) > 100 else ch.body,
            season=ch.season,
        )
        for ch in chapters
    ]

    has_more = (offset + page_size) < total

    return StoryArchiveResponse(
        chapters=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/context/today", response_model=StoryContextResponse)
async def get_today_context(
    db: AsyncSession = Depends(get_db),
) -> StoryContextResponse:
    """Get today's story generation context (weather, tides, season, news)."""
    context_builder = ContextBuilder(db)
    context = await context_builder.build_context(date.today(), include_news=True)

    # Convert news items to brief format for response
    news_items_brief = [
        NewsItemBrief(
            id=n.id,
            headline=n.headline,
            summary=n.summary[:200] + "..." if len(n.summary) > 200 else n.summary,
            article_url=n.article_url,
        )
        for n in context.news_items
    ]

    return StoryContextResponse(
        weather=context.weather,
        tide=context.tide,
        season=context.season,
        news_items=news_items_brief,
    )


@router.post("/generate-today", response_model=GenerateStoryResponse)
async def generate_today_story(
    force: bool = Query(default=False, description="Force regeneration if chapter exists"),
    target_date: Optional[date] = Query(default=None, description="Generate for a specific date (default: today)"),
    db: AsyncSession = Depends(get_db),
) -> GenerateStoryResponse:
    """Generate today's story chapter.

    This endpoint is primarily for development and testing.
    In production, story generation should be triggered by a scheduled task.
    """
    if not settings.enable_manual_generation:
        raise HTTPException(
            status_code=403,
            detail="Manual story generation is disabled",
        )

    today = target_date or date.today()

    # Check if chapter already exists
    result = await db.execute(
        select(StoryChapter).where(StoryChapter.chapter_date == today)
    )
    existing = result.scalar_one_or_none()

    if existing and not force:
        # Get news items for existing chapter
        context_builder = ContextBuilder(db)
        news_items = None
        if existing.used_news_item_ids:
            news_items = await context_builder.get_news_items_by_ids(
                existing.used_news_item_ids
            )

        return GenerateStoryResponse(
            success=False,
            message=f"Story already exists for {today}. Use force=true to regenerate.",
            chapter=StoryChapterResponse(
                id=existing.id,
                chapter_date=existing.chapter_date,
                title=existing.title,
                body=existing.body,
                weather_summary=existing.weather_summary,
                tide_state=existing.tide_state,
                season=existing.season,
                month_name=existing.month_name,
                day_of_week=existing.day_of_week,
                used_news_item_ids=existing.used_news_item_ids,
                created_at=existing.created_at,
                news_items=news_items,
            ),
        )

    # Build context and generate story
    context_builder = ContextBuilder(db)
    context = await context_builder.build_context(today)

    # Get the appropriate story generator (LLM or template-based)
    generator = get_story_generator()
    engine = StoryEngine(db, generator=generator)
    chapter = await engine.generate_story_for_date(
        context=context,
        target_date=today,
        force_regenerate=force,
    )

    await db.commit()

    # Fetch news items for response
    news_items = None
    if chapter.used_news_item_ids:
        news_items = await context_builder.get_news_items_by_ids(
            chapter.used_news_item_ids
        )

    return GenerateStoryResponse(
        success=True,
        message=f"Story {'regenerated' if existing else 'generated'} for {today}",
        chapter=StoryChapterResponse(
            id=chapter.id,
            chapter_date=chapter.chapter_date,
            title=chapter.title,
            body=chapter.body,
            weather_summary=chapter.weather_summary,
            tide_state=chapter.tide_state,
            season=chapter.season,
            month_name=chapter.month_name,
            day_of_week=chapter.day_of_week,
            used_news_item_ids=chapter.used_news_item_ids,
            created_at=chapter.created_at,
            news_items=news_items,
        ),
    )


@router.get("/feed.xml", response_class=Response)
async def get_rss_feed(
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Get RSS feed of recent stories."""
    import html
    from datetime import datetime

    # Get recent stories
    result = await db.execute(
        select(StoryChapter)
        .order_by(desc(StoryChapter.chapter_date))
        .limit(20)
    )
    chapters = result.scalars().all()

    # Build RSS XML
    site_url = "https://ipswichstoryweaver.com"

    items_xml = ""
    for ch in chapters:
        # Format date as RFC 822
        pub_date = datetime.combine(ch.chapter_date, datetime.min.time())
        pub_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Escape HTML entities in content
        title_escaped = html.escape(ch.title)
        body_escaped = html.escape(ch.body)

        # Convert newlines to <br> for description
        body_html = body_escaped.replace("\n\n", "</p><p>").replace("\n", "<br/>")
        body_html = f"<p>{body_html}</p>"

        items_xml += f"""
    <item>
      <title>{title_escaped}</title>
      <link>{site_url}/chapter/{ch.chapter_date}</link>
      <guid isPermaLink="true">{site_url}/chapter/{ch.chapter_date}</guid>
      <pubDate>{pub_date_str}</pubDate>
      <description><![CDATA[{body_html}]]></description>
    </item>"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Ipswich Story Weaver</title>
    <link>{site_url}</link>
    <description>Daily tales woven from weather, tides, and local news in Ipswich, Massachusetts</description>
    <language>en-us</language>
    <atom:link href="{site_url}/api/story/feed.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
    <image>
      <url>{site_url}/favicon.svg</url>
      <title>Ipswich Story Weaver</title>
      <link>{site_url}</link>
    </image>{items_xml}
  </channel>
</rss>"""

    return Response(
        content=rss_xml,
        media_type="application/rss+xml",
        headers={"Content-Type": "application/rss+xml; charset=utf-8"}
    )
