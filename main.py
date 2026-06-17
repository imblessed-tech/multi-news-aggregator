import aiohttp
import argparse
import asyncio
import logging
import json

from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

from src.aggregator.models import Article
from src.aggregator.fetchers.bbc import BBCFetcher
from src.aggregator.fetchers.guardian import GuardianAPIFetcher
from src.aggregator.fetchers.hackernews import HackerNewsAPIFetcher
from src.aggregator.fetchers.newsapi import NEWSAPIFetcher
from src.aggregator.pipeline import (
    deduplicate,
    score_articles,
    filter_by_score,
    sort_by_score
)
from config import GUARDIAN_API_KEY, NEWS_API_KEY


logging.basicConfig(
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H-%M-%S',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Multi-news aggregator")

    parser.add_argument("-k", "--keywords", nargs="+", required=True, help="List of comma separated keywords.")
    parser.add_argument("-m", "--min_score", type=float, default=0.3, required=False, help="The minimum score threshold to filter articles.")
    parser.add_argument("-o", "--output_dir", type=str, default="output", required=False, help="The directory where news results are saved.")

    args = parser.parse_args()

    keywords = []
    for kw in args.keywords:
        keywords.extend([k.strip() for k in kw.split(",") if k.strip()])

    try:
        async with asyncio.timeout(100):
            async with aiohttp.ClientSession() as async_session:
                fetchers = [
                    BBCFetcher(session=async_session),
                    GuardianAPIFetcher(session=async_session, api_key=GUARDIAN_API_KEY),
                    HackerNewsAPIFetcher(session=async_session),
                    NEWSAPIFetcher(session=async_session, api_key=NEWS_API_KEY)
                ]

                results = await asyncio.gather(*[f.fetch(keywords) for f in fetchers], return_exceptions=True)

                flattened_articles = []
                for result in results:
                    if isinstance(result, list):
                        flattened_articles.extend(result)
                    else:
                        logger.error(f"A fetcher failed during execution: {result}")

                dededup_articles = deduplicate(flattened_articles)
                rescored_articles = score_articles(dededup_articles, keywords)
                filtered_articles = filter_by_score(rescored_articles, args.min_score)
                sorted_articles = sort_by_score(filtered_articles)

                # Save the filtered and sorted articles to JSON
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                file_name = datetime.now(timezone.utc).strftime("news_%Y-%m-%d_%H-%M.json")
                file_path = output_dir / file_name

                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(
                        [a.to_dict() for a in sorted_articles],
                        file,
                        indent=4,
                        default=str,
                    )
                logger.info(f"Successfully saved aggregated news to {file_path}")

                # Tracking Statistics
                source_stats = {}
                
                for article in flattened_articles:
                    stats = source_stats.setdefault(article.source, {"fetched": 0, "filtered": 0})
                    stats["fetched"] += 1
                    
                for article in filtered_articles:
                    if article.source in source_stats:
                        source_stats[article.source]["filtered"] += 1

                # 8. Print Console Summary Table
                row_template = "{:<20} | {:<16} | {:<16}"
                print("\n" + "="*56)
                print(row_template.format("Source Name", "Articles Fetched", "Passed Filter"))
                print("-" * 56)
                for source, counts in source_stats.items():
                    print(row_template.format(source, counts["fetched"], counts["filtered"]))
                
                # Calculate Totals
                total_fetched = sum(c["fetched"] for c in source_stats.values())
                total_filtered = sum(c["filtered"] for c in source_stats.values())
                print("-" * 56)
                print(row_template.format("Total", total_fetched, total_filtered))
                print("="*56 + "\n")

    except asyncio.TimeoutError:
        print("Aggregation engine timed out after 100 seconds.")
    except Exception as e:
        print(f"An unexpected critical failure occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())





