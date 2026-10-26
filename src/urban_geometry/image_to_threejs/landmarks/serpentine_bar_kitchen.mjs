// Serpentine Bar & Kitchen (the former Dell Restaurant), eastern end of the Serpentine,
// Hyde Park. Patrick Gwynne, opened 1964-65, Grade II*: a single-storey glazed pavilion
// on a polygonal plan with an underlying octagonal form under a tent-like glass
// reinforced plastic roof (which hides an office), a central concrete core, and steel
// trusses cantilevered over the water carrying a balcony with tilted steel railings.
export default {
  id: 'serpentine_bar_kitchen',
  name: 'Serpentine Bar & Kitchen (Dell Restaurant)',
  claims: ['b147e576-892d-4feb-97a4-b21e0e2e318e'],
  references: [
    {
      title: 'Dell Restaurant - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Dell_Restaurant',
      used_for: 'Grade II* restaurant at the eastern end of the Serpentine, Patrick Gwynne, 1964',
    },
    {
      title: 'Dell Restaurant - British Listed Buildings (Historic England 1251150)',
      url: 'https://britishlistedbuildings.co.uk/101251150-dell-restaurant-knightsbridge-and-belgravia-ward',
      used_for:
        'polygonal plan with octagonal underlying form; single storey with office hidden in tent-like GRP roof; central concrete core; steel trusses cantilevered over the Serpentine; balcony with tilted steel railings',
    },
    {
      title: 'Serpentine Bar & Kitchen - The Royal Parks',
      url: 'https://www.royalparks.org.uk/parks/hyde-park/food-and-drink/serpentine-bar-and-kitchen',
      used_for: 'modernist building by Patrick Gwynne opened 1964, overlooking the lake',
    },
    {
      title: 'Serpentine cafe by Mizzi Studio - Dezeen',
      url: 'https://www.dezeen.com/2018/06/21/serpentine-cafe-mizzi-studio-architecture/',
      used_for: "reference to Gwynne's Dell Restaurant (1965) and its curving roof",
    },
  ],
  notes:
    'Walls follow the footprint inset by 1.2 m (the roof overhang); glazing height (3.2 m), the eight-sided tent ' +
    'roof with up-turned eaves rising to 8.2 m, the office lantern near the apex, and the extent of the timber ' +
    'balcony over the water on the west (lake) side are estimates; the white GRP and dark-framed glazing ' +
    'colours are assumptions.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    let cx = 0,
      cy = 0,
      ar = 0;
    for (let k = 0; k < ring.length; k++) {
      const p = ring[k],
        q = ring[(k + 1) % ring.length],
        cr = p[0] * q[1] - q[0] * p[1];
      ar += cr;
      cx += (p[0] + q[0]) * cr;
      cy += (p[1] + q[1]) * cr;
    }
    cx /= 3 * ar;
    cy /= 3 * ar;
    const glassM = kit.mat('#35454f', { roughness: 0.12, metalness: 0.4 });
    const mull = kit.mat('#2a2d2f', { roughness: 0.45, metalness: 0.5 });
    const grp = kit.mat('#f1efe8', { roughness: 0.55, side: THREE.DoubleSide });
    const soffit = kit.mat('#d9d4c8', { roughness: 0.7 });
    const concrete = kit.mat('concrete');
    const deck = kit.mat('#8b6e52', { roughness: 0.85 });
    const steel = kit.mat('#3b4144', { roughness: 0.4, metalness: 0.6 });
    const paving = kit.mat('#bdb6a8');

    const EAVE = 3.4;
    const body = kit.offsetRing(ring, -1.2);
    kit.cap(batch, paving, [[kit.offsetRing(ring, 0.6)]], 0.15);
    kit.walls(batch, glassM, [[body]], 0.15, EAVE, { bay: 1e6 });
    // mullions every ~1.5 m and a transom
    for (let k = 0; k < body.length; k++) {
      const a = body[k],
        b = body[(k + 1) % body.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const an = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const nx = (b[1] - a[1]) / len,
        ny = -(b[0] - a[0]) / len;
      const n = Math.max(1, Math.round(len / 1.5));
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        kit.box(
          batch,
          mull,
          a[0] + (b[0] - a[0]) * t + nx * 0.05,
          a[1] + (b[1] - a[1]) * t + ny * 0.05,
          0.15,
          0.09,
          0.12,
          EAVE - 0.15,
          an,
        );
      }
      kit.box(
        batch,
        mull,
        (a[0] + b[0]) / 2 + nx * 0.05,
        (a[1] + b[1]) / 2 + ny * 0.05,
        2.5,
        len,
        0.1,
        0.08,
        an,
      );
    }
    // central concrete core rising through the roof
    kit.box(batch, concrete, cx, cy, 0, 4.5, 4.5, 6.8, 0.39);

    // tent roof: octagonal, up-swept eaves, apex lantern
    const R = Math.sqrt(Math.abs(ar) / 2 / (2 * Math.sqrt(2))) * 1.02; // octagon of equal area
    const prof = [
      [R + 0.9, EAVE + 0.55],
      [R * 0.92, EAVE + 0.15],
      [R * 0.78, EAVE + 0.9],
      [R * 0.55, EAVE + 2.3],
      [R * 0.3, EAVE + 3.7],
      [R * 0.1, EAVE + 4.6],
      [0.0, EAVE + 4.8],
    ];
    const roofG = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(r, h)),
      8,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(grp, roofG, new THREE.Matrix4().makeRotationZ(0.39).setPosition(cx, cy, 0));
    roofG.dispose();
    // soffit under the overhang (a down-facing octagon ring)
    const oct = (r) => {
      const out = [];
      for (let k = 0; k < 8; k++) {
        const a = 0.39 + Math.PI / 2 + (k * Math.PI) / 4;
        out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
      }
      return out;
    };
    kit.cap(batch, soffit, [[oct(R * 0.92)]], EAVE + 0.14, { down: true });
    // ridges along the eight hips
    for (let k = 0; k < 8; k++) {
      const a = 0.39 + Math.PI / 2 + (k * Math.PI) / 4;
      for (let i = 0; i < prof.length - 1; i++) {
        const [r0, z0] = prof[i],
          [r1, z1] = prof[i + 1];
        const x0 = cx + Math.cos(a) * r0,
          y0 = cy + Math.sin(a) * r0,
          x1 = cx + Math.cos(a) * r1,
          y1 = cy + Math.sin(a) * r1;
        const len = Math.hypot(r1 - r0, z1 - z0);
        const geo = new THREE.BoxGeometry(len, 0.22, 0.18);
        const m = new THREE.Matrix4()
          .makeRotationZ(a)
          .multiply(new THREE.Matrix4().makeRotationY(-Math.atan2(z1 - z0, r1 - r0) + Math.PI));
        m.setPosition((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2 + 0.06);
        batch.addGeometry(grp, geo, m);
        geo.dispose();
      }
    }
    // office windows hidden in the roof: a band of small dormer lights on two faces
    for (const k of [1, 5]) {
      const a = 0.39 + Math.PI / 2 + ((k + 0.5) * Math.PI) / 4;
      const r = R * 0.48;
      kit.box(
        batch,
        glassM,
        cx + Math.cos(a) * r,
        cy + Math.sin(a) * r,
        EAVE + 2.4,
        0.25,
        3.0,
        0.7,
        a,
      );
    }
    // vent finial at the apex
    const fin = new THREE.CylinderGeometry(0.15, 0.35, 1.2, 8).rotateX(Math.PI / 2);
    batch.addGeometry(steel, fin, new THREE.Matrix4().makeTranslation(cx, cy, EAVE + 5.3));
    fin.dispose();

    // cantilevered balcony over the water on the west (lake) side
    const west = ring.reduce((m, p) => (p[0] < m[0] ? p : m), ring[0]);
    const bx0 = west[0] + 2.0;
    const deckPts = [
      [bx0, cy - 11],
      [bx0 + 3, cy - 13],
      [bx0 + 3, cy + 12],
      [bx0, cy + 10],
      [bx0 - 6.5, cy + 6],
      [bx0 - 7.5, cy],
      [bx0 - 6.5, cy - 6],
    ].map(([x, y]) => [x, y]);
    const dr = kit.ringArea(deckPts) < 0 ? deckPts.reverse() : deckPts;
    kit.cap(batch, deck, [[dr]], 1.0);
    kit.cap(batch, steel, [[dr]], 0.75, { down: true });
    kit.walls(batch, steel, [[dr]], 0.75, 1.0, { bay: 1e6 });
    // trusses below, tilted railing posts with a top rail
    for (let k = 0; k < dr.length; k++) {
      const a = dr[k],
        b = dr[(k + 1) % dr.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const an = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const nx = (b[1] - a[1]) / len,
        ny = -(b[0] - a[0]) / len;
      if (a[0] >= bx0 && b[0] >= bx0) continue; // building side
      const n = Math.max(1, Math.round(len / 1.4));
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        const x = a[0] + (b[0] - a[0]) * t,
          y = a[1] + (b[1] - a[1]) * t;
        const post = new THREE.BoxGeometry(0.06, 0.06, 1.15);
        const m = new THREE.Matrix4()
          .makeRotationZ(an)
          .multiply(new THREE.Matrix4().makeRotationX(0.35));
        m.setPosition(x + nx * 0.2, y + ny * 0.2, 1.55);
        batch.addGeometry(steel, post, m);
        post.dispose();
      }
      kit.box(
        batch,
        steel,
        (a[0] + b[0]) / 2 + nx * 0.4,
        (a[1] + b[1]) / 2 + ny * 0.4,
        2.05,
        len,
        0.08,
        0.08,
        an,
      );
      // underside truss
      kit.box(batch, steel, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.25, len, 0.15, 0.5, an);
    }

    g.add(batch.toGroup('serpentine_bar_kitchen'));
    return g;
  },
};
