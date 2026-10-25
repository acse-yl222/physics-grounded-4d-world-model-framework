// Imperial College Translation & Innovation Hub (I-HUB), White City Campus
// (PLP Architecture / Aukett Swanke, Laing O'Rourke, completed 2016). ~187,000 sq ft
// research and enterprise building on Wood Lane beside the elevated Westway: a
// 13-storey block with a seven-storey wing that buffers it from the motorway, joined
// by a central atrium under an asymmetric steel-and-glass roof. Fully unitised facade
// of glazing, terracotta and cantilevered metal sun-shades.
export default {
  id: 'imperial_i_hub',
  name: 'Imperial College Translation & Innovation Hub (I-HUB)',
  claims: ['1debec9f-f376-4c58-bdc2-8d7dd6c03604'],
  references: [
    {
      title:
        'Imperial College, White City Campus, Translation & Innovation Hub - Thornton Tomasetti',
      url: 'https://thorntontomasetti.com/project/imperial-college-white-city-campus-translation-innovation-hub',
      used_for:
        '12-storey building with seven-storey wing buffering the motorway; unitised glazing + metal sun shading + terracotta; asymmetric steel atrium roof',
    },
    {
      title: 'Imperial launches its new hub for innovation at White City - Imperial News',
      url: 'https://www.imperial.ac.uk/news/175572/imperial-launches-innovation-white-city/',
      used_for: '13-storey building, scale',
    },
    {
      title: 'Imperial College London - PLP Architecture',
      url: 'https://plparchitecture.com/?p=5696',
      used_for: 'PLP design, 12-storey facility',
    },
    {
      title: "Laing O'Rourke hands over £200m uni hub - Building",
      url: 'https://building.co.uk/news/laing-orourke-hands-over-200m-uni-hub/5083518.article',
      used_for: 'architects PLP and Aukett Swanke, cost',
    },
  ],
  notes:
    'Overture h=11 m is wrong. Heights from storey counts: 13-storey block ~54 m, 7-storey Westway wing ~30 m ' +
    '(6 m ground + 4.0 m floors, estimated). Which part of the footprint carries the tall block (north, away ' +
    'from the Westway) and the atrium position/roof shape are inferred from the "buffer wing" description, not ' +
    'from drawings. Terracotta colour and sun-shade spacing approximate.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();

    // ---- helpers -------------------------------------------------------------
    const edgesOf = (r) =>
      r.map((a, k) => {
        const b = r[(k + 1) % r.length];
        const dx = b[0] - a[0],
          dy = b[1] - a[1],
          len = Math.hypot(dx, dy) || 1;
        return { a, b, len, dx: dx / len, dy: dy / len, nx: dy / len, ny: -dx / len };
      });
    const skin = (mat, r, z0, z1, tw, th, base = 0) => {
      let s = 0;
      for (const e of edgesOf(r)) {
        if (e.len < 0.05) continue;
        const v0 = (z0 - base) / th,
          v1 = (z1 - base) / th;
        batch.quad(
          mat,
          [e.a[0], e.a[1], z0],
          [e.b[0], e.b[1], z0],
          [e.b[0], e.b[1], z1],
          [e.a[0], e.a[1], z1],
          [s / tw, v0],
          [(s + e.len) / tw, v0],
          [(s + e.len) / tw, v1],
          [s / tw, v1],
        );
        s += e.len;
      }
    };
    // Keep the part of ring with  n . p >= d  (Sutherland-Hodgman, one half-plane).
    const clip = (r, nx, ny, d) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const p = r[k],
          q = r[(k + 1) % r.length];
        const fp = nx * p[0] + ny * p[1] - d,
          fq = nx * q[0] + ny * q[1] - d;
        if (fp >= 0) out.push(p);
        if (fp * fq < 0) {
          const t = fp / (fp - fq);
          out.push([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])]);
        }
      }
      return out;
    };
    const prism = (wallMat, roofMat, r, z0, z1, tw, th, base) => {
      skin(wallMat, r, z0, z1, tw, th, base);
      kit.cap(batch, roofMat, [[r]], z1);
    };

    // ---- materials -----------------------------------------------------------
    const facade = kit.paintedMaterial(
      'ihub:facade',
      512,
      512,
      (c, w, h) => {
        // 6 m x 2 storeys: four 1.5 m bays; glass with terracotta piers and spandrels.
        c.fillStyle = '#d29a74';
        c.fillRect(0, 0, w, h);
        const bw = w / 4,
          sh = h / 2;
        for (let s = 0; s < 2; s++)
          for (let k = 0; k < 4; k++) {
            const x = k * bw + 14,
              y = s * sh + 22;
            const grd = c.createLinearGradient(x, y, x, y + sh - 70);
            grd.addColorStop(0, '#4f6676');
            grd.addColorStop(1, '#2f404d');
            c.fillStyle = grd;
            c.fillRect(x, y, bw - 28, sh - 70);
            c.fillStyle = 'rgba(210,225,235,0.2)';
            c.fillRect(x + 4, y + 4, (bw - 28) * 0.35, sh - 80);
          }
        c.fillStyle = 'rgba(90,40,20,0.18)';
        for (let y = 0; y < h; y += 10) c.fillRect(0, y, w, 1);
      },
      { roughness: 0.6 },
    );
    const curtain = kit.paintedMaterial(
      'ihub:curtain',
      512,
      512,
      (c, w, h) => {
        c.fillStyle = '#3b5262';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#c2c6c8';
        for (let k = 0; k < 4; k++) c.fillRect((k * w) / 4, 0, 5, h);
        c.fillRect(0, h / 2 - 16, w, 16);
        c.fillRect(0, h - 16, w, 16);
      },
      { roughness: 0.25, metalness: 0.3 },
    );
    const shade = kit.mat('aluminium');
    const roofM = kit.mat('#8e908d');
    const atriumGlass = kit.mat('#7d98a8', {
      roughness: 0.15,
      metalness: 0.4,
      transparent: true,
      opacity: 0.75,
    });
    const steel = kit.mat('white_steel');

    // ---- massing ---------------------------------------------------------------
    // Axis along the Westway frontage (longest south-ish edge).
    const E = edgesOf(ring);
    const front = E.filter((e) => e.nx * 0 + e.ny < -0.8).sort((p, q) => q.len - p.len)[0];
    const ux = front.dx,
      uy = front.dy; // along frontage
    const nx = -front.nx,
      ny = -front.ny; // inward (north)
    const d0 = nx * front.a[0] + ny * front.a[1];
    const G = 6,
      ST = 4.0;
    const zW = G + 6 * ST; // 7 storeys = 30 m
    const zT = G + 12 * ST; // 13 storeys = 54 m
    const wing = clip(clip(ring, -nx, -ny, -(d0 + 15)), nx, ny, d0 - 1);
    const atrium = clip(clip(ring, nx, ny, d0 + 15), -nx, -ny, -(d0 + 24));
    const tower = clip(ring, nx, ny, d0 + 24);

    // Glazed ground floor all round, set back under the upper floors.
    const shrink = (r, d) => {
      const o = kit.offsetRing(r, -d);
      return kit.ringArea(o) > 0 ? o : r;
    };
    for (const part of [wing, tower]) {
      skin(kit.mat('dark_glass'), shrink(part, 1.0), 0, G, 6, 8);
      kit.cap(batch, steel, [[part]], G, { down: true });
    }
    // Wing (Westway side), 7 storeys.
    prism(facade, roofM, wing, G, zW, 6, 2 * ST, G);
    kit.walls(batch, steel, [[wing]], zW, zW + 1.1);
    // Tower, 13 storeys.
    prism(facade, roofM, tower, G, zT, 6, 2 * ST, G);
    kit.walls(batch, steel, [[tower]], zT, zT + 1.1);
    // Roof plant on the tower.
    const plant = shrink(tower, 5);
    skin(
      kit.paintedMaterial('ihub:louvre', 128, 128, (c, w, h) => {
        c.fillStyle = '#b8bcbd';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#80868a';
        for (let y = 0; y < h; y += 10) c.fillRect(0, y, w, 4);
      }),
      plant,
      zT,
      zT + 4,
      3,
      4,
      zT,
    );
    kit.cap(batch, roofM, [[plant]], zT + 4);

    // Atrium: glazed ends, asymmetric glass roof rising from the wing to the tower.
    skin(curtain, atrium, 0, zW, 6, 2 * ST, G);
    {
      // Roof: rows of glazing panels from wing top (zW) at d0+15 to zT-8 at d0+24.
      const zLow = zW + 1,
        zHigh = zW + 12;
      const ex = kit.orientedExtent(atrium, Math.atan2(uy, ux));
      const v0 = ex.v0,
        v1 = ex.v1;
      const P = (u, v) => {
        const z = zLow + ((v - v0) / (v1 - v0)) * (zHigh - zLow);
        return [...ex.at(u, v, 0).slice(0, 2), z];
      };
      // glass slope
      batch.quad(
        atriumGlass,
        P(ex.u0, v0),
        P(ex.u1, v0),
        P(ex.u1, v1),
        P(ex.u0, v1),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        atriumGlass,
        P(ex.u0, v1),
        P(ex.u1, v1),
        P(ex.u1, v0),
        P(ex.u0, v0),
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      // steel rafters
      for (let u = ex.u0; u <= ex.u1 + 0.01; u += (ex.u1 - ex.u0) / 12) {
        const a = P(u, v0),
          b = P(u, v1);
        const len = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
        const X = new THREE.Vector3(ux, uy, 0);
        const Y = new THREE.Vector3((b[0] - a[0]) / len, (b[1] - a[1]) / len, (b[2] - a[2]) / len);
        const Z = new THREE.Vector3().crossVectors(X, Y);
        const m = new THREE.Matrix4()
          .makeBasis(X, Y, Z)
          .setPosition((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2 + 0.25);
        const geo = new THREE.BoxGeometry(0.3, len, 0.5);
        batch.addGeometry(steel, geo, m);
        geo.dispose();
      }
      // side gables between wing roof and the sloping roof
      for (const u of [ex.u0, ex.u1]) {
        const a = ex.at(u, v0, 0),
          b = ex.at(u, v1, 0);
        const vs = [
          [a[0], a[1], zW],
          [b[0], b[1], zW],
          [b[0], b[1], zHigh],
          [a[0], a[1], zLow],
        ];
        const uvs = [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ];
        batch.add(atriumGlass, vs, uvs, [0, 1, 2, 0, 2, 3]);
        batch.add(atriumGlass, vs, uvs, [0, 2, 1, 0, 3, 2]);
      }
    }

    // Cantilevered metal sun-shades at every floor on the wing (all faces) and tower.
    const shades = (r, z0, n) => {
      for (const e of edgesOf(r)) {
        if (e.len < 4) continue;
        // skip edges internal to the atrium cut (parallel to frontage and inside the plan)
        const ang = Math.atan2(e.dy, e.dx);
        const cx = (e.a[0] + e.b[0]) / 2 + e.nx * 0.6,
          cy = (e.a[1] + e.b[1]) / 2 + e.ny * 0.6;
        for (let k = 1; k <= n; k++)
          kit.box(batch, shade, cx, cy, z0 + k * ST - 0.55, e.len, 1.2, 0.12, ang);
      }
    };
    shades(
      wing.filter(() => true),
      G - ST,
      7,
    );
    shades(tower, G - ST, 13);
    // Vertical terracotta fins on the Westway (south) face, every 3 m.
    {
      const e = front,
        ang = Math.atan2(e.dy, e.dx);
      const terra = kit.mat('#b9714b', { roughness: 0.7 });
      for (let s = 1.5; s < e.len - 1; s += 3)
        kit.box(
          batch,
          terra,
          e.a[0] + e.dx * s + e.nx * 0.45,
          e.a[1] + e.dy * s + e.ny * 0.45,
          G,
          0.3,
          0.9,
          zW - G,
          ang,
        );
    }
    g.add(batch.toGroup('imperial_i_hub'));
    return g;
  },
};
