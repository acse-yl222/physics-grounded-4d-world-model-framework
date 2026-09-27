/* Scene selection. Every scene lives in scenes/<id>/ with a scene.json that describes its grid, model, masks and field
   layers (see scenes/README.md); scenes/index.json lists them. ?scene=<id> picks one, otherwise the index's default. */
export const ROOT = new URL('../', import.meta.url).href;   // repository root (viewer/../)

export async function loadScene() {
  const index = await (await fetch(ROOT + 'scenes/index.json', { cache: 'no-cache' })).json();
  const qs = new URLSearchParams(location.search);
  let id = qs.get('scene') || index.default;
  if (!index.scenes.some(s => s.id === id)) { console.warn('unknown scene', id, '- using', index.default); id = index.default; }
  const base = ROOT + 'scenes/' + id + '/';
  const r = await fetch(base + 'scene.json', { cache: 'no-cache' });
  if (!r.ok) throw new Error(`scene ${id}: ${base}scene.json is missing (HTTP ${r.status})`);
  const scene = await r.json();
  scene.id = id; scene.base = base; scene.physics = base + 'physics/'; scene.index = index;
  scene.url = rel => /^https?:/.test(rel) ? rel : base + rel;
  return scene;
}

/** URL of this page for another scene (keeps ?lite / ?tile style flags, drops view state). */
export function sceneLink(id) {
  const qs = new URLSearchParams(location.search);
  for (const k of [...qs.keys()]) if (!['lite', 'tile', 'expansion'].includes(k)) qs.delete(k);
  qs.set('scene', id);
  return location.pathname + '?' + qs.toString();
}
