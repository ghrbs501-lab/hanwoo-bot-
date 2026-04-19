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
    storage: str = "냉장"

class BaseCrawler(ABC):
    @abstractmethod
    def fetch(self) -> list[CrawlResult]:
        pass

    def to_dict(self, results: list[CrawlResult]) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [{**asdict(r), "crawled_at": now} for r in results]

    @staticmethod
    def _is_valid_price(price_per_kg: float, weight_kg: float) -> bool:
        """가격과 중량이 모두 양수인 유효한 매물인지 확인한다."""
        return price_per_kg > 0 and weight_kg > 0
