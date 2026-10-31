#!/usr/bin/env python3
"""Collect fact-check headlines about Donald Trump from independent RSS feeds.

Output is a list of unreviewed research leads, never published automatically.
Exits non-zero when every feed failed, so the workflow run turns red instead of passing silently.
"""
import datetime as dt
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEEDS = {
    "FactCheck.org": "https://www.factcheck.org/feed/",
    "PolitiFact": "https://www.politifact.com/rss/factchecks/",
}
KEYWORDS = ("trump", "donald")


def main():
    out = Path("research/factcheck-leads.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    leads, failures = [], []
    for name, url in FEEDS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OhDonaldResearch/1.1"})
            with urllib.request.urlopen(req, timeout=25) as response:
                root = ET.fromstring(response.read())
            for item in root.findall(".//item")[:30]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                if any(k in title.lower() for k in KEYWORDS):
                    leads.append({"source": name, "title": title, "url": link, "status": "UNREVIEWED LEAD"})
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    out.write_text(json.dumps({
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "leads": leads,
        "failures": failures,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Unreviewed leads: {len(leads)}; feed failures: {len(failures)}")
    for f in failures:
        print("  ", f, file=sys.stderr)
    if len(failures) == len(FEEDS):
        sys.exit(1)


if __name__ == "__main__":
    main()
