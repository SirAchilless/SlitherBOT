from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List

import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import TopicInsight

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetLogger:
    def __init__(self, spreadsheet_id: str, timezone_name: str) -> None:
        credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if not credentials_json:
            raise RuntimeError("Missing GOOGLE_CREDENTIALS_JSON environment variable")
        info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        self.client = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        self.spreadsheet_id = spreadsheet_id
        self.timezone = pytz.timezone(timezone_name)

    def _values_resource(self):
        return self.client.spreadsheets().values()

    def has_entry_for_date(self, sheet_range: str, date_key: str) -> bool:
        try:
            result = self._values_resource().get(spreadsheetId=self.spreadsheet_id, range=sheet_range).execute()
        except HttpError as error:
            if error.resp.status in {404}:
                return False
            raise
        rows = result.get("values", [])
        return any(row and row[0] == date_key for row in rows)

    def append(self, sheet_range: str, payload: List[str]) -> Dict:
        body = {
            "values": [payload],
        }
        return (
            self._values_resource()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_range,
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )


def format_row(insight: TopicInsight, post_text: str, post_response: Dict, runtime_ms: int, timezone_name: str) -> List[str]:
    tz = pytz.timezone(timezone_name)
    now = datetime.now(pytz.utc).astimezone(tz)
    sources = "\n".join(insight.sources)
    hashtags = " ".join(insight.hashtags)
    post_url = post_response.get("post_url") or post_response.get("id") or post_response.get("status")
    return [
        now.strftime("%Y-%m-%d"),
        insight.headline,
        "\n".join(insight.summary_points),
        insight.takeaway,
        hashtags,
        insight.sources[0] if insight.sources else "",
        sources,
        post_url,
        f"{insight.topic_score:.2f}",
        f"{insight.sentiment:.2f}",
        str(runtime_ms),
        post_text,
    ]


__all__ = ["SheetLogger", "format_row"]
