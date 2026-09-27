// Build the classified asset library under assets/ from the city model and its companions.
//
//   node --experimental-loader ./geometry/completion/scripts/three-loader.mjs assets/tools/build_asset_library.mjs [--only main|supplement|refined|actors]
//
// Every exported file is a plain, uncompressed glTF binary (.glb) in the shared model frame (X east, Y up, Z south, metres;
// world transforms baked into the vertices), one node per source node with the source node's name and extras preserved, and
// colour-only PBR materials (the nine textured materials of the main model are exported with their base colour; the texture
// itself stays in the main model). Buildings get one folder per OSM id with original / refined / supplement GLBs and a meta.json.
import fs from 'node:fs';
import path from 'node:path';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const ROOT = process.cwd();
const OUT = path.join(ROOT, 'assets');
const only = (process.argv.find(a => a.startsWith('--only')) || '').split('=')[1] || null;
const index = { generated: new Date().toISOString(), frame: 'model metres, X east, Y up, Z south; EPSG:32630 minus (695238.304719173, 5709236.965026026) for X and -Z (north)', classes: {}, buildings: {} };
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

// ------------------------------------------------------------------ GLB writer (positions baked to world space)
const _v = new THREE.Vector3(), _n = new THREE.Vector3(), _nm = new THREE.Matrix3();
function align4(n) { return (n + 3) & ~3; }
function writeGLB(file, objects, { extrasRoot = {} } = {}) {
  const json = { asset: { version: '2.0', generator: 'UrbanWorldModel asset library' }, scene: 0, scenes: [{ nodes: [] }], nodes: [], meshes: [], materials: [], accessors: [], bufferViews: [], buffers: [] };
  const chunks = []; let byteLength = 0;
  const matIndex = new Map();
  function addBuffer(typed, target) {
    const bv = { buffer: 0, byteOffset: byteLength, byteLength: typed.byteLength }; if (target) bv.target = target;
    json.bufferViews.push(bv); chunks.push(typed); byteLength = align4(byteLength + typed.byteLength);
    if (byteLength - (bv.byteOffset + typed.byteLength) > 0) chunks.push(new Uint8Array(byteLength - (bv.byteOffset + typed.byteLength)));
    return json.bufferViews.length - 1;
  }
  function addAccessor(typed, type, componentType, count, minmax) {
    const a = { bufferView: addBuffer(typed, componentType === 5125 || componentType === 5123 ? 34963 : 34962), componentType, count, type };
    if (minmax) { a.min = minmax[0]; a.max = minmax[1]; }
    json.accessors.push(a); return json.accessors.length - 1;
  }
  function material(m) {
    if (matIndex.has(m.uuid)) return matIndex.get(m.uuid);
    const c = m.color || new THREE.Color(0.8, 0.8, 0.8);
    const mat = { name: m.name || 'material', pbrMetallicRoughness: { baseColorFactor: [c.r, c.g, c.b, m.opacity ?? 1], metallicFactor: m.metalness ?? 0, roughnessFactor: m.roughness ?? 1 } };
    if (m.transparent && (m.opacity ?? 1) < 1) mat.alphaMode = 'BLEND';
    if (m.side === THREE.DoubleSide) mat.doubleSided = true;
    if (m.emissive && (m.emissive.r || m.emissive.g || m.emissive.b)) mat.emissiveFactor = [m.emissive.r, m.emissive.g, m.emissive.b];
    if (m.map) mat.extras = { textured_in_source: true };
    json.materials.push(mat); matIndex.set(m.uuid, json.materials.length - 1); return json.materials.length - 1;
  }
  let tris = 0;
  for (const o of objects) {
    if (!o.isMesh) continue;
    const g = o.geometry, pos = g.attributes.position, n = pos.count;
    const world = o.matrixWorld; _nm.getNormalMatrix(world);
    const P = new Float32Array(n * 3); const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < n; i++) { _v.fromBufferAttribute(pos, i).applyMatrix4(world); P[i * 3] = _v.x; P[i * 3 + 1] = _v.y; P[i * 3 + 2] = _v.z; for (let k = 0; k < 3; k++) { const x = P[i * 3 + k]; if (x < min[k]) min[k] = x; if (x > max[k]) max[k] = x; } }
    const attributes = { POSITION: addAccessor(P, 'VEC3', 5126, n, [min, max]) };
    if (g.attributes.normal) { const N = new Float32Array(n * 3), na = g.attributes.normal; for (let i = 0; i < n; i++) { _n.fromBufferAttribute(na, i).applyMatrix3(_nm).normalize(); N[i * 3] = _n.x; N[i * 3 + 1] = _n.y; N[i * 3 + 2] = _n.z; } attributes.NORMAL = addAccessor(N, 'VEC3', 5126, n); }
    if (g.attributes.uv) { const U = new Float32Array(n * 2), ua = g.attributes.uv; for (let i = 0; i < n; i++) { U[i * 2] = ua.getX(i); U[i * 2 + 1] = ua.getY(i); } attributes.TEXCOORD_0 = addAccessor(U, 'VEC2', 5126, n); }
    if (g.attributes.color) { const ca = g.attributes.color, s = ca.itemSize, C = new Float32Array(n * s); for (let i = 0; i < n; i++) { C[i * s] = ca.getX(i); C[i * s + 1] = ca.getY(i); C[i * s + 2] = ca.getZ(i); if (s === 4) C[i * s + 3] = ca.getW(i); } attributes.COLOR_0 = addAccessor(C, s === 4 ? 'VEC4' : 'VEC3', 5126, n); }
    const idx = g.index ? g.index.array : Uint32Array.from({ length: n }, (_, i) => i);
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const groups = (Array.isArray(o.material) && g.groups.length) ? g.groups : [{ start: 0, count: idx.length, materialIndex: 0 }];
    const primitives = [];
    for (const grp of groups) {
      const count = grp.count === Infinity ? idx.length - grp.start : grp.count;
      const slice = idx.subarray ? idx.subarray(grp.start, grp.start + count) : idx.slice(grp.start, grp.start + count);
      const I = n < 65536 ? Uint16Array.from(slice) : Uint32Array.from(slice);
      primitives.push({ attributes, indices: addAccessor(I, 'SCALAR', n < 65536 ? 5123 : 5125, I.length), material: material(mats[grp.materialIndex] || mats[0]), mode: 4 });
      tris += count / 3;
    }
    json.meshes.push({ name: o.name, primitives });
    const node = { name: o.name, mesh: json.meshes.length - 1 };
    const extras = { ...(o.userData || {}) }; for (const a = { p: o.parent }; a.p && a.p.parent; a.p = a.p.parent) for (const [k, v] of Object.entries(a.p.userData || {})) if (!(k in extras)) extras[k] = v;
    if (Object.keys(extras).length) node.extras = extras;
    json.nodes.push(node); json.scenes[0].nodes.push(json.nodes.length - 1);
  }
  json.buffers.push({ byteLength });
  if (Object.keys(extrasRoot).length) json.asset.extras = extrasRoot;
  const jsonStr = JSON.stringify(json); const jsonBytes = Buffer.from(jsonStr, 'utf8'); const jsonPad = align4(jsonBytes.length);
  const header = Buffer.alloc(12 + 8 + jsonPad + 8 + byteLength);
  header.writeUInt32LE(0x46546C67, 0); header.writeUInt32LE(2, 4); header.writeUInt32LE(header.length, 8);
  header.writeUInt32LE(jsonPad, 12); header.writeUInt32LE(0x4E4F534A, 16); jsonBytes.copy(header, 20); header.fill(0x20, 20 + jsonBytes.length, 20 + jsonPad);
  let off = 20 + jsonPad; header.writeUInt32LE(byteLength, off); header.writeUInt32LE(0x004E4942, off + 4); off += 8;
  for (const c of chunks) { Buffer.from(c.buffer, c.byteOffset, c.byteLength).copy(header, off); off += c.byteLength; }
  fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, header);
  return { bytes: header.length, tris: Math.round(tris), meshes: json.meshes.length };
}
function meshesOf(objs) { const out = []; for (const o of objs) o.traverse(m => { if (m.isMesh) out.push(m); }); return out; }
function bbox(objs) { const b = new THREE.Box3(); for (const m of meshesOf(objs)) { if (!m.geometry.boundingBox) m.geometry.computeBoundingBox(); b.union(new THREE.Box3().copy(m.geometry.boundingBox).applyMatrix4(m.matrixWorld)); } return b.isEmpty() ? null : [b.min.toArray().map(v => +v.toFixed(2)), b.max.toArray().map(v => +v.toFixed(2))]; }
function safe(s) { return s.replace(/[^A-Za-z0-9_.-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 80) || 'node'; }

async function loadGLB(file) {
  const b = fs.readFileSync(file);
  const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
  loader.register(() => ({ name: 'NoTextures', loadTexture: () => Promise.resolve(null) }));
  const gltf = await loader.parseAsync(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), '');
  gltf.scene.updateMatrixWorld(true); return gltf;
}
function record(cls, entry) { (index.classes[cls] ||= []).push(entry); }

// ------------------------------------------------------------------ classification of the main model's top-level nodes
function classify(top) {
  const n = top.name, layer = top.userData?.layer || '';
  if (/^Traffic_road/.test(n)) return ['roads/traffic_lanes', 'street'];
  if (/^(Mapped_roads|Perimeter_roads|Four_perimeter_roads|East_road_correction)/.test(n)) return ['roads/campus', 'node'];
  if (/^(Site_\|_ground|Central_ground|Garden_|Mapped_paths|Entry_approaches|Dalby_Court|William_Penney_shared_landing)/.test(n)) return ['ground', 'node'];
  if (/^Site_\|_(road-network|path-network)/.test(n)) return ['roads/site_network', 'node'];   // the site's own road / path surfaces (campus preview)
  if (/^Site_\|_(way-|relation-)/.test(n)) return ['ground/site_polygons', 'node'];
  if (/^Site_\|_/.test(n)) return ['ground', 'node'];   // forecourts, entrance paving, datum plinth
  if (/^(Tree_|Estimated_planting|Public_realm_tree)/.test(n)) return ['vegetation/trees', 'node'];
  if (/^Mapped_core_landscape/.test(n)) return ['vegetation/landscape', 'node'];
  if (/^AERIAL-VEHICLE/.test(n)) return ['parked_vehicles', 'node'];
  if (/^(OSM-|Public_realm_fixtures|AERIAL-PLANTER|Huxley-Sherfield_mapped_covered_walkway)/.test(n)) return ['street_furniture', 'node'];
  if (/^Traffic_vehicle/.test(n) || layer === 'traffic_vehicle') return ['simulation_layers/traffic_vehicle', 'bundle'];
  if (/^Traffic_prediction/.test(n) || layer === 'traffic_prediction') return ['simulation_layers/traffic_prediction', 'bundle'];
  if (/^Bird_site/.test(n)) return ['simulation_layers/bird_sites', 'bundle'];
  if (/^Bird/.test(n) || layer === 'bird') return ['simulation_layers/birds', 'bundle'];
  return ['unclassified', 'node'];
}

// ------------------------------------------------------------------ 1. main model
async function exportMain() {
  log('loading main model…');
  const gltf = await loadGLB(path.join(ROOT, 'models', 'south_kensington_core008_web.glb'));
  const assetIndex = JSON.parse(fs.readFileSync(path.join(ROOT, 'geometry', 'expansion', 'asset_index.json'), 'utf8'));
  const byId = new Map(); for (const b of assetIndex.buildings) byId.set(b.id, b);
  const osm = JSON.parse(fs.readFileSync(path.join(ROOT, 'geometry', 'completion', 'sources', 'osm_buildings.json'), 'utf8'));
  const tags = new Map(); for (const e of osm.elements) if (e.tags) tags.set(`${e.type}-${e.id}`, e.tags);
  const buildings = new Map(); const bundles = new Map(); const streets = new Map();
  let done = 0;
  for (const top of gltf.scene.children) {
    let id = top.userData?.building_id; if (!id) top.traverse(o => { if (!id && o.userData?.building_id) id = o.userData.building_id; });
    if (id) { (buildings.get(id) || buildings.set(id, []).get(id)).push(top); continue; }
    const [cls, mode] = classify(top);
    if (mode === 'bundle') { (bundles.get(cls) || bundles.set(cls, []).get(cls)).push(top); continue; }
    if (mode === 'street') { const st = safe((top.name.split('_|_')[1] || 'unnamed')); (streets.get(st) || streets.set(st, []).get(st)).push(top); continue; }
    const file = path.join(OUT, cls, safe(top.name) + '.glb');
    const r = writeGLB(file, meshesOf([top]));
    record(cls, { name: top.name, file: path.relative(OUT, file), bbox: bbox([top]), ...r, source: 'south_kensington_core008_web.glb' });
    if (++done % 200 === 0) log(done, 'non-building nodes');
  }
  for (const [st, tops] of streets) { const file = path.join(OUT, 'roads/traffic_lanes', st + '.glb'); const r = writeGLB(file, meshesOf(tops)); record('roads/traffic_lanes', { name: st, nodes: tops.length, file: path.relative(OUT, file), bbox: bbox(tops), ...r, source: 'south_kensington_core008_web.glb' }); }
  for (const [cls, tops] of bundles) { const file = path.join(OUT, cls, path.basename(cls) + '.glb'); const r = writeGLB(file, meshesOf(tops)); record(cls, { name: cls, nodes: tops.length, file: path.relative(OUT, file), bbox: bbox(tops), ...r, source: 'south_kensington_core008_web.glb', note: 'hidden in the viewer (demo_rev02 city filter); superseded by the replay layers' }); }
  log('buildings:', buildings.size);
  let k = 0;
  for (const [id, tops] of buildings) {
    const dir = path.join(OUT, 'buildings', id); const file = path.join(dir, 'original.glb');
    const r = writeGLB(file, meshesOf(tops));
    const ai = byId.get(id); let fidelity = null, names = new Set();
    for (const t of tops) t.traverse(o => { if (o.userData?.geometry_fidelity && !fidelity) fidelity = o.userData.geometry_fidelity; });
    for (const t of tops) names.add((t.name.split('_|_')[0] || '').replace(/_/g, ' '));
    const detail = fidelity && /procedural/i.test(fidelity) ? 'procedural_baseline' : 'authored_detail';
    const meta = { id, names: ai ? ai.names : [...names], detail_class: detail, geometry_fidelity: fidelity, statuses: ai?.statuses, osm_tags: tags.get(id) || null, bbox: bbox(tops), nodes: tops.map(t => t.name), triangles: r.tris, files: { original: 'original.glb' }, source: { original: 'south_kensington_core008_web.glb' } };
    fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify(meta, null, 1));
    const prev = index.buildings[id];   // keep supplement / refined flags from earlier runs
    index.buildings[id] = { ...(prev || {}), dir: path.relative(OUT, dir), detail_class: detail, names: meta.names, bbox: meta.bbox, triangles: r.tris, has: [...new Set([...(prev?.has || []), 'original'])] };
    if (++k % 500 === 0) log(k, 'buildings');
  }
}

// ------------------------------------------------------------------ 2. supplement (306 OSM footprints)
async function exportSupplement() {
  log('supplement…');
  const gltf = await loadGLB(path.join(ROOT, 'models', 'buildings_supplement.glb'));
  const groups = new Map();
  gltf.scene.traverse(o => { if (o.isMesh) { let id = null; for (let a = o; a && !id; a = a.parent) id = a.userData?.building_id || null; if (id) (groups.get(id) || groups.set(id, []).get(id)).push(o); } });
  for (const [id, meshes] of groups) {
    const dir = path.join(OUT, 'buildings', id); const file = path.join(dir, 'supplement.glb'); const r = writeGLB(file, meshes);
    const metaFile = path.join(dir, 'meta.json'); const meta = fs.existsSync(metaFile) ? JSON.parse(fs.readFileSync(metaFile, 'utf8')) : { id, names: [meshes[0].parent?.name || id], detail_class: 'supplement_estimated', bbox: null, files: {}, source: {} };
    meta.files.supplement = 'supplement.glb'; meta.source.supplement = 'geometry/completion/output/buildings_supplement.glb'; meta.bbox ||= bbox(meshes); meta.supplement_triangles = r.tris;
    fs.writeFileSync(metaFile, JSON.stringify(meta, null, 1));
    const e = index.buildings[id] ||= { dir: path.relative(OUT, dir), detail_class: 'supplement_estimated', names: meta.names, bbox: meta.bbox, triangles: r.tris, has: [] }; if (!e.has.includes('supplement')) e.has.push('supplement');
  }
  log('supplement buildings:', groups.size);
}

// ------------------------------------------------------------------ 3. refined buildings (geometry/expansion batches)
async function exportRefined() {
  const src = fs.readFileSync(path.join(ROOT, 'viewer', '3d', 'expansion.js'), 'utf8');
  const urls = [...new Set([...src.matchAll(/'(\.\.\/\.\.\/geometry\/expansion\/output\/[^'?]+\.glb)/g)].map(m => m[1].replace('../../', '')))];
  const manifests = new Map();
  for (const m of fs.readdirSync(path.join(ROOT, 'geometry', 'expansion')).filter(d => /^(batch|revision)/.test(d))) {
    const f = path.join(ROOT, 'geometry', 'expansion', m, 'manifest.json'); if (!fs.existsSync(f)) continue;
    for (const feat of JSON.parse(fs.readFileSync(f, 'utf8')).features) manifests.set(feat.id, { batch: m, ...feat });
  }
  const pilotFile = path.join(ROOT, 'geometry', 'expansion', 'feature.json');   // the pilot building has no batch manifest
  if (fs.existsSync(pilotFile)) { const f = JSON.parse(fs.readFileSync(pilotFile, 'utf8')); if (!manifests.has(f.id)) manifests.set(f.id, { batch: 'pilot', slug: 'kensington_gore_23', ...f }); }
  let n = 0;
  for (const rel of urls) {
    const file = path.join(ROOT, rel); if (!fs.existsSync(file)) { log('missing', rel); continue; }
    const gltf = await loadGLB(file); const groups = new Map();
    gltf.scene.traverse(o => { if (o.isMesh) { let id = null; for (let a = o; a && !id; a = a.parent) id = a.userData?.building_id || null; if (id) (groups.get(id) || groups.set(id, []).get(id)).push(o); } });
    for (const [id, meshes] of groups) {
      const dir = path.join(OUT, 'buildings', id); const out = path.join(dir, 'refined.glb'); const r = writeGLB(out, meshes);
      const mf = manifests.get(id); const metaFile = path.join(dir, 'meta.json');
      const meta = fs.existsSync(metaFile) ? JSON.parse(fs.readFileSync(metaFile, 'utf8')) : { id, names: [mf?.name || id], files: {}, source: {} };
      meta.files.refined = 'refined.glb'; meta.source.refined = rel; meta.refined = mf ? { batch: mf.batch, name: mf.name, slug: mf.slug, levels: mf.levels, height_m: mf.height_m, height_basis: mf.height_basis, area_m2: mf.area_m2, footprint_ring_xy_north: mf.ring } : { batch: null }; meta.refined_triangles = r.tris;
      // renders and editable source next to the building
      if (mf) { for (const cand of [path.join(ROOT, 'geometry', 'expansion', 'output', mf.batch + '_v1', mf.slug + '_front.png'), path.join(ROOT, 'geometry', 'expansion', 'output', mf.slug + '_v1', 'front.png')]) if (fs.existsSync(cand)) { fs.copyFileSync(cand, path.join(dir, 'refined_front.png')); meta.files.refined_front = 'refined_front.png'; break; } const mod = [path.join(ROOT, 'geometry', 'expansion', mf.batch, 'modules', mf.slug + '.py'), path.join(ROOT, 'geometry', 'expansion', 'modules', mf.slug + '.py')].find(fs.existsSync) || ''; if (fs.existsSync(mod)) { fs.copyFileSync(mod, path.join(dir, 'refined_module.py')); meta.files.refined_module = 'refined_module.py'; } }
      fs.writeFileSync(metaFile, JSON.stringify(meta, null, 1));
      const e = index.buildings[id] ||= { dir: path.relative(OUT, dir), detail_class: 'refined', names: meta.names, bbox: bbox(meshes), triangles: r.tris, has: [] }; if (!e.has.includes('refined')) e.has.push('refined'); e.refined_batch = mf?.batch || null;
      n++;
    }
  }
  log('refined buildings:', n, 'from', urls.length, 'files');
}

// ------------------------------------------------------------------ 4. actors (moving agents) and pointers to the big companions
function exportActors() {
  const copies = [
    ['agents/demo_rev02/assets/hexacopter_cargo.glb', 'actors/uav/hexacopter_cargo.glb', 'cargo UAV model used by the NVMF replay (1.3 m wide; enlarged 4x in the wide shot)'],
    ['agents/demo_rev02/actors/pigeon.glb', 'actors/birds/pigeon.glb', 'low-poly pigeon, instanced for the flock replay'],
    ['agents/demo_rev02/actors/build_pigeon.mjs', 'actors/birds/build_pigeon.mjs', 'generator of pigeon.glb'],
    ['agents/demo_rev02/actors/pigeon_geometry_QA.json', 'actors/birds/pigeon_geometry_QA.json', 'QA record for pigeon.glb'],
    ['agents/demo_rev02/actors/sedan_4p5m.glb', 'actors/vehicles/sedan_4p5m.glb', 'the 4.5 m sedan used for every SUMO car (instanced, per-id colour)'],
    ['agents/demo_rev02/actors/build_sedan.mjs', 'actors/vehicles/build_sedan.mjs', 'generator of the 4.5 m sedan used for every SUMO car (built at runtime by actor-layer.js; instanced, per-id colour)'],
    ['agents/demo_rev02/actors/actor-layer.js', 'actors/actor-layer.js', 'instanced car / UAV layer (three.js) that consumes these models'],
    ['agents/demo_rev02/actors/README.md', 'actors/README.md', 'actor layer documentation'],
  ];
  for (const [src, dst, note] of copies) { const s = path.join(ROOT, src), d = path.join(OUT, dst); if (!fs.existsSync(s)) { log('missing', src); continue; } fs.mkdirSync(path.dirname(d), { recursive: true }); fs.copyFileSync(s, d); record('actors', { file: dst, bytes: fs.statSync(d).size, source: src, note }); }
  record('pointers', { name: 'station detail tile', file: '../south_kensington_current.glb', note: '180 MB Blender export of the 390 x 400 m plate around South Kensington station; placed by viewer/3d/tile.js with a rigid transform (+0.03799 rad about Y, +(901.85, 0.3, 689.57) m); ?tile=1' });
  record('pointers', { name: 'main city model', file: '../south_kensington_core008_web.glb', note: 'source of buildings/*/original.glb and the ground / roads / vegetation / street_furniture / parked_vehicles / simulation_layers classes' });
  record('pointers', { name: 'traffic replay and lane ribbons', file: '../demo_rev02/data/', note: 'roads.json (6,209 drivable lane ribbons), traffic/replay/*, signal_layer_v2.json, schedule.json, birds_southken/' });
}

// ------------------------------------------------------------------ run
fs.mkdirSync(OUT, { recursive: true });
const indexFile = path.join(OUT, 'index.json');
if (only && fs.existsSync(indexFile)) Object.assign(index, JSON.parse(fs.readFileSync(indexFile, 'utf8')), { generated: index.generated });
if (only === 'main') for (const k of Object.keys(index.classes)) if (!['actors', 'pointers'].includes(k)) delete index.classes[k];   // main re-export rebuilds every model-derived class
if (!only || only === 'main') await exportMain();
if (!only || only === 'supplement') await exportSupplement();
if (!only || only === 'refined') await exportRefined();
if (!only || only === 'actors') exportActors();
// summary
const summary = {};
for (const [cls, list] of Object.entries(index.classes)) summary[cls] = { files: list.length, triangles: list.reduce((a, e) => a + (e.tris || 0), 0), bytes: list.reduce((a, e) => a + (e.bytes || 0), 0) };
const bl = Object.values(index.buildings);
summary.buildings = { folders: bl.length, authored_detail: bl.filter(b => b.detail_class === 'authored_detail').length, procedural_baseline: bl.filter(b => b.detail_class === 'procedural_baseline').length, supplement: bl.filter(b => b.has.includes('supplement')).length, refined: bl.filter(b => b.has.includes('refined')).length, triangles: bl.reduce((a, b) => a + (b.triangles || 0), 0) };
index.summary = summary;
fs.writeFileSync(indexFile, JSON.stringify(index));
log('done', JSON.stringify(summary));
