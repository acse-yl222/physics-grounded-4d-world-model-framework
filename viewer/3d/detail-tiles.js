// Level-of-detail city geometry: the coarse model stays loaded for the overview; when the camera comes close,
// fine 1 km tiles (detailed buildings + their landmarks) stream in and the coarse model is clipped away inside them.
// index.json (scene.model.detail_tiles): tiles[] with centre_xz, half_m, rotation_rad, file, landmarks[].file.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const MAX_RECTS = 16;

export function createDetailTiles({ scene, camera, coarse, indexUrl, onChange = () => {}, onStatus = () => {},
                                    radius = 650, keep = 900, maxTiles = 6, maxHeight = 1600 }) {
  const loader = new GLTFLoader();
  const base = new URL('./', indexUrl);
  const group = new THREE.Group(); group.name = 'detail_tiles'; scene.add(group);
  const uniforms = {
    uDetailRects: { value: Array.from({ length: MAX_RECTS }, () => new THREE.Vector4()) },
    uDetailCount: { value: 0 }, uDetailHalf: { value: 500 },
  };
  const state = new Map();   // id -> {tile, root, ready, loading, disposed}
  let tiles = [], enabled = true, busy = false, lastCheck = 0;
  const patched = new WeakSet();

  // Coarse model: discard fragments inside loaded detail tiles (oriented squares in viewer x/z).
  function patchMaterial(material) {
    if (patched.has(material)) return; patched.add(material);
    const previous = material.onBeforeCompile;
    material.onBeforeCompile = (shader, renderer) => {
      previous?.call(material, shader, renderer);
      Object.assign(shader.uniforms, uniforms);
      shader.vertexShader = 'varying vec2 vDetailW;\n' + shader.vertexShader.replace('#include <project_vertex>',
        '#include <project_vertex>\n  vDetailW = (modelMatrix * vec4(transformed, 1.0)).xz;');
      shader.fragmentShader = `varying vec2 vDetailW;\nuniform vec4 uDetailRects[${MAX_RECTS}];\nuniform int uDetailCount;\nuniform float uDetailHalf;\n`
        + shader.fragmentShader.replace('void main() {', `void main() {
  for (int i = 0; i < ${MAX_RECTS}; i++) {
    if (i >= uDetailCount) break;
    vec2 d = vDetailW - uDetailRects[i].xy;
    vec2 l = vec2(dot(d, uDetailRects[i].zw), dot(d, vec2(-uDetailRects[i].w, uDetailRects[i].z)));
    if (abs(l.x) < uDetailHalf && abs(l.y) < uDetailHalf) discard;
  }`);
    };
    const key = material.customProgramCacheKey?.bind(material);
    material.customProgramCacheKey = () => (key ? key() : '') + '|detail-clip';
    material.needsUpdate = true;
  }
  function patchCoarse() {
    coarse.traverse(o => { if (o.isMesh) (Array.isArray(o.material) ? o.material : [o.material]).forEach(patchMaterial); });
  }

  function refreshRects() {
    const ready = [...state.values()].filter(s => s.ready && !s.disposed).slice(0, MAX_RECTS);
    ready.forEach((s, i) => {
      const t = s.tile; uniforms.uDetailRects.value[i].set(t.centre_xz[0], t.centre_xz[1], Math.cos(t.rotation_rad), Math.sin(t.rotation_rad));
    });
    uniforms.uDetailCount.value = enabled ? ready.length : 0;
    if (ready[0]) uniforms.uDetailHalf.value = ready[0].tile.half_m;
    onChange();
  }

  function distanceTo(t, x, z) {
    const dx = x - t.centre_xz[0], dz = z - t.centre_xz[1], c = Math.cos(t.rotation_rad), s = Math.sin(t.rotation_rad);
    const lx = Math.abs(dx * c + dz * s) - t.half_m, lz = Math.abs(-dx * s + dz * c) - t.half_m;
    return Math.hypot(Math.max(0, lx), Math.max(0, lz));
  }

  function dispose(entry) {
    entry.disposed = true; entry.ready = false;
    if (entry.root) {
      group.remove(entry.root);
      entry.root.traverse(o => {
        if (o.geometry) o.geometry.dispose();
        (Array.isArray(o.material) ? o.material : o.material ? [o.material] : []).forEach(m => {
          Object.values(m).forEach(v => v?.isTexture && v.dispose()); m.dispose();
        });
      });
    }
    state.delete(entry.tile.id);
  }

  async function load(tile) {
    const entry = { tile, root: new THREE.Group(), ready: false, disposed: false };
    entry.root.name = `detail:${tile.id}`; state.set(tile.id, entry); group.add(entry.root);
    const files = [tile.file, ...tile.landmarks.map(l => l.file)].filter(Boolean);
    for (const [k, file] of files.entries()) {
      if (entry.disposed) return;
      onStatus(`Detail · ${tile.id} · ${k + 1}/${files.length}`);
      try {
        const gltf = await loader.loadAsync(new URL(file, base).href);
        if (entry.disposed) { gltf.scene.traverse(o => o.geometry?.dispose()); return; }
        entry.root.add(gltf.scene);
        if (k === 0 || !tile.file) { entry.ready = true; refreshRects(); }   // clip coarse once the tile's buildings are in
        onChange();
      } catch (error) { console.warn('detail tile part failed', file, error); }
    }
    onStatus('');
  }

  function update(now = performance.now()) {
    if (!tiles.length || now - lastCheck < 300) return; lastCheck = now;
    patchCoarse();
    const x = camera.position.x, z = camera.position.z, high = camera.position.y > maxHeight;
    const ranked = tiles.map(t => [distanceTo(t, x, z), t]).sort((a, b) => a[0] - b[0]);
    const wanted = new Set(enabled && !high ? ranked.filter(([d]) => d < radius).slice(0, maxTiles).map(([, t]) => t.id) : []);
    let changed = false;
    for (const entry of [...state.values()]) {
      const d = distanceTo(entry.tile, x, z);
      if (!wanted.has(entry.tile.id) && (high || !enabled || d > keep || state.size > maxTiles)) { dispose(entry); changed = true; }
    }
    if (changed) refreshRects();
    if (!busy) {
      const next = ranked.find(([, t]) => wanted.has(t.id) && !state.has(t.id));
      if (next) { busy = true; load(next[1]).finally(() => { busy = false; lastCheck = 0; }); }
    }
  }

  const ready = fetch(indexUrl).then(r => { if (!r.ok) throw new Error(`detail tiles: HTTP ${r.status}`); return r.json(); })
    .then(index => { tiles = index.tiles.filter(t => t.file || t.landmarks.length); patchCoarse(); onChange(); return tiles.length; });

  return {
    ready, update, group,
    setEnabled(on) { enabled = on; group.visible = on; refreshRects(); lastCheck = 0; },
    get loaded() { return [...state.values()].filter(s => s.ready).map(s => s.tile.id); },
  };
}
