// South Kensington Underground station: the street-level buildings between Thurloe
// Street, Pelham Street and Old Brompton Road. Station of 1867-68, substantially altered
// in 1907 when George Sherrin laid out the Edwardian shopping arcade for the
// Metropolitan Railway: a glazed barrel-vaulted roof over shops on each side, closed at
// the Thurloe Street and Pelham Street ends by wrought-iron screens carrying the
// station's name. The single-storey shop island curves round to Old Brompton Road; to the
// east the 1907 Leslie Green frontage on Pelham Street (Piccadilly tube) in ox-blood
// glazed faience with large semicircular first-floor windows. Grade II (2004).
export default {
  id: 'south_kensington_station',
  name: 'South Kensington station and arcade',
  claims: ['ba224f4d-4d76-45b4-a986-8ab89770845e', 'a19bd501-a7cf-4b4f-9552-0c6f4f985f0b'],
  references: [
    {
      title: 'South Kensington Underground Station - British Listed Buildings (list entry 1392067)',
      url: 'https://britishlistedbuildings.co.uk/101392067-south-kensington-underground-station-brompton-hans-town-ward',
      used_for:
        '1867-68, altered 1907; Sherrin arcade between Thurloe Street and Pelham Street with glazed barrel-vaulted roof over shops; wrought-iron screens with the station name; Leslie Green frontage on Pelham Street',
    },
    {
      title: 'South Kensington tube station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/South_Kensington_tube_station',
      used_for: 'history of the District/Circle and Piccadilly entrances',
    },
    {
      title: 'Exterior of South Kensington Underground station, c 1908 - London Transport Museum',
      url: 'https://www.ltmuseum.co.uk/collections/collections-online/photographs/item/1998-57400',
      used_for: 'Edwardian exterior (catalogue record)',
    },
    {
      title: 'RBKC Listed Buildings Search - South Kensington station',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=491726',
      used_for: 'listing summary',
    },
  ],
  notes:
    'Arcade width (6.5 m), vault springing (4.6 m) and its line are taken from the OSM arcade path; shop unit ' +
    'widths, fascia colours, the curved island parapet and the iron screen design are approximations. The ' +
    'Leslie Green block is modelled as two storeys (7.2 m data height) of ox-blood faience with arched ground-floor ' +
    'openings and semicircular first-floor windows on Pelham Street; its upper back is plain. Roundel signs and ' +
    'lettering are painted.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const T = tools(THREE, kit, batch);
    const isl = byId['ba224f4d-4d76-45b4-a986-8ab89770845e'];
    const east = byId['a19bd501-a7cf-4b4f-9552-0c6f4f985f0b'];
    const stucco = kit.mat('#e8e1d2', { roughness: 0.85 });
    const stone = kit.mat('#d9cfba', { roughness: 0.85 });
    const oxblood = kit.mat('#7a1f1c', { roughness: 0.35, metalness: 0.05 });
    const iron = kit.mat('#2a3a33', { roughness: 0.5, metalness: 0.6 });
    const glass = kit.mat('#2a343d', { roughness: 0.12, metalness: 0.4 });
    const roofGlass = kit.mat('#b9d0d8', {
      roughness: 0.1,
      metalness: 0.1,
      transparent: true,
      opacity: 0.55,
    });
    const fasciaCols = ['#1e3a5f', '#2d4a2d', '#5a2121', '#222222', '#6b5a2a', '#3c3c5a'];
    const r = kit.rng(0.77);
    const SH = 4.6; // shop height
    const shopfronts = (e, z1, skip = () => false) => {
      const n = Math.max(1, Math.round(e.len / 5));
      for (let k = 0; k < n; k++) {
        const s0 = (k * e.len) / n,
          s1 = ((k + 1) * e.len) / n;
        if (skip((s0 + s1) / 2)) continue;
        T.ebox(glass, e, s0 + 0.3, s1 - 0.3, -0.02, 0.03, 0.4, 3.2);
        T.ebox(kit.mat('#1f1f1f'), e, s0 + 0.3, s1 - 0.3, 0, 0.08, 0, 0.4);
        T.ebox(
          kit.mat(fasciaCols[Math.floor(r() * fasciaCols.length)]),
          e,
          s0 + 0.15,
          s1 - 0.15,
          0,
          0.2,
          3.25,
          4.0,
        );
        T.ebox(stone, e, s0 - 0.15, s0 + 0.15, 0, 0.22, 0, z1);
      }
      T.ebox(stone, e, 0, e.len, 0, 0.3, z1 - 0.5, z1 - 0.2);
    };
    // --- arcade axis from the OSM path (x ~ 1822 at Thurloe St to ~1820 at Pelham St) ---
    const A0 = [1822.3, -1346.0],
      A1 = [1820.0, -1384.5];
    const AW = 6.5;
    const ad = [A1[0] - A0[0], A1[1] - A0[1]],
      al = Math.hypot(ad[0], ad[1]);
    const au = [ad[0] / al, ad[1] / al],
      an = [au[1], -au[0]]; // an points west
    const AP = (s, d) => [A0[0] + au[0] * s + an[0] * d, A0[1] + au[1] * s + an[1] * d];
    // clip a ring to the half-plane side*d(p) >= off, d = offset from the arcade axis (west +)
    const dOf = (p) => (p[0] - A0[0]) * an[0] + (p[1] - A0[1]) * an[1];
    const clip = (ring, side, off) => {
      const out = [];
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const fp = side * dOf(p) - off,
          fq = side * dOf(q) - off;
        if (fp >= 0) out.push(p);
        if (fp * fq < 0) {
          const t = fp / (fp - fq);
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
      }
      return out;
    };
    const shared = (e) => {
      const m = [(e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2];
      const L0 = [1828.2, -1386.2],
        L1 = [1830.7, -1350.1];
      const dx = L1[0] - L0[0],
        dy = L1[1] - L0[1],
        ll = Math.hypot(dx, dy);
      return Math.abs(((m[0] - L0[0]) * dy - (m[1] - L0[1]) * dx) / ll) < 0.6;
    };
    // --- island block (curved shops), split by the open arcade passage ---
    if (isl) {
      const full = T.ccw(isl.polys[0][0]);
      for (const side of [1, -1]) {
        const ring = T.ccw(clip(full, side, AW / 2));
        if (ring.length < 3 || Math.abs(kit.ringArea(ring)) < 5) continue;
        const E = T.edges(ring);
        for (const e of E) T.quad(stucco, e.a, e.b, 0, SH);
        kit.cornice(batch, stone, ring, SH - 0.4, { height: 0.4, projection: 0.35 });
        kit.walls(batch, stucco, [[ring]], SH, SH + 0.9);
        kit.cap(batch, kit.mat('#8d8d89'), [[kit.offsetRing(ring, -0.3)]], SH + 0.1);
        for (const e of E) {
          if (e.len < 3 || shared(e)) continue;
          shopfronts(e, SH);
          if (
            Math.abs(Math.abs(dOf(e.a)) - AW / 2) > 0.3 ||
            Math.abs(Math.abs(dOf(e.b)) - AW / 2) > 0.3
          )
            kit.balustrade(batch, stone, [T.at(e, 0.1, -0.15), T.at(e, e.len - 0.1, -0.15)], SH, {
              height: 0.9,
              spacing: 0.35,
            });
        }
        if (side < 0) continue;
        // station entrance on Old Brompton Road (west curve): canopy and name band
        const wE = E.filter((e) => e.nx < -0.85 && e.len > 3)[0] ?? E[0];
        const sign = kit.paintedMaterial('south_kensington_station:name', 512, 64, (c, w, h) => {
          c.fillStyle = '#f2efe6';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#1b2a5a';
          c.font = 'bold 34px serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('SOUTH KENSINGTON STATION', w / 2, h / 2 + 2);
        });
        const sa = T.at(wE, -2, 0.4),
          sb = T.at(wE, wE.len + 2, 0.4);
        T.quad(sign, sa, sb, SH - 0.2, SH + 0.8);
        T.ebox(iron, wE, -1.5, wE.len + 1.5, 0, 2.2, 3.4, 3.55);
      }
    }
    // --- arcade: glazed barrel vault on iron ribs, shopfronts both sides, iron screens ---
    {
      const vault = new THREE.CylinderGeometry(
        AW / 2,
        AW / 2,
        al,
        16,
        1,
        true,
        -Math.PI / 2,
        Math.PI,
      ).rotateX(Math.PI / 2);
      // cylinder axis along local z after rotateX? use explicit matrix: axis -> au
      const m = new THREE.Matrix4();
      const ang = Math.atan2(au[1], au[0]);
      const g0 = new THREE.CylinderGeometry(AW / 2, AW / 2, al, 16, 1, true, 0, Math.PI);
      g0.rotateZ(Math.PI / 2); // axis along x, half-cylinder spans +y/-y over +z? fix below
      vault.dispose();
      const half = new THREE.CylinderGeometry(
        AW / 2,
        AW / 2,
        al,
        16,
        1,
        true,
        -Math.PI / 2,
        Math.PI,
      );
      half.rotateZ(-Math.PI / 2); // axis now along x; the half-shell faces +z
      m.makeRotationZ(ang).setPosition((A0[0] + A1[0]) / 2, (A0[1] + A1[1]) / 2, SH + 0.6);
      batch.addGeometry(roofGlass, half, m);
      half.dispose();
      g0.dispose();
      for (let s = 0; s <= al; s += 2.4) {
        const rib = new THREE.TorusGeometry(AW / 2, 0.06, 4, 12, Math.PI);
        const p = AP(s, 0);
        const mr = new THREE.Matrix4()
          .makeRotationZ(ang + Math.PI / 2)
          .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
        mr.setPosition(p[0], p[1], SH + 0.6);
        batch.addGeometry(iron, rib, mr);
        rib.dispose();
      }
      kit.cap(
        batch,
        kit.mat('#c9c3b6'),
        [[T.ccw([AP(0, -AW / 2), AP(al, -AW / 2), AP(al, AW / 2), AP(0, AW / 2)])]],
        0.03,
      );
      // wrought-iron name screens at both ends
      const screen = kit.paintedMaterial(
        'south_kensington_station:screen',
        512,
        256,
        (c, w, h) => {
          c.clearRect(0, 0, w, h);
          c.strokeStyle = '#2a3a33';
          c.lineWidth = 6;
          c.beginPath();
          c.arc(w / 2, h, w / 2 - 4, Math.PI, 0);
          c.stroke();
          for (let i = 1; i < 12; i++) {
            c.beginPath();
            c.moveTo(w / 2, h);
            const a = Math.PI + (i * Math.PI) / 12;
            c.lineTo(w / 2 + Math.cos(a) * (w / 2 - 4), h + Math.sin(a) * (w / 2 - 4));
            c.stroke();
          }
          c.fillStyle = '#2a3a33';
          c.fillRect(20, h * 0.62, w - 40, 46);
          c.fillStyle = '#e8d9a0';
          c.font = 'bold 30px serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('SOUTH KENSINGTON STATION', w / 2, h * 0.62 + 24);
        },
        { transparent: true, alphaTest: 0.4, side: THREE.DoubleSide },
      );
      for (const [s, d0] of [
        [0, 1],
        [al, -1],
      ]) {
        const p = AP(s, (d0 * AW) / 2),
          q = AP(s, (-d0 * AW) / 2);
        batch.quad(
          screen,
          [p[0], p[1], SH + 0.6],
          [q[0], q[1], SH + 0.6],
          [q[0], q[1], SH + 0.6 + AW / 2],
          [p[0], p[1], SH + 0.6 + AW / 2],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.quad(
          iron,
          [p[0], p[1], SH + 0.3],
          [q[0], q[1], SH + 0.3],
          [q[0], q[1], SH + 0.6],
          [p[0], p[1], SH + 0.6],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    }
    // --- Leslie Green ox-blood faience block on Pelham Street ---
    if (east) {
      const ring = T.ccw(east.polys[0][0]);
      const E = T.edges(ring);
      const H = 7.2;
      for (const e of E) T.quad(e.ny < -0.5 || e.nx > 0.5 ? oxblood : stucco, e.a, e.b, 0, H);
      kit.cap(batch, kit.mat('#8a8a86'), [[ring]], H + 0.2);
      kit.cornice(batch, oxblood, ring, H - 0.6, { height: 0.6, projection: 0.35, steps: 2 });
      kit.cornice(batch, oxblood, ring, 3.6, { height: 0.35, projection: 0.15 });
      for (const e of E) {
        if (e.len < 2.5) continue;
        const face = e.ny < -0.5 || e.nx > 0.5; // Pelham Street (south / south-east)
        if (face) {
          const n = Math.max(1, Math.round(e.len / 3.6));
          for (let k = 0; k < n; k++) {
            const s = ((k + 0.5) * e.len) / n;
            // ground floor: arched openings between faience piers
            T.ebox(glass, e, s - 1.2, s + 1.2, -0.05, 0.02, 0.3, 3.0);
            const ar = new THREE.CylinderGeometry(
              1.2,
              1.2,
              0.06,
              12,
              1,
              false,
              -Math.PI / 2,
              Math.PI,
            ).rotateX(Math.PI / 2);
            const p = T.at(e, s, 0.0);
            batch.addGeometry(
              glass,
              ar,
              new THREE.Matrix4()
                .makeRotationZ(e.ang)
                .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2))
                .setPosition(p[0], p[1], 3.0),
            );
            ar.dispose();
            T.ebox(oxblood, e, s - 1.8, s - 1.2, 0, 0.35, 0, 3.6);
            // first floor: big semicircular window
            T.ebox(glass, e, s - 1.3, s + 1.3, -0.05, 0.02, 4.1, 4.9);
            const lw = new THREE.CylinderGeometry(
              1.3,
              1.3,
              0.06,
              14,
              1,
              false,
              -Math.PI / 2,
              Math.PI,
            ).rotateX(Math.PI / 2);
            batch.addGeometry(
              glass,
              lw,
              new THREE.Matrix4()
                .makeRotationZ(e.ang)
                .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2))
                .setPosition(p[0], p[1], 4.9),
            );
            lw.dispose();
            for (const dd of [-0.65, 0, 0.65])
              T.ebox(oxblood, e, s + dd - 0.05, s + dd + 0.05, 0, 0.08, 4.1, 6.0);
            T.ebox(oxblood, e, s - 1.4, s + 1.4, 0, 0.15, 3.95, 4.1);
          }
          T.ebox(oxblood, e, 0, e.len, 0, 0.35, 0, 0.3);
        } else if (e.k !== 1) {
          T.win(e, 0, e.len, 4.2, {
            width: 1.1,
            height: 2.0,
            bay: 3.2,
            glass,
            frame: kit.mat('white'),
            sill: stone,
            head: 'lintel',
            bars: 1,
          });
          shopfronts(e, 3.6);
        }
      }
      // Underground roundel on Pelham Street
      const roundel = kit.paintedMaterial(
        'south_kensington_station:roundel',
        128,
        128,
        (c, w, h) => {
          c.clearRect(0, 0, w, h);
          c.strokeStyle = '#dc241f';
          c.lineWidth = 22;
          c.beginPath();
          c.arc(w / 2, h / 2, w / 2 - 14, 0, Math.PI * 2);
          c.stroke();
          c.fillStyle = '#0019a8';
          c.fillRect(0, h / 2 - 14, w, 28);
          c.fillStyle = '#ffffff';
          c.font = 'bold 15px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('UNDERGROUND', w / 2, h / 2 + 1);
        },
        { transparent: true, alphaTest: 0.3, side: THREE.DoubleSide },
      );
      const pe = E.filter((e) => e.ny < -0.9).sort((p, q) => q.len - p.len)[0];
      if (pe) {
        const p = T.at(pe, pe.len / 2, 1.2);
        const ax = [Math.cos(pe.ang + Math.PI / 2) * 0.75, Math.sin(pe.ang + Math.PI / 2) * 0.75];
        batch.quad(
          roundel,
          [p[0] - ax[0], p[1] - ax[1], 3.9],
          [p[0] + ax[0], p[1] + ax[1], 3.9],
          [p[0] + ax[0], p[1] + ax[1], 5.4],
          [p[0] - ax[0], p[1] - ax[1], 5.4],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        T.ebox(iron, pe, pe.len / 2 - 0.05, pe.len / 2 + 0.05, 0, 1.25, 4.6, 4.7);
      }
    }
    g.add(batch.toGroup('south_kensington_station'));
    return g;
  },
};

// ---- local geometry helpers (modules have no imports) -------------------------------
function tools(THREE, kit, batch) {
  const ccw = (r) => {
    r = r.slice();
    if (kit.ringArea(r) < 0) r.reverse();
    return r;
  };
  const edges = (r) =>
    r.map((a, k) => {
      const b = r[(k + 1) % r.length];
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy) || 1;
      return {
        a,
        b,
        k,
        len,
        dx: dx / len,
        dy: dy / len,
        nx: dy / len,
        ny: -dx / len,
        ang: Math.atan2(dy, dx),
      };
    });
  // point along edge e at distance s, offset d outward
  const at = (e, s, d = 0) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
  // box aligned with edge e: s0..s1 along, d0..d1 outward, z0..z1
  const ebox = (m, e, s0, s1, d0, d1, z0, z1, c) => {
    const p = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
    kit.box(
      batch,
      m,
      p[0],
      p[1],
      z0,
      Math.max(0.01, s1 - s0),
      Math.max(0.01, d1 - d0),
      Math.max(0.01, z1 - z0),
      e.ang,
      c,
    );
  };
  const prism = (m, ring, z0, z1, opts) => {
    kit.walls(batch, m, [[ring]], z0, z1, opts);
    kit.cap(batch, m, [[ring]], z1);
  };
  const M = (x, y, z) => new THREE.Matrix4().makeTranslation(x, y, z);
  const cyl = (m, x, y, z0, h, r0, r1 = r0, seg = 12) => {
    const g = new THREE.CylinderGeometry(r1, r0, h, seg).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z0 + h / 2));
    g.dispose();
  };
  const lathe = (m, prof, x, y, z, seg = 24) => {
    const g = new THREE.LatheGeometry(
      prof.map(([r, h]) => new THREE.Vector2(Math.max(0.001, r), h)),
      seg,
    ).rotateX(Math.PI / 2);
    batch.addGeometry(m, g, M(x, y, z));
    g.dispose();
  };
  // windows on the sub-span s0..s1 of edge e
  const win = (e, s0, s1, z, opts) => kit.windowRow(batch, at(e, s0), at(e, s1), z, opts);
  const quad = (m, p, q, z0, z1, c) =>
    batch.quad(
      m,
      [p[0], p[1], z0],
      [q[0], q[1], z0],
      [q[0], q[1], z1],
      [p[0], p[1], z1],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
      c,
    );
  const tri = (m, p, q, r, c) =>
    batch.add(
      m,
      [p, q, r],
      [
        [0, 0],
        [1, 0],
        [0.5, 1],
      ],
      [0, 1, 2],
      c,
    );
  // sloped band from ring at z0 to the ring inset by d at z1 (mansards, hips); returns inner ring
  const slope = (m, ring, z0, d, z1, capTop = true) => {
    const inn = kit.offsetRing(ring, -d);
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length],
        c = inn[(k + 1) % ring.length],
        e = inn[k];
      batch.add(
        m,
        [
          [a[0], a[1], z0],
          [b[0], b[1], z0],
          [c[0], c[1], z1],
          [e[0], e[1], z1],
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
    if (capTop) kit.cap(batch, m, [[inn]], z1);
    return inn;
  };
  // pitched gable roof over an edge-aligned rectangle: along e from s0..s1, depth d0..d1 (outward
  // negative = inward), ridge parallel to e. Gable triangles in wall material.
  const gableRoof = (roofM, wallM, e, s0, s1, d0, d1, z, rise, ov = 0.3) => {
    const dm = (d0 + d1) / 2;
    const P = (s, d, zz) => {
      const p = at(e, s, d);
      return [p[0], p[1], zz];
    };
    const A = P(s0 - ov, d0 - ov * Math.sign(d1 - d0), z),
      B = P(s1 + ov, d0 - ov * Math.sign(d1 - d0), z);
    const C = P(s1 + ov, dm, z + rise),
      D = P(s0 - ov, dm, z + rise);
    const A2 = P(s0 - ov, d1 + ov * Math.sign(d1 - d0), z),
      B2 = P(s1 + ov, d1 + ov * Math.sign(d1 - d0), z);
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 1, 2, 0, 2, 3],
    );
    // undersides so the roof reads from below/behind
    batch.add(
      roofM,
      [A, B, C, D],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    batch.add(
      roofM,
      [B2, A2, D, C],
      [
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      ],
      [0, 2, 1, 0, 3, 2],
    );
    for (const s of [s0, s1]) {
      const p = P(s, d0, z),
        q = P(s, d1, z),
        r = P(s, dm, z + rise);
      tri(wallM, p, q, r);
      tri(wallM, q, p, r);
    }
  };
  const hasRoad = (e) => e; // placeholder for symmetry
  return { ccw, edges, at, ebox, prism, cyl, lathe, win, quad, tri, slope, gableRoof, M, hasRoad };
}

// Stucco terrace house fronts (Kensington type): rusticated raised ground floor,
// porches, first-floor balcony, moulded window surrounds, cornice, attic, mansard.
function stuccoTerrace(T, kit, batch, ring, o) {
  const { edges, at, ebox, win, cyl, slope } = T;
  const wall = o.wall ?? kit.mat('#ece6da');
  const back = o.back ?? kit.mat('#c9b48e');
  const trim = o.trim ?? kit.mat('#f6f2ea');
  const roofM = o.roofM ?? kit.mat('slate');
  const glass = o.glass ?? kit.mat('#2c3640', { roughness: 0.2, metalness: 0.3 });
  const frame = o.frame ?? kit.mat('#f4f4f0');
  const black = kit.mat('#1d1f22', { roughness: 0.5, metalness: 0.4 });
  const Z = o.levels; // floor lines e.g. [0, 1.2, 5.2, 9.4, 12.8, 15.9] ; last = main cornice
  const top = Z[Z.length - 1];
  const fronts = new Set(o.fronts);
  const E = edges(ring);
  // body
  for (const e of E) {
    const m = fronts.has(e.k) || (o.stuccoAll ?? false) ? wall : back;
    T.quad(m, e.a, e.b, 0, top);
  }
  // basement area / plinth band
  kit.cornice(batch, trim, ring, 0, { height: Z[1], projection: 0.08 });
  // string courses
  for (let i = 2; i < Z.length - 1; i++)
    kit.cornice(batch, trim, ring, Z[i] - 0.2, { height: 0.22, projection: 0.1 });
  // main cornice + blocking course
  kit.cornice(batch, trim, ring, top - 0.55, { height: 0.55, projection: 0.45, steps: 2 });
  kit.walls(batch, wall, [[ring]], top, top + 0.9);
  const pin = kit.offsetRing(ring, -0.3);
  kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + 0.9);
  kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + 0.9);
  // roof
  const zr = top + 0.6;
  let roofTop = zr;
  if (o.mansard !== false) {
    const mh = o.mansardH ?? 3.0;
    const inn = slope(roofM, pin, zr, mh * 0.35, zr + mh, false);
    const inn2 = kit.offsetRing(inn, -0.3);
    kit.cap(batch, kit.mat('lead'), [[inn]], zr + mh);
    roofTop = zr + mh;
    // dormers on fronts
    for (const e of E) {
      if (!fronts.has(e.k) || e.len < 4) continue;
      const n = Math.max(1, Math.round((e.len - 2) / (o.bay ?? 2.6)));
      for (let i = 0; i < n; i++) {
        const s = 1 + ((e.len - 2) * (i + 0.5)) / n;
        ebox(roofM, e, s - 0.75, s + 0.75, -1.6, -0.55, zr, zr + 2.2);
        ebox(trim, e, s - 0.8, s + 0.8, -1.6, -0.5, zr + 2.2, zr + 2.35);
        ebox(glass, e, s - 0.45, s + 0.45, -0.58, -0.5, zr + 0.4, zr + 1.9);
      }
    }
  } else {
    kit.cap(batch, kit.mat('#8a8a86'), [[pin]], zr);
  }
  // chimney stacks along party walls (short edges perpendicular to the front) or spaced
  let chim = o.chimneys ?? [];
  if (o.autoChimneys)
    for (const e of E)
      if (!fronts.has(e.k) && e.len > 6) {
        const p = at(e, e.len / 2, -0.7);
        chim = chim.concat([[p[0], p[1], e.ang + Math.PI / 2]]);
      }
  if (chim.length) {
    const pot = kit.mat('#b0603e');
    for (const [x, y, ang] of chim) {
      kit.box(batch, back, x, y, roofTop - 1, 0.7, 2.4, 2.4, ang);
      kit.box(batch, trim, x, y, roofTop + 1.4, 0.85, 2.6, 0.2, ang);
      for (let k = -1; k <= 1; k++)
        cyl(
          pot,
          x - Math.sin(ang) * k * 0.7,
          y + Math.cos(ang) * k * 0.7,
          roofTop + 1.6,
          0.6,
          0.14,
          0.11,
          6,
        );
    }
  }
  // fenestration
  const bay = o.bay ?? 2.6;
  for (const e of E) {
    if (e.len < 1.6) continue;
    const front = fronts.has(e.k);
    for (let s = 1; s < Z.length - 1; s++) {
      const h = Z[s + 1] - Z[s];
      const first = s === 2;
      const opts = front
        ? {
            width: 1.15,
            height: Math.min(h - 1.0, first ? 2.9 : 2.3),
            bay,
            margin: 0.7,
            glass,
            frame,
            sill: trim,
            surround: 0.16,
            surroundMat: trim,
            head: first ? 'pediment' : s === 1 ? 'lintel' : 'lintel',
            bars: 1,
          }
        : {
            width: 1.0,
            height: Math.min(h - 1.0, 2.0),
            bay: bay + 0.6,
            margin: 0.8,
            glass,
            frame,
            sill: trim,
            head: 'none',
            bars: 1,
          };
      if (!front && o.plainBack === 'blank') continue;
      win(e, 0, e.len, Z[s] + (first ? 0.25 : 0.7), opts);
    }
    if (!front) continue;
    // rusticated ground floor: horizontal grooves
    for (let z = Z[1] + 0.5; z < Z[2] - 0.3; z += 0.5)
      ebox(trim, e, 0, e.len, 0, 0.06, z, z + 0.08);
    // first-floor balcony with balustrade
    if (o.balcony !== false) {
      ebox(trim, e, 0.2, e.len - 0.2, 0, 0.9, Z[2] - 0.22, Z[2]);
      kit.balustrade(batch, trim, [at(e, 0.3, 0.8), at(e, e.len - 0.3, 0.8)], Z[2], {
        height: 0.95,
        spacing: 0.32,
      });
    }
    // area railings at pavement edge
    if (o.railings !== false) {
      for (let s = 0.2; s < e.len; s += 0.25)
        ebox(black, e, s - 0.015, s + 0.015, 2.4, 2.43, 0, 1.1);
      ebox(black, e, 0, e.len, 2.38, 2.45, 1.05, 1.1);
    }
  }
  // porches
  for (const [k, s] of o.porches ?? []) {
    const e = E[k];
    const w = 2.4,
      z0 = Z[1],
      zc = Z[2] - 0.3;
    for (const ds of [-w / 2, w / 2]) cyl(trim, ...at(e, s + ds, 1.9), z0, zc - z0, 0.22, 0.2, 10);
    for (const ds of [-w / 2, w / 2]) ebox(trim, e, s + ds - 0.2, s + ds + 0.2, 0, 0.4, z0, zc);
    ebox(trim, e, s - w / 2 - 0.35, s + w / 2 + 0.35, 0, 2.3, zc, Z[2] - 0.22);
    // steps up from pavement across the area
    for (let i = 0; i < 5; i++)
      ebox(trim, e, s - 0.9, s + 0.9, 1.6 + i * 0.3, 2.5 + 0.3 * i, 0, z0 - i * (z0 / 5));
    ebox(kit.mat('#1f2a30'), e, s - 0.6, s + 0.6, 0, 0.05, z0, zc - 0.5);
  }
  return { top, roofTop };
}

// Generic masonry block: walls, storey windows on every edge long enough, string
// courses, cornice, parapet and a flat or slated (mansard / hipped) roof.
function masonryBlock(T, kit, batch, ring, o) {
  const wall = o.wall,
    trim = o.trim ?? wall;
  const Z = o.levels;
  const top = Z[Z.length - 1];
  const E = T.edges(ring);
  for (const e of E) T.quad(o.wallFor ? o.wallFor(e) : wall, e.a, e.b, 0, top);
  if (o.plinth) kit.cornice(batch, trim, ring, 0, { height: o.plinth, projection: 0.08 });
  for (const z of o.bands ?? [])
    kit.cornice(batch, trim, ring, z, { height: 0.25, projection: 0.1 });
  kit.cornice(batch, trim, ring, top - (o.corniceH ?? 0.45), {
    height: o.corniceH ?? 0.45,
    projection: o.corniceP ?? 0.35,
    steps: 2,
  });
  const par = o.parapet ?? 0.8;
  const pin = kit.offsetRing(ring, -0.3);
  if (par > 0) {
    kit.walls(batch, wall, [[ring]], top, top + par);
    kit.walls(batch, wall, [[pin.slice().reverse()]], top, top + par);
    kit.cap(batch, trim, [[ring, pin.slice().reverse()]], top + par);
  }
  let roofTop = top;
  if (o.roof === 'slope') {
    const inn = T.slope(
      o.roofM ?? kit.mat('slate'),
      pin,
      top + 0.2,
      o.roofInset ?? 2.5,
      top + (o.roofRise ?? 3.5),
      false,
    );
    kit.cap(batch, kit.mat('lead'), [[inn]], top + (o.roofRise ?? 3.5));
    roofTop = top + (o.roofRise ?? 3.5);
  } else kit.cap(batch, o.roofM ?? kit.mat('#8b8b87'), [[pin]], top + 0.15);
  for (const e of E) {
    if (e.len < (o.minEdge ?? 2.5)) continue;
    for (let s = 0; s < Z.length - 1; s++) {
      const w = typeof o.win === 'function' ? o.win(s, e, Z[s + 1] - Z[s]) : o.win;
      if (!w) continue;
      T.win(e, 0, e.len, Z[s] + (w.sillOff ?? 0.9), w);
    }
  }
  return { top, roofTop, E };
}

// Frame facade: brick piers proud of the wall, concrete floor bands, metal windows between.
function pierFrame(T, kit, batch, e, z0, z1, storey, o) {
  const n = Math.max(1, Math.round(e.len / (o.bay ?? 3.2)));
  for (let k = 0; k <= n; k++) {
    const s = (k * e.len) / n;
    T.ebox(
      o.pier,
      e,
      Math.max(0, s - (o.pierW ?? 0.3)),
      Math.min(e.len, s + (o.pierW ?? 0.3)),
      -0.05,
      o.pierD ?? 0.3,
      z0,
      z1,
    );
  }
  for (let z = z0; z < z1 - 0.5; z += storey) {
    T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z, z + (o.bandH ?? 0.4));
    for (let k = 0; k < n; k++) {
      const s0 = (k * e.len) / n + (o.pierW ?? 0.3),
        s1 = ((k + 1) * e.len) / n - (o.pierW ?? 0.3);
      if (s1 - s0 < 0.4) continue;
      const zt = Math.min(z1, z + storey);
      if (o.spandrel)
        T.ebox(
          o.spandrel,
          e,
          s0,
          s1,
          0.0,
          0.07,
          z + (o.bandH ?? 0.4),
          z + (o.bandH ?? 0.4) + o.spandrelH,
        );
      const g0 = z + (o.bandH ?? 0.4) + (o.spandrel ? o.spandrelH : 0);
      T.ebox(o.glass, e, s0, s1, 0.01, 0.05, g0, zt);
      const m = Math.max(1, Math.round((s1 - s0) / (o.mullion ?? 1.1)));
      for (let j = 1; j < m; j++) {
        const s = s0 + ((s1 - s0) * j) / m;
        T.ebox(o.frame, e, s - 0.035, s + 0.035, 0.03, 0.1, g0, zt);
      }
      T.ebox(o.frame, e, s0, s1, 0.03, 0.1, g0 + (zt - g0) * 0.62, g0 + (zt - g0) * 0.62 + 0.06);
    }
  }
  T.ebox(o.band, e, 0, e.len, -0.05, o.bandD ?? 0.35, z1 - 0.1, z1 + 0.3);
}

// Clip a ring to the half-plane n . p >= c (Sutherland-Hodgman).
function clipHalf(ring, n, c) {
  const out = [];
  for (let k = 0; k < ring.length; k++) {
    const p = ring[k],
      q = ring[(k + 1) % ring.length];
    const fp = n[0] * p[0] + n[1] * p[1] - c,
      fq = n[0] * q[0] + n[1] * q[1] - c;
    if (fp >= 0) out.push(p);
    if (fp * fq < 0) {
      const t = fp / (fp - fq);
      out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
    }
  }
  return out;
}
