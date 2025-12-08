"""News service for fetching Ipswich local news from The Local News RSS feed."""

import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsItem
from app.models.story import StoryChapter

logger = logging.getLogger(__name__)

# The Local News RSS feed URL
IPSWICH_NEWS_RSS_URL = "https://thelocalnews.news/feed/"

# User agent for RSS fetching
USER_AGENT = "IpswichStoryWeaver/1.0 (RSS Reader)"


class NewsService:
    """Service for fetching and managing Ipswich news items."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def fetch_and_update_ipswich_news(self) -> list[NewsItem]:
        """Fetch news from The Local News RSS feed and update database.

        Filters for Ipswich-related articles only.

        Returns:
            List of NewsItem objects that were created or updated.
        """
        logger.info(f"Fetching Ipswich news from RSS: {IPSWICH_NEWS_RSS_URL}")

        try:
            rss_content = await self._fetch_rss(IPSWICH_NEWS_RSS_URL)
            if not rss_content:
                logger.warning("Failed to fetch RSS feed")
                return []

            articles = self._parse_rss_feed(rss_content)
            logger.info(f"Parsed {len(articles)} Ipswich articles from RSS feed")

            updated_items = []
            for article_data in articles:
                news_item = await self._upsert_news_item(article_data)
                if news_item:
                    updated_items.append(news_item)

            await self.db.commit()
            logger.info(f"Successfully updated {len(updated_items)} news items")
            return updated_items

        except Exception as e:
            logger.error(f"Error fetching Ipswich news: {e}")
            await self.db.rollback()
            return []

    async def _fetch_rss(self, url: str) -> Optional[str]:
        """Fetch RSS feed content."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=15.0,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching RSS {url}: {e}")
            return None

    def _parse_rss_feed(self, rss_content: str) -> list[dict]:
        """Parse RSS feed and extract Ipswich-related articles.

        Args:
            rss_content: Raw RSS XML content.

        Returns:
            List of dictionaries with article data.
        """
        soup = BeautifulSoup(rss_content, "xml")
        articles = []

        for item in soup.find_all("item"):
            # Check if this article is about Ipswich
            categories = [cat.get_text(strip=True).lower() for cat in item.find_all("category")]
            title = item.find("title").get_text(strip=True) if item.find("title") else ""

            # Only include if Ipswich is in categories or title
            is_ipswich = "ipswich" in categories or "ipswich" in title.lower()
            if not is_ipswich:
                continue

            # Skip obituaries, death notices, sensitive content, and politics
            title_lower = title.lower()
            skip_keywords = [
                # Obituaries and deaths
                "obituary", "obituaries", "death", "dies", "died",
                "memorial", "funeral", "passed away", "in memoriam",
                # Crime and police
                "police log", "arrest", "charged with", "fatal",
                # Politics
                "campaign", "election", "candidate", "endorsement", "endorses",
                "democrat", "republican", "congressional", "senator", "governor",
                "ballot", "vote", "voting", "primary", "caucus", "political",
            ]
            if any(keyword in title_lower for keyword in skip_keywords):
                logger.debug(f"Skipping filtered article: {title[:50]}")
                continue
            skip_categories = [
                "obituaries", "police", "crime",
                "politics", "election", "elections",
            ]
            if any(keyword in categories for keyword in skip_categories):
                logger.debug(f"Skipping article in filtered category: {title[:50]}")
                continue

            # Extract article data
            link = item.find("link").get_text(strip=True) if item.find("link") else None
            if not link:
                continue

            # Get description/summary
            description = ""
            desc_elem = item.find("description")
            if desc_elem:
                # Description often contains HTML, parse it
                desc_html = desc_elem.get_text()
                desc_soup = BeautifulSoup(desc_html, "html.parser")
                description = desc_soup.get_text(strip=True)
                # Clean up and truncate
                description = re.sub(r'\s+', ' ', description)
                if len(description) > 500:
                    description = description[:497] + "..."

            # Get author
            author = None
            creator = item.find("dc:creator")
            if creator:
                author = creator.get_text(strip=True)

            # Get published date from URL (more reliable than RSS pubDate)
            # URL format: https://thelocalnews.news/YYYY/MM/DD/article-slug/
            published_at = None
            article_date = None
            url_date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', link)
            if url_date_match:
                try:
                    year, month, day = map(int, url_date_match.groups())
                    article_date = date(year, month, day)
                    published_at = datetime(year, month, day, 12, 0, 0)  # Noon on that day
                except Exception:
                    pass

            # Fallback to RSS pubDate if URL parsing failed
            if published_at is None:
                pub_date = item.find("pubDate")
                if pub_date:
                    try:
                        dt = parsedate_to_datetime(pub_date.get_text(strip=True))
                        published_at = dt.replace(tzinfo=None)
                        article_date = published_at.date()
                    except Exception:
                        pass

            # Include articles from today and yesterday (24-hour window for story generation)
            today = date.today()
            yesterday = today - timedelta(days=1)
            if article_date is None or article_date < yesterday:
                logger.debug(f"Skipping article older than yesterday ({article_date}): {title[:50]}")
                continue

            articles.append({
                "headline": title[:500],
                "summary": description or title,
                "article_url": link,
                "author": author[:200] if author else None,
                "published_at": published_at,
                "category_label": "Ipswich",
            })

        return articles[:10]  # Limit to 10 most recent

    async def get_recent_news_items(self, limit: int = 5) -> list[NewsItem]:
        """Get today's news items from database.

        Args:
            limit: Maximum number of items to return.

        Returns:
            List of NewsItem objects from today only.
        """
        today = date.today()
        result = await self.db.execute(
            select(NewsItem)
            .where(NewsItem.published_at >= datetime.combine(today, datetime.min.time()))
            .where(NewsItem.published_at < datetime.combine(today, datetime.max.time()))
            .order_by(
                desc(NewsItem.published_at),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    def _get_article_date_from_url(self, url: str) -> Optional[date]:
        """Extract the actual publication date from the article URL.

        URL format: https://thelocalnews.news/YYYY/MM/DD/article-slug/
        """
        if not url:
            return None
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if match:
            try:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
            except Exception:
                pass
        return None

    async def get_news_for_date(self, target_date: date, limit: int = 5) -> list[NewsItem]:
        """Get news items within 24-hour window ending at target date.

        This includes articles from target_date AND the previous day, to capture
        late evening articles that may have been published after the previous
        day's story automation ran.

        Excludes articles that were already used in recent stories to prevent
        the same news from appearing in consecutive days' stories.

        Args:
            target_date: The date to get news for.
            limit: Maximum number of items to return.

        Returns:
            List of NewsItem objects from target_date and previous day,
            excluding any already used in recent stories.
        """
        # Get IDs of news items already used in recent stories (last 7 days)
        used_ids = await self._get_recently_used_news_ids()

        # Fetch recent items (wider window to account for RSS timestamp issues)
        # Then filter by actual article date from URL
        result = await self.db.execute(
            select(NewsItem)
            .order_by(desc(NewsItem.published_at))
            .limit(50)  # Get more items to filter from
        )
        all_items = list(result.scalars().all())

        # Include articles from target_date and the previous day (24-hour window)
        # Exclude articles already used in recent stories
        previous_day = target_date - timedelta(days=1)
        matching_items = []
        for item in all_items:
            # Skip if already used in a recent story
            if item.id in used_ids:
                logger.debug(f"Skipping already-used article: {item.headline[:50]}")
                continue

            article_date = self._get_article_date_from_url(item.article_url)
            if article_date in (target_date, previous_day):
                matching_items.append(item)
                if len(matching_items) >= limit:
                    break

        return matching_items

    async def _get_recently_used_news_ids(self, days: int = 7) -> set[int]:
        """Get IDs of news items used in stories from the last N days.

        Args:
            days: Number of days to look back.

        Returns:
            Set of news item IDs that have been used recently.
        """
        cutoff_date = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(StoryChapter.used_news_item_ids)
            .where(StoryChapter.chapter_date >= cutoff_date)
        )
        rows = result.scalars().all()

        used_ids: set[int] = set()
        for ids_list in rows:
            if ids_list:
                used_ids.update(ids_list)

        return used_ids

    async def get_news_items_by_ids(self, ids: list[int]) -> list[NewsItem]:
        """Fetch specific news items by their IDs."""
        if not ids:
            return []

        result = await self.db.execute(
            select(NewsItem).where(NewsItem.id.in_(ids))
        )
        return list(result.scalars().all())

    async def _upsert_news_item(self, article_data: dict) -> Optional[NewsItem]:
        """Create or update a news item based on article URL.

        Args:
            article_data: Dictionary with article data.

        Returns:
            NewsItem object or None.
        """
        try:
            # Check if article already exists
            result = await self.db.execute(
                select(NewsItem).where(NewsItem.article_url == article_data["article_url"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing item
                existing.headline = article_data["headline"]
                existing.summary = article_data["summary"]
                if article_data.get("author"):
                    existing.author = article_data["author"]
                if article_data.get("published_at"):
                    existing.published_at = article_data["published_at"]
                existing.fetched_at = datetime.utcnow()
                return existing
            else:
                # Create new item
                news_item = NewsItem(
                    headline=article_data["headline"],
                    summary=article_data["summary"],
                    article_url=article_data["article_url"],
                    author=article_data.get("author"),
                    category_label=article_data.get("category_label", "Ipswich"),
                    published_at=article_data.get("published_at"),
                    fetched_at=datetime.utcnow(),
                )
                self.db.add(news_item)
                await self.db.flush()
                return news_item

        except Exception as e:
            logger.error(f"Error upserting news item: {e}")
            return None
