// Shared navigation remains usable while an individual scene is loading.
const legacyRoot = new URL('../', import.meta.url);
const local = legacyRoot.pathname.endsWith('/src/visualization/legacy/');
const root = local ? new URL('../../../', legacyRoot) : legacyRoot;
const catalogue = new URL('src/visualization/public-scenes.json', root);
const select = document.getElementById('scene-select');
const home = document.getElementById('scene-home');
home.href = root.href;
const query = new URLSearchParams(location.search);
const current = location.pathname.includes('/windfarm-movie/')
  ? 'windfarm'
  : { south_kensington: 'south_ken', region: 'windfarm' }[query.get('scene')] ||
    query.get('scene') ||
    'south_ken';
try {
  const response = await fetch(catalogue, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Scene catalogue: HTTP ${response.status}`);
  const { scenes } = await response.json();
  select.replaceChildren(
    ...scenes.map((scene) => {
      const option = document.createElement('option');
      option.value = scene.scene_id;
      option.textContent = scene.title;
      const target = new URL(scene.viewer_url, root);
      // Carry rendering preferences through the windfarm round trip as well.
      for (const key of ['lite', 'tile', 'expansion']) {
        if (query.has(key)) target.searchParams.set(key, query.get(key));
      }
      option.dataset.url = target.href;
      return option;
    }),
  );
  select.value = current;
  select.disabled = false;
  select.addEventListener('change', () => {
    const target = select.selectedOptions[0]?.dataset.url;
    if (target) location.assign(target);
  });
} catch (error) {
  select.replaceChildren(new Option('Scenes unavailable — use Home', ''));
  select.disabled = true;
  console.error(error);
}
