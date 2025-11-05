from __future__ import annotations

import random
from typing import Dict, List

from .models import FeedItem, TopicCandidate, TopicInsight


def truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"


def truncate_chars(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def choose_headline(candidate: TopicCandidate, max_chars: int) -> str:
    latest = candidate.best_item()
    base = latest.title
    return truncate_chars(base, max_chars)


def summarize_item(item: FeedItem, max_words: int) -> str:
    summary = item.summary or item.title
    for delimiter in (". ", "? ", "! "):
        if delimiter in summary:
            summary = summary.split(delimiter)[0]
            break
    text = f"{summary.strip()} ({item.source})"
    return truncate_words(text, max_words)


def build_hashtags(config: Dict, keyword: str) -> List[str]:
    mandatory = [f"#{tag}" for tag in config.get("mandatory_hashtags", [])]
    pool = config.get("hashtags_pool", [])
    random.shuffle(pool)
    selected = pool[: max(0, 5 - len(mandatory))]
    keyword_tag = f"#{keyword.split()[0].replace(' ', '')[:20]}"
    hashtags = mandatory + [f"#{tag}" for tag in selected]
    if keyword_tag.lower() not in {tag.lower() for tag in hashtags}:
        hashtags.append(keyword_tag)
    # Ensure uniqueness while preserving order
    seen = set()
    ordered = []
    for tag in hashtags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            ordered.append(tag)
    return ordered[:5]


def compose_post(candidate: TopicCandidate, config: Dict) -> TopicInsight:
    headline = choose_headline(candidate, config.get("headline_max_chars", 80))
    bullets = [
        summarize_item(item, config.get("max_bullet_words", 22))
        for item in candidate.items[:3]
    ]
    takeaway_base = "; ".join(bullet.split("(")[0].strip() for bullet in bullets if bullet)
    takeaway = truncate_words(takeaway_base, config.get("takeaway_max_words", 25))
    disclaimer = config.get("closing_disclaimer", "This is not investment advice.")
    hashtags = build_hashtags(config, candidate.keyword)
    composed_takeaway = f"{takeaway}. {disclaimer}" if disclaimer not in takeaway else takeaway

    return TopicInsight(
        headline=headline,
        summary_points=bullets,
        takeaway=composed_takeaway,
        hashtags=hashtags,
        disclaimer=disclaimer,
        sources=[item.link for item in candidate.items],
        topic_score=candidate.score,
        sentiment=candidate.sentiment,
    )


def format_for_linkedin(insight: TopicInsight) -> str:
    bullet_lines = "\n".join(f"• {point}" for point in insight.summary_points)
    hashtags_line = " ".join(insight.hashtags)
    post = f"{insight.headline}\n\n{bullet_lines}\n\nTakeaway: {insight.takeaway}\n\n{hashtags_line}"
    if len(post) > 1200:
        post = post[:1199]
    return post


def build_payload(candidate: TopicCandidate, config: Dict) -> Dict:
    insight = compose_post(candidate, config)
    post_text = format_for_linkedin(insight)
    return {
        "post_text": post_text,
        "insight": insight,
    }


__all__ = ["compose_post", "build_payload", "format_for_linkedin"]
