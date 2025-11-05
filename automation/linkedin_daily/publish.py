from __future__ import annotations

import json
import os
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import requests

from .models import TopicInsight


class PublishError(RuntimeError):
    """Raised when the publish step fails."""


def _with_utm(link: str) -> str:
    if not link:
        return link
    parsed = urlparse(link)
    query = dict(parse_qsl(parsed.query))
    query.update(
        {
            "utm_source": "linkedin",
            "utm_medium": "organic",
            "utm_campaign": "daily_finance_9am_ist",
        }
    )
    new_query = urlencode(query)
    return urlunparse(parsed._replace(query=new_query))


def publish_via_make(webhook_url: str, payload: Dict) -> Dict:
    response = requests.post(webhook_url, json=payload, timeout=20)
    if response.status_code >= 300:
        raise PublishError(f"Make.com webhook failed: {response.status_code} {response.text}")
    try:
        return response.json()
    except ValueError:
        return {"status": "queued", "raw": response.text}


def publish_via_buffer(token: str, payload: Dict) -> Dict:
    url = "https://api.bufferapp.com/1/updates/create.json"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
    if response.status_code >= 300:
        raise PublishError(f"Buffer API error: {response.status_code} {response.text}")
    return response.json()


def publish_via_linkedin(access_token: str, org_urn: Optional[str], person_urn: Optional[str], text: str, link: str) -> Dict:
    owner = org_urn or person_urn
    if not owner:
        raise PublishError("LinkedIn publish requires an organization or person URN")
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    body = {
        "author": owner,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "originalUrl": link,
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    response = requests.post(url, headers=headers, json=body, timeout=20)
    if response.status_code >= 300:
        raise PublishError(f"LinkedIn API error: {response.status_code} {response.text}")
    return response.json()


def resolve_publisher(insight: TopicInsight, post_text: str, config: Dict, dry_run: bool = False) -> Dict:
    primary_link = _with_utm(insight.sources[0]) if insight.sources else ""
    payload = {
        "text": post_text,
        "link": primary_link,
        "headline": insight.headline,
        "hashtags": insight.hashtags,
        "topic_score": insight.topic_score,
        "sentiment": insight.sentiment,
    }
    if dry_run:
        return {"status": "dry_run", "payload": payload}

    make_url = os.getenv("MAKE_WEBHOOK_URL")
    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN")
    linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN")

    if make_url:
        payload.update({"disclaimer": insight.disclaimer})
        return publish_via_make(make_url, payload)

    if buffer_token:
        buffer_payload = {
            "text": post_text,
            "profile_ids": [],
            "media": {"link": primary_link},
            "shorten": False,
            "now": False,
        }
        return publish_via_buffer(buffer_token, buffer_payload)

    if linkedin_token:
        org_urn = os.getenv("LINKEDIN_ORG_URN")
        person_urn = os.getenv("LINKEDIN_PERSON_URN")
        return publish_via_linkedin(linkedin_token, org_urn, person_urn, post_text, primary_link)

    raise PublishError("No publishing provider configured.")


__all__ = ["resolve_publisher", "PublishError"]
