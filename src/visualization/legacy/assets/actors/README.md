# Car and cargo-UAV actors

This folder is independent of the city loader, route builder, traffic simulation, and scheduler. All geometry uses metres, +Y up, and +Z forward. The updater's `x/y/z` is the horizontal model centre with its bottom contact at `y`; it is not the model's geometric centre height.

## Integration

The viewer's existing import map for `three` is required by Three's GLTFLoader. This module itself imports the bundled `../vendor/three` files and has no network/CDN dependency.

```js
import {createActorLayer, sumoHeadingToWorldYaw} from './actors/actor-layer.js';

const actors = await createActorLayer({
  scene,
  carCapacity: 1500,
  uavCapacity: 300,
  // Defaults: ./sedan_4p5m.glb relative to this module, and the original cargo model:
  uavURL: '/assets/hexacopter_cargo.glb',
});

// Snapshot update: omitted actors become hidden. idIndex is a stable slot index,
// not an arbitrary string or an unbounded SUMO departure ID.
actors.updateCars([
  {idIndex: 0, x: 120, y: 0.02, z: 340,
   headingRadians: sumoHeadingToWorldYaw(Math.PI / 2),
   visible: true, color: '#466779'},
]);
actors.updateUavs([
  {idIndex: 0, x: 120, y: 35, z: 340, headingRadians: 0.3, visible: true},
]);

// For a delta update, preserve actors not mentioned:
actors.updateCars([{idIndex: 0, visible: false}], {hideUnmentioned: false});
// Or update both kinds together:
actors.update({cars: carSnapshot, uavs: uavSnapshot});
actors.setVisible({cars: true, uavs: true});
// At teardown only:
// actors.dispose();
```

Heading is a right-handed rotation around world +Y: zero faces +Z, `Math.PI / 2` faces +X, and `Math.PI` faces −Z. A SUMO angle clockwise from north is converted with `Math.PI - sumoAngleRadians`. Existing traffic samples already use the vehicle centre: do not subtract half the car length again.

The updater does not accept scale. It rejects duplicate or out-of-range indices and non-finite visible positions before mutating the snapshot. `visible: false` requires only `idIndex`. Actor capacities can be increased at construction if the replay's maximum concurrent slot count requires it.

Cars have a deterministic muted colour palette. An explicit `color` tints only body paint; tyres, windows and lamps preserve their colours. UAVs preserve the original orange/graphite model; an optional `color` multiplies the pearl shell only. No rotor animation is implemented in this first layer.

## Geometry and checks

- `sedan_4p5m.glb` is original procedural geometry, with wheels, windows, mirrors, front/rear lights, and plates. No external textures. Nominal dimensions: **width 1.80 m, length 4.50 m, height 1.45 m**. Tyre contact is Y = 0. The asset contains 660 triangles and seven material primitives; 52,236 bytes.
- The original `hexacopter_cargo.glb` is loaded read-only. Its measured dimensions are **width 1.358253 m, length 1.228179 m, height 0.517000 m**. Scale remains exactly 1. The original 0.025 m bottom offset is baked out solely to make `y` a consistent ground/landing contact reference. The geometry is not rescaled or simplified.
- Default batching merges source primitives sharing a material, retaining their complete baked geometry, then uses an `InstancedMesh` per resulting material group. The cargo model's 53 source primitives become seven instance groups. Use `mergeByMaterial: false` to keep a group per source primitive if needed.
- `sedan_gltf_validation.json`: Khronos validator, **0 errors / 0 warnings**.
- `actor_browser_scale_QA.json` plus `actor_scale_preview.png`: both original-scale models loaded in a browser and visually inspected against a 1 m grid; input validation and hiding checks pass.
- `actor_browser_fleet_QA.json` plus `actor_fleet_preview.png`: 1,500 cars and 300 cargo UAVs loaded together, 6,027,602 rendered triangles including floor, 16 draw calls including floor/grid, no page errors. A short 90-frame actor-only check averaged about 16.68 ms/frame. This does **not** establish the integrated city's frame rate.

The first headless browser launch was blocked by the default command sandbox and exited. The subsequent bounded local browser QA used approved execution permissions, completed both checks, and closed its browser. No original city/UAV assets, Main's viewer files, traffic data, scheduler, report, or shared state were edited.

These actors only display supplied replay positions. They do not create traffic-rule compliance, collision avoidance, a flight model, or scheduler results.

## Pigeon display model (added 2026-09-11, revision_02 v3)

- `pigeon.glb` is original procedural geometry written by `build_pigeon.mjs` (run `node build_pigeon.mjs` in this folder; no external asset, no textures). Real feral-pigeon scale: **length 0.38 m beak-to-tail, wingspan 0.66 m**, 1,376 triangles, 12 flat materials (blue-grey body, white rump, green/purple neck sheen, two black wing bars, black tail band, orange eyes and feet). `pigeon_geometry_QA.json` records the measured extents.
- Three named nodes: `body` (origin at the body centre, +Z forward, +Y up) and `wing_L` / `wing_R`, whose node translations are the shoulder pivots (±0.042, 0.034, 0.02). `birds.js` builds one `InstancedMesh` per primitive per node and composes `bodyMatrix × (pivot · foldOrFlap)` for each wing per frame, so 100 birds flap independently from one draw call per primitive.
- Wing flap (4.5 Hz), fold (roosting / foraging / slow), pitch (vertical speed) and roll (recorded bank) are **display only**: the recorded position, heading and state of every bird come unchanged from `data/birds/`. The model is a stand-in for Akira's bird and can be swapped for any GLB that keeps the three node names.
