import logging
import logging
import asyncio
import aiohttp
from typing import Any
from datetime import datetime, UTC
from urllib.parse import urljoin

from src.aggregator.fetchers.base import BaseFetcher
from src.aggregator.models import Article
from src.aggregator.utils import generate_article_id


logging.basicConfig(
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # Custom format removing milliseconds
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


class HackerNewsAPIFetcher(BaseFetcher): 
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session
        self.base_url = "https://hacker-news.firebaseio.com/v0/"
        self.semaphore = asyncio.Semaphore(10)


    @property
    def source_name(self) -> str:
        return "hacker_news"

    async def _fetch_single(self, keywords: list[str], url:str) -> Article | None:
        async with self.semaphore:
            try:
                async with asyncio.timeout(10):            
                    async with self.session.get(url=url) as response:
                        response.raise_for_status()
                        data = await response.json()

                        title=data.get("title", "").lower()
                        text=data.get("text", "").lower()
                        url_lower = data.get("url", "").lower()
                        if any (
                            kw.lower() in title or kw.lower() in url_lower or kw.lower() in text
                            for kw in keywords
                        ):                        
                            article = self._parse_item(data)
                            if article:
                                return article
            except asyncio.TimeoutError:
                logger.error("Hacker News single story request timed out after 10 seconds")
                return None
            except Exception as exc:
                logger.error(f"Hacker News API fetch failed with {exc}")
                return None


    async def fetch(self, keywords: list[str]) -> list[Article]:
        
        if not keywords:
            return []

        top_stories_url = urljoin(self.base_url, "topstories.json")        

        try:
            async with asyncio.timeout(10):            
                async with self.session.get(url=top_stories_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    tasks = []
                    for id in data[:30]:
                        single_story_url = urljoin(self.base_url, f"item/{id}.json")
                        task = asyncio.create_task(
                            coro=self._fetch_single(keywords=keywords, url = single_story_url)                           
                        )
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    articles = []
                    for r in results:
                        if isinstance(r, Article):
                            articles.append(r)
                    return articles
        except asyncio.TimeoutError:
            logger.error("Hacker News top 30 stories request timed out after 10 seconds")
            return []

        except Exception as exc:
            logger.error(f"Hacker News API fetch failed with {exc}")
            return []


    def _parse_item(self, raw: dict[str, Any]) -> Article:
        url = raw.get("url")
        if not url:
            return None

        timestamp_str = raw.get("time")
        try:
            published_at = datetime.fromtimestamp(timestamp_str, UTC)
        except (AttributeError, ValueError):
            return None

        return Article(
            id=generate_article_id(url),
            title=raw.get("title", ""),
            url=url,
            source=self.source_name,
            published_at=published_at,
            summary=raw.get("text", ""),
            tags=[],
            score=0.0
        )