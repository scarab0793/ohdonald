# OhDonald.com

An evidence-first, satirical, bilingual (English / Spanish) archive of public claims.
Receipts are factual and sourced. The jokes live in the headlines and the interface, never in the verdicts.

## How the site is built

Everything is static: no server, no framework. Edit the data, run one command, commit.

```
python3 scripts/build.py
```

| You edit | What it controls |
|---|---|
| `data/claims.json` | Fact checks (English originals). Only entries with `reviewed: true` and at least one source are published. |
| `data/claims.es.json` | Spanish translations, keyed by the claim's `slug`. Missing translation = the English text is shown, marked `lang="en"`. |
| `data/contradictions.json` / `data/contradictions.es.json` | "He Said WHAT Yesterday?" pairs and their translations, keyed by `id`. |
| `data/ui.json` | Every piece of interface text in both languages, including the satirical copy and the methodology page. |

`scripts/build.py` generates `index.html`, `es/index.html`, one page per fact check
(`/claims/<slug>/` and `/es/claims/<slug>/`, with `ClaimReview` structured data), the methodology
pages, `404.html`, `sitemap.xml`, `robots.txt`, `favicon.svg` and `og.png`. Do not edit those files by hand.
New claims get a permanent `slug` automatically. **Never change a slug once published**: it is the URL.
The `Check generated site` workflow fails a push or pull request if you forgot to rebuild.

### Adding a fact check

```json
{
  "date": "2026-01-01",
  "title": "Example headline",
  "claim": "Exact quotation",
  "topic": "Economy",
  "verdict": "Needs context",
  "summary": "Documented analysis",
  "reviewed": true,
  "sources": [{ "label": "Primary source", "url": "https://example.org" }],
  "statementDate": null,
  "statementVenue": null,
  "statementSource": null
}
```

Verdicts: `False`, `Misleading`, `Needs context`, `Unsupported`, `Supported` (see the methodology page).
Then add the Spanish version to `data/claims.es.json` (`title`, `claim`, `summary`, `sourceLabels`, and
`statementVenue` when there is one) and run the build. The build prints a warning for any missing translation.

## Editorial rules

- No generated images, no fabricated quotes, no fabricated statistics.
- Never publish automatically generated verdicts without evidence review.
- Satire targets claims and public conduct. It never speculates about anyone's health, memory or intent.
- The two scheduled workflows only collect *unreviewed* leads as downloadable run artifacts.
  They now fail loudly (red run) when a source is unreachable.

## Preview locally

```
python3 scripts/build.py && python3 -m http.server 8000
```

## Publish

GitHub Pages: Settings → Pages → Deploy from a branch → `main`, folder `/ (root)`.
Custom domain: `ohdonald.com` (see `CNAME`).
