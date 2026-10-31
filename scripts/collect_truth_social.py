#!/usr/bin/env python3
"""Collect public Truth Social post candidates. No verdicts are generated.

The output is a research lead list only. It is never published automatically.
Exits non-zero when nothing could be collected, so a broken collector turns the
workflow run red (and GitHub emails the repository owner) instead of failing silently.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

ACCOUNT = os.environ.get("TRUTH_SOCIAL_ACCOUNT", "realDonaldTrump")
BASE = "https://truthsocial.com/api/v1"
HEADERS = {"User-Agent": "OhDonaldResearchBot/0.2 (public-source research)", "Accept": "application/json"}


def get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def main():
    out = Path("research/truth-social-leads.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    results = []
    errors = []
    try:
        acct = get_json(f"{BASE}/accounts/lookup?acct={ACCOUNT}")
        posts = get_json(f"{BASE}/accounts/{acct['id']}/statuses?limit=40&exclude_replies=true")
        for post in posts:
            if post.get("reblog"):
                continue
            results.append({
                "id": str(post.get("id", "")),
                "published_at": post.get("created_at"),
                "url": post.get("url") or f"https://truthsocial.com/@{ACCOUNT}/posts/{post.get('id')}",
                "content_html": post.get("content", ""),
                "status": "UNREVIEWED",
                "note": "Not independently fact-checked. Do not publish as a verdict.",
            })
    except Exception as exc:  # network errors, HTTP 4xx/5xx, bad JSON
        errors.append(f"Public API unavailable: {type(exc).__name__}: {exc}")

    out.write_text(json.dumps({
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "account": ACCOUNT,
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
