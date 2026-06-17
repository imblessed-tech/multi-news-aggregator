import logging
import logging
import asyncio
import aiohttp
from typing import Any
from datetime import datetime

from src.aggregator.fetchers.base import BaseFetcher
from src.aggregator.models import Article
from src.aggregator.utils import generate_article_id


logging.basicConfig(
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # Custom format removing milliseconds
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


class NEWSAPIFetcher(BaseFetcher): 
    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self.session = session
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/everything"

    @property
    def source_name(self) -> str:
        return "newsapi"

    async def fetch(self, keywords: list[str]) -> list[Article]:
        if not self.api_key:
            logger.error("NewsAPI key is missiong in the config")
            return []

        if not keywords:
            return []

        query = " OR ".join(keywords) 
        params = { 
            "q": query,
            "apiKey": self.api_key
        }
        semaphore = asyncio.Semaphore(5)
        try:
            async with asyncio.timeout(10):
                async with semaphore:
                    async with self.session.get(self.base_url, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()

                        if data.get("status") != "ok":
                            logger.error(f"NewsAPI returned non-ok status: {data.get("status")})")
                            return []

                        articles = []
                        for item in data.get("articles", []):
                            article = self._parse_item(item)
                            if article:
                                articles.append(article)
                        return articles
        except asyncio.TimeoutError:
            logger.error("NewsAPI request timed out after 10 seconds.")
            return []
        
        except Exception as exc:
            logger.error(f"NewsAPI fetch failed: {exc}")
            return []
        
                

    def _parse_item(self, raw: dict[str, Any]) -> Article | None:
        url = raw.get("url")
        if not url:
            return None
        
        published_at_str = raw.get("publishedAt")
        try:
            published_at = datetime.fromisoformat(
                published_at_str.replace("Z", "+00:00")
            )
        except (AttributeError, ValueError):
            return None
        
        return Article(
                id=generate_article_id(url),
                title=raw.get("title", ""),
                url=url,
                source=self.source_name,
                published_at=published_at,
                summary=raw.get("description") or raw.get("content") or "",
                tags=[],
                score=0.0
            )