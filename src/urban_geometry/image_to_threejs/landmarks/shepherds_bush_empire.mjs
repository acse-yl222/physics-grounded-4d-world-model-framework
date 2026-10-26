// Shepherd's Bush Empire (O2 Shepherd's Bush Empire), Shepherd's Bush Green.
// Frank Matcham, 1903, for Oswald Stoll; BBC Television Theatre 1953-1991. Grade II.
// Unusually for Matcham an Arts and Crafts composition in terracotta, brick and
// roughcast, asymmetrical. From the Green (east): on the left the round corner
// tower (brick base, roughcast main stage with terracotta-framed windows,
// octagonal terracotta top stage with classical details and arched windows,
// lantern and cupola); in the centre the brick entrance bay with bracketed eaves
// and a first-floor terracotta arcade above the iron entrance canopy; on the right
// a roughcast gabled bay and a wide splayed brick return to Rockwood Place.
// Auditorium under a hipped slate roof and the fly tower behind (west).
export default {
  id: 'shepherds_bush_empire',
  name: "Shepherd's Bush Empire",
  claims: ['c48cc70b-bab2-4fe0-806b-238192436bd1'],
  references: [
    {
      title: 'BBC Television Theatre - British Listed Buildings (Historic England listing)',
      url: 'https://www.britishlistedbuildings.co.uk/101358593-bbc-television-theatre-shepherds-bush-green-ward',
      used_for:
        'Matcham 1903; asymmetrical terracotta/brick/roughcast front; round tower on the left (brick base, roughcast stage with terracotta-framed windows, octagonal top stage with classical details and arched windows, lantern and cupola); brick entrance bay with bracketed eaves and first-floor terracotta arcade; roughcast gabled bay and wide splayed brick return on the right; iron entrance canopy with modern cladding',
    },
    {
      title: "Shepherd's Bush Empire - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Shepherd%27s_Bush_Empire',
      used_for: 'history (Stoll, BBC Television Theatre), Grade II status',
    },
    {
      title: "About Us | O2 Shepherd's Bush Empire",
      url: 'https://academymusicgroup.com/o2shepherdsbushempire/about-us',
      used_for: 'tower as a skyline landmark, current O2 branding',
    },
    {
      title: 'Shepherds Bush Empire - Theatres Trust database',
      url: 'https://database.theatrestrust.org.uk/resources/theatres/show/2026',
      used_for: 'theatre type / auditorium behind the front range',
    },
  ],
  notes:
    'The entrance front faces east onto Shepherds Bush Green (the earlier model put it on the Rockwood Place side); the tower stands at the south-east corner as in the listing. OSM height (8.4 m) replaced by estimates: front range eaves 14 m, auditorium roof ~20 m, fly tower 24 m, tower ~30 m to the finial. Bay widths, window counts, canopy depth and the arcade (now partly hidden by signage) are inferred from the listing text, not measured from photographs.',
  build({ THREE, kit, buildings, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();

    // Local frame: origin at the tower centre, u along the Green front (to NNW),
    // v into the building (west). Front face at v ~ -3 .. -1.
    const O = [-1637.8, -331.5];
    const ANG = 1.885;
    const c = Math.cos(ANG),
      s = Math.sin(ANG);
    const L = (u, v, z = 0) => [O[0] + u * c - v * s, O[1] + u * s + v * c, z];
    const toL = ([x, y]) => [(x - O[0]) * c + (y - O[1]) * s, -(x - O[0]) * s + (y - O[1]) * c];
    const wallAng = ANG; // world angle of the u axis

    // ---------- materials ----------
    const brickTex = (key, base) =>
      kit.paintedMaterial(
        key,
        256,
        256,
        (x, w, h) => {
          x.fillStyle = base;
          x.fillRect(0, 0, w, h);
          const r = kit.rng(0.903 + key.length * 0.01);
          for (let row = 0; row < 32; row++)
            for (let k = (row % 2) * -8; k < w; k += 16) {
              const t = 0.85 + r() * 0.3;
              x.fillStyle = `rgb(${Math.round(148 * t)},${Math.round(70 * t)},${Math.round(50 * t)})`;
              x.fillRect(k + 1, row * 8 + 1, 14, 6);
            }
        },
        DS,
      );
    const brick = brickTex('sbe:brick', '#bfae98');
    const rough = kit.paintedMaterial(
      'sbe:roughcast',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#e9e1cf';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.33);
        for (let k = 0; k < 2600; k++) {
          x.fillStyle = `rgba(${r() > 0.5 ? 120 : 255},${r() > 0.5 ? 105 : 250},90,${0.05 + r() * 0.07})`;
          x.fillRect(r() * w, r() * h, 2, 2);
        }
      },
      DS,
    );
    const terra = kit.mat('#c07a52', { roughness: 0.7, side: THREE.DoubleSide });
    const terraDark = kit.mat('#a6603e', { roughness: 0.75, side: THREE.DoubleSide });
    const slate = kit.roof('slate', 1);
    const lead = kit.mat('#6f787c', { roughness: 0.6, metalness: 0.3, side: THREE.DoubleSide });
    const leadRoof = kit.roof('lead');
    const glass = kit.mat('#26323b', { roughness: 0.12, metalness: 0.35 });
    const frame = kit.mat('#ece7da', { roughness: 0.6 });
    const doorFrame = kit.mat('#1f2a2a', { roughness: 0.5, metalness: 0.3 });
    const gold = kit.mat('gold');
    const iron = kit.mat('#1e2326', { roughness: 0.5, metalness: 0.5, side: THREE.DoubleSide });
    const blueSign = kit.mat('#0f4aa0', { roughness: 0.5, side: THREE.DoubleSide });
    const stone = kit.mat('#8d8a84', { roughness: 0.8, side: THREE.DoubleSide });
    const warm = kit.mat('#ffe9b8', {
      emissive: '#7a5a24',
      roughness: 0.4,
      side: THREE.DoubleSide,
    });

    // ---------- walls by edge ----------
    const Z1 = 7.4, // brick / roughcast change (string course)
      EAVE = 14;
    const edges = [];
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      const la = toL(a),
        lb = toL(b);
      const mu = (la[0] + lb[0]) / 2,
        mv = (la[1] + lb[1]) / 2;
      // Round tower edges are drawn by the tower itself.
      const tower = Math.hypot(mu, mv) < 4.6 && mv < 4;
      const front = !tower && mv < 0 && mu > 2 && mu < 18.5;
      const ret = !tower && mu > 17 && mv < 8.5; // splayed return
      const side = !front && !ret && !tower;
      edges.push({ a, b, len, la, lb, mu, mv, tower, front, ret, side, k });
    }
    const wall = (m, a, b, z0, z1, scale = 4) => {
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      batch.quad(
        m,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [0, z0 / scale],
        [len / scale, z0 / scale],
        [len / scale, z1 / scale],
        [0, z1 / scale],
      );
    };
    const sub = (e, t0, t1) => [
      [e.a[0] + (e.b[0] - e.a[0]) * t0, e.a[1] + (e.b[1] - e.a[1]) * t0],
      [e.a[0] + (e.b[0] - e.a[0]) * t1, e.a[1] + (e.b[1] - e.a[1]) * t1],
    ];
    for (const e of edges) {
      if (e.tower) {
        // Short chords behind the round tower: plain brick.
        wall(brick, e.a, e.b, 0, EAVE);
        continue;
      }
      const entrance = e.front && e.len > 6; // central projecting entrance bay
      const top = e.mv > 30 && e.side ? 15.5 : EAVE; // back walls rise to the roof
      wall(stone, e.a, e.b, 0, 0.6);
      if (entrance || e.ret) wall(brick, e.a, e.b, 0.6, top);
      else {
        wall(brick, e.a, e.b, 0.6, Z1);
        wall(rough, e.a, e.b, Z1, top);
      }
    }
    // String course, eaves cornice and plinth following the footprint.
    kit.cornice(batch, terra, ring, Z1 - 0.15, { height: 0.35, projection: 0.12 });
    kit.cornice(batch, terraDark, ring, 0, { height: 0.6, projection: 0.06 });
    kit.cornice(batch, terra, ring, EAVE - 0.5, { height: 0.5, projection: 0.35, steps: 2 });
    // Flat lead roof over the front range (pitched roofs sit on top).
    kit.cap(batch, leadRoof, [[ring]], EAVE, { scale: 3 });

    // ---------- windows ----------
    const winBase = {
      glass,
      frame,
      sill: terra,
      surroundMat: terra,
      depth: 0.14,
    };
    for (const e of edges) {
      if (e.tower) continue;
      const entrance = e.front && e.len > 6;
      if (entrance) {
        // Ground floor: glazed doors under the canopy.
        kit.windowRow(batch, e.a, e.b, 0.6, {
          ...winBase,
          frame: doorFrame,
          sill: doorFrame,
          count: 4,
          width: 1.5,
          height: 2.7,
          margin: 0.5,
          head: 'none',
          bars: 1,
        });
        // First floor: the terracotta arcade (round-headed, columns between).
        kit.windowRow(batch, e.a, e.b, 5.0, {
          ...winBase,
          count: 4,
          width: 1.25,
          height: 1.9,
          margin: 0.7,
          head: 'arch',
          surround: 0.18,
        });
        const [p0, p1] = sub(e, 0.03, 0.97);
        kit.colonnade(batch, terra, [p0[0] + Math.sin(wallAng) * 0, p0[1]], p1, 4.7, 3.0, {
          count: 5,
          radius: 0.16,
          offset: 0.2,
          capital: 'doric',
          segments: 8,
        });
        // Second and third floors: paired windows with terracotta surrounds.
        kit.windowRow(batch, e.a, e.b, 8.3, {
          ...winBase,
          count: 3,
          width: 1.5,
          height: 2.0,
          margin: 0.8,
          surround: 0.2,
          bars: 1,
        });
        kit.windowRow(batch, e.a, e.b, 11.3, {
          ...winBase,
          count: 3,
          width: 1.3,
          height: 1.6,
          margin: 0.8,
          surround: 0.2,
          bars: 1,
        });
        // Bracketed eaves: timber brackets under a deep eaves board.
        const n = 9;
        for (let i = 0; i <= n; i++) {
          const [p] = sub(e, i / n, i / n);
          const dx = (e.b[1] - e.a[1]) / e.len,
            dy = -(e.b[0] - e.a[0]) / e.len;
          kit.box(
            batch,
            terraDark,
            p[0] + dx * 0.35,
            p[1] + dy * 0.35,
            EAVE - 1.0,
            0.18,
            0.7,
            0.55,
            Math.atan2(dy, dx) + Math.PI / 2,
          );
        }
        continue;
      }
      if (e.front || e.ret) {
        if (e.len < 2.5) continue;
        const cnt = Math.max(1, Math.round(e.len / 3));
        kit.windowRow(batch, e.a, e.b, 1.2, {
          ...winBase,
          count: cnt,
          width: 1.3,
          height: 2.2,
          margin: 0.6,
          surround: 0.2,
          head: 'segment',
        });
        kit.windowRow(batch, e.a, e.b, 4.6, {
          ...winBase,
          count: cnt,
          width: 1.3,
          height: 2.0,
          margin: 0.6,
          surround: 0.2,
        });
        kit.windowRow(batch, e.a, e.b, 8.3, {
          ...winBase,
          count: cnt,
          width: 1.4,
          height: 2.0,
          margin: 0.6,
          surround: 0.22,
        });
        kit.windowRow(batch, e.a, e.b, 11.3, {
          ...winBase,
          count: cnt,
          width: 1.2,
          height: 1.6,
          margin: 0.6,
          surround: 0.22,
        });
        continue;
      }
      // Side elevations: windows only along the front range (v < 13); the
      // auditorium walls behind are largely blind with a few small openings.
      const va = e.la[1],
        vb = e.lb[1];
      const t13 = (13 - va) / (vb - va);
      let t0 = 0,
        t1 = 1;
      if (Math.abs(vb - va) > 1) {
        if (va < 13 && vb > 13) t1 = t13;
        else if (va > 13 && vb < 13) t0 = t13;
        else if (va > 13 && vb > 13) t1 = -1;
      } else if (va > 13) t1 = -1;
      if (t1 > t0 && e.len * (t1 - t0) > 2.5) {
        const [p0, p1] = sub(e, t0, t1);
        for (const [z, hh] of [
          [1.4, 2.0],
          [4.6, 2.0],
          [8.3, 2.0],
          [11.3, 1.6],
        ])
          kit.windowRow(batch, p0, p1, z, {
            ...winBase,
            bay: 3.0,
            width: 1.2,
            height: hh,
            margin: 0.8,
            surround: 0.18,
          });
      }
      if (t1 < 1 && e.len > 12) {
        // Auditorium flank: tall exit doors and a row of small high windows.
        const [p0, p1] = sub(e, Math.max(0, t1), 1);
        kit.windowRow(batch, p0, p1, 0.6, {
          ...winBase,
          frame: doorFrame,
          sill: doorFrame,
          bay: 9,
          width: 1.8,
          height: 2.4,
          margin: 2,
          head: 'none',
          bars: 1,
        });
        kit.windowRow(batch, p0, p1, 9.5, {
          ...winBase,
          bay: 4.5,
          width: 0.9,
          height: 1.4,
          margin: 2,
          surround: 0.15,
          head: 'arch',
        });
      }
    }

    // ---------- roofs behind the front ----------
    // Auditorium: hipped slate roof over the body (v 11 .. 34).
    const box4 = (u0, u1, v0, v1) =>
      [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)].map((p) => [p[0], p[1]]);
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const aud = ccw(box4(-5.5, 22, 11, 34));
    for (let k = 0; k < 4; k++) wall(rough, aud[k], aud[(k + 1) % 4], EAVE, 16.2);
    kit.cornice(batch, terra, aud, 15.9, { height: 0.35, projection: 0.3 });
    kit.pitchedRoof(batch, slate, rough, aud, ANG + Math.PI / 2, 16.2, 5.2, 'hipped', {
      overhang: 0.4,
    });
    // Ridge ventilator lantern over the auditorium.
    {
      const p = L(8.2, 22.5);
      kit.box(batch, lead, p[0], p[1], 20.6, 2.6, 7, 1.3, ANG + Math.PI / 2);
      kit.pitchedRoof(
        batch,
        leadRoof,
        lead,
        ccw([L(6.7, 19), L(9.7, 19), L(9.7, 26), L(6.7, 26)].map((q) => [q[0], q[1]])),
        ANG + Math.PI / 2,
        21.9,
        0.9,
        'hipped',
        { overhang: 0.3 },
      );
    }
    // Fly tower at the back (stage house), brick with a shallow gabled roof.
    const fly = ccw(box4(-6.5, 21, 34, 46.5));
    for (let k = 0; k < 4; k++) wall(brick, fly[k], fly[(k + 1) % 4], 15.5, 24);
    kit.cornice(batch, terraDark, fly, 23.7, { height: 0.3, projection: 0.2 });
    kit.pitchedRoof(batch, slate, brick, fly, ANG, 24, 2.4, 'gabled', { overhang: 0.3 });
    kit.cap(batch, leadRoof, [[ring]], 15.55, { scale: 3 }); // back flat roofs
    // Smoke vents / fly-tower hatches.
    for (const u of [2, 12]) {
      const p = L(u, 40);
      kit.box(batch, lead, p[0], p[1], 25.2, 2.2, 1.6, 0.8, ANG);
    }

    // ---------- front gables and entrance bay roof ----------
    // Roughcast gabled bay (right of the entrance) and the entrance-bay hipped roof.
    const gable = (u0, u1, vFront, depth, top) => {
      const p0 = L(u0, vFront),
        p1 = L(u1, vFront),
        pm = L((u0 + u1) / 2, vFront);
      batch.add(
        rough,
        [
          [p1[0], p1[1], EAVE],
          [p0[0], p0[1], EAVE],
          [pm[0], pm[1], top],
        ],
        [
          [0, 0],
          [1, 0],
          [0.5, 1],
        ],
        [0, 1, 2],
      );
      // Terracotta coping on the verges.
      const q0 = L(u0 - 0.35, vFront - 0.15),
        q1 = L(u1 + 0.35, vFront - 0.15),
        qm = L((u0 + u1) / 2, vFront - 0.15);
      for (const [A, B, za, zb] of [
        [q0, qm, EAVE - 0.2, top + 0.25],
        [qm, q1, top + 0.25, EAVE - 0.2],
      ]) {
        const dx = B[0] - A[0],
          dy = B[1] - A[1],
          dz = zb - za;
        const len = Math.hypot(dx, dy, dz);
        const geo = new THREE.BoxGeometry(len, 0.45, 0.35);
        const m = new THREE.Matrix4().makeRotationZ(ANG);
        m.multiply(
          new THREE.Matrix4().makeRotationY(
            -Math.atan2(dz, Math.hypot(dx, dy)) * Math.sign(dx * c + dy * s || 1),
          ),
        );
        m.setPosition((A[0] + B[0]) / 2 - s * 0.1, (A[1] + B[1]) / 2 + c * 0.1, (za + zb) / 2);
        batch.addGeometry(terra, geo, m);
        geo.dispose();
      }
      // Finial on the apex.
      kit.box(batch, terra, qm[0], qm[1], top + 0.3, 0.35, 0.35, 0.9, ANG);
      // Gable window (three-light, terracotta mullions).
      const w0 = L((u0 + u1) / 2 - 1.2, vFront - 0.01),
        w1 = L((u0 + u1) / 2 + 1.2, vFront - 0.01);
      kit.windowRow(batch, [w1[0], w1[1]], [w0[0], w0[1]], EAVE + 0.6, {
        ...winBase,
        count: 1,
        width: 1.9,
        height: 1.5,
        margin: 0,
        bars: 2,
        surround: 0.2,
        head: 'segment',
      });
      const gr = ccw(box4(u0, u1, vFront, vFront + depth));
      kit.pitchedRoof(batch, slate, rough, gr, ANG + Math.PI / 2, EAVE, top - EAVE, 'gabled', {
        overhang: 0.25,
      });
    };
    gable(13.7, 18.1, -1.0, 12, 19.2);
    // Entrance bay: hipped slate roof with the deep bracketed eaves.
    {
      const r = ccw(box4(6.3, 13.9, -3.9, 9));
      kit.pitchedRoof(batch, slate, brick, r, ANG, EAVE, 3.6, 'hipped', { overhang: 0.75 });
    }

    // ---------- iron entrance canopy (modern cladding) with the venue name ----------
    const sign = kit.paintedMaterial(
      'sbe:sign',
      1024,
      64,
      (x, w, h) => {
        x.fillStyle = '#0c1c3a';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#ffffff';
        x.font = 'bold 40px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText("O2  SHEPHERD'S BUSH EMPIRE", w / 2, h / 2 + 2);
        x.fillStyle = '#2f7fd8';
        x.beginPath();
        x.arc(70, h / 2, 22, 0, Math.PI * 2);
        x.fill();
        x.beginPath();
        x.arc(w - 70, h / 2, 22, 0, Math.PI * 2);
        x.fill();
      },
      DS,
    );
    const posters = kit.paintedMaterial(
      'sbe:posters',
      512,
      128,
      (x, w, h) => {
        const r = kit.rng(0.61);
        const cols = ['#d33a2c', '#f2c230', '#2a6fdb', '#1d1d1d', '#e75b9b', '#3fa66a'];
        for (let k = 0; k < 4; k++) {
          x.fillStyle = cols[Math.floor(r() * cols.length)];
          x.fillRect(k * 128 + 6, 4, 116, h - 8);
          x.fillStyle = 'rgba(255,255,255,0.85)';
          x.fillRect(k * 128 + 16, 18, 96, 14);
          x.fillRect(k * 128 + 16, 90, 70, 8);
        }
      },
      DS,
    );
    {
      const u0 = 2.6,
        u1 = 18.4,
        vf = -3.9, // canopy root line (just in front of the entrance bay)
        dep = 3.4,
        z = 4.1,
        th = 0.95;
      const p = [L(u0, vf), L(u1, vf), L(u1, vf - dep), L(u0, vf - dep)].map((q) => [q[0], q[1]]);
      const pr = ccw(p);
      kit.cap(batch, iron, [[pr]], z + th);
      kit.cap(batch, warm, [[pr]], z, { down: true });
      // Fascia on the three open sides.
      for (const [A, B] of [
        [p[2], p[3]],
        [p[1], p[2]],
        [p[3], p[0]],
      ]) {
        const len = Math.hypot(B[0] - A[0], B[1] - A[1]);
        const main = len > 8;
        batch.quad(
          sign,
          [A[0], A[1], z],
          [B[0], B[1], z],
          [B[0], B[1], z + th],
          [A[0], A[1], z + th],
          [main ? 1 : 0, 0],
          [main ? 0 : 0.06, 0],
          [main ? 0 : 0.06, 1],
          [main ? 1 : 0, 1],
        );
      }
      // Lamp strip along the fascia top and suspension rods back to the wall.
      for (let i = 0; i <= 6; i++) {
        const u = u0 + 0.5 + ((u1 - u0 - 1) * i) / 6;
        const A = L(u, vf - dep + 0.25),
          B = L(u, vf - 0.1);
        const dz = 3.2;
        const len = Math.hypot(dep - 0.35, dz);
        const geo = new THREE.CylinderGeometry(0.035, 0.035, len, 4);
        const m = new THREE.Matrix4().makeRotationZ(ANG);
        m.multiply(new THREE.Matrix4().makeRotationX(Math.atan2(dep - 0.35, dz)));
        m.setPosition((A[0] + B[0]) / 2, (A[1] + B[1]) / 2, z + th + dz / 2);
        batch.addGeometry(iron, geo, m);
        geo.dispose();
      }
      // Vertical blade sign at the north end of the front.
      const bs = L(18.0, -2.2);
      kit.box(batch, blueSign, bs[0], bs[1], 6.0, 0.3, 1.5, 7.2, ANG);
      const bsign = kit.paintedMaterial(
        'sbe:blade',
        64,
        512,
        (x, w, h) => {
          x.fillStyle = '#0f4aa0';
          x.fillRect(0, 0, w, h);
          x.fillStyle = '#ffffff';
          x.font = 'bold 40px sans-serif';
          x.textAlign = 'center';
          x.textBaseline = 'middle';
          'EMPIRE'.split('').forEach((ch, k) => x.fillText(ch, w / 2, 50 + k * 80));
        },
        DS,
      );
      for (const sg of [-1, 1]) {
        const a1 = L(18.0 + sg * 0.16, -2.2 - 0.75),
          b1 = L(18.0 + sg * 0.16, -2.2 + 0.75);
        batch.quad(
          bsign,
          [a1[0], a1[1], 6.1],
          [b1[0], b1[1], 6.1],
          [b1[0], b1[1], 13.1],
          [a1[0], a1[1], 13.1],
          [sg > 0 ? 0 : 1, 0],
          [sg > 0 ? 1 : 0, 0],
          [sg > 0 ? 1 : 0, 1],
          [sg > 0 ? 0 : 1, 1],
        );
      }
      // Poster frames on the piers either side of the doors.
      for (const u of [3.4, 15.4]) {
        const A = L(u - 1.0, -2.0 - 0.02),
          B = L(u + 1.0, -2.0 - 0.02);
        batch.quad(
          posters,
          [B[0], B[1], 1.0],
          [A[0], A[1], 1.0],
          [A[0], A[1], 3.0],
          [B[0], B[1], 3.0],
          [u > 10 ? 0.5 : 0, 0],
          [u > 10 ? 1 : 0.5, 0],
          [u > 10 ? 1 : 0.5, 1],
          [u > 10 ? 0.5 : 0, 1],
        );
      }
      // Entrance steps.
      for (let k = 0; k < 2; k++) {
        const pc = L(10.1, -4.2 - k * 0.35);
        kit.box(batch, stone, pc[0], pc[1], 0, 8.2, 0.4 + 0.35 * (1 - k), 0.15 * (2 - k), ANG);
      }
    }

    // ---------- round corner tower ----------
    const tc = L(0, 0.4);
    const R = 3.5;
    const add = (geo, m, z, us = 1, vs = 1) => {
      const uv = geo.attributes.uv;
      if (uv && (us !== 1 || vs !== 1))
        for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * us, uv.getY(i) * vs);
      geo.rotateX(Math.PI / 2);
      batch.addGeometry(m, geo, new THREE.Matrix4().makeTranslation(tc[0], tc[1], z));
      geo.dispose();
    };
    add(new THREE.CylinderGeometry(R + 0.12, R + 0.12, 0.6, 32, 1, true), stone, 0.3);
    add(
      new THREE.CylinderGeometry(R, R, 7.8, 32, 1, true),
      brick,
      4.5,
      (2 * Math.PI * R) / 4,
      7.8 / 4,
    );
    add(new THREE.CylinderGeometry(R + 0.3, R + 0.3, 0.45, 32), terra, 8.6);
    add(
      new THREE.CylinderGeometry(R - 0.05, R - 0.05, 9.6, 32, 1, true),
      rough,
      13.6,
      (2 * Math.PI * R) / 4,
      9.6 / 4,
    );
    add(new THREE.CylinderGeometry(R + 0.45, R + 0.25, 0.7, 32), terra, 18.75);
    // Tower windows: brick stage (two levels) and the roughcast stage with
    // terracotta-framed windows, on the faces turned to the Green and the junction.
    const towerWin = (theta, z, w, h, opts = {}) => {
      const nx = Math.cos(theta),
        ny = Math.sin(theta);
      const P = [tc[0] + nx * R, tc[1] + ny * R];
      const t = [-ny, nx];
      kit.windowRow(
        batch,
        [P[0] - t[0] * w, P[1] - t[1] * w],
        [P[0] + t[0] * w, P[1] + t[1] * w],
        z,
        {
          ...winBase,
          count: 1,
          width: w,
          height: h,
          margin: 0,
          surround: 0.22,
          ...opts,
        },
      );
    };
    const faceGreen = ANG - Math.PI / 2; // world angle of the front normal (east)
    for (const d of [-1.7, -0.85, 0, 0.85]) {
      const th = faceGreen + d;
      towerWin(th, 1.4, 1.0, 2.0, { head: 'segment' });
      towerWin(th, 4.9, 1.0, 2.0);
      towerWin(th, 9.6, 1.15, 2.2);
      towerWin(th, 13.6, 1.15, 2.2);
      towerWin(th, 16.6, 0.9, 1.3);
    }
    // Octagonal terracotta top stage: pilasters at the angles and arched windows.
    const r8 = R * 0.92;
    add(new THREE.CylinderGeometry(r8, r8, 4.6, 8, 1, true), terra, 21.4);
    for (let k = 0; k < 8; k++) {
      const a = (k * Math.PI) / 4;
      const px = tc[0] + Math.cos(a) * r8 * 1.0,
        py = tc[1] + Math.sin(a) * r8 * 1.0;
      kit.box(batch, terraDark, px, py, 19.1, 0.45, 0.45, 4.6, a);
      const am = a + Math.PI / 8;
      const ap = r8 * Math.cos(Math.PI / 8);
      const P = [tc[0] + Math.cos(am) * ap, tc[1] + Math.sin(am) * ap];
      const t = [-Math.sin(am), Math.cos(am)];
      kit.windowRow(batch, [P[0] - t[0], P[1] - t[1]], [P[0] + t[0], P[1] + t[1]], 19.7, {
        ...winBase,
        count: 1,
        width: 1.0,
        height: 2.2,
        margin: 0,
        head: 'arch',
        bars: 1,
      });
    }
    add(new THREE.CylinderGeometry(r8 + 0.55, r8 + 0.3, 0.7, 8), terra, 24.05);
    // Balustraded parapet round the octagon.
    {
      const pts = [];
      for (let k = 0; k <= 8; k++) {
        const a = (k * Math.PI) / 4;
        pts.push([tc[0] + Math.cos(a) * (r8 + 0.35), tc[1] + Math.sin(a) * (r8 + 0.35)]);
      }
      kit.balustrade(batch, terra, pts, 24.4, { height: 0.8, spacing: 0.35 });
    }
    // Ogee cupola, open lantern and finial.
    const cup = kit.lathe(
      lead,
      [
        [r8 * 0.95, 0],
        [r8 * 0.92, 0.5],
        [r8 * 0.75, 1.3],
        [r8 * 0.45, 1.9],
        [r8 * 0.3, 2.5],
        [r8 * 0.22, 2.9],
        [0.9, 3.0],
      ],
      { x: tc[0], y: tc[1], z: 24.4, segments: 8 },
    );
    g.add(cup);
    for (let k = 0; k < 6; k++) {
      const a = (k * Math.PI) / 3;
      kit.box(
        batch,
        terra,
        tc[0] + Math.cos(a) * 0.75,
        tc[1] + Math.sin(a) * 0.75,
        27.4,
        0.2,
        0.2,
        1.4,
        a,
      );
    }
    add(new THREE.CylinderGeometry(0.55, 0.55, 1.4, 6, 1, true), glass, 28.1);
    add(new THREE.CylinderGeometry(1.0, 1.0, 0.25, 6), terra, 28.9);
    add(new THREE.ConeGeometry(0.95, 1.4, 6), lead, 29.7);
    add(new THREE.SphereGeometry(0.28, 10, 8), gold, 30.6);
    add(new THREE.CylinderGeometry(0.05, 0.05, 1.3, 4), gold, 31.4);
    add(new THREE.TorusGeometry(0.3, 0.04, 4, 12), gold, 31.2);

    // ---------- immediate surroundings ----------
    // Bollards along the Green frontage.
    const bol = [];
    for (let u = -2; u <= 20; u += 2.2) {
      const p = L(u, -7.6);
      bol.push([p[0], p[1], ANG]);
    }
    g.add(placeAssets('bollard', bol));

    g.add(batch.toGroup('shepherds_bush_empire'));
    return g;
  },
};
