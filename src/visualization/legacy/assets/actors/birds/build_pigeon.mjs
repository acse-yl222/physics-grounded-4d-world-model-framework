// Procedural feral-pigeon display asset for the bird layer (CO, 2026-09-11).
// Real scale: body ~0.33 m beak-to-tail, wingspan ~0.66 m. Metres, +Y up, +Z forward, +X right.
// Three nodes so the viewer can flap the wings per instance: 'body' (origin at the body centre),
// 'wing_L' and 'wing_R' (each mesh built with its shoulder pivot at the node origin; node translation
// = shoulder position on the body). No image textures, no downloaded assets, no source-asset edits.
// Display only: the bird trajectories come from Akira's model and are never changed by this asset.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as T from '../vendor/three/build/three.module.js';
const out = path.dirname(fileURLToPath(import.meta.url));

const materialDefs = [                      // name, baseColor RGBA, metallic, roughness, doubleSided
  ['Blue-grey plumage', [.545, .565, .615, 1], .05, .85, false],
  ['Head and neck', [.33, .35, .40, 1], .05, .85, false],
  ['Neck sheen green', [.16, .55, .40, 1], .35, .45, false],
  ['Neck sheen purple', [.40, .28, .58, 1], .35, .45, false],
  ['Black wing bars and tail band', [.10, .10, .12, 1], .05, .8, true],
  ['Wing plumage', [.58, .60, .65, 1], .05, .85, true],
  ['Primaries', [.19, .20, .23, 1], .05, .8, true],
  ['White rump', [.90, .90, .90, 1], 0, .9, false],
  ['Beak', [.20, .19, .19, 1], .1, .6, false],
  ['Cere', [.92, .92, .90, 1], 0, .7, false],
  ['Eye', [.93, .53, .18, 1], .2, .4, false],
  ['Legs and feet', [.76, .33, .22, 1], .05, .7, false],
];
const meshes = {body: materialDefs.map(() => []), wing_L: materialDefs.map(() => []), wing_R: materialDefs.map(() => [])};

function add(target, g, m, pos = [0, 0, 0], rot = [0, 0, 0], scale = [1, 1, 1]) {
  const mat = new T.Matrix4().compose(new T.Vector3(...pos), new T.Quaternion().setFromEuler(new T.Euler(...rot)), new T.Vector3(...scale));
  g.applyMatrix4(mat);
  meshes[target][m].push(g.index ? g.toNonIndexed() : g);
}
const sphere = (target, r, m, pos, scale = [1, 1, 1], seg = 12) => add(target, new T.SphereGeometry(r, seg, Math.max(6, seg - 4)), m, pos, [0, 0, 0], scale);
const cyl = (target, r0, r1, h, m, pos, rot = [0, 0, 0]) => add(target, new T.CylinderGeometry(r0, r1, h, 8), m, pos, rot);
const box = (target, w, h, l, m, pos, rot = [0, 0, 0]) => add(target, new T.BoxGeometry(w, h, l), m, pos, rot);
function quad(target, a, b, c, d, m) {           // flat double-sided quad from 4 corners (counter-clockwise seen from above)
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute([...a, ...b, ...c, ...a, ...c, ...d], 3));
  g.computeVertexNormals();
  meshes[target][m].push(g);
}

// ---------------- body (origin = centre of the body ellipsoid) ----------------
add('body', new T.SphereGeometry(.055, 14, 10), 0, [0, 0, 0], [-.12, 0, 0], [1, 1.05, 2.0]);   // body, chest slightly raised
sphere('body', .046, 7, [0, .012, -.075], [.9, .7, 1]);              // white rump patch on the lower back
cyl('body', .026, .036, .07, 1, [0, .04, .085], [Math.PI / 2 - .55, 0, 0]);   // neck: tapered, leaning forward-up
sphere('body', .026, 2, [.014, .034, .088], [.75, .7, .9]);           // green sheen (right side of the neck)
sphere('body', .026, 3, [-.014, .032, .086], [.75, .7, .9]);          // purple sheen (left side)
sphere('body', .029, 1, [0, .062, .124], [1, .95, 1.05]);            // head
cyl('body', .003, .009, .022, 8, [0, .053, .163], [Math.PI / 2, 0, 0]); // beak (cone pointing +Z)
sphere('body', .006, 9, [0, .06, .152], [1, .7, .8], 8);             // cere (white patch above the beak)
sphere('body', .0055, 10, [.022, .068, .132], [1, 1, 1], 8);         // eyes
sphere('body', .0055, 10, [-.022, .068, .132], [1, 1, 1], 8);
// tail: flat fan, grey with a black terminal band, slightly raised
quad('body', [-.03, .008, -.10], [.03, .008, -.10], [.045, .014, -.175], [-.045, .014, -.175], 0);
quad('body', [-.045, .014, -.175], [.045, .014, -.175], [.05, .016, -.205], [-.05, .016, -.205], 4);
// legs and feet (tucked under the body; visible when perched)
cyl('body', .0035, .0035, .034, 11, [.02, -.062, .01]);
cyl('body', .0035, .0035, .034, 11, [-.02, -.062, .01]);
box('body', .012, .004, .028, 11, [.02, -.079, .02]);
box('body', .012, .004, .028, 11, [-.02, -.079, .02]);

// ---------------- wings (pivot at the shoulder = node origin; +X points along the span for the right wing) ----------------
// planform along +X (span 0.29 m from the shoulder), chord along Z (leading edge at +z), slight camber (y) and dihedral
function wing(target, sign) {
  const S = sign;                                                  // +1 right wing (+X), -1 left wing (-X)
  const P = (x, y, z) => [S * x, y, z];
  // span-wise stations: x from the shoulder, leading-edge z, trailing-edge z, camber y.  Broad arm section,
  // a wrist at ~0.14 m, then hand/primaries tapering to a swept, pointed tip at 0.29 m.
  const st = [[0, .045, -.085, 0], [.05, .052, -.092, .003], [.10, .054, -.088, .006], [.14, .052, -.076, .009], [.19, .044, -.058, .014], [.24, .032, -.036, .021], [.29, .012, -.014, .03]];
  const mat = i => (i >= 4 ? 6 : 5);                              // outer panels (hand) = dark primaries
  for (let i = 0; i < st.length - 1; i++) {
    const [x0, l0, t0, y0] = st[i], [x1, l1, t1, y1] = st[i + 1];
    quad(target, P(x0, y0, l0), P(x1, y1, l1), P(x1, y1, t1), P(x0, y0, t0), mat(i));
  }
  // primary "fingers": five slightly separated feather tips along the outer trailing edge
  for (let k = 0; k < 5; k++) {
    const x0 = .165 + k * .026, x1 = x0 + .02, xm = x0 + .011;
    const tz = -.058 + (x0 - .19) * .44, ty = .014 + (x0 - .19) * .13;   // trailing edge at x0
    quad(target, P(x0, ty, tz + .004), P(x1, ty + .003, tz - .006), P(xm + .006, ty + .002, tz - .030 - k * .002), P(xm - .006, ty + .001, tz - .026 - k * .002), 6);
  }
  // two black bars across the secondaries (inner 0.11 m), parallel to the trailing edge, drawn 1 mm above the surface
  quad(target, P(.005, .0013, -.048), P(.11, .0075, -.052), P(.11, .0075, -.066), P(.005, .0013, -.062), 4);
  quad(target, P(.005, .0013, -.022), P(.11, .0075, -.026), P(.11, .0075, -.040), P(.005, .0013, -.036), 4);
  // leading-edge covert strip (darker) for silhouette, inner two thirds
  quad(target, P(.02, .0025, .049), P(.15, .010, .050), P(.15, .010, .036), P(.02, .0025, .035), 1);
}
wing('wing_R', +1);
wing('wing_L', -1);
const SHOULDER = {wing_R: [.042, .034, .02], wing_L: [-.042, .034, .02]};

// ---------------- GLB writer (same layout as build_sedan.mjs; three nodes) ----------------
const blob = []; const bufferViews = []; const accessors = []; let offset = 0;
function pushBuffer(f32, target) {
  const b = Buffer.from(f32.buffer, f32.byteOffset, f32.byteLength);
  blob.push(b); const pad = (4 - b.length % 4) % 4; if (pad) blob.push(Buffer.alloc(pad, 0));
  bufferViews.push({buffer: 0, byteOffset: offset, byteLength: b.length, target});
  offset += b.length + pad; return bufferViews.length - 1;
}
function accessor(f32, bv) {
  const n = f32.length / 3; const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < f32.length; i += 3) for (let k = 0; k < 3; k++) { min[k] = Math.min(min[k], f32[i + k]); max[k] = Math.max(max[k], f32[i + k]); }
  accessors.push({bufferView: bv, componentType: 5126, count: n, type: 'VEC3', min, max}); return accessors.length - 1;
}
const gltfMeshes = []; const nodes = []; const qa = {materials: materialDefs.length, parts: {}};
for (const [name, groups] of Object.entries(meshes)) {
  const primitives = [];
  let tris = 0;
  groups.forEach((list, m) => {
    if (!list.length) return;
    const merged = list.map(g => g.getAttribute('position').array);
    const pos = new Float32Array(merged.reduce((s, a) => s + a.length, 0)); let o = 0;
    for (const a of merged) { pos.set(a, o); o += a.length; }
    const nrm = new Float32Array(pos.length);
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(pos, 3)); g.computeVertexNormals(); nrm.set(g.getAttribute('normal').array);
    const pa = accessor(pos, pushBuffer(pos, 34962)), na = accessor(nrm, pushBuffer(nrm, 34962));
    primitives.push({attributes: {POSITION: pa, NORMAL: na}, material: m, mode: 4});
    tris += pos.length / 9;
  });
  const meshIndex = gltfMeshes.length;
  gltfMeshes.push({name: `${name} primitives`, primitives});
  const node = {name, mesh: meshIndex};
  if (SHOULDER[name]) node.translation = SHOULDER[name];
  nodes.push(node);
  const ext = accessors.filter((_, i) => i % 2 === 0).slice(-primitives.length);
  qa.parts[name] = {triangles: tris, primitives: primitives.length, pivot_translation: SHOULDER[name] || [0, 0, 0]};
}
// overall extents (body + wings at rest, wings flat)
const all = [];
for (const groups of Object.values(meshes)) for (const list of groups) for (const g of list) all.push(g.getAttribute('position').array);
const ext = {min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity]};
for (const a of all) for (let i = 0; i < a.length; i += 3) for (let k = 0; k < 3; k++) { ext.min[k] = Math.min(ext.min[k], a[i + k]); ext.max[k] = Math.max(ext.max[k], a[i + k]); }
qa.extents_with_wings_flat_m = {x: [ext.min[0] - .042, ext.max[0] + .042], y: [ext.min[1], ext.max[1] + .034], z: [ext.min[2], ext.max[2]]};
qa.wingspan_m = Math.round(((ext.max[0] + .042) - (ext.min[0] - .042)) * 1000) / 1000;
qa.length_m = Math.round((ext.max[2] - ext.min[2]) * 1000) / 1000;
const json = {
  asset: {version: '2.0', generator: 'FieldFleet UWM demo procedural pigeon builder'},
  scene: 0, scenes: [{name: 'Pigeon metres +Z forward Y up', nodes: nodes.map((_, i) => i)}],
  nodes, meshes: gltfMeshes,
  materials: materialDefs.map(([name, color, metallicFactor, roughnessFactor, doubleSided]) => ({name, pbrMetallicRoughness: {baseColorFactor: color, metallicFactor, roughnessFactor}, doubleSided})),
  buffers: [{byteLength: offset}], bufferViews, accessors,
  extras: {units: 'metres', up_axis: '+Y', forward_axis: '+Z', placement_reference: 'body node origin = body centre; wing nodes carry their shoulder pivot as translation; flap = rotation of a wing node about its local Z (forward) axis',
           provenance: 'Procedurally generated low-poly feral pigeon (Columba livia domestica, blue-bar colouring) for the revision_02 demo bird layer. Display asset only: bird trajectories come from Akira\'s flock model and are not changed by this asset. Not Akira\'s art, no photographic textures.'},
};
let jb = Buffer.from(JSON.stringify(json)); jb = Buffer.concat([jb, Buffer.alloc((4 - jb.length % 4) % 4, 0x20)]);
const bb = Buffer.concat(blob), header = Buffer.alloc(12), jh = Buffer.alloc(8), bh = Buffer.alloc(8);
header.writeUInt32LE(0x46546c67); header.writeUInt32LE(2, 4); header.writeUInt32LE(12 + 8 + jb.length + 8 + bb.length, 8);
jh.writeUInt32LE(jb.length); jh.writeUInt32LE(0x4e4f534a, 4); bh.writeUInt32LE(bb.length); bh.writeUInt32LE(0x004e4942, 4);
const file = Buffer.concat([header, jh, jb, bh, bb]);
fs.writeFileSync(path.join(out, 'pigeon.glb'), file);
qa.bytes = file.length;
fs.writeFileSync(path.join(out, 'pigeon_geometry_QA.json'), JSON.stringify(qa, null, 2));
console.log(JSON.stringify(qa));
