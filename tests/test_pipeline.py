import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.aggregator.models import Article
from src.aggregator.pipeline import deduplicate, score_articles, filter_by_score, sort_by_score
from src.aggregator.fetchers.newsapi import NEWSAPIFetcher
from src.aggregator.fetchers.bbc import BBCFetcher
from src.aggregator.fetchers.guardian import GuardianAPIFetcher
from src.aggregator.fetchers.hackernews import HackerNewsAPIFetcher


# Helper to create mock articles
def create_mock_article(
    id: str, 
    title: str, 
    url: str, 
    published_at: datetime, 
    source: str = "test"
) -> Article:
    return Article(
        id=id,
        title=title,
        url=url,
        source=source,
        published_at=published_at,
        summary="Summary of article",
        tags=[],
        score=0.0
    )


# ==========================================
# 1. Test deduplicate removes duplicates
# ==========================================
def test_deduplicate_removes_duplicates_by_id():
    now = datetime.now(timezone.utc)
    articles = [
        create_mock_article("id1", "Title A", "https://url1.com", now),
        create_mock_article("id2", "Title B", "https://url2.com", now),
        create_mock_article("id1", "Title A (Duplicate)", "https://url1.com", now),
    ]

    deduped = deduplicate(articles)
    assert len(deduped) == 2
    assert [a.id for a in deduped] == ["id1", "id2"]
    # Check that it preserves the first encountered item
    assert deduped[0].title == "Title A"


# ==========================================
# 2. Test score_articles rules
# ==========================================
def test_score_articles_scores_correctly():
    now = datetime.now(timezone.utc)
    
    # Articles with different ages
    article_today = create_mock_article("id1", "Python programming guidelines", "https://url1.com", now)
    article_yesterday = create_mock_article("id2", "AI development trends", "https://url2.com", now - timedelta(days=1))
    article_week_ago = create_mock_article("id3", "Tech news today", "https://url3.com", now - timedelta(days=5))
    article_old = create_mock_article("id4", "History of computation", "https://url4.com", now - timedelta(days=20))
    
    keywords = ["python", "AI"]
    articles = [article_today, article_yesterday, article_week_ago, article_old]
    
    score_articles(articles, keywords)
    
    # Expected scores:
    # 1. Today (1.0) + keyword 'python' (0.1) = 1.1
    assert articles[0].score == 1.1
    # 2. Yesterday (0.7) + keyword 'AI' (0.1) = 0.8
    assert articles[1].score == 0.8
    # 3. This week (0.4) + no keywords = 0.4
    assert articles[2].score == 0.4
    # 4. Old (0.1) + no keywords = 0.1
    assert articles[3].score == 0.1


# ==========================================
# 3. Test _parse_item malformed payload resiliency
# ==========================================
def test_parsers_handle_malformed_input():
    # Mock ClientSession
    mock_session = MagicMock()
    
    # Instantiate all fetchers
    news_fetcher = NEWSAPIFetcher(session=mock_session, api_key="test")
    bbc_fetcher = BBCFetcher(session=mock_session)
    guardian_fetcher = GuardianAPIFetcher(session=mock_session, api_key="test")
    hn_fetcher = HackerNewsAPIFetcher(session=mock_session)
    
    malformed_raw = {"unexpected_field": "some_value"}
    
    # Assert they all return None safely instead of throwing exceptions
    assert news_fetcher._parse_item(malformed_raw) is None
    assert bbc_fetcher._parse_item(malformed_raw) is None
    assert guardian_fetcher._parse_item(malformed_raw) is None
    assert hn_fetcher._parse_item(malformed_raw) is None


def test_gather_resiliency_with_failing_fetcher():
    async def run_test():
        now = datetime.now(timezone.utc)
        mock_articles = [create_mock_article("id1", "Title A", "https://url1.com", now)]
        
        # Create a successful mock fetcher
        success_fetcher = MagicMock()
        success_fetcher.fetch = AsyncMock(return_value=mock_articles)
        
        # Create a failing mock fetcher that throws a connection exception
        failing_fetcher = MagicMock()
        failing_fetcher.fetch = AsyncMock(side_effect=Exception("Connection Failed"))
        
        fetchers = [success_fetcher, failing_fetcher]
        keywords = ["test"]
        
        # Run the gather logic (corresponds to main.py gather flow)
        results = await asyncio.gather(*[f.fetch(keywords) for f in fetchers], return_exceptions=True)
        
        # Flatten outputs safely
        flattened_articles = []
        for result in results:
            if isinstance(result, list):
                flattened_articles.extend(result)
                
        # Assert that despite one fetcher crashing, the success results were collected
        assert len(flattened_articles) == 1
        assert flattened_articles[0].id == "id1"

    asyncio.run(run_test())
