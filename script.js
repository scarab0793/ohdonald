/* OhDonald — front end for the archive pages (index.html and es/index.html).
 * The page text is pre-rendered by scripts/build.py; this file only fills in the dynamic
 * parts (feed, filters, contradiction tracker). All data is inserted with textContent,
 * never innerHTML. */
(() => {
  'use strict';

  const LANG = document.documentElement.lang === 'es' ? 'es' : 'en';
  const PREFIX = LANG === 'es' ? '/es' : '';
  const VERDICT_ORDER = ['False', 'Misleading', 'Needs context', 'Unsupported', 'Supported'];

  const $ = (selector) => document.querySelector(selector);

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  /* Only http(s) links are ever written into href attributes. */
  const safeUrl = (url) => (/^https?:\/\//i.test(url || '') ? url : '#');

  function link(href, text, external) {
    const a = el('a', '', text);
    a.href = safeUrl(href);
    if (external) {
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
    }
    return a;
  }

  function fmtDate(iso) {
    try {
      return new Intl.DateTimeFormat(LANG, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(iso + 'T00:00:00Z'));
    } catch (_) {
      return iso;
    }
  }

  /* Lower-case and strip accents so "economia" finds "Economía". */
  const normalize = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  async function getJSON(url, optional) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(url + ' ' + response.status);
      return await response.json();
    } catch (error) {
      if (optional) return {};
      throw error;
    }
  }

  const state = { ui: null, items: [], pairs: [], year: '', section: 'checks' };

  /* ---------- Data ---------- */

  async function loadData() {
    const wantEs = LANG === 'es';
    const [uiAll, claims, contradictions, claimsEs, contradictionsEs] = await Promise.all([
      getJSON('/data/ui.json'),
      getJSON('/data/claims.json'),
      getJSON('/data/contradictions.json'),
      wantEs ? getJSON('/data/claims.es.json', true) : {},
      wantEs ? getJSON('/data/contradictions.es.json', true) : {},
    ]);

    state.ui = uiAll[LANG];

    state.items = claims
      .filter((x) => x.reviewed === true && Array.isArray(x.sources) && x.sources.length)
      .map((x) => {
        const tr = claimsEs[x.slug] || {};
        const topic = (state.ui.topics && state.ui.topics[x.topic]) || x.topic;
        return {
          raw: x,
          slug: x.slug,
          date: x.date,
          topic,
          verdict: x.verdict,
          translated: LANG === 'en' || Boolean(tr.title),
          title: tr.title || x.title,
          claim: tr.claim || x.claim,
          summary: tr.summary || x.summary,
          venue: tr.statementVenue || x.statementVenue,
          statementDate: x.statementDate,
          sources: x.sources.map((s, i) => ({ url: s.url, label: (tr.sourceLabels && tr.sourceLabels[i]) || s.label })),
          haystack: normalize([x.title, x.claim, x.topic, x.summary, tr.title, tr.claim, tr.summary, topic].join(' ')),
        };
      })
      .sort((a, b) => b.date.localeCompare(a.date));

    state.pairs = contradictions
      .filter((p) => p.reviewed === true && p.before && p.after && p.before.url && p.after.url
        && p.before.quote && p.after.quote && p.before.date && p.after.date)
      .map((p) => ({ raw: p, tr: contradictionsEs[p.id] || {} }))
      .sort((a, b) => b.raw.after.date.localeCompare(a.raw.after.date));
  }

  /* ---------- Rendering ---------- */

  function markUntranslated(node, item) {
    if (!item.translated) node.lang = 'en';
    return node;
  }

  function verdictBadge(verdict) {
    const info = state.ui.verdicts[verdict] || { label: verdict, quip: '' };
    const wrap = el('span');
    const badge = el('span', 'verdict', info.label);
    badge.dataset.verdict = verdict;
    wrap.append(badge);
    if (info.quip) wrap.append(document.createTextNode(' '), el('span', 'quip', '· ' + info.quip));
    return wrap;
  }

  function renderCard(item) {
    const ui = state.ui;
    const article = el('article', 'story');

    const meta = el('div', 'meta');
    meta.append(el('b', '', item.topic), document.createTextNode(' · '));
    meta.append(document.createTextNode(item.statementDate
      ? ui.said + ' ' + fmtDate(item.statementDate)
      : ui.archived + ' ' + fmtDate(item.date)));
    meta.append(document.createTextNode(' · '), verdictBadge(item.verdict));

    const heading = el('h3');
    const titleLink = el('a', 'story-link', item.title);
    titleLink.href = PREFIX + '/claims/' + item.slug + '/';
    markUntranslated(titleLink, item);
    heading.append(titleLink);

    const where = el('p', 'statement-location', item.venue ? ui.where + ': ' + item.venue : ui.whereUnknown);
    if (item.venue) markUntranslated(where, item);

    const summary = markUntranslated(el('p', '', item.summary), item);

    const sources = el('div', 'source-links');
    for (const s of item.sources) sources.append(link(s.url, s.label + ' ↗', true));

    article.append(meta, heading, where, summary, sources);
    return article;
  }

  function matches(item, query, verdict) {
    return (!state.year || item.date.startsWith(state.year))
      && (!verdict || item.verdict === verdict)
      && (!query || item.haystack.includes(query));
  }

  function renderFeed() {
    const ui = state.ui;
    const query = normalize($('#search').value.trim());
    const verdict = $('#verdict').value;
    const filtered = state.items.filter((item) => matches(item, query, verdict));

    $('#count').textContent = ui.count.replace('{n}', filtered.length);

    const cards = $('#cards');
    cards.replaceChildren();
    if (!filtered.length) cards.append(el('p', 'empty', ui.empty));
    for (const item of filtered) cards.append(renderCard(item));
  }

  function renderSidebar() {
    const side = $('#side-items');
    side.replaceChildren();
    for (const item of state.items.slice(0, 9)) {
      const row = el('div', 'side-item');
      row.append(el('small', '', item.topic.toUpperCase() + ' · ' + fmtDate(item.date)));
      const a = el('a', '', item.title);
      a.href = PREFIX + '/claims/' + item.slug + '/';
      markUntranslated(a, item);
      row.append(a);
      side.append(row);
    }
  }

  /* The year list always runs from the oldest entry to the current year, so nothing is hard-coded. */
  function yearRange() {
    const years = state.items.map((x) => Number(x.date.slice(0, 4)));
    const first = years.length ? Math.min(...years) : new Date().getFullYear();
    const last = Math.max(new Date().getFullYear(), ...(years.length ? years : [first]));
    const out = [];
    for (let y = first; y <= last; y++) out.push(String(y));
    return out;
  }

  function renderYears() {
    const root = $('#years');
    root.replaceChildren();
    for (const y of ['', ...yearRange()]) {
      const button = el('button', '', y || state.ui.allYears);
      button.type = 'button';
      button.setAttribute('aria-pressed', String(state.year === y));
      button.addEventListener('click', () => {
        state.year = y;
        renderYears();
        renderFeed();
      });
      root.append(button);
    }
  }

  function renderCoverage() {
    const grid = $('#coverage-grid');
    grid.replaceChildren();
    for (const y of yearRange()) {
      const n = state.items.filter((x) => x.date.startsWith(y)).length;
      const cell = el('span', n ? 'has' : '', y + ' · ' + n);
      grid.append(cell);
    }
  }

  function quotePanel(label, side, tr) {
    const ui = state.ui;
    const panel = el('div', 'quote-panel');
    panel.append(el('strong', '', label + ' · ' + fmtDate(side.date)));

    const translated = LANG === 'es' && tr && tr.quote;
    const quote = el('blockquote', '', translated ? tr.quote : side.quote);
    if (LANG === 'es' && !translated) quote.lang = 'en';
    panel.append(quote);
    if (translated) {
      const orig = el('p', 'orig', ui.original + ': “' + side.quote + '”');
      orig.lang = 'en';
      panel.append(orig);
    }

    const whereText = (tr && tr.where) || side.where;
    if (whereText) {
      const where = el('p', 'where', ui.where + ': ' + whereText);
      if (LANG === 'es' && !(tr && tr.where)) where.lang = 'en';
      panel.append(where);
    }
    panel.append(link(side.url, ui.readSource, true));
    return panel;
  }

  function renderPairs() {
    const ui = state.ui;
    const list = $('#pairs-list');
    list.replaceChildren();
    if (!state.pairs.length) list.append(el('p', 'empty', ui.emptyPairs));

    for (const { raw: p, tr } of state.pairs) {
      const article = el('article', 'pair');
      article.id = p.id;
      const title = el('h3', '', tr.title || p.title);
      if (LANG === 'es' && !tr.title) title.lang = 'en';
      article.append(title);
      article.append(quotePanel(ui.then, p.before, tr.before), quotePanel(ui.andThen, p.after, tr.after));

      const context = el('p', 'pair-context', tr.context || p.context || '');
      if (LANG === 'es' && !tr.context) context.lang = 'en';
      article.append(context);

      if (Array.isArray(p.moreSources) && p.moreSources.length) {
        const more = el('div', 'source-links');
        more.append(el('span', 'statement-location', ui.moreSources + ':'));
        p.moreSources.forEach((s, i) => {
          const label = (tr.moreSourceLabels && tr.moreSourceLabels[i]) || s.label;
          more.append(link(s.url, label + ' ↗', true));
        });
        article.append(more);
      }
      list.append(article);
    }
  }

  /* ---------- Tabs ---------- */

  function switchSection(name, updateHash) {
    state.section = name;
    document.querySelectorAll('[role="tab"]').forEach((tab) => {
      const active = tab.dataset.section === name;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    $('#checks-section').hidden = name !== 'checks';
    $('#pairs-section').hidden = name !== 'pairs';
    if (updateHash) {
      try {
        history.replaceState(null, '', name === 'pairs' ? '#pairs' : location.pathname + location.search);
      } catch (_) { /* ignore: history may be unavailable */ }
    }
  }

  function setupTabs() {
    const tabs = [...document.querySelectorAll('[role="tab"]')];
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => switchSection(tab.dataset.section, true));
      tab.addEventListener('keydown', (event) => {
        if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
        const next = tabs[(i + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
        next.focus();
        switchSection(next.dataset.section, true);
      });
    });
    switchSection(location.hash === '#pairs' ? 'pairs' : 'checks', false);
  }

  /* ---------- Boot ---------- */

  function setupFilters() {
    const select = $('#verdict');
    for (const key of VERDICT_ORDER) {
      const option = el('option', '', (state.ui.verdicts[key] || { label: key }).label);
      option.value = key;
      select.append(option);
    }
    $('#search').addEventListener('input', renderFeed);
    select.addEventListener('change', renderFeed);
  }

  function showError() {
    const message = (state.ui && state.ui.loadError) || 'The archive is temporarily unavailable.';
    const retry = (state.ui && state.ui.retry) || 'Try again';
    const box = el('div', 'error', message);
    box.setAttribute('role', 'alert');
    const button = el('button', '', retry);
    button.type = 'button';
    button.addEventListener('click', () => location.reload());
    box.append(button);
    $('#cards').replaceChildren(box);
  }

  async function init() {
    setupTabs();
    try {
      await loadData();
    } catch (error) {
      console.error(error);
      showError();
      return;
    }
    setupFilters();
    renderYears();
    renderSidebar();
    renderCoverage();
    renderFeed();
    renderPairs();
  }

  init();
})();
