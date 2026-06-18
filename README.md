# Async Multi-Source News Aggregator

A concurrent command-line application designed to pull, filter, score, and persist news articles from multiple API and RSS feed endpoints asynchronously.

The system pulls live articles concurrently, aggregates them safely in memory, resolves duplicate submissions, and evaluates matching relevancy scores before saving them as a structured JSON dump.

## Context & Purpose

In today's fast-paced tech and business landscape, staying updated across multiple channels means manually scanning RSS feeds, news API results, and platform forums. For developers, analysts, or automated ingestion pipelines, doing this programmatically usually leads to writing brittle, sequential scripts that fail if a single feed is offline, or bottlenecking when making dozens of external API calls.

This project solves these operational bottlenecks by providing a unified, concurrent, and highly resilient news aggregation pipeline. It pulls and normalizes raw stories from diverse channels, resolves duplicates, filters noise, and scores content based on custom parameters—all within seconds.

In practice, this tool serves as a reliable data ingestion layer for automated newsletters, technology-tracking Slack integrations, and internal intelligence dashboards. It is also well-suited to act as a pre-processing utility for AI workflows, feeding clean, structured news texts directly into retrieval-augmented generation (RAG) embedding pipelines.

## Key Engineering Features

*   **Concurrent Fetching via Asyncio**: Leverages Python's `asyncio` and `aiohttp` to request data from all news sources concurrently, ensuring the aggregation run completes in under 5 seconds regardless of source counts.
*   **Interface Contracts (ABCs)**: Implements an abstract contract class `BaseFetcher` (using `abc.ABC` and `@abstractmethod`) to guarantee consistency across all fetchers.
*   **Concurrency Throttling**: Limits concurrent sub-requests dynamically (e.g. during Hacker News individual story detail fetches) using an `asyncio.Semaphore` set to a maximum of 10 concurrent requests to prevent rate-limiting or network choking.
*   **Time-Out Wrappers**: Each API and RSS feed request is safely guarded by `asyncio.timeout(10)` limits to prevent slow network responses from hanging the main execution.
*   **Partial Failure Resilience**: Handles fetch errors gracefully at a per-source level. Utilizing `asyncio.gather(..., return_exceptions=True)` along with custom fallback exception filters guarantees that if one fetcher fails, the remaining active sources are still aggregated safely.
*   **Deduplication and Scoring**:
    *   Preserves insertion order during deduplication by indexing unique URL hashes inside a dictionary.
    *   Calculates dynamic scoring based on publication recency (sliding scale from 1.0 to 0.1) and keyword matching density in the title (0.1 per hit).

---

## Directory Structure

```text
news_aggregator/
├── src/
│   └── aggregator/
│       ├── __init__.py
│       ├── models.py         # Article dataclass
│       ├── fetchers/
│       │   ├── __init__.py
│       │   ├── base.py       # Abstract Base Fetcher
│       │   ├── newsapi.py    # NewsAPI crawler
│       │   ├── bbc.py        # BBC RSS XML scraper
│       │   ├── guardian.py   # Guardian API crawler
│       │   └── hackernews.py # HackerNews Firebase API client
│       ├── pipeline.py       # Scoring and sorting routines
│       └── storage.py        # Persistence routines (JSON exporter)
├── tests/
│   └── test_pipeline.py      # Automated tests
├── main.py                  # CLI Coordinator
├── config.py                 # Key binding mapping
├── .env.example              # Environment key templates
├── requirements.txt         # Project dependencies
└── README.md
```

---

## Installation & Setup

### 1. Set up Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Credentials
Copy the environment template:
```powershell
cp .env.example .env
```
Fill in your credentials inside the generated `.env` file (e.g., [`NEWS_API_KEY`](https://newsapi.org/register) and [`GUARDIAN_API_KEY`](https://open-platform.theguardian.com/access/)).

---

## Running the Application

Query multiple keywords concurrently (either space-separated or comma-separated formats are supported):
```bash
python main.py --keywords python,AI,data --min_score 0.3
```

### Expected Output
Upon successful aggregation, a formatted summary statistics table is printed to the console:
```text
========================================================
Source Name          | Articles Fetched | Passed Filter
--------------------------------------------------------
bbc                  | 17               | 16
newsapi              | 89               | 73
hackernews           | 12               | 2
guardian             | 10               | 6
--------------------------------------------------------
Total                | 128              | 97
========================================================
```
Filtered and sorted results are saved in a timestamped file: `output/news_YYYY-MM-DD_HH-MM.json`. 

#### Sample JSON Output Structure
```json
[
    {
        "id": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "title": "US Firm Announces New Anthropic Partnership",
        "url": "https://www.example.com/news/anthropic-partnership",
        "source": "newsapi",
        "published_at": "2026-06-17T21:50:00+00:00",
        "summary": "A detailed look at the partnership and its implications...",
        "tags": ["ai", "model", "government"],
        "score": 1.2
    }
]
```

---

## Testing

Run the test suite covering list deduplication, recency scoring arithmetic, parser resilience, and asynchronous failure resistance:
```bash
python -m pytest tests/ -v
```
