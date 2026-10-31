#!/usr/bin/env python3
"""Build the bilingual (English / Spanish) static site from data/*.json.

Run from the repository root after editing any file in data/:

    python3 scripts/build.py

Generated files (commit them, GitHub Pages serves them as-is):
    index.html, es/index.html               archive pages (the feed itself is filled in by script.js)
    claims/<slug>/index.html                one static page per fact check (English)
    es/claims/<slug>/index.html             the same in Spanish (falls back to English text if untranslated)
    methodology.html, es/metodologia.html
    404.html, sitemap.xml, robots.txt, favicon.svg, og.png

Single sources of truth: data/claims.json, data/contradictions.json (English originals),
data/claims.es.json, data/contradictions.es.json (translations), data/ui.json (all interface text).
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = "https://ohdonald.com"
ISSUES_URL = "https://github.com/scarab0793/ohdonald/issues"
LANGS = ("en", "es")
OTHER = {"en": "es", "es": "en"}
RATING = {"False": 1, "Misleading": 2, "Unsupported": 2, "Needs context": 3, "Supported": 5}
FONTS_URL = ("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800;900"
             "&family=Libre+Baskerville:wght@400;700&display=swap")
MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
}
IMAGES = [
    "https://commons.wikimedia.org/wiki/Special:FilePath/Donald_Trump_official_portrait.jpg?width=900",
    "https://commons.wikimedia.org/wiki/Special:FilePath/TrumpPortrait.jpg?width=900",
    "https://commons.wikimedia.org/wiki/Special:FilePath/Official_Presidential_Portrait_of_President_Donald_J._Trump_%282025%29.jpg?width=900",
]
CREDITS = {
    "en": [
        ("2017 White House / Shealah Craighead", "https://commons.wikimedia.org/wiki/File:Donald_Trump_official_portrait.jpg"),
        ("January 2025 / Daniel Torok", "https://commons.wikimedia.org/wiki/File:TrumpPortrait.jpg"),
        ("June 2025 / Daniel Torok", "https://commons.wikimedia.org/wiki/File:Official_Presidential_Portrait_of_President_Donald_J._Trump_(2025).jpg"),
    ],
    "es": [
        ("2017 Casa Blanca / Shealah Craighead", "https://commons.wikimedia.org/wiki/File:Donald_Trump_official_portrait.jpg"),
        ("enero de 2025 / Daniel Torok", "https://commons.wikimedia.org/wiki/File:TrumpPortrait.jpg"),
        ("junio de 2025 / Daniel Torok", "https://commons.wikimedia.org/wiki/File:Official_Presidential_Portrait_of_President_Donald_J._Trump_(2025).jpg"),
    ],
}

warnings: list[str] = []


# ----------------------------------------------------------------------------- helpers

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def slugify(text: str, limit: int = 64) -> str:
    text = re.sub(r"[’'`]", "", text)
    text = re.sub(r"[–—/]", " ", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > limit:
        text = text[:limit].rsplit("-", 1)[0]
    return text


def fmt_date(iso: str, lang: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS['en'][m - 1]} {d}, {y}" if lang == "en" else f"{d} {MONTHS['es'][m - 1]} {y}"


def clip(text: str, n: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def home_path(lang: str) -> str:
    return "/" if lang == "en" else "/es/"


def claim_path(lang: str, slug: str) -> str:
    return f"/claims/{slug}/" if lang == "en" else f"/es/claims/{slug}/"


def method_path(lang: str) -> str:
    return "/methodology.html" if lang == "en" else "/es/metodologia.html"


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save_json(name: str, payload) -> None:
    (DATA / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def is_http(url) -> bool:
    return isinstance(url, str) and re.match(r"^https?://", url) is not None


# ----------------------------------------------------------------------------- data

def load_all():
    ui = load_json("ui.json")
    claims = load_json("claims.json")
    pairs = load_json("contradictions.json")
    claims_es = load_json("claims.es.json")
    pairs_es = load_json("contradictions.es.json")

    # Slugs / ids are permanent URLs. New entries get one automatically (and it is saved).
    changed = False
    seen = set()
    for c in claims:
        if not c.get("slug"):
            base = f"{c['date']}-{slugify(c['title'])}"
            slug, i = base, 2
            while slug in seen or any(o.get("slug") == slug for o in claims):
                slug, i = f"{base}-{i}", i + 1
            c["slug"] = slug
            changed = True
            print(f"  new slug: {slug}")
        if c["slug"] in seen:
            sys.exit(f"ERROR: duplicate slug {c['slug']}")
        seen.add(c["slug"])
    for p in pairs:
        if not p.get("id"):
            p["id"] = f"{p['after']['date']}-{slugify(p['title'])}"
            changed = True
            print(f"  new pair id: {p['id']}")
    if changed:
        save_json("claims.json", claims)
        save_json("contradictions.json", pairs)

    errors = []
    for c in claims:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", c["date"]):
            errors.append(f"{c['slug']}: bad date {c['date']!r}")
        if c["verdict"] not in ui["en"]["verdicts"]:
            errors.append(f"{c['slug']}: unknown verdict {c['verdict']!r}")
        for s in c.get("sources", []):
            if not is_http(s.get("url")):
                errors.append(f"{c['slug']}: source URL is not http(s): {s.get('url')!r}")
        if c.get("statementSource") and not is_http(c["statementSource"]):
            errors.append(f"{c['slug']}: statementSource is not http(s)")
    for p in pairs:
        for side in ("before", "after"):
            if not is_http(p[side].get("url")):
                errors.append(f"{p['id']}: {side} URL is not http(s)")
    if errors:
        sys.exit("ERROR:\n  " + "\n  ".join(errors))

    published = [c for c in claims if c.get("reviewed") is True and c.get("sources")]
    published.sort(key=lambda c: c["date"], reverse=True)

    for c in published:
        if c["slug"] not in claims_es:
            warnings.append(f"no Spanish translation for claim {c['slug']} (English text will be shown)")
    for slug in claims_es:
        if slug not in seen:
            warnings.append(f"data/claims.es.json has an unknown key: {slug}")
    ids = {p["id"] for p in pairs}
    for p in pairs:
        if p["id"] not in pairs_es:
            warnings.append(f"no Spanish translation for pair {p['id']}")
    for key in pairs_es:
        if key not in ids:
            warnings.append(f"data/contradictions.es.json has an unknown key: {key}")
    return ui, published, claims_es


# ----------------------------------------------------------------------------- shared HTML

def head(lang, t, *, title, description, path, alt, og_type="website", jsonld=None, noindex=False, has_og=False):
    canonical = SITE + path
    alt_links = "".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE}{alt[l]}">' for l in LANGS
    ) + f'<link rel="alternate" hreflang="x-default" href="{SITE}{alt["en"]}">'
    other = OTHER[lang]
    og = [
        ("og:site_name", "OhDonald"), ("og:type", og_type), ("og:title", title),
        ("og:description", description), ("og:url", canonical),
        ("og:locale", t["locale"]), ("og:locale:alternate", ui_locale(other)),
    ]
    if has_og:
        og += [("og:image", SITE + "/og.png"), ("og:image:width", "1200"), ("og:image:height", "630")]
    og_html = "".join(f'<meta property="{k}" content="{esc(v)}">' for k, v in og)
    tw = '<meta name="twitter:card" content="summary_large_image">' if has_og else '<meta name="twitter:card" content="summary">'
    ld = ""
    if jsonld:
        payload = json.dumps(jsonld, ensure_ascii=False).replace("<", "\\u003c")
        ld = f'<script type="application/ld+json">{payload}</script>'
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    return (
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title>"
        f'<meta name="description" content="{esc(description)}">{robots}'
        f'<link rel="canonical" href="{esc(canonical)}">{alt_links}{og_html}{tw}'
        '<meta name="theme-color" content="#111a16">'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link rel="stylesheet" href="{FONTS_URL}">'
        '<link rel="stylesheet" href="/style.css">'
        f"{ld}</head>"
    )


_UI_LOCALES: dict[str, str] = {}


def ui_locale(lang: str) -> str:
    return _UI_LOCALES[lang]


def lang_nav(lang, t, alt):
    items = []
    for l in LANGS:
        current = ' aria-current="true"' if l == lang else ""
        name = esc(ALL_UI[l]["langName"])
        items.append(f'<a href="{alt[l]}" hreflang="{l}" lang="{l}"{current}>{name}</a>')
    return f'<nav class="lang-nav" aria-label="{esc(t["langNav"])}">{"".join(items)}</nav>'


def footer(lang, t):
    return (
        f'<footer><strong>OhDonald.</strong><span>{esc(t["footer"])}</span>'
        f'<a href="{method_path(lang)}">{esc(t["method"])}</a></footer>'
    )


def page(lang, t, *, head_html, body, home=False):
    data_home = ' data-home="true"' if home else ""
    return (
        f'<!doctype html><html lang="{lang}"{data_home}>{head_html}<body>'
        f'<a class="skip-link" href="#main">{esc(t["skip"])}</a>'
        f'<div class="site">{body}{footer(lang, t)}</div>'
        '<script src="/lang.js" defer></script>{extra}</body></html>'
    )


def simple_masthead(lang, t, alt):
    return (
        '<header class="article-header">'
        f'<div class="topline"><span>{esc(t["topline1"])}</span>'
        f'<a href="{home_path(lang)}">{esc(t["back_to_archive"])}</a></div>'
        f'<a class="logo" href="{home_path(lang)}">Oh<span>Donald</span><i>.</i></a>'
        f'{lang_nav(lang, t, alt)}</header><div class="mainline"></div>'
    )


# ----------------------------------------------------------------------------- pages

def build_index(lang, t, published, has_og):
    alt = {"en": home_path("en"), "es": home_path("es")}
    credits = " · ".join(
        f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(name)}</a>' for name, url in CREDITS[lang]
    )
    eager = 'loading="eager" fetchpriority="high"'
    lazy = 'loading="lazy"'
    figures = "".join(
        f'<figure><img src="{esc(src)}" alt="{esc(t["altImages"][i])}" width="900" height="1100" '
        f'{eager if i == 0 else lazy} decoding="async">'
        f'<figcaption>{esc(t["captions"][i])}</figcaption></figure>'
        for i, src in enumerate(IMAGES)
    )
    masthead = (
        '<header class="masthead">'
        f'<div class="topline"><span>{esc(t["topline1"])}</span><span>{esc(t["topline2"])}</span></div>'
        f'<a class="logo" href="{home_path(lang)}">Oh<span>Donald</span><i>.</i></a>'
        f'{lang_nav(lang, t, alt)}'
        f'<div class="strap"><h1>{esc(t["tagline"])}</h1><p>{esc(t["strap"])}</p></div>'
        f'<div class="visual-strip">{figures}</div>'
        f'<p class="photo-note">{esc(t["photoLead"])} {credits}. {esc(t["photoTail"])}</p>'
        '</header><div class="mainline"></div>'
    )
    noscript = (
        f'<noscript><p>{esc(t["noscript"])}</p><ul>'
        + "".join(
            f'<li><a href="{claim_path(lang, c["slug"])}">{esc(title_for(lang, c))}</a></li>' for c in published
        )
        + "</ul></noscript>"
    )
    body = (
        masthead
        + '<div class="layout">'
        f'<aside class="sidebar" aria-labelledby="side-h"><div class="side-head"><h2 id="side-h">{esc(t["sideTitle"])}</h2>'
        f'<p>{esc(t["sideDesc"])}</p></div><div id="side-items"></div>'
        f'<div class="side-foot"><a href="{method_path(lang)}">{esc(t["method"])}</a></div></aside>'
        '<main id="main" class="content" tabindex="-1">'
        f'<div class="toolbar"><div class="tabs" role="tablist" aria-label="{esc(t["tabsLabel"])}">'
        f'<button type="button" role="tab" id="tab-checks" data-section="checks" aria-controls="checks-section" aria-selected="true">{esc(t["tabChecks"])}</button>'
        f'<button type="button" role="tab" id="tab-pairs" data-section="pairs" aria-controls="pairs-section" aria-selected="false" tabindex="-1">{esc(t["tabPairs"])}</button>'
        "</div></div>"
        '<section id="checks-section" role="tabpanel" aria-labelledby="tab-checks">'
        '<div class="filters">'
        f'<div id="years" class="yearbar" role="group" aria-label="{esc(t["yearsLabel"])}"></div>'
        f'<label class="sr-only" for="search">{esc(t["searchLabel"])}</label>'
        f'<input id="search" type="search" autocomplete="off" placeholder="{esc(t["searchPlaceholder"])}">'
        f'<label class="sr-only" for="verdict">{esc(t["verdictLabel"])}</label>'
        f'<select id="verdict"><option value="">{esc(t["allVerdicts"])}</option></select></div>'
        f'<div class="feed-intro"><h2 class="eyebrow">{esc(t["archiveLabel"])}</h2>'
        '<span id="count" role="status" aria-live="polite"></span></div>'
        f'<div id="cards" class="story-grid">{noscript}</div>'
        f'<div class="coverage"><h2>{esc(t["coverageTitle"])}</h2><p>{esc(t["coverageNote"])}</p>'
        '<div id="coverage-grid"></div></div></section>'
        '<section id="pairs-section" role="tabpanel" aria-labelledby="tab-pairs" hidden>'
        f'<p class="eyebrow">{esc(t["pairsLabel"])}</p>'
        f'<h2 class="section-title">{esc(t["pairsTitle"])}</h2>'
        f'<p class="section-desc">{esc(t["pairsDesc"])}</p><div id="pairs-list"></div></section>'
        "</main></div>"
    )
    head_html = head(lang, t, title=t["metaTitle"], description=t["metaDescription"],
                     path=home_path(lang), alt=alt, has_og=has_og)
    out = page(lang, t, head_html=head_html, body=body, home=(lang == "en"))
    return out.replace("{extra}", '<script src="/script.js" defer></script>')


CLAIMS_ES: dict = {}


def tr(lang, claim) -> dict:
    return CLAIMS_ES.get(claim["slug"], {}) if lang == "es" else {}


def title_for(lang, claim) -> str:
    return tr(lang, claim).get("title") or claim["title"]


def build_article(lang, t, claim, published, ui_all, has_og):
    a = t["article"]
    slug = claim["slug"]
    tl = tr(lang, claim)
    translated = lang == "en" or bool(tl.get("title"))
    lang_attr = "" if translated else ' lang="en"'
    alt = {"en": claim_path("en", slug), "es": claim_path("es", slug)}
    verdict = t["verdicts"][claim["verdict"]]
    topic = t["topics"].get(claim["topic"], claim["topic"])
    title = tl.get("title") or claim["title"]
    claim_text = tl.get("claim") or claim["claim"]
    summary = tl.get("summary") or claim["summary"]
    venue = tl.get("statementVenue") or claim.get("statementVenue")
    labels = tl.get("sourceLabels") or []

    # ---- provenance box
    prov = [f'<h2>{esc(a["provTitle"])}</h2>']
    unver = esc(a["unverified"])
    when = fmt_date(claim["statementDate"], lang) if claim.get("statementDate") else unver
    prov.append(f'<p>{esc(a["when"])}: {when}</p>')
    prov.append(f'<p>{esc(a["where"])}: <span{lang_attr if venue else ""}>{esc(venue) if venue else unver}</span></p>')
    if claim.get("statementSource"):
        prov.append(f'<a href="{esc(claim["statementSource"])}" target="_blank" rel="noopener noreferrer">{esc(a["originalContext"])}</a>')
    else:
        prov.append(f'<p class="provenance-note">{esc(a["archiveNote"])}</p>')

    # ---- claim (+ original quote on the Spanish page)
    claim_html = f'<blockquote class="article-claim"{lang_attr}>{esc(claim_text)}</blockquote>'
    if lang == "es":
        if translated:
            claim_html += (f'<p class="article-orig" lang="en">{esc(t["original"])}: “{esc(claim["claim"])}”</p>'
                           f'<p class="article-orig">{esc(a["translationNote"])}</p>')

    sources = "".join(
        f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">'
        f'{esc(labels[i] if i < len(labels) else s["label"])} ↗</a></li>'
        for i, s in enumerate(claim["sources"])
    )

    # ---- related: same topic first, then newest
    others = [c for c in published if c["slug"] != slug]
    related = [c for c in others if c["topic"] == claim["topic"]][:3]
    for c in others:
        if len(related) >= 3:
            break
        if c not in related:
            related.append(c)
    def related_item(c):
        untranslated = lang == "es" and not tr(lang, c).get("title")
        attr = ' lang="en"' if untranslated else ""
        return f'<li><a href="{claim_path(lang, c["slug"])}"{attr}>{esc(title_for(lang, c))}</a></li>'

    related_html = (
        f'<h2 class="article-sources-title">{esc(a["moreLabel"])}</h2><ul>'
        + "".join(related_item(c) for c in related)
        + "</ul>"
    )

    article = (
        f'<article class="full-article">'
        f'<div class="article-meta">{esc(topic)} · {esc(fmt_date(claim["date"], lang))} · {esc(verdict["label"])}</div>'
        f'<h1 class="article-title"{lang_attr}>{esc(title)}</h1>'
        f'<section class="statement-provenance">{"".join(prov)}</section>'
        f'<div class="article-eyebrow">{esc(a["claimEyebrow"])}</div>{claim_html}'
        f'<div class="article-eyebrow">{esc(a["factsEyebrow"])}</div>'
        f'<p class="article-summary"{lang_attr}>{esc(summary)}</p>'
        f'<p class="article-finding">{esc(a["finding"])}: <span class="verdict" data-verdict="{esc(claim["verdict"])}">{esc(verdict["label"])}</span>'
        f'<span class="quip">{esc(verdict["quip"])}</span></p>'
        f'<h2 class="article-sources-title">{esc(a["sourcesTitle"])}</h2><ul>{sources}</ul>'
        f'{related_html}'
        f'<p class="article-note">{esc(a["editorialNote"])}</p></article>'
    )
    aside = (
        f'<aside class="article-aside"><h2>{esc(a["asideTitle"])}</h2><p>{esc(a["asideText"])}</p>'
        f'<a href="{method_path(lang)}">{esc(a["asideLink"])}</a></aside>'
    )
    body = (
        simple_masthead(lang, t, alt)
        + '<div class="article-layout">'
        f'<a class="back-link" href="{home_path(lang)}">{esc(a["back"])}</a>'
        f'<main id="main">{article}</main>{aside}</div>'
    )

    review = {
        "@context": "https://schema.org",
        "@type": "ClaimReview",
        "url": SITE + claim_path(lang, slug),
        "inLanguage": lang,
        "datePublished": claim["date"],
        "claimReviewed": claim_text,
        "author": {"@type": "Organization", "name": "OhDonald", "url": SITE},
        "itemReviewed": {"@type": "Claim", "author": {"@type": "Person", "name": "Donald Trump"}},
        "reviewRating": {
            "@type": "Rating", "ratingValue": RATING[claim["verdict"]], "bestRating": 5, "worstRating": 1,
            "alternateName": verdict["label"],
        },
    }
    if claim.get("statementDate"):
        review["itemReviewed"]["datePublished"] = claim["statementDate"]
    if claim.get("statementSource"):
        review["itemReviewed"]["appearance"] = [{"@type": "CreativeWork", "url": claim["statementSource"]}]

    head_html = head(lang, t, title=f"{title} · OhDonald", description=clip(summary), path=claim_path(lang, slug),
                     alt=alt, og_type="article", jsonld=review, has_og=has_og)
    return page(lang, t, head_html=head_html, body=body).replace("{extra}", "")


def build_methodology(lang, t, has_og):
    m = t["methodology"]
    alt = {"en": method_path("en"), "es": method_path("es")}
    parts = []
    for s in m["sections"]:
        parts.append(f'<h2>{esc(s["h"])}</h2>')
        if s.get("p"):
            parts.append(f'<p>{esc(s["p"])}</p>')
        if s.get("list"):
            parts.append("<dl>" + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in s["list"]) + "</dl>")
        if s.get("link") == "issues":
            parts.append(f'<p><a href="{ISSUES_URL}" target="_blank" rel="noopener noreferrer">{esc(m["issueLink"])}</a></p>')
    body = (
        simple_masthead(lang, t, alt)
        + f'<main id="main" class="doc"><p class="eyebrow">{esc(m["eyebrow"])}</p><h1>{esc(m["title"])}</h1>'
        f'<p class="lead">{esc(m["lead"])}</p>{"".join(parts)}</main>'
    )
    head_html = head(lang, t, title=m["metaTitle"], description=m["metaDescription"], path=method_path(lang),
                     alt=alt, has_og=has_og)
    return page(lang, t, head_html=head_html, body=body).replace("{extra}", "")


def build_404(ui_all, has_og):
    blocks = []
    for lang in LANGS:
        n = ui_all[lang]["notFound"]
        tag = "h1" if lang == "en" else "h2"  # exactly one h1 per page
        blocks.append(
            f'<section lang="{lang}" class="notfound"><{tag}>{esc(n["title"])}</{tag}><p>{esc(n["text"])}</p>'
            f'<p><a href="{home_path(lang)}">{esc(n["home"])}</a></p></section>'
        )
    t = ui_all["en"]
    body = (
        '<header class="article-header"><div class="topline"><span>THE PUBLIC RECORD · SINCE 2015</span></div>'
        '<a class="logo" href="/">Oh<span>Donald</span><i>.</i></a></header><div class="mainline"></div>'
        f'<main id="main">{"".join(blocks)}</main>'
    )
    head_html = head("en", t, title=ui_all["en"]["notFound"]["metaTitle"], description=ui_all["en"]["metaDescription"],
                     path="/404.html", alt={"en": "/404.html", "es": "/404.html"}, noindex=True, has_og=has_og)
    return page("en", t, head_html=head_html, body=body).replace("{extra}", "")


def build_sitemap(published):
    def url(path_en, path_es, lastmod=None):
        lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        alts = (f'<xhtml:link rel="alternate" hreflang="en" href="{SITE}{path_en}"/>'
                f'<xhtml:link rel="alternate" hreflang="es" href="{SITE}{path_es}"/>'
                f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{path_en}"/>')
        return "".join(f"<url><loc>{SITE}{p}</loc>{lm}{alts}</url>" for p in (path_en, path_es))

    newest = published[0]["date"] if published else date.today().isoformat()
    entries = [url("/", "/es/", newest), url("/methodology.html", "/es/metodologia.html")]
    entries += [url(claim_path("en", c["slug"]), claim_path("es", c["slug"]), c["date"]) for c in published]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(entries) + "\n</urlset>\n")


FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#111a16"/>'
    '<text x="32" y="46" text-anchor="middle" font-family="Impact,Arial Narrow,sans-serif" font-weight="900" '
    'font-size="46" fill="#f3c34b">O</text><circle cx="50" cy="48" r="4" fill="#ff744e"/></svg>\n'
)

LANG_JS = """/* Remembers the visitor's language choice and sends returning Spanish readers to /es/. */
(() => {
  'use strict';
  const KEY = 'ohdonald-lang';
  let stored = null;
  try { stored = localStorage.getItem(KEY); } catch (_) { /* storage blocked: fine */ }

  document.querySelectorAll('.lang-nav a').forEach((a) => {
    a.addEventListener('click', () => {
      try { localStorage.setItem(KEY, a.hreflang); } catch (_) { /* ignore */ }
    });
  });

  const root = document.documentElement;
  if (root.dataset.home === 'true' && root.lang === 'en') {
    const wantsEs = stored === 'es' || (!stored && /^es\\b/i.test(navigator.language || ''));
    if (wantsEs) location.replace('/es/' + location.hash);
  }
})();
"""


def build_og(ui_all) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        warnings.append("Pillow not installed: og.png was not regenerated")
        return (ROOT / "og.png").exists()
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    font_path = next((p for p in candidates if Path(p).exists()), None)
    if not font_path:
        warnings.append("no bold font found: og.png was not regenerated")
        return (ROOT / "og.png").exists()
    img = Image.new("RGB", (1200, 630), "#111a16")
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(font_path, 190)
    mid = ImageFont.truetype(font_path, 54)
    small = ImageFont.truetype(font_path, 30)
    d.rectangle([0, 0, 1200, 14], fill="#ff744e")
    d.text((70, 150), "Oh", font=big, fill="#e7e9e1")
    x = 70 + d.textlength("Oh", font=big)
    d.text((x, 150), "Donald", font=big, fill="#f3c34b")
    x += d.textlength("Donald", font=big)
    d.text((x, 150), ".", font=big, fill="#ff744e")
    d.text((74, 400), ui_all["en"]["tagline"], font=mid, fill="#e7e9e1")
    d.text((74, 480), "RECEIPTS OVER RHETORIC · SINCE 2015", font=small, fill="#a3afa6")
    d.text((74, 530), "ohdonald.com", font=small, fill="#ff744e")
    img.save(ROOT / "og.png", optimize=True)
    return True


# ----------------------------------------------------------------------------- main

ALL_UI: dict = {}


def main() -> None:
    global CLAIMS_ES
    ui_all, published, claims_es = load_all()
    ALL_UI.update(ui_all)
    CLAIMS_ES = claims_es
    for l in LANGS:
        _UI_LOCALES[l] = ui_all[l]["locale"]
        ui_all[l]["back_to_archive"] = "BACK TO THE ARCHIVE ↗" if l == "en" else "VOLVER AL ARCHIVO ↗"

    has_og = build_og(ui_all)

    # Start from a clean slate for generated article pages so removed claims disappear.
    for folder in (ROOT / "claims", ROOT / "es" / "claims"):
        if folder.exists():
            shutil.rmtree(folder)

    for lang in LANGS:
        t = ui_all[lang]
        write("index.html" if lang == "en" else "es/index.html", build_index(lang, t, published, has_og))
        write("methodology.html" if lang == "en" else "es/metodologia.html", build_methodology(lang, t, has_og))
        for claim in published:
            rel = claim_path(lang, claim["slug"]).strip("/") + "/index.html"
            write(rel, build_article(lang, t, claim, published, ui_all, has_og))

    write("404.html", build_404(ui_all, has_og))
    write("sitemap.xml", build_sitemap(published))
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    write("favicon.svg", FAVICON)
    write("lang.js", LANG_JS)

    print(f"Built {len(published)} fact checks x {len(LANGS)} languages, plus index, methodology, 404, sitemap.")
    for w in warnings:
        print("  warning:", w)


if __name__ == "__main__":
    main()
