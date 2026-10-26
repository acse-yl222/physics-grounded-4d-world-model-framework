// Generic building geometry of the image-to-three.js city model: ring normalisation,
// roof fallbacks and closed, outward-facing shells on synthetic footprints.
import assert from 'node:assert/strict';
import test from 'node:test';

const MODULES = process.env.IMAGE_TO_THREEJS_DIR ?? '../src/urban_geometry/image_to_threejs/';
const root = new URL(MODULES, import.meta.url);
// The checker maps 'three' to the vendored build and stubs canvases for textures.
const { checkPiece, footprintArea, triangles } = await import(
  new URL('check_buildings.mjs', root).href
);
const kit = await import(new URL('three/kit.mjs', root).href);
const { buildGeneric, pitchedFor } = await import(new URL('three/generic.mjs', root).href);

const SQUARE = [
  [0, 0],
  [10, 0],
  [10, 10],
  [0, 10],
];
const L_SHAPE = [
  [0, 0],
  [12, 0],
  [12, 5],
  [5, 5],
  [5, 9],
  [0, 9],
];

function building(polys, props = {}) {
  return {
    id: 'b',
    c: [5, 5],
    polys,
    h: 9,
    minh: 0,
    floors: 2,
    roof: 'flat',
    roofH: 0,
    ridge: 0,
    style: 'london_stock',
    group: 'house',
    seed: 0.42,
    ...props,
  };
}

/** Build each piece (the building or each part) on its own and run the diagnostic. */
function check(b) {
  return (b.parts ?? [null]).map((part) => {
    const piece = part ?? b;
    const tris = triangles(buildGeneric({ buildings: [part ? { ...b, parts: [part] } : b] }));
    return checkPiece(tris, piece.polys, piece.h, piece.minh ?? 0, { rays: 96 });
  });
}

function roofTriangles(b) {
  const tris = triangles(buildGeneric({ buildings: [b] }));
  let up = 0,
    sloped = 0;
  for (let t = 0; t < tris.kind.length; t++) {
    if (tris.kind[t] !== 0) continue;
    const p = tris.p.slice(9 * t, 9 * t + 9);
    const nz = (p[3] - p[0]) * (p[7] - p[1]) - (p[4] - p[1]) * (p[6] - p[0]);
    if (nz > 0) up++;
    if (new Set([p[2], p[5], p[8]].map((z) => z.toFixed(3))).size > 1) sloped++;
  }
  return { up, sloped };
}

test('rings lose duplicate, closing and collinear points and are wound CCW / CW', () => {
  const messy = [
    [0, 10],
    [10, 10],
    [10, 10],
    [10, 5],
    [10, 0],
    [5, 0.000001],
    [0, 0],
    [0, 10],
  ]; // clockwise, closed, with a repeat and two collinear points
  const ring = kit.normaliseRing(messy);
  assert.equal(ring.length, 4);
  assert.ok(kit.ringArea(ring) > 0);
  const hole = kit.normaliseRing(SQUARE, { hole: true });
  assert.ok(kit.ringArea(hole) < 0);
  assert.equal(
    kit.normaliseRing([
      [0, 0],
      [1, 1],
      [2, 2],
      [0, 0],
    ]),
    null,
  );
  assert.equal(
    kit.normaliseRing([
      [0, 0],
      [NaN, 1],
      [1, 0],
    ]),
    null,
  );
  const polys = kit.normalisePolys([
    [
      SQUARE.slice().reverse(),
      [
        [2, 2],
        [4, 2],
        [4, 4],
        [2, 4],
      ],
    ],
  ]);
  assert.ok(kit.ringArea(polys[0][0]) > 0 && kit.ringArea(polys[0][1]) < 0);
});

test('caps cover rings with holes and any winding, facing up', () => {
  const batch = new kit.MeshBatch();
  const material = kit.mat('slate');
  const outer = SQUARE.slice()
    .reverse()
    .concat([[0, 0]]); // CW with closing point
  kit.cap(
    batch,
    material,
    [
      [
        outer,
        [
          [2, 2],
          [2, 4],
          [4, 4],
          [4, 2],
        ],
      ],
    ],
    3,
  );
  const tris = triangles(batch.toGroup());
  let area = 0;
  for (let t = 0; t < tris.kind.length; t++) {
    const p = tris.p.slice(9 * t, 9 * t + 9);
    const cross = (p[3] - p[0]) * (p[7] - p[1]) - (p[4] - p[1]) * (p[6] - p[0]);
    assert.ok(cross > 0, 'cap triangle faces down');
    area += cross / 2;
  }
  assert.ok(Math.abs(area - 96) < 1e-6, `cap area ${area}`);
});

test('pitched roofs fall back to flat where they would not fit', () => {
  const norm = (ring) => kit.normalisePolys([[ring]]);
  assert.deepEqual(pitchedFor({ roof: 'gabled' }, norm(SQUARE), 0), { kind: 'gabled', ridge: 0 });
  assert.equal(pitchedFor({ roof: 'hipped' }, norm(L_SHAPE), 0).kind, 'hipped');
  const thinL = [
    [0, 0],
    [12, 0],
    [12, 2],
    [2, 2],
    [2, 12],
    [0, 12],
  ];
  assert.equal(pitchedFor({ roof: 'gabled' }, norm(thinL), 0), null);
  const holed = kit.normalisePolys([
    [
      SQUARE,
      [
        [3, 3],
        [3, 6],
        [6, 6],
        [6, 3],
      ],
    ],
  ]);
  assert.equal(pitchedFor({ roof: 'gabled' }, holed, 0), null);
  assert.equal(pitchedFor({ roof: 'flat' }, norm(SQUARE), 0), null);
  // A part without its own ridge is laid out along its own long axis.
  const long = norm([
    [0, 0],
    [4, 0],
    [4, 20],
    [0, 20],
  ]);
  assert.ok(Math.abs(Math.sin(pitchedFor({ roof: 'gabled' }, long).ridge)) > 0.99);
  const holedRoof = roofTriangles(
    building(
      [
        [
          SQUARE,
          [
            [3, 3],
            [3, 6],
            [6, 6],
            [6, 3],
          ],
        ],
      ],
      { roof: 'gabled' },
    ),
  );
  assert.equal(holedRoof.sloped, 0);
  assert.ok(holedRoof.up > 0);
});

test('synthetic footprints build closed, outward-facing shells', () => {
  const cases = {
    'gabled L-shape': building([[L_SHAPE]], { roof: 'gabled', roofH: 2.5 }),
    'hipped L-shape on terrain': building([[L_SHAPE]], { roof: 'hipped', roofH: 3, ground_z: 0 }),
    'pyramidal square': building([[SQUARE]], { roof: 'pyramidal', roofH: 3 }),
    'flat ring with a hole': building([
      [
        SQUARE,
        [
          [3, 3],
          [3, 6],
          [6, 6],
          [6, 3],
        ],
      ],
    ]),
    'gabled ring with a hole (flat fallback)': building(
      [
        [
          SQUARE,
          [
            [3, 3],
            [3, 6],
            [6, 6],
            [6, 3],
          ],
        ],
      ],
      { roof: 'gabled' },
    ),
    'clockwise ring with duplicate points': building(
      [
        [
          [
            [0, 0],
            [0, 10],
            [0, 10],
            [10, 10],
            [10, 0],
            [5, 0],
            [0, 0],
          ],
        ],
      ],
      { roof: 'gabled', roofH: 2 },
    ),
    'parts on a floor': building([[SQUARE]], {
      parts: [
        {
          id: 'p1',
          polys: [[L_SHAPE.map(([x, y]) => [x * 0.8, y])]],
          h: 9,
          minh: 0,
          roof: 'gabled',
          roofH: 2,
        },
        {
          id: 'p2',
          polys: [
            [
              [
                [1, 1],
                [4, 1],
                [4, 4],
                [1, 4],
              ],
            ],
          ],
          h: 14,
          minh: 9,
          roof: 'flat',
        },
      ],
    }),
  };
  for (const [name, b] of Object.entries(cases)) {
    for (const { flags, metrics } of check(b))
      assert.deepEqual([...flags], [], `${name}: ${JSON.stringify(metrics)}`);
  }
});

test('the checker flags a rectangle roof over an L-shaped footprint', () => {
  // The pre-fit construction: walls to the eaves and kit.pitchedRoof over the
  // oriented rectangle, which overhangs the missing corner and leaves gaps.
  const batch = new kit.MeshBatch();
  const polys = [[L_SHAPE]];
  kit.walls(batch, kit.facade('london_stock'), polys, 0, 6);
  kit.pitchedRoof(batch, kit.roof('slate'), kit.facade('london_stock'), L_SHAPE, 0, 6, 3, 'gabled');
  const { flags } = checkPiece(triangles(batch.toGroup()), polys, 9, 0, { rays: 96 });
  assert.ok(flags.has('pitched_overhang'), [...flags].join());
  assert.ok(flags.has('roof_wall_gap'), [...flags].join());
  assert.ok(footprintArea(polys) > 0);
});

test('flat roofs on a sloping ground plane stay level, wall feet follow it', () => {
  const b = building(
    [
      [
        [
          [-20, -3],
          [20, -3],
          [20, 3],
          [-20, 3],
        ],
      ],
    ],
    { c: [0, 0], h: 10, ground_z: 0, ground_max: 4, ground_plane: [2, 0.1, 0] },
  );
  const tris = triangles(buildGeneric({ buildings: [b] }));
  const roofZ = new Set(),
    feet = [];
  for (let t = 0; t < tris.kind.length; t++)
    for (let v = 0; v < 3; v++) {
      const [x, , z] = tris.p.slice(9 * t + 3 * v, 9 * t + 3 * v + 3);
      if (tris.kind[t] === 0) roofZ.add(z.toFixed(3));
      else if (tris.kind[t] === 1 && z < 2 + 0.1 * x) feet.push([x, z]);
    }
  assert.equal(roofZ.size, 1, `roof heights ${[...roofZ]}`);
  for (const [x, z] of feet) assert.ok(Math.abs(z - (2 + 0.1 * x - 0.5)) < 1e-6);
  // Pitched roofs keep following the plane (sheared terraces).
  const g = building(b.polys, { ...b, roof: 'gabled', roofH: 2 });
  const gt = triangles(buildGeneric({ buildings: [g] }));
  const eaves = new Set();
  for (let t = 0; t < gt.kind.length; t++)
    if (gt.kind[t] === 0) eaves.add(gt.p[9 * t + 2].toFixed(1));
  assert.ok(eaves.size > 2);
});
