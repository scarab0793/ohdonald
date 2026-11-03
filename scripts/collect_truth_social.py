#!/usr/bin/env python3
"""Collect public Truth Social post candidates. No verdicts are generated.

Source: the public RSS archive at trumpstruth.org (a project of Defending Democracy
Together, not affiliated with Truth Social). The original Truth Social API started
answering HTTP 403 to GitHub-hosted runners on 2026-11-01, so it is no longer used.
Each item keeps a link to the original post (originalUrl) so it can be checked at source.

The output is a research lead list only. It is never published automatically.
Exits non-zero when nothing could be collected, so a broken collector turns the
workflow run red (and GitHub emails the repository owner) instead of failing silently.
"""
import datetime as dt
import email.utils
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ACCOUNT = os.environ.get("TRUTH_SOCIAL_ACCOUNT", "realDonaldTrump")
FEED = os.environ.get("TRUTH_FEED_URL", "https://www.trumpstruth.org/feed")
LIMIT = 40
HEADERS = {"User-Agent": "OhDonaldResearchBot/0.3 (public-source research)", "Accept": "application/rss+xml, application/xml"}
ARCHIVE = "{https://www.trumpstruth.org/rss-extensions}"
TRUTH = "{https://truthsocial.com/ns}"


def get_feed(url):
    request = urllib.request.Request(f"{url}?limit={LIMIT}", headers=HEADERS)
    with urllib.request.urlopen(request, timeout=25) as response:
        return ET.fromstring(response.read())


def iso(pub_date):
    try:
        return email.utils.parsedate_to_datetime(pub_date).astimezone(dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        return pub_date


def main():
    out = Path("research/truth-social-leads.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    results = []
    errors = []
    try:
        root = get_feed(FEED)
        for item in root.findall("channel/item"):
            if item.findtext(ARCHIVE + "postType") != "original" or item.findtext(ARCHIVE + "removed") == "true":
                continue  # reposts are not his words; removed posts are not citable
            original_id = item.findtext(TRUTH + "originalId") or ""
            results.append({
                "id": original_id or item.findtext("guid", ""),
                "published_at": iso(item.findtext("pubDate")),
                "url": item.findtext(TRUTH + "originalUrl") or f"https://truthsocial.com/@{ACCOUNT}/posts/{original_id}",
                "archive_url": item.findtext("link"),
                "content_html": item.findtext("description", ""),
                "status": "UNREVIEWED",
                "note": "Not independently fact-checked. Do not publish as a verdict. Verify against the original post.",
            })
    except Exception as exc:  # network errors, HTTP 4xx/5xx, bad XML
        errors.append(f"Archive feed unavailable: {type(exc).__name__}: {exc}")

    out.write_text(json.dumps({
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "account": ACCOUNT,
        "source": FEED,
        "posts": results,
        "errors": errors,
        "editorial_status": "RESEARCH ONLY — NOT APPROVED FOR PUBLICATION",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Collected {len(results)} candidate posts; errors: {len(errors)}")
    for e in errors:
        print("  ", e, file=sys.stderr)
    if errors and not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
