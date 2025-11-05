from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class FeedItem:
    title: str
    link: str
    summary: str
    published: datetime
    source: str


@dataclass
class TopicInsight:
    headline: str
    summary_points: List[str]
    takeaway: str
    hashtags: List[str]
    disclaimer: str
    sources: List[str]
    topic_score: float
    sentiment: float


@dataclass
class TopicCandidate:
    keyword: str
    items: List[FeedItem]
    score: float
    sentiment: float
    created_at: datetime = field(default_factory=datetime.utcnow)

    def best_item(self) -> FeedItem:
        return max(self.items, key=lambda item: item.published)
