// The Old Police House, Hyde Park (former Hyde Park police station, 1900-02, by John
// Dixon Butler, architect and surveyor to the Metropolitan Police). A domestic-style
// two-storey building of red brick with Portland stone dressings next to the Ranger's
// Lodge, now The Royal Parks' headquarters; stables for the Park Police horses are in
// the yard behind.
export default {
  id: 'hyde_park_police_station',
  name: 'The Old Police House (Hyde Park Police Station)',
  claims: ['9694fb35-2a33-475e-ab0c-3eb9bd562468'],
  references: [
    {
      title: 'The Old Police House - Historic England list entry 1022332',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1022332',
      used_for: 'Grade II listed, first listed 1988',
    },
    {
      title: 'Hidden in Hyde Park - Adam Yamey',
      url: 'https://www.goodreads.com/author_blog_posts/21033318-hidden-in-hyde-park',
      used_for:
        "built 1900-02 by John Dixon Butler; beside the Ranger's Lodge; police horse stables in the yard",
    },
    {
      title: 'Old Police House - VoiceMap (German tour)',
      url: 'https://voicemap.me/tour/london/hyde-park-und-kensington-gardens-konigtum-entspannung-und-rebellion/sites/old-police-house-2',
      used_for: 'dates from 1902, now the main office of The Royal Parks',
    },
    {
      title: 'John Butler (architect) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/John_Butler_(architect)',
      used_for: 'Metropolitan Police architect 1895-1920',
    },
    {
      title: 'Pinner Police Station listing - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101411163-pinner-police-station-including-stable-block-boundary-wall-gate-pier-and-fences-bollards-and-police-lamps-pinner-ward',
      used_for:
        "Butler's usual palette: red brick with Portland stone dressings, tiled roofs, Domestic Revival manner",
    },
  ],
  notes:
    'The listing text was not available: the red brick / Portland stone / tiled-roof palette, the two storeys ' +
    "with attic gables, chimneys and the entrance with a blue police lamp on the north (Policeman's Path) front " +
    "follow Butler's typical stations, not this building's description. The large footprint is treated as " +
    'ranges round a covered core: walls follow the outline, a ring of pitched roof on the fitted rectangle with ' +
    'a flat centre. Storey heights (3.7 m) are estimates.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const brick = kit.mat('#9a4a36', { roughness: 0.9 });
    const stone = kit.mat('portland_stone');
    const tiles = kit.roof('clay_tile', 0);
    const tileM = kit.mat('#8c4a35', { roughness: 0.85 });
    const glass = kit.mat('dark_glass');
    const white = kit.mat('white');
    const door = kit.mat('#283544');
    const lampBlue = kit.mat('#2a4f9c', {
      emissive: new THREE.Color('#2a4f9c'),
      emissiveIntensity: 0.4,
    });
    void tiles;

    const ST = 3.7,
      EAVE = 2 * ST + 0.6;
    kit.walls(batch, brick, [[ring]], 0, EAVE, { bay: 1e6 });
    kit.cornice(batch, stone, ring, 0, { height: 0.6, projection: 0.08 });
    kit.cornice(batch, stone, ring, ST + 0.2, { height: 0.25, projection: 0.07 });
    kit.cornice(batch, stone, ring, EAVE - 0.35, { height: 0.35, projection: 0.3, steps: 2 });
    kit.windowGrid(batch, ring, 1.0, 2, ST + 0.2, (s, k) => {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      return {
        count: len < 2.6 ? 0 : undefined,
        bay: 3.0,
        width: 1.1,
        height: s === 0 ? 2.0 : 1.8,
        head: s === 0 ? 'segment' : 'lintel',
        bars: 2,
        glass,
        frame: white,
        sill: stone,
      };
    });
    kit.cap(batch, kit.mat('#6d5148'), [[ring]], EAVE - 0.01);
    // pitched ring roof on the fitted rectangle
    const fr = kit.ringFrame(ring);
    const c = Math.cos(fr.angle),
      s = Math.sin(fr.angle);
    const P = (u, v, z) => [fr.cx + u * c - v * s, fr.cy + u * s + v * c, z];
    const hl = fr.length / 2 - 0.6,
      hw = fr.width / 2 - 0.6,
      D = 5.5,
      RISE = 3.6;
    const outer = [
      [-hl, -hw],
      [hl, -hw],
      [hl, hw],
      [-hl, hw],
    ];
    const inner = outer.map(([u, v]) => [u - Math.sign(u) * D, v - Math.sign(v) * D]);
    const inner2 = outer.map(([u, v]) => [u - Math.sign(u) * 2 * D, v - Math.sign(v) * 2 * D]);
    for (let k = 0; k < 4; k++) {
      const o0 = outer[k],
        o1 = outer[(k + 1) % 4],
        i0 = inner[k],
        i1 = inner[(k + 1) % 4],
        j0 = inner2[k],
        j1 = inner2[(k + 1) % 4];
      batch.add(
        tileM,
        [
          P(o0[0], o0[1], EAVE),
          P(o1[0], o1[1], EAVE),
          P(i1[0], i1[1], EAVE + RISE),
          P(i0[0], i0[1], EAVE + RISE),
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
      batch.add(
        tileM,
        [
          P(i0[0], i0[1], EAVE + RISE),
          P(i1[0], i1[1], EAVE + RISE),
          P(j1[0], j1[1], EAVE),
          P(j0[0], j0[1], EAVE),
        ],
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }
    // gables with stone copings on the north front, chimneys along the ridge
    const north = [];
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const ny = -(b[0] - a[0]) / len;
      if (ny > 0.8 && len > 10) north.push({ a, b, len });
    }
    for (const e of north) {
      const ux = (e.b[0] - e.a[0]) / e.len,
        uy = (e.b[1] - e.a[1]) / e.len;
      const eang = Math.atan2(uy, ux);
      const nx = uy,
        ny = -ux;
      for (const t of [0.18, 0.82]) {
        const gx = e.a[0] + ux * e.len * t,
          gy = e.a[1] + uy * e.len * t;
        const W = 6,
          H = 3.4;
        const tri = new THREE.Shape([
          new THREE.Vector2(-W / 2, 0),
          new THREE.Vector2(W / 2, 0),
          new THREE.Vector2(0, H),
        ]);
        const geo = new THREE.ExtrudeGeometry(tri, { depth: 4.5, bevelEnabled: false });
        const m = new THREE.Matrix4().makeBasis(
          new THREE.Vector3(ux, uy, 0),
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(nx, ny, 0),
        );
        m.setPosition(gx - nx * 4.5, gy - ny * 4.5, EAVE);
        batch.addGeometry(brick, geo, m);
        geo.dispose();
        // gable roof slopes
        for (const sd of [-1, 1]) {
          const len = Math.hypot(W / 2 + 0.3, H + 0.2);
          const bx = new THREE.BoxGeometry(len, 4.9, 0.12);
          const mm = new THREE.Matrix4()
            .makeRotationZ(eang)
            .multiply(new THREE.Matrix4().makeRotationY(sd * Math.atan2(H, W / 2)));
          mm.setPosition(
            gx + ux * sd * W * 0.25 - nx * 2.2,
            gy + uy * sd * W * 0.25 - ny * 2.2,
            EAVE + H / 2 + 0.1,
          );
          batch.addGeometry(tileM, bx, mm);
          bx.dispose();
        }
        kit.windowRow(
          batch,
          [gx - ux * 1.2 + nx * 0.01, gy - uy * 1.2 + ny * 0.01],
          [gx + ux * 1.2 + nx * 0.01, gy + uy * 1.2 + ny * 0.01],
          EAVE + 0.4,
          {
            count: 1,
            width: 1.2,
            height: 1.6,
            bars: 2,
            glass,
            frame: white,
            sill: stone,
          },
        );
      }
      // entrance: stone doorcase and blue lamp at the centre of the north front
      const mx = e.a[0] + ux * e.len * 0.5,
        my = e.a[1] + uy * e.len * 0.5;
      kit.box(batch, stone, mx + nx * 0.15, my + ny * 0.15, 0, 2.4, 0.3, 3.3, eang);
      kit.box(batch, door, mx + nx * 0.31, my + ny * 0.31, 0.1, 1.4, 0.05, 2.6, eang);
      kit.box(batch, stone, mx + nx * 0.4, my + ny * 0.4, 3.3, 2.8, 0.6, 0.25, eang);
      const lamp = new THREE.BoxGeometry(0.35, 0.35, 0.55);
      batch.addGeometry(
        lampBlue,
        lamp,
        new THREE.Matrix4().makeTranslation(mx + nx * 0.9, my + ny * 0.9, 3.9),
      );
      lamp.dispose();
    }
    for (const [u, v] of [
      [-hl + D * 0.5, 0],
      [hl - D * 0.5, 0],
      [0, -hw + D * 0.5],
      [0, hw - D * 0.5],
    ]) {
      const p = P(u, v, 0);
      kit.box(batch, brick, p[0], p[1], EAVE + 1.0, 1.0, 2.2, RISE + 0.6, fr.angle);
      kit.box(batch, stone, p[0], p[1], EAVE + RISE + 1.6, 1.2, 2.4, 0.2, fr.angle);
    }

    g.add(batch.toGroup('hyde_park_police_station'));
    return g;
  },
};
