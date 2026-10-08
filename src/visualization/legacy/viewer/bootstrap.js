// Keep recovery controls independent of WebGL and scene data initialization.
const windfarm = location.pathname.includes('/windfarm-movie/');
const root = new URL('../', import.meta.url);
const home = root.pathname.endsWith('/src/visualization/legacy/')
  ? new URL('../../../', root)
  : root;
const panel = document.createElement('section');
panel.id = 'viewer-error';
panel.hidden = true;
panel.setAttribute('role', 'alert');
panel.style.cssText =
  'position:fixed;inset:0;z-index:20;background:#101923ed;display:none;align-items:center;justify-content:center;padding:24px;color:#eef5fa;font:15px/1.6 system-ui';
const box = document.createElement('div');
box.style.maxWidth = '520px';
const title = document.createElement('h2');
title.textContent = 'Unable to display this scene';
const message = document.createElement('p');
message.id = 'viewer-error-message';
const actions = document.createElement('div');
actions.style.cssText = 'display:flex;gap:12px;flex-wrap:wrap';
function link(text, href, id) {
  const a = document.createElement('a');
  a.textContent = text;
  a.href = href;
  a.id = id;
  a.style.cssText =
    'background:#264b5b;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none';
  actions.append(a);
}
link('Retry', location.href, 'viewer-retry');
if (!windfarm) {
  const lite = new URL(location.href);
  lite.searchParams.set('lite', '1');
  link('Use lightweight geometry', lite.href, 'viewer-lite');
}
link('All scenes', home.href, 'viewer-home');
box.append(title, message, actions);
panel.append(box);
document.body.append(panel);
if (!windfarm) {
  const help = actions.cloneNode(true);
  for (const child of help.children) child.removeAttribute('id');
  document.querySelector('#loading .box')?.append(help);
}
function fail(error) {
  message.textContent = error?.message || String(error);
  panel.hidden = false;
  panel.style.display = 'flex';
  document.getElementById('viewer-retry').focus();
  console.error('Scene initialization failed:', error);
}
document.addEventListener(
  'webglcontextlost',
  (event) => {
    event.preventDefault();
    fail(
      new Error(
        'The browser lost its graphics context. Reload the scene, or try lightweight geometry on a city scene.',
      ),
    );
  },
  true,
);
window.addEventListener('viewer-context-lost', () =>
  fail(new Error('The browser lost its graphics context. Reload the scene to recover.')),
);
const quality = document.getElementById('geometry-quality');
if (quality) {
  const value = new URLSearchParams(location.search).get('lite');
  quality.value = value === '1' ? 'lite' : value === '0' ? 'full' : 'auto';
  quality.addEventListener('change', () => {
    const url = new URL(location.href);
    if (quality.value === 'auto') url.searchParams.delete('lite');
    else url.searchParams.set('lite', quality.value === 'lite' ? '1' : '0');
    location.assign(url.href);
  });
}
try {
  await import(windfarm ? './windfarm-movie/main.js' : './3d/main.js');
} catch (error) {
  fail(error);
}
