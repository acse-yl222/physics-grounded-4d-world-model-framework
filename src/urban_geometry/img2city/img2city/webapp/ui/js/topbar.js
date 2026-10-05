// topbar.js -- adds the Jobs nav link + active-job count badge to every page.
// Plain script; needs i18n.js first.
(function () {
  function init() {
    const nav = document.querySelector('.topbar .nav');
    if (!nav || document.getElementById('nav-jobs')) return;
    const a = document.createElement('a');
    a.id = 'nav-jobs';
    a.href = '/jobs.html';
    if (location.pathname === '/jobs.html') a.className = 'active';
    a.textContent = t('nav.jobs');
    const badge = document.createElement('span');
    badge.id = 'jobs-badge';
    badge.style.cssText = 'display:none;background:var(--accent);color:#08131f;' +
      'border-radius:99px;padding:0 7px;font-size:11px;font-weight:700;' +
      'margin-left:4px;vertical-align:1px';
    a.appendChild(badge);
    nav.appendChild(a);

    async function poll() {
      try {
        const { count } = await (await fetch('/api/jobs/active')).json();
        badge.style.display = count ? '' : 'none';
        badge.textContent = count;
      } catch (e) { /* server briefly away -- keep quiet */ }
    }
    poll();
    setInterval(poll, 6000);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
