// Earl's Court station (District and Piccadilly lines; Grade II). Train shed of 1878 by
// John Wolfe Barry: an elaborate pitched glazed roof carried on arched iron trusses
// running across the tracks, between brick side walls with arched niches. Earl's Court
// Road frontage of 1906 by Harry W. Ford in buff glazed faience with green trimmings,
// three entrance bays with white terracotta keystones, Ionic columns and a lettered
// fascia. The station was extended to Warwick Road in 1937 (curved-fronted entrance,
// later topped by a 1970s addition).
export default {
  id: 'earls_court_station',
  name: "Earl's Court station",
  claims: [
    'a0da8673-68a2-4c8f-9eb6-180036b83f30',
    '77d3571a-55c1-4dd3-95c3-235a623e9d47',
    '26940f5c-b0b3-4959-8a51-cbe88de7d48e',
  ],
  references: [
    {
      title: 'Earls Court Station - Historic England',
      url: 'https://historicengland.org.uk/listing/the-list/list-entry/1358162',
      used_for:
        '1878 train shed by John Wolfe Barry with pitched roof on arched iron trusses at right angles; 1906 Earl’s Court Road facade by Harry W Ford in buff glazed faience with green trimmings, three entrance bays, keystones, Ionic columns, fascia; 1937 Warwick Road extension, 1970s top',
    },
    {
      title: "Earl's Court tube station - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Earl%27s_Court_tube_station',
      used_for: 'station layout: two island platforms, four District tracks under the shed',
    },
    {
      title: 'Interior of Earls Court station, 1878 - London Transport Museum',
      url: 'https://www.ltmuseum.co.uk/collections/collections-online/photographs/item/1998-85109',
      used_for: 'glass and iron roof on iron beams, walls with arched niches, timber platforms',
    },
    {
      title: 'Works commence at Earl’s Court to restore Grade II listed roof - TfL',
      url: 'https://tfl.gov.uk/info-for/media/press-releases/2006/december/works-commence-at-earls-court-to-restore-grade-ii-listed-roof',
      used_for: 'Victorian train shed roof restored c.2008',
    },
  ],
  notes:
    'Shed extent, wall height (7.5 m), ridge (13 m), truss pitch (7.5 m), the proportion of glazing and the ' +
    'platform positions are estimates; the two narrow Warwick Road-end strips of the footprint are modelled as ' +
    'platform canopies. The Earl’s Court Road block is modelled as a two-storey faience frontage (10.5 m) in ' +
    'front of a 12.3 m brick block; bay widths, column count and lettering approximate. Warwick Road entrance ' +
    'curved front and 1970s top are schematic.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const frameOf = (deg, cx, cy) => {
      const a = (deg * Math.PI) / 180,
        c = Math.cos(a),
        s = Math.sin(a);
      return { a, L: (u, v) => [cx + u * c - v * s, cy + u * s + v * c] };
    };
    const rectOf = (F, u0, u1, v0, v1) => [F.L(u0, v0), F.L(u1, v0), F.L(u1, v1), F.L(u0, v1)];
    const brick = kit.mat('#8a5a44', { roughness: 0.9 });
    const stock = kit.mat('#b49c74', { roughness: 0.9 });
    const faience = kit.mat('#d9c58f', { roughness: 0.45 });
    const green = kit.mat('#2f5a43', { roughness: 0.45 });
    const white = kit.mat('#efeadc', { roughness: 0.5 });
    const glassR = kit.mat('#a9bfc8', {
      roughness: 0.15,
      metalness: 0.3,
      transparent: true,
      opacity: 0.7,
    });
    const iron = kit.mat('#4e5a5e', { roughness: 0.5, metalness: 0.5 });
    const lead = kit.mat('#6c7276', { roughness: 0.6, metalness: 0.2 });
    const glass = kit.mat('#2b3640', { roughness: 0.3, metalness: 0.2 });
    const paving = kit.mat('#b9b3a6', { roughness: 0.9 });

    // ---- train shed ---------------------------------------------------------------
    {
      const F = frameOf(48.34, 447.63, -1653.56);
      const U0 = -38,
        U1 = 69,
        V = 15,
        WH = 7.5,
        RIDGE = 13;
      for (const v of [-V, V]) {
        const r = rectOf(F, U0, U1, v < 0 ? -V - 0.9 : V, v < 0 ? -V : V + 0.9);
        kit.walls(batch, brick, [[r]], 0, WH, { bay: 1e6 });
        kit.cap(batch, stock, [[r]], WH);
        // arched niches (blind arcade) on the inner face, pilasters outside
        for (let u = U0 + 2; u < U1 - 2; u += 5) {
          const p = F.L(u + 2.5, v < 0 ? -V + 0.03 : V - 0.03);
          kit.box(batch, kit.mat('#6e4535'), p[0], p[1], 0.8, 3.4, 0.06, 4.4, F.a);
          const q = F.L(u, v < 0 ? -V - 1.0 : V + 1.0);
          kit.box(batch, brick, q[0], q[1], 0, 0.7, 0.25, WH, F.a);
        }
        kit.cornice(batch, stock, r, WH - 0.4, { height: 0.4, projection: 0.15 });
      }
      // pitched roof: glazed central band, lead-clad margins
      const slope = (v0, v1, mat) => {
        const z = (v) => WH + 0.2 + (RIDGE - WH - 0.2) * (1 - Math.abs(v) / V);
        const a0 = F.L(U0, v0),
          a1 = F.L(U1, v0),
          b1 = F.L(U1, v1),
          b0 = F.L(U0, v1);
        const verts = [
          [a0[0], a0[1], z(v0)],
          [a1[0], a1[1], z(v0)],
          [b1[0], b1[1], z(v1)],
          [b0[0], b0[1], z(v1)],
        ];
        const [p0, p1, p2] = verts;
        const nz = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0]);
        const tri = nz > 0 ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2];
        batch.add(
          mat,
          verts,
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          ],
          tri,
        );
      };
      slope(-V, -9, lead);
      slope(-9, 0, glassR);
      slope(V, 9, lead);
      slope(9, 0, glassR);
      // ridge lantern and glazing bars
      const rg = F.L((U0 + U1) / 2, 0);
      kit.box(batch, lead, rg[0], rg[1], RIDGE - 0.1, U1 - U0, 1.6, 0.7, F.a);
      kit.box(batch, lead, rg[0], rg[1], RIDGE + 0.6, U1 - U0, 2.2, 0.15, F.a);
      for (const side of [-1, 1])
        for (let k = 1; k < 4; k++) {
          const v = side * (k * 2.25);
          const p = F.L((U0 + U1) / 2, v);
          const z = WH + 0.2 + (RIDGE - WH - 0.2) * (1 - Math.abs(v) / V);
          kit.box(batch, iron, p[0], p[1], z, U1 - U0, 0.08, 0.1, F.a);
        }
      // arched iron trusses across the tracks
      const nT = Math.round((U1 - U0) / 7.5);
      for (let k = 0; k <= nT; k++) {
        const u = U0 + ((U1 - U0) * k) / nT;
        const N = 12;
        let prev = null;
        for (let i = 0; i <= N; i++) {
          const v = -V + (2 * V * i) / N;
          const t = v / V;
          const zArch = WH - 1.2 + 4.0 * (1 - t * t); // curved bottom chord
          const zTop = WH + 0.2 + (RIDGE - WH - 0.2) * (1 - Math.abs(t));
          const p = F.L(u, v);
          if (prev) {
            const m = [(p[0] + prev.p[0]) / 2, (p[1] + prev.p[1]) / 2];
            const len = (2 * V) / N,
              dz = zArch - prev.z;
            const geo = new THREE.BoxGeometry(0.18, Math.hypot(len, dz), 0.35);
            const mtx = new THREE.Matrix4()
              .makeRotationZ(F.a)
              .multiply(new THREE.Matrix4().makeRotationX(Math.atan2(dz, len)))
              .setPosition(m[0], m[1], (zArch + prev.z) / 2);
            batch.addGeometry(iron, geo, mtx);
            geo.dispose();
          }
          // vertical web members
          if (i % 2 === 0 && zTop - zArch > 0.4)
            kit.box(batch, iron, p[0], p[1], zArch, 0.1, 0.1, zTop - zArch, F.a);
          prev = { p, z: zArch };
        }
      }
      // two island platforms
      for (const v of [-7.5, 7.5]) {
        const p = F.L((U0 + U1) / 2, v);
        kit.box(batch, paving, p[0], p[1], 0, U1 - U0 - 2, 7.0, 0.95, F.a);
        for (let u = U0 + 4; u < U1 - 3; u += 15) {
          const q = F.L(u, v);
          kit.box(batch, kit.mat('#7a3b2a'), q[0], q[1], 0.95, 0.15, 1.6, 2.6, F.a); // timber sign boards
        }
      }
      // Warwick Road-end platform canopies (the two narrow footprint strips)
      for (const [va, vb] of [
        [3.0, 11.8],
        [-9.6, -1.8],
      ]) {
        const p = F.L(-53.5, (va + vb) / 2);
        kit.box(batch, lead, p[0], p[1], 4.4, 31, vb - va, 0.25, F.a);
        kit.box(batch, green, p[0], p[1], 4.0, 31.2, vb - va + 0.1, 0.4, F.a);
        for (let u = -67; u <= -40; u += 6) {
          const q = F.L(u, (va + vb) / 2);
          kit.box(batch, iron, q[0], q[1], 0, 0.2, 0.2, 4.2, F.a);
        }
        kit.box(batch, paving, p[0], p[1], 0, 31, vb - va, 0.95, F.a);
      }
    }

    // ---- Earl's Court Road building (Harry W. Ford, 1906) ------------------------------
    {
      const F = frameOf(136.27, 501.54, -1596.21);
      const ring = byId['77d3571a-55c1-4dd3-95c3-235a623e9d47'].polys[0][0].slice();
      if (kit.ringArea(ring) < 0) ring.reverse();
      kit.walls(batch, stock, [[ring]], 0, 12.3, { bay: 1e6 });
      kit.cap(batch, kit.mat('#8d8f8c'), [[ring]], 12.3);
      // faience frontage on the v = -10.8 side, facing Earl's Court Road (NE)
      const V = -10.85,
        U0 = -15.1,
        U1 = 12.5,
        FH = 10.5;
      const fr = rectOf(F, U0, U1, V - 0.6, V + 0.2);
      kit.walls(batch, faience, [[fr]], 0, FH, { bay: 1e6 });
      kit.cap(batch, faience, [[fr]], FH);
      kit.cornice(batch, green, fr, FH - 0.5, { height: 0.5, projection: 0.25 });
      kit.cornice(batch, faience, fr, 4.6, { height: 0.25, projection: 0.12 });
      // green fascia band with lettering
      const sign = kit.paintedMaterial(
        'earls_court:fascia',
        1024,
        64,
        (c, w, h) => {
          c.fillStyle = '#2f5a43';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#efe3b8';
          c.font = 'bold 27px serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText(
            "EARL'S COURT STATION  ·  DISTRICT RAILWAY  ·  PICCADILLY & BROMPTON",
            w / 2,
            h / 2 + 2,
          );
        },
        { roughness: 0.5 },
      );
      {
        const a = F.L(U0 + 0.3, V - 0.63),
          b = F.L(U1 - 0.3, V - 0.63);
        batch.quad(
          sign,
          [a[0], a[1], 4.9],
          [b[0], b[1], 4.9],
          [b[0], b[1], 5.8],
          [a[0], a[1], 5.8],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      // ground floor: three entrance bays in the centre, shopfronts either side
      const edgeA = F.L(U0, V - 0.6),
        edgeB = F.L(U1, V - 0.6); // a->b with outward normal to the NE
      const t = (u) => (u - U0) / (U1 - U0);
      const lerp = (k) => [
        edgeA[0] + (edgeB[0] - edgeA[0]) * k,
        edgeA[1] + (edgeB[1] - edgeA[1]) * k,
      ];
      const out = (p, d) => {
        // outward normal of a->b is (dy, -dx)/len
        const dx = edgeB[0] - edgeA[0],
          dy = edgeB[1] - edgeA[1],
          l = Math.hypot(dx, dy);
        return [p[0] + (dy / l) * d, p[1] - (dx / l) * d];
      };
      for (let k = 0; k < 3; k++) {
        const u = -4.6 + k * 4.6;
        const p = out(lerp(t(u)), 0.04);
        kit.box(batch, kit.mat('#1e2326'), p[0], p[1], 0, 3.4, 0.06, 3.9, F.a);
        const ks = out(lerp(t(u)), 0.12);
        kit.box(batch, white, ks[0], ks[1], 3.9, 0.6, 0.18, 0.7, F.a); // keystone
      }
      for (const u of [-6.9, -2.3, 2.3, 6.9]) {
        // Ionic columns between the bays
        const p = out(lerp(t(u)), 0.35);
        const geo = new THREE.CylinderGeometry(0.28, 0.32, 4.4, 12).rotateX(Math.PI / 2);
        batch.addGeometry(faience, geo, new THREE.Matrix4().makeTranslation(p[0], p[1], 2.2));
        geo.dispose();
        kit.box(batch, faience, p[0], p[1], 4.35, 0.9, 0.9, 0.3, F.a);
      }
      for (const [ua, ub] of [
        [U0 + 0.6, -7.6],
        [7.6, U1 - 0.6],
      ]) {
        const a = lerp(t(ua)),
          b = lerp(t(ub));
        kit.windowRow(batch, a, b, 0.6, {
          glass,
          frame: green,
          head: 'none',
          count: 2,
          width: 2.6,
          height: 3.4,
          bars: 1,
          margin: 0.3,
        });
      }
      // first floor: arched windows with keystones
      kit.windowRow(batch, edgeA, edgeB, 6.4, {
        glass,
        frame: white,
        head: 'arch',
        count: 7,
        width: 1.8,
        height: 2.2,
        margin: 1.0,
        bars: 2,
        surround: 0.2,
        surroundMat: green,
      });
      // parapet blocks
      for (const u of [U0 + 0.5, U1 - 0.5, -1.3]) {
        const p = out(lerp(t(u)), -0.2);
        kit.box(batch, faience, p[0], p[1], FH, 1.4, 1.0, 1.2, F.a);
      }
    }

    // ---- Warwick Road entrance (1937) with the 1970s addition above ---------------------
    {
      const ring = byId['26940f5c-b0b3-4959-8a51-cbe88de7d48e'].polys[0][0].slice();
      if (kit.ringArea(ring) < 0) ring.reverse();
      kit.walls(batch, stock, [[ring]], 0, 5.6, { bay: 1e6 });
      kit.cornice(batch, kit.mat('#d8d2c2'), ring, 5.2, { height: 0.4, projection: 0.3 });
      kit.cap(batch, kit.mat('#8d8f8c'), [[ring]], 5.6);
      const inner = kit.offsetRing(ring, -0.05);
      for (let k = 0; k < inner.length; k++) {
        const a = inner[k],
          b = inner[(k + 1) % inner.length];
        if (Math.hypot(b[0] - a[0], b[1] - a[1]) < 1.5) continue;
        kit.windowRow(batch, a, b, 1.2, {
          glass,
          frame: kit.mat('#d8d2c2'),
          head: 'none',
          width: 1.6,
          height: 3.2,
          bay: 2.2,
          margin: 0.3,
          bars: 2,
        });
      }
      const top = kit.offsetRing(ring, -2.2);
      kit.walls(batch, kit.mat('#5c5f61'), [[top]], 5.6, 10.4, { bay: 1e6 });
      kit.cap(batch, kit.mat('#8d8f8c'), [[top]], 10.4);
      for (let k = 0; k < top.length; k++) {
        const a = top[k],
          b = top[(k + 1) % top.length];
        if (Math.hypot(b[0] - a[0], b[1] - a[1]) < 2) continue;
        kit.windowRow(batch, a, b, 6.6, {
          glass,
          frame: kit.mat('#3a3d3f'),
          head: 'none',
          width: 2.0,
          height: 1.6,
          bay: 2.6,
          margin: 0.4,
          bars: 0,
        });
        kit.windowRow(batch, a, b, 8.6, {
          glass,
          frame: kit.mat('#3a3d3f'),
          head: 'none',
          width: 2.0,
          height: 1.4,
          bay: 2.6,
          margin: 0.4,
          bars: 0,
        });
      }
      // Underground roundel on the curved front
      const F = frameOf(226.82, 343.28, -1791.82);
      const p = F.L(11.5, 0);
      const disc = new THREE.CylinderGeometry(0.9, 0.9, 0.08, 24);
      batch.addGeometry(
        kit.mat('#c8102e'),
        disc,
        new THREE.Matrix4().makeRotationZ(F.a + Math.PI / 2).setPosition(p[0], p[1], 4.3),
      );
      disc.dispose();
      kit.box(
        batch,
        kit.mat('#10239e'),
        p[0] + Math.cos(F.a) * 0.06,
        p[1] + Math.sin(F.a) * 0.06,
        4.08,
        0.05,
        2.3,
        0.44,
        F.a,
      );
    }

    g.add(batch.toGroup('earls_court_station'));
    return g;
  },
};
