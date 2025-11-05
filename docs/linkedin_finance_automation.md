# Daily LinkedIn Finance Automation Architecture

## Overview
This document describes the fully unattended workflow that researches trending finance topics, composes a LinkedIn-ready post, publishes it using an approved partner integration, and logs the details to Google Sheets every day at 09:00 India Standard Time (IST).

## Components
1. **GitHub Actions Workflow** (`.github/workflows/daily_linkedin.yml`): Runs on a cron schedule at 03:30 UTC (09:00 IST) on the free tier. It checks out the repository, installs dependencies, and executes `automation/linkedin_daily/main.py`.
2. **Research Pipeline** (`automation/linkedin_daily/research.py`): Pulls from multiple finance-related RSS feeds, deduplicates items, scores hot topics using freshness, cross-source frequency, and mention density, and performs lightweight fact validation.
3. **Post Composer** (`automation/linkedin_daily/compose.py`): Converts the selected topics into a LinkedIn post that satisfies length, style, and compliance rules.
4. **Publisher** (`automation/linkedin_daily/publish.py`): Sends the post to Make.com (or the LinkedIn Marketing API if credentials exist) and returns the resulting post URL or provider identifier.
5. **Logger** (`automation/linkedin_daily/log_to_sheets.py`): Appends an audit row to a Google Sheet via a service account.
6. **Configuration and Secrets**: `config.yaml` defines feeds, thresholds, and styling rules. Secrets are injected through GitHub Secrets.
7. **Alerting**: Failures emit emails via GitHub Action’s `actions/send-mail` or a Make.com email node.

## Data Flow
RSS feeds → `research.py` (dedupe, score) → `compose.py` (generate formatted post) → `publish.py` (Make.com webhook) → LinkedIn → Google Sheets log. `main.py` handles retries, idempotency, dry-run mode, and orchestration.

## Failure & Recovery
* **Idempotency**: The workflow checks the Google Sheet for an existing row stamped with today’s date before publishing. If found, it skips publication to prevent duplicates.
* **Retries**: The workflow retries transient HTTP and Sheets operations with exponential backoff.
* **Alerting**: On failure, an email is sent to stakeholders with logs attached.
* **Manual Re-run**: Use GitHub’s “Run workflow” button with the same date; idempotency ensures safety.

