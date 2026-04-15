from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class CrawlResult:
    site: str
    grade: str
    cut: str
    gender: str
    price_per_kg: int
    weight_kg: float
    url: str

class BaseCrawler(ABC):
    @abstractmethod
    def fetch(self) -> list[CrawlResult]:
        """2등급 목심 매물 목록을 반환한다."""
        pass

    def to_dict(self, results: list[CrawlResult]) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [{**asdict(r), "crawled_at": now} for r in results]
