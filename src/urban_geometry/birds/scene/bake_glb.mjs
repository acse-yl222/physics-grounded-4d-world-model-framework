// Bake a published (meshopt / quantized / node-transformed) city GLB into the plain form that
// urban_geometry/voxelization/prepare_glb.py reads: float positions, no compression extensions,
// every node transform applied to its vertices, no hierarchy, no textures. Material and node
// names are kept because prepare_glb classifies land cover from them.
//
// usage: node bake_glb.mjs <out.glb> <in.glb> [<supplement.glb> ...]
// needs: npm install --no-save @gltf-transform/core@4 @gltf-transform/extensions@4 \
//        @gltf-transform/functions@4 meshoptimizer
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import {
  clearNodeTransform,
  dequantize,
  flatten,
  mergeDocuments,
  prune,
  unpartition,
} from '@gltf-transform/functions';
import { MeshoptDecoder } from 'meshoptimizer';

const [out, input, ...supplements] = process.argv.slice(2);
if (!out || !input) {
  console.error('usage: node bake_glb.mjs <out.glb> <in.glb> [<supplement.glb> ...]');
  process.exit(2);
}
await MeshoptDecoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.decoder': MeshoptDecoder });

const doc = await io.read(input);
for (const path of supplements) {
  // merged as extra scenes; flatten below works per scene, so move their roots into scene 0
  mergeDocuments(doc, await io.read(path));
}
const root = doc.getRoot();
const [main, ...extra] = root.listScenes();
for (const s of extra) {
  for (const n of s.listChildren()) main.addChild(n);
  s.dispose();
}
root.setDefaultScene(main);

// Animated actors baked into some city GLBs (South Kensington: demo birds, traffic vehicles and
// prediction markers) are not city geometry; the viewer hides the same layers (replay.js display
// filter). Animated nodes would also block flatten().
const DROP_LAYERS = new Set(['bird', 'bird_site', 'traffic_vehicle', 'traffic_prediction']);
for (const a of root.listAnimations()) a.dispose();
let dropped = 0;
const drop = (node) => {
  for (const c of node.listChildren()) drop(c);
  node.dispose();
  dropped++;
};
for (const node of root.listNodes())
  if (!node.isDisposed() && DROP_LAYERS.has(node.getExtras()?.layer)) drop(node);

// prepare_glb reads POSITION and indices only; dropping normals, UVs, colours and textures
// before dequantisation keeps large cities (South Kensington: 39 M vertices) within memory
for (const mesh of root.listMeshes())
  for (const prim of mesh.listPrimitives()) {
    for (const semantic of prim.listSemantics())
      if (semantic !== 'POSITION') prim.setAttribute(semantic, null);
    for (const target of prim.listTargets()) target.dispose();
  }
for (const t of root.listTextures()) t.dispose();
await doc.transform(prune({ keepLeaves: true }));
await doc.transform(dequantize());
await doc.transform(flatten());

let baked = 0,
  cloned = 0;
for (const node of root.listNodes()) {
  const mesh = node.getMesh();
  if (mesh) {
    // a mesh shared by several nodes would be transformed once per node: give each node its own copy
    const users = mesh.listParents().filter((p) => p.propertyType === 'Node');
    if (users.length > 1) {
      node.setMesh(mesh.clone());
      cloned++;
    }
  }
  clearNodeTransform(node);
  baked++;
}
for (const name of [
  'EXT_meshopt_compression',
  'KHR_mesh_quantization',
  'KHR_draco_mesh_compression',
  'EXT_mesh_gpu_instancing',
]) {
  root
    .listExtensionsUsed()
    .filter((e) => e.extensionName === name)
    .forEach((e) => e.dispose());
}
// merged supplements bring their own buffer; a GLB holds exactly one
await doc.transform(prune({ keepLeaves: false }), unpartition());

const left = root
  .listNodes()
  .filter(
    (n) =>
      n.listChildren().length ||
      n.getMatrix().some((v, i) => v !== [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1][i]),
  );
if (left.length) throw Error(`${left.length} nodes still carry a transform or children`);
await io.write(out, doc);
console.log(
  JSON.stringify({
    out,
    input,
    supplements,
    nodes: root.listNodes().length,
    meshes: root.listMeshes().length,
    materials: root.listMaterials().length,
    transforms_baked: baked,
    shared_meshes_cloned: cloned,
    actor_nodes_dropped: dropped,
  }),
);
