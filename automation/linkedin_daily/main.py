from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pytz

from .compose import build_payload
from .log_to_sheets import SheetLogger, format_row
from .publish import PublishError, resolve_publisher
from .research import build_topic_bundle, load_config, localize_timestamp, pick_primary_topic

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
SHEET_RANGE = "Posts!A:L"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily LinkedIn finance automation")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Run without publishing or logging")
    return parser.parse_args()


def _load_config(config_path: str) -> Dict:
    config = load_config(config_path)
    override_dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    if override_dry_run:
        config["dry_run"] = True
    return config


def _should_skip(sheet_logger: SheetLogger, timezone_name: str) -> bool:
    tz = pytz.timezone(timezone_name)
    today = datetime.now(tz).strftime("%Y-%m-%d")
    return sheet_logger.has_entry_for_date(SHEET_RANGE, today)


def orchestrate(config_path: str, dry_run_flag: bool = False) -> int:
    config = _load_config(config_path)
    dry_run = dry_run_flag or config.get("dry_run", False)
    start_time = time.time()

    topics = build_topic_bundle(config_path)
    if not topics:
        print("No viable topics found", file=sys.stderr)
        return 2

    primary = pick_primary_topic(topics)
    if not primary:
        print("Unable to select a primary topic", file=sys.stderr)
        return 3

    payload = build_payload(primary, config)
    post_text = payload["post_text"]
    insight = payload["insight"]

    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    sheet_logger = None
    if spreadsheet_id and not dry_run:
        sheet_logger = SheetLogger(spreadsheet_id, config.get("timezone", "Asia/Kolkata"))
        if _should_skip(sheet_logger, config.get("timezone", "Asia/Kolkata")):
            print("Post already logged for today; skipping publish.")
            return 0

    try:
        publish_response = resolve_publisher(insight, post_text, config, dry_run=dry_run)
    except PublishError as err:
        print(f"Publish failed: {err}", file=sys.stderr)
        return 4

    runtime_ms = int((time.time() - start_time) * 1000)

    if sheet_logger:
        row = format_row(insight, post_text, publish_response, runtime_ms, config.get("timezone", "Asia/Kolkata"))
        try:
            sheet_logger.append(SHEET_RANGE, row)
        except Exception as error:  # pragma: no cover - network exception path
            print(f"Failed to log to Google Sheets: {error}", file=sys.stderr)
            return 5

    timestamp = localize_timestamp(datetime.now(timezone.utc), config.get("timezone", "Asia/Kolkata"))
    print(json.dumps({
        "status": publish_response.get("status", "ok"),
        "headline": insight.headline,
        "hashtags": insight.hashtags,
        "topic_score": insight.topic_score,
        "sentiment": insight.sentiment,
        "timestamp": timestamp,
    }))
    return 0


def main() -> None:
    args = parse_args()
    exit_code = orchestrate(args.config, args.dry_run)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
