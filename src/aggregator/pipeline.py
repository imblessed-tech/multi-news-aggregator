import logging

from datetime import datetime, timezone
from src.aggregator.models import Article


logging.basicConfig(
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H-%M-%s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


def deduplicate(articles: list[Article]) -> list[Article]:
    seen = set()
    unique_articles = []
    for article in articles:
        if article.id not in seen:
            seen.add(article.id)
            unique_articles.append(article)
    return unique_articles
    
def score_articles(articles: list[Article], keywords: list[str]) -> list[Article]:
    current_datetime = datetime.now(timezone.utc)
    for article in articles:
        score = 0.0

        if not article.published_at:
            logger.warning(f"Skipping article {getattr(article, 'id', '')}: Missing publication date.")
            continue

        try:
            date_diff = int((current_datetime - article.published_at).days)
        except TypeError as e:
            logger.error(f"Skipping article due to unexpected type mismatch: {e}")
            continue

        if date_diff < 0:
            logger.warning(f"Invalid date for article published in the future: {article.published_at}")
            continue
        elif date_diff == 0:
            score += 1.0
        elif date_diff == 1:
            score += 0.7
        elif 2 <= date_diff <= 7:
            score += 0.4
        else:
            score += 0.1
        
        matches = sum(1 for kw in keywords if kw.lower() in article.title.lower())
        score += 0.1 * matches

        article.score = round(score, 1)
    return articles


def filter_by_score(articles, min_score: float = 0.3) -> list[Article]:

    return [
        article for article in articles 
        if article.score >= min_score
    ]


def sort_by_score(articles: list[Article]) -> list[Article]:
    sorted_articles = sorted(
        articles,
        key= lambda article: article.score,
        reverse=True
    )
    return sorted_articles
