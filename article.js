/* Legacy links: article.html?id=<date>|<title> now redirects to the permanent page /claims/<slug>/. */
(() => {
  'use strict';
  const id = new URLSearchParams(location.search).get('id');
  const message = document.querySelector('#message');
  const home = '/';

  function fail() {
    message.textContent = 'This entry may have moved. / Esta entrada pudo haberse movido.';
    const back = document.createElement('a');
    back.href = home;
    back.textContent = ' ← OhDonald';
    message.append(back);
  }

  if (!id) {
    location.replace(home);
    return;
  }

  fetch('/data/claims.json')
    .then((r) => {
      if (!r.ok) throw new Error('Archive unavailable');
      return r.json();
    })
    .then((rows) => {
      const hit = rows.find((x) => x.date + '|' + x.title === id && x.reviewed === true);
      if (hit && hit.slug) location.replace('/claims/' + hit.slug + '/');
      else fail();
    })
    .catch(fail);
})();
