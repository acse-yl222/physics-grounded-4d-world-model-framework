/* Scene selection. Every scene lives in scenes/<id>/ with a scene.json that describes its grid, model, masks and field
   layers (see scenes/README.md); scenes/index.json lists them. ?scene=<id> picks one, otherwise the index's default. */
export const ROOT = new URL('../', import.meta.url).href;   // repository root (viewer/../)

export async function loadScene() {
  const custom = new URLSearchParams(location.search).get('scene_config');
  if(custom){
    const url=new URL(custom,location.href);
    if(url.origin!==location.origin || !/^\/project\/south_ken\/(runs|configs)\//.test(url.pathname))throw new Error('Custom scene config must be a local South Kensington project file');
    const response=await fetch(url,{cache:'no-cache'});if(!response.ok)throw new Error('Custom scene config: HTTP '+response.status);
    const scene=await response.json();
    if(scene.id!=='south_ken'||!scene.model?.url||!scene.grid)throw new Error('Invalid local scene configuration');
    scene.base=new URL('./',url).href;scene.physics=new URL(scene.physics_base||'physics/',scene.base).href;
    scene.url=rel=>new URL(rel,scene.base).href;scene.index={default:scene.id,scenes:[{id:scene.id,title:scene.title}]};return scene;
  }
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
  for (const k of [...qs.keys()]) if (!['lite', 'tile', 'expansion', 'scene_config'].includes(k)) qs.delete(k);
  qs.set('scene', id);
  return location.pathname + '?' + qs.toString();
}
