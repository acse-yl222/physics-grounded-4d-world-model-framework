# Authoring landmark modules

Landmarks replace the generic extrusion of one or more Overture footprints with a
hand-written three.js model reconstructed from reference material (photographs,
listing descriptions, architects' pages). One module per landmark:
`landmarks/<id>.mjs`, `id` in lower snake_case.

## Module contract

The module has **no imports**; everything comes through `ctx`:

```js
export default {
  id: 'royal_albert_hall',
  name: 'Royal Albert Hall',
  claims: ['f8dc8756-8083-4501-8b2d-1ec37d51d0a3'], // Overture building ids replaced
  references: [{ title: '…', url: 'https://…', used_for: 'what was taken from this source' }],
  notes: 'what is approximated / unknown',
  build(ctx) {
    const { THREE, kit, buildings, byId, frame, scene } = ctx;
    const group = new THREE.Group();
    // … ENU metres: x east, y north, z up; ground at z = 0
    return group;
  },
};
```

- `claims`: every footprint the model covers. Claimed buildings are removed from the
  generic layer; unclaimed overlapping buildings would be drawn twice. Claims may be
  empty for structures without a building footprint (a memorial, a bridge).
- `references`: only URLs actually returned by a search or fetch. Never invent a URL.
- `buildings`: the claimed records: `polys` (polygons → rings → `[x, y]`, outer ring
  CCW, holes CW), `h`, `minh`, `floors`, `roof`, `parts` (sub-volumes with their own
  `polys`, `h`, `minh`), `name`, `c` (centroid).
- `frame`: oriented frame of the largest claimed outer ring:
  `{ cx, cy, angle, length, width }` (angle of the long axis, radians from east).
  Build in local coordinates and place with `group.position.set(frame.cx, frame.cy, 0)`
  and `group.rotation.z = frame.angle`, or build directly in scene coordinates from
  `polys`.
- `scene`: the whole prepared scene (read only), e.g. to look up nearby roads.
- `asset(id)` / `placeAssets(id, [[x, y, heading], …])`: reuse an asset from the
  `resources/` library (street furniture, vehicles, trees) instead of modelling it
  again — e.g. lamps along a forecourt or a K6 kiosk beside an entrance.

## Kit (`ctx.kit`, see `three/kit.mjs`)

- `kit.mat(nameOrCss, overrides)` — shared solid materials. Palette names include
  `portland_stone, bath_stone, terracotta, buff_terracotta, red_brick, london_stock,
white_render, concrete, dark_concrete, glass, dark_glass, green_glass, steel,
dark_steel, white_steel, aluminium, copper_green, copper, lead, slate, gold, bronze,
timber, black, white, grass, water, asphalt, paving, gravel, foliage, bark, red, blue`.
- `kit.facade(style, variant)` — windowed facade texture material (4 bays × 2 storeys
  per tile). Styles: `stucco, london_stock, red_brick, portland_stone, glass,
modern_clad, concrete, metal_clad, ragstone, timber`. Uses vertex colours (white
  = untinted) and needs the UVs produced by `kit.walls`.
- `kit.paintedMaterial(key, w, h, draw(ctx2d, w, h), params)` — material from your own
  canvas drawing (a facade bay traced from photos, a clock face, signage). Keep
  canvases ≤ 1024 px and key them uniquely (`'<id>:bay'`).
- `new kit.MeshBatch()` + `batch.toGroup(name)` — accumulate many faces per material
  into few meshes (use for anything repeated: windows, columns, arcades).
- `kit.walls(batch, material, polys, z0, z1, { bay, storey, uvBase, color })` — wall
  quads with storey-aligned UVs; `kit.cap(batch, material, polys, z, { scale, down })`
  — triangulated roof / floor; `kit.pitchedRoof(batch, roofMat, wallMat, ring, angle,
eave, rise, 'gabled'|'hipped'|'pyramidal'|'mansard')`; `kit.box(batch, material, x,
y, z0, w, d, h, angle)`.
- `kit.offsetRing(ring, d)` (grow / shrink a ring), `kit.ringFrame(ring)`,
  `kit.orientedExtent(ring, angle)`, `kit.ringArea(ring)`, `kit.rng(seed)`.

Detailing helpers (real geometry, all into a MeshBatch):

- `kit.windowRow(batch, a, b, sillZ, { width, height, count | bay, margin, depth, glass,
frame, sill, head: 'lintel'|'arch'|'segment'|'pediment'|'none', bars, surround })` —
  framed windows with glazing bars, sills and heads on wall edge a → b (outward normal
  on the right of a → b for an outer CCW ring); `kit.windowGrid(batch, ring, z0,
storeys, storey, opts | (storey, edge) => opts)` does every edge and storey.
- `kit.cornice(batch, mat, ring, z, { height, projection, steps })` — projecting
  cornices, string courses and plinths that follow the footprint.
- `kit.colonnade(batch, mat, a, b, z0, height, { count, radius, offset, capital:
'doric'|'corinthian' })`, `kit.balustrade(batch, mat, polyline, z, { height,
spacing })`, `kit.lathe(mat, [[r, z], …], { x, y, z, segments })` for domes, drums,
  lanterns and finials.

Plain three.js geometry (`THREE.BoxGeometry`, `CylinderGeometry`, `LatheGeometry`,
`ExtrudeGeometry`, `SphereGeometry`, …) is fine. three.js primitives are y-up: rotate
cylinders / cones / lathes with `.rotateX(Math.PI / 2)` so their axis is +z.

## Budget and quality

- Aim for ≤ 60 000 triangles per landmark (≤ 150 000 for very large complexes such as
  Westfield or the Natural History Museum). Reuse materials; prefer MeshBatch.
- Model what makes the building recognisable from a few hundred metres and from the
  street: massing and setbacks from the footprint/parts, roof form (domes, spires,
  pediments, glazed roofs), dominant materials and colours, window rhythm, arcades,
  towers, signage colour. Heights must be consistent with `h` / `parts` unless a
  reference gives a better number (say so in `notes`).
- No textures loaded from the network; draw them on canvases.

## Preview

```sh
node src/urban_geometry/image_to_threejs/render.cjs landmark <id> \
  --views ne,sw,street_s --out <dir> [--context 0] [--shadows] [--zoom 0.4]
```

Writes `<dir>/<id>_<view>.png` (views: `ne nw se sw top street_n street_s street_e
street_w`) and prints triangle counts plus any page errors. `--context 0` hides the
surrounding city. Look at the screenshots and iterate.
`python3 src/urban_geometry/image_to_threejs/find_buildings.py --name … | --near X Y
--radius R` lists footprint ids, centroids and heights.

## Reusable assets (`resources/`)

Anything that appears more than once — street furniture, vehicles, trees — is an
asset in `resources/<street|vehicles|vegetation>/<id>.mjs` with the same no-import
contract plus `kind` and `size: [width, depth, height]` (metres). `build({ THREE, kit })`
returns a group with its origin at the base centre, z up and the front facing +y;
vegetation is authored at 1 m height and scaled per tree. Facade, roof, road and
ground materials are in `resources/materials/textures.mjs` and reached through
`kit.facade`, `kit.roof`, `kit.road`, `kit.ground`.

Mapped Overture points are placed automatically (`prepare_scene.py`,
`ASSET_FOR_CLASS`), oriented towards the nearest carriageway. Add a new asset, run
`node collect_landmarks.mjs` to refresh `resources/index.json`, and check it with
`node render.cjs gallery`.
