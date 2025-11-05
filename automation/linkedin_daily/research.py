from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence

import feedparser
import pytz
import requests
import yaml
from dateutil import parser as dateparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .models import FeedItem, TopicCandidate

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "for",
    "in",
    "to",
    "on",
    "with",
    "by",
    "from",
    "as",
    "at",
    "is",
    "be",
    "are",
    "was",
    "were",
    "has",
    "had",
    "have",
    "it",
    "that",
    "this",
    "will",
    "into",
    "about",
    "after",
    "before",
    "over",
    "under",
    "india",
    "indian",
    "finance",
    "financial",
    "market",
    "markets",
}

analyzer = SentimentIntensityAnalyzer()


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def fetch_feed(url: str, source_name: str) -> List[FeedItem]:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    items: List[FeedItem] = []
    for entry in parsed.entries:
        title = _normalize_text(entry.get("title", "").strip())
        summary = _normalize_text(entry.get("summary", "").strip())
        link = entry.get("link") or entry.get("id")
        if not (title and link):
            continue
        published = entry.get("published") or entry.get("updated")
        if published:
            published_dt = dateparser.parse(published)
            if published_dt.tzinfo is None:
                published_dt = published_dt.replace(tzinfo=timezone.utc)
            else:
                published_dt = published_dt.astimezone(timezone.utc)
        else:
            published_dt = datetime.now(timezone.utc)
        items.append(
            FeedItem(
                title=title,
                summary=summary,
                link=link,
                published=published_dt,
                source=source_name,
            )
        )
    return items


def fetch_all_feeds(feeds: Sequence[Dict[str, str]]) -> List[FeedItem]:
    items: List[FeedItem] = []
    for feed in feeds:
        try:
            items.extend(fetch_feed(feed["url"], feed["name"]))
        except Exception:
            continue
    return deduplicate_items(items)


def deduplicate_items(items: Iterable[FeedItem]) -> List[FeedItem]:
    seen = {}
    unique_items: List[FeedItem] = []
    for item in items:
        key = hashlib.sha1(item.link.encode("utf-8")).hexdigest()
        existing = seen.get(key)
        if not existing or existing.published < item.published:
            seen[key] = item
    unique_items.extend(seen.values())
    unique_items.sort(key=lambda x: x.published, reverse=True)
    return unique_items


def extract_keywords(item: FeedItem) -> List[str]:
    text = f"{item.title} {item.summary}".lower()
    tokens = [
        token.strip(".,:;!?()[]")
        for token in text.split()
        if token and token not in STOPWORDS and token.isalpha()
    ]
    keywords: List[str] = []
    for token in tokens:
        if len(token) > 3:
            keywords.append(token)
    # simple bigram extraction
    for first, second in zip(tokens, tokens[1:]):
        if first not in STOPWORDS and second not in STOPWORDS:
            keywords.append(f"{first} {second}")
    return keywords


def group_topics(items: Sequence[FeedItem], min_sources: int) -> List[TopicCandidate]:
    keyword_map: Dict[str, List[FeedItem]] = defaultdict(list)
    for item in items:
        keywords = extract_keywords(item)
        for keyword in keywords:
            keyword_map[keyword].append(item)

    candidates: List[TopicCandidate] = []
    for keyword, occurrences in keyword_map.items():
        sources = {occ.source for occ in occurrences}
        if len(sources) < min_sources:
            continue
        score = compute_score(keyword, occurrences)
        sentiment = sum(analyzer.polarity_scores(f"{occ.title}. {occ.summary}")["compound"] for occ in occurrences)
        sentiment = sentiment / len(occurrences)
        candidates.append(TopicCandidate(keyword=keyword, items=occurrences, score=score, sentiment=sentiment))
    return candidates


def compute_score(keyword: str, items: Sequence[FeedItem]) -> float:
    now = datetime.now(timezone.utc)
    recency_scores = []
    distinct_sources = len({item.source for item in items})
    for item in items:
        age_hours = (now - item.published).total_seconds() / 3600
        recency_scores.append(math.exp(-age_hours / 12.0))
    base_score = sum(recency_scores)
    density = len(items)
    uniqueness = 1.0 + math.log(distinct_sources + 1)
    keyword_bonus = 1.0 + min(len(keyword.split()), 2) * 0.1
    return base_score * uniqueness * keyword_bonus + density


def select_top_topics(candidates: Sequence[TopicCandidate], max_topics: int) -> List[TopicCandidate]:
    ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
    top_keywords: set[str] = set()
    chosen: List[TopicCandidate] = []
    for candidate in ranked:
        primary_keyword = candidate.keyword.split()[0]
        if primary_keyword in top_keywords:
            continue
        top_keywords.add(primary_keyword)
        chosen.append(candidate)
        if len(chosen) >= max_topics:
            break
    return chosen


def choose_supporting_items(candidate: TopicCandidate, limit: int = 3) -> List[FeedItem]:
    sorted_items = sorted(candidate.items, key=lambda item: item.published, reverse=True)
    unique_sources = {}
    for item in sorted_items:
        if item.source not in unique_sources:
            unique_sources[item.source] = item
        if len(unique_sources) >= limit:
            break
    # ensure deterministic order for logging
    ordered = list(unique_sources.values())
    ordered.sort(key=lambda item: item.published, reverse=True)
    return ordered


def build_topic_bundle(config_path: str) -> List[TopicCandidate]:
    config = load_config(config_path)
    feeds = config.get("feeds", [])
    items = fetch_all_feeds(feeds)
    candidates = group_topics(items, config.get("minimum_sources_per_topic", 2))
    if not candidates:
        return []
    top_candidates = select_top_topics(candidates, config.get("max_topics", 2))
    # attach only the most relevant occurrences
    trimmed: List[TopicCandidate] = []
    for candidate in top_candidates:
        supporting = choose_supporting_items(candidate)
        trimmed.append(
            TopicCandidate(
                keyword=candidate.keyword,
                items=supporting,
                score=candidate.score,
                sentiment=candidate.sentiment,
            )
        )
    return trimmed


def pick_primary_topic(topics: Sequence[TopicCandidate]) -> TopicCandidate | None:
    if not topics:
        return None
    # Add slight randomness to avoid repetitiveness when scores are similar
    weighted: List[tuple[TopicCandidate, float]] = []
    for topic in topics:
        weighted.append((topic, topic.score + random.uniform(0, 0.5)))
    weighted.sort(key=lambda pair: pair[1], reverse=True)
    return weighted[0][0]


def localize_timestamp(dt: datetime, timezone_name: str) -> str:
    tz = pytz.timezone(timezone_name)
    localized = dt.astimezone(tz)
    return localized.strftime("%Y-%m-%d %H:%M:%S %Z")


__all__ = [
    "build_topic_bundle",
    "pick_primary_topic",
    "localize_timestamp",
    "load_config",
]
