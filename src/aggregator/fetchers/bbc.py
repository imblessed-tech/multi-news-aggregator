import logging
import logging
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any
from datetime import datetime

from src.aggregator.fetchers.base import BaseFetcher
from src.aggregator.models import Article
from src.aggregator.utils import generate_article_id

logging.basicConfig(
    format= '%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H-%M-%S',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

class BBCFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session
        self.base_url = "https://feeds.bbci.co.uk/news/rss.xml"

    @property
    def source_name(self) -> str:
        return "bbc"

    async def fetch(self, keywords: list[str]) -> list[Article]:
        if not keywords:
            return []

        semaphore = asyncio.Semaphore(5)

        try:
            async with asyncio.timeout(10):
                async with semaphore:
                    async with self.session.get(self.base_url) as response:
                        response.raise_for_status()
                        
                        xml_data = await response.text()
                        root = ET.fromstring(xml_data)

                        articles = []
                        for item in root.findall("./channel/item"):

                            title = item.findtext("title", "")
                            description = item.findtext("description", "")

                            title_lower = title.lower()
                            description_lower = description.lower()

                            if any(kw.lower() in title_lower 
                                    or kw.lower() in description_lower
                                    for kw in keywords):
                                item_dict = {
                                    "title": title,
                                    "link": item.findtext("link", ""),
                                    "description": description,
                                    "pubDate": item.findtext("pubDate", "")
                                }

                                article = self._parse_item(item_dict)
                                if article:
                                    articles.append(article)
                        return articles

        except asyncio.TimeoutError:
            logger.error("BBC News request timed out after 10 seconds.")
            return []
        
        except Exception as exc:
            logger.error(f"BBC News fetch failed: {exc}")
            return []


    def _parse_item(self, raw: dict[str, Any]) -> Article | None:
        url = raw.get("link")
        if not url:
            return None
        url = url.split('?')[0]
        
        published_at_str = raw.get("pubDate")
        
        try:
            published_at = parsedate_to_datetime(published_at_str)
        except (AttributeError, ValueError):
            published_at = None
        
        return Article(
            id=generate_article_id(url),
            title=raw.get("title", ""),
            url=url,
            source=self.source_name,
            published_at=published_at,
            summary=raw.get("description") or "",
            tags=[],
            score=0.0
        )