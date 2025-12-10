"""Admin API routes (internal/development use only).

These endpoints are for development and administrative purposes.
Protected by API key authentication in production.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.news import RefreshNewsResponse
from app.services.news_service import NewsService

router = APIRouter()
settings = get_settings()


async def verify_admin_api_key(x_api_key: str = Header(None)) -> str:
    """Verify the admin API key.

    If ADMIN_API_KEY is not set, allows access (development mode).
    If set, requires matching X-API-Key header.
    """
    if not settings.admin_api_key:
        # No API key configured - allow access (dev mode)
        return "dev-mode"

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
        )

    if x_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return x_api_key


@router.post("/refresh-news", response_model=RefreshNewsResponse)
async def refresh_ipswich_news(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_admin_api_key),
) -> RefreshNewsResponse:
    """Refresh Ipswich news from The Local News.

    This endpoint triggers a scrape of the Ipswich category page
    and updates the news_items database table.

    For production use, this should be called via a scheduled task
    rather than a public endpoint.
    """
    news_service = NewsService(db)
    updated_items = await news_service.fetch_and_update_ipswich_news()

    return RefreshNewsResponse(
        success=True,
        message=f"Successfully refreshed Ipswich news from The Local News",
        items_updated=len(updated_items),
    )
