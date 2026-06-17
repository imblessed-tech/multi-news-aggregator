from typing import Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Article:
    id: str
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str
    tags: list[str]
    score: float = 0.0

    def __eq__(self, other):
        if not isinstance(other, Article):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "summary": self.summary,
            "tags": self.tags,
            "score": self.score,
        }
