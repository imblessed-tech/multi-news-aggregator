from typing import Any
from abc import ABC, abstractmethod

from src.aggregator.models import Article

class BaseFetcher(ABC):

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass
    
    @abstractmethod
    async def fetch(self, keywords: list[str]) -> list[Article]:
        pass

    def _parse_item(self, raw: dict[str, Any]) -> Article | None:
        pass