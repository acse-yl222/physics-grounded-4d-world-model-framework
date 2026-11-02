// Retain every source mesh and transform; no distance eviction or simplification.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export function createDetailTiles({scene, coarse, indexUrl, onChange = () => {}}) {
  const group = new THREE.Group();
  group.name = 'complete_detail_geometry';
  scene.add(group);
  coarse.visible = false;
  const progress = {loaded: 0, total: 0, complete: false, errors: []};
  const loaded = [];
  const badge = document.createElement('div');
  badge.id = 'complete-geometry-status';
  badge.style.cssText = 'position:fixed;bottom:12px;left:12px;z-index:30;background:#10202ee8;color:white;padding:8px 12px;border-radius:6px;font:13px sans-serif;pointer-events:none';
  document.body.append(badge);
  function status() {
    badge.textContent = progress.errors.length
      ? `Geometry incomplete · ${progress.loaded}/${progress.total} assets · ${progress.errors.length} failed (reload to retry)`
      : progress.complete ? `Complete geometry · ${loaded.length} tiles · ${progress.loaded} assets`
      : `Loading complete geometry · ${progress.loaded}/${progress.total} assets`;
  }
  status();
  const ready = (async () => {
    const response = await fetch(indexUrl);
    if (!response.ok) throw new Error(`Geometry index HTTP ${response.status}`);
    const index = await response.json();
    const jobs = [];
    for (const tile of index.tiles) {
      const root = new THREE.Group(); root.name = `detail:${tile.id}`; group.add(root);
      const files = [tile.file, ...(tile.landmarks || []).map(l => l.file)].filter(Boolean);
      let remaining = files.length;
      for (const file of files) jobs.push(async loader => {
        const gltf = await loader.loadAsync(new URL(file, indexUrl).href);
        root.add(gltf.scene);
        progress.loaded++;
        if (--remaining === 0) loaded.push(tile.id);
      });
    }
    progress.total = jobs.length; status();
    let cursor = 0;
    await Promise.all(Array.from({length: 3}, async () => {
      const loader = new GLTFLoader();
      while (cursor < jobs.length) {
        const job = jobs[cursor++];
        try { await job(loader); }
        catch (error) { progress.errors.push(String(error)); console.error(error); }
        status(); onChange();
      }
    }));
    progress.complete = progress.errors.length === 0;
    status(); onChange();
    return loaded.length;
  })().catch(error => {progress.errors.push(String(error)); status(); console.error(error); return 0;});
  return {ready, group, progress, get loaded() {return [...loaded];},
    update() {coarse.visible = false;},
    setEnabled(on) {group.visible = on; coarse.visible = false; onChange();}};
}
