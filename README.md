# OhDonald.com

An evidence-first, satirical archive of public claims.

## Publish
Enable GitHub Pages in Settings > Pages, source: Deploy from a branch, branch: main, folder: / (root). Configure the custom domain `ohdonald.com` after the DNS records are ready.

## Editorial process
`data/claims.json` starts empty deliberately. Only entries with `reviewed: true` and at least one source are rendered. Never publish automatically generated verdicts without evidence review.

## Example data shape (not a published claim)
```json
[{"title":"Example headline","claim":"Exact quotation","date":"2026-01-01","topic":"Economy","verdict":"Needs context","summary":"Documented analysis","reviewed":true,"sources":[{"label":"Primary source","url":"https://example.org"}]}]
```

No generated images or fabricated statistics are used.
