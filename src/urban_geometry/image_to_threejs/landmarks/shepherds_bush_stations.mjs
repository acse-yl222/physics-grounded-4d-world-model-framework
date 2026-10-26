// Shepherd's Bush stations at the east end of Shepherd's Bush Green.
// Central line: surface building replaced in 2008 (Westfield s106) by a light
// glass, steel and granite pavilion with a deep flat roof, identifiable from the
// Southern Interchange and calmer towards the conservation area to the west.
// London Overground (West London line) station opened 28 September 2008,
// designed and funded by Westfield (Ian Ritchie Architects): a discreet glazed
// station building and footbridge beside the Holland Park roundabout, side
// platforms on the two tracks.
export default {
  id: 'shepherds_bush_stations',
  name: "Shepherd's Bush stations (Central line and Overground)",
  claims: [
    'f8566caf-5b2b-4bf3-bbd4-606701a7f5ef', // Shepherd's Bush tube station
    '1ffe4a65-4bba-42e1-9081-78102c9b81a3', // Shepherd's Bush Railway Station
  ],
  references: [
    {
      title: "Modernisation complete as Shepherd's Bush Tube station re-opens - TfL",
      url: 'https://tfl.gov.uk/info-for/media/press-releases/2008/october/modernisation-complete-as-shepherds-bush-tube-station-reopens',
      used_for: 'new building in glass, steel and granite, modern and light, 2008',
    },
    {
      title: "Shepherd's Bush tube station - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Shepherd%27s_Bush_tube_station',
      used_for: 'surface building completely replaced in 2008, Westfield section 106',
    },
    {
      title: "Shepherd's Bush railway station - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Shepherd%27s_Bush_railway_station',
      used_for: 'Overground station opened 28 September 2008, designed and funded by Westfield',
    },
    {
      title: "Shepherd's Bush Central Line Station - Ritchie Studio",
      url: 'https://www.ritchie.studio/projects/shepherds_bush_station/',
      used_for:
        'contemporary, elegant entrance structure; identifiable presence on Uxbridge Road at the western edge of the Southern Interchange, calmer facade towards the Shepherds Bush Town Conservation Area',
    },
    {
      title: 'West London Line station - Ritchie Studio',
      url: 'https://www.ritchie.studio/projects/west_london_line/',
      used_for:
        'discreet station at the Holland Park roundabout / Uxbridge Road junction, scale matched to the Central line station; formal layout of station building and footbridge',
    },
  ],
  notes:
    "Pavilion height (~7 m) replaces the OSM 11.9 m; glazing grid, roof depth, rooflights and signage are generic for the 2008 TfL/Westfield station style. The west (Green) face is drawn as solid granite for the 'calmer facade'. Overground: the footprint lies west of the two tracks, so it holds the station building (south) and the west platform; the east platform, footbridge span and stair/lift tower are drawn just outside the footprint, with lengths and canopy forms inferred, not measured.",
  build({ THREE, kit, byId, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const clip = (r, f) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length],
          fa = f(a),
          fb = f(b);
        if (fa >= 0) out.push(a);
        if (fa >= 0 !== fb >= 0) {
          const t = fa / (fa - fb);
          out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
        }
      }
      return out;
    };
    const edgesOf = (r) =>
      r
        .map((a, k) => {
          const b = r[(k + 1) % r.length];
          const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
          return {
            a,
            b,
            len,
            f: Math.atan2(b[1] - a[1], b[0] - a[0]),
            nx: len ? (b[1] - a[1]) / len : 0,
            ny: len ? -(b[0] - a[0]) / len : 0,
          };
        })
        .filter((e) => e.len > 0.05);
    const wallQ = (m, a, b, z0, z1, su = 3, sv = 3) => {
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      batch.quad(
        m,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [0, z0 / sv],
        [len / su, z0 / sv],
        [len / su, z1 / sv],
        [0, z1 / sv],
      );
    };

    // ---------- materials ----------
    const glass = kit.mat('#5d7787', {
      roughness: 0.06,
      metalness: 0.35,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const doorGlass = kit.mat('#30424e', { roughness: 0.08, metalness: 0.3 });
    const granite = kit.paintedMaterial(
      'sbs:granite',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#5f5c58';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.71);
        for (let k = 0; k < 3000; k++) {
          const v = 60 + Math.floor(r() * 90);
          x.fillStyle = `rgba(${v},${v - 4},${v - 8},0.5)`;
          x.fillRect(r() * w, r() * h, 2, 2);
        }
        x.fillStyle = 'rgba(30,30,30,0.6)';
        for (let k = 0; k < w; k += 128) x.fillRect(k, 0, 2, h);
        for (let k = 0; k < h; k += 64) x.fillRect(0, k, w, 2);
      },
      { roughness: 0.45, side: THREE.DoubleSide },
    );
    const roofM = kit.roof('flat', 2);
    const fascia = kit.mat('#e9ebec', { roughness: 0.35, metalness: 0.4, side: THREE.DoubleSide });
    const soffit = kit.mat('#eef0f0', { emissive: '#2d2f31', side: THREE.DoubleSide });
    const downlight = kit.mat('#fff4d6', { emissive: '#e8d49a' });
    const steel = kit.mat('#c9ced1', { roughness: 0.3, metalness: 0.7, side: THREE.DoubleSide });
    const dark = kit.mat('dark_steel', DS);
    const plat = kit.mat('#b4afa5', DS);
    const yellow = kit.mat('#e2c02c', DS);
    const rooflight = kit.mat('glass', DS);
    const roundelMat = (key, ring, text) =>
      kit.paintedMaterial(
        key,
        256,
        256,
        (x, w, h) => {
          x.fillStyle = '#ffffff';
          x.fillRect(0, 0, w, h);
          x.strokeStyle = ring;
          x.lineWidth = 40;
          x.beginPath();
          x.arc(w / 2, h / 2, 90, 0, Math.PI * 2);
          x.stroke();
          x.fillStyle = '#0019a8';
          x.fillRect(4, h / 2 - 26, w - 8, 52);
          x.fillStyle = '#ffffff';
          x.font = 'bold 22px sans-serif';
          x.textAlign = 'center';
          x.textBaseline = 'middle';
          x.fillText(text, w / 2, h / 2 + 1);
        },
        DS,
      );
    const tubeR = roundelMat('sbs:roundel', '#dc241f', "SHEPHERD'S BUSH");
    const overR = roundelMat('sbs:overground', '#ee7c0e', "SHEPHERD'S BUSH");
    const roundel = (m, x, y, z, f, d, twoSided = true) => {
      const geo = new THREE.CylinderGeometry(d / 2, d / 2, 0.04, 28).rotateY(Math.PI / 2);
      for (const k of twoSided ? [0, 1] : [0]) {
        const a = f + k * Math.PI;
        const mm = new THREE.Matrix4().makeRotationZ(a);
        const o = twoSided ? 0.025 : 0;
        mm.setPosition(x + Math.sin(a) * o, y - Math.cos(a) * o, z + d / 2);
        batch.addGeometry(m, geo, mm);
      }
      geo.dispose();
    };
    const totem = (m, x, y, f) => {
      kit.box(batch, dark, x, y, 0, 0.22, 0.22, 3.6, f);
      kit.box(batch, dark, x, y, 0, 0.6, 0.6, 0.15, f);
      roundel(m, x, y, 3.6, f, 1.6);
    };

    // A glass pavilion with granite piers, mullion grid and a deep flat roof.
    const pavilion = (ring, H, overhang, solidEdge, doorEdge) => {
      const r = ccw(ring);
      for (const e of edgesOf(r)) {
        wallQ(granite, e.a, e.b, 0, 0.6);
        if (solidEdge(e)) {
          wallQ(granite, e.a, e.b, 0.6, H);
          // Narrow vertical slot windows in the granite.
          kit.windowRow(batch, e.a, e.b, 1.2, {
            glass: doorGlass,
            frame: steel,
            sill: steel,
            bay: 6,
            width: 0.5,
            height: H - 2.2,
            margin: 2,
            head: 'none',
            bars: 0,
          });
          continue;
        }
        wallQ(glass, e.a, e.b, 0.6, H);
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let j = 0; j <= n; j++) {
          const t = j / n;
          const x = e.a[0] + (e.b[0] - e.a[0]) * t,
            y = e.a[1] + (e.b[1] - e.a[1]) * t;
          const pier = j === 0 || j === n || j % 4 === 0;
          if (pier) kit.box(batch, granite, x, y, 0, 0.7, 0.7, H, e.f);
          else
            kit.box(batch, steel, x + e.nx * 0.05, y + e.ny * 0.05, 0.6, 0.07, 0.18, H - 0.6, e.f);
        }
        const m = [(e.a[0] + e.b[0]) / 2 + e.nx * 0.06, (e.a[1] + e.b[1]) / 2 + e.ny * 0.06];
        for (const z of [0.6, 3.1, H - 0.1])
          kit.box(batch, steel, m[0], m[1], z, e.len, 0.1, 0.1, e.f);
        if (doorEdge(e))
          kit.windowRow(batch, e.a, e.b, 0.6, {
            glass: doorGlass,
            frame: steel,
            sill: steel,
            bay: 3,
            width: 2.0,
            height: 2.4,
            margin: 1.5,
            head: 'none',
            bars: 1,
            depth: 0.15,
          });
      }
      kit.cap(batch, kit.mat('#9a9fa2', DS), [[r]], H);
      const big = ccw(kit.offsetRing(r, overhang));
      kit.cap(batch, roofM, [[big]], H + 1.0, { scale: 4 });
      kit.cap(batch, soffit, [[big]], H, { down: true });
      kit.walls(batch, fascia, [[big]], H, H + 1.0, { bay: 1e6 });
      kit.cornice(batch, fascia, big, H + 1.0, { height: 0.15, projection: 0.05 });
      // Downlights in the soffit band outside the glass line.
      for (const e of edgesOf(r)) {
        const n = Math.floor(e.len / 2.4);
        for (let j = 0; j < n; j++) {
          const t = (j + 0.5) / n;
          const x = e.a[0] + (e.b[0] - e.a[0]) * t + e.nx * overhang * 0.55,
            y = e.a[1] + (e.b[1] - e.a[1]) * t + e.ny * overhang * 0.55;
          kit.box(batch, downlight, x, y, H - 0.03, 0.3, 0.3, 0.04, e.f);
        }
      }
      return { r, big };
    };

    // ---------- Central line pavilion ----------
    const tRing = byId['f8566caf-5b2b-4bf3-bbd4-606701a7f5ef'].polys[0][0];
    const TH = 6.2;
    const { r: t } = pavilion(
      tRing,
      TH,
      2.4,
      (e) => e.nx < -0.7 && e.len > 15, // west face to the Green: calm granite
      (e) => e.nx > 0.7 || e.ny < -0.7, // doors to the interchange and Uxbridge Road
    );
    // Rooflights and plant screen on the roof.
    const fr = kit.ringFrame(t);
    const ca = Math.cos(fr.angle),
      sa = Math.sin(fr.angle);
    for (const off of [-0.3, -0.1, 0.1, 0.3]) {
      const cx = fr.cx + ca * fr.length * off,
        cy = fr.cy + sa * fr.length * off;
      kit.box(batch, fascia, cx, cy, TH + 1.0, 3.4, fr.width * 0.55, 0.35, fr.angle);
      for (const sg of [-1, 1]) {
        const geo = new THREE.BoxGeometry(1.7, fr.width * 0.55, 0.04);
        const m = new THREE.Matrix4().makeRotationZ(fr.angle);
        m.multiply(new THREE.Matrix4().makeRotationY(sg * 0.45));
        m.setPosition(cx + ca * sg * 0.78, cy + sa * sg * 0.78, TH + 1.75);
        batch.addGeometry(rooflight, geo, m);
        geo.dispose();
      }
    }
    {
      const cx = fr.cx - sa * fr.width * 0.3,
        cy = fr.cy + ca * fr.width * 0.3;
      kit.box(batch, kit.mat('#8e9497', DS), cx, cy, TH + 1.0, 6, 3.5, 1.6, fr.angle);
    }
    // Roundels: on the east fascia and on totems at the corners.
    {
      const es = edgesOf(t);
      const east = es.filter((e) => e.nx > 0.7).sort((p, q) => q.len - p.len)[0];
      const south = es.filter((e) => e.ny < -0.7).sort((p, q) => q.len - p.len)[0];
      for (const e of [east, south]) {
        if (!e) continue;
        const m = [(e.a[0] + e.b[0]) / 2 + e.nx * 2.45, (e.a[1] + e.b[1]) / 2 + e.ny * 2.45];
        roundel(tubeR, m[0], m[1], TH + 1.1, e.f, 1.5, false);
        // Name board along the fascia.
        const nameM = kit.paintedMaterial(
          'sbs:name',
          512,
          64,
          (x, w, h) => {
            x.fillStyle = '#e9ebec';
            x.fillRect(0, 0, w, h);
            x.fillStyle = '#0019a8';
            x.font = 'bold 30px sans-serif';
            x.textAlign = 'center';
            x.textBaseline = 'middle';
            x.fillText("SHEPHERD'S BUSH STATION", w / 2, h / 2 + 2);
          },
          DS,
        );
        const half = Math.min(9, e.len * 0.35);
        const ux = Math.cos(e.f),
          uy = Math.sin(e.f);
        for (const sg of [-1, 1]) {
          const c0 = [m[0] + ux * sg * 2.0, m[1] + uy * sg * 2.0];
          const c1 = [m[0] + ux * sg * (2.0 + half), m[1] + uy * sg * (2.0 + half)];
          const P0 = sg > 0 ? c0 : c1,
            P1 = sg > 0 ? c1 : c0;
          batch.quad(
            nameM,
            [P0[0], P0[1], TH + 0.25],
            [P1[0], P1[1], TH + 0.25],
            [P1[0], P1[1], TH + 0.8],
            [P0[0], P0[1], TH + 0.8],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
        }
        totem(tubeR, e.b[0] + e.nx * 4.5, e.b[1] + e.ny * 4.5, e.f);
      }
      // Bollards and cycle stands along the interchange frontage.
      if (east) {
        const bol = [],
          bikes = [];
        for (let s = 2; s < east.len - 1; s += 2.5)
          bol.push([
            east.a[0] + Math.cos(east.f) * s + east.nx * 6,
            east.a[1] + Math.sin(east.f) * s + east.ny * 6,
            east.f,
          ]);
        for (let s = 3; s < 12; s += 1.2)
          bikes.push([
            east.a[0] + Math.cos(east.f) * s + east.nx * 8,
            east.a[1] + Math.sin(east.f) * s + east.ny * 8,
            east.f + Math.PI / 2,
          ]);
        g.add(placeAssets('bollard', bol));
        g.add(placeAssets('bicycle_stand', bikes));
      }
    }

    // ---------- London Overground station ----------
    // Local frame along the tracks: origin at the SE corner, u to NNW, w west.
    const OO = [-1180.3, -158.5],
      OA = 1.9341;
    const oc = Math.cos(OA),
      os = Math.sin(OA);
    const L = (u, w, z = 0) => [OO[0] + u * oc - w * os, OO[1] + u * os + w * oc, z];
    const toL = ([x, y]) => [
      (x - OO[0]) * oc + (y - OO[1]) * os,
      -(x - OO[0]) * os + (y - OO[1]) * oc,
    ];
    const oRing = ccw(byId['1ffe4a65-4bba-42e1-9081-78102c9b81a3'].polys[0][0].slice());
    const PW = 5.5; // west platform width inside the footprint
    const bld = ccw(
      clip(
        clip(oRing, (p) => 15 - toL(p)[0]),
        (p) => toL(p)[1] - PW,
      ),
    );
    const OH = 4.4;
    pavilion(
      bld,
      OH,
      1.6,
      () => false,
      (e) => e.ny < -0.5 || e.nx < -0.5,
    );
    const box2 = (m, u0, u1, w0, w1, z0, h) => {
      const p = L((u0 + u1) / 2, (w0 + w1) / 2);
      kit.box(batch, m, p[0], p[1], z0, u1 - u0, w1 - w0, h, OA);
    };
    // Platforms (west inside the footprint, east beyond the tracks).
    const U0 = 2,
      U1 = 41;
    box2(plat, U0, U1, 0.15, PW, 0, 0.95);
    box2(plat, U0 + 4, U1, -11.4, -7.5, 0, 0.95);
    for (const we of [0.6, -7.95]) box2(yellow, U0, U1, we - 0.08, we + 0.08, 0.95, 0.01);
    // Platform canopies: monopitch on raking steel columns.
    const canopy = (w0, w1, uA, uB) => {
      const hi = w1 > 0 ? w1 : w0; // high at the back
      const p0 = L(uA, w0),
        p1 = L(uB, w0),
        p2 = L(uB, w1),
        p3 = L(uA, w1);
      const zl = 4.0,
        zh = 4.6;
      const z0 = w0 === hi ? zh : zl,
        z1 = w1 === hi ? zh : zl;
      batch.quad(
        fascia,
        [p0[0], p0[1], z0 + 0.2],
        [p1[0], p1[1], z0 + 0.2],
        [p2[0], p2[1], z1 + 0.2],
        [p3[0], p3[1], z1 + 0.2],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      batch.quad(
        soffit,
        [p0[0], p0[1], z0],
        [p1[0], p1[1], z0],
        [p2[0], p2[1], z1],
        [p3[0], p3[1], z1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
      for (let u = uA + 1.5; u < uB; u += 6) {
        const wc = hi - Math.sign(hi) * 0.6;
        const p = L(u, wc);
        kit.box(batch, steel, p[0], p[1], 0.95, 0.25, 0.25, zh - 0.95, OA);
        const q = L(u, (w0 + w1) / 2);
        kit.box(batch, steel, q[0], q[1], 4.05, 0.18, Math.abs(w1 - w0), 0.22, OA);
      }
      const rp = L((uA + uB) / 2, (w0 + w1) / 2);
      roundel(overR, rp[0], rp[1], 2.6, OA, 1.0);
    };
    canopy(0.2, PW + 0.3, 15, 36);
    canopy(-7.4, -11.6, 12, 34);
    // Footbridge from the station building over both tracks to the east platform.
    {
      const BZ = 6.2,
        uB = 9;
      box2(steel, uB - 1.7, uB + 1.7, -11.6, PW + 2, BZ, 0.5);
      box2(glass, uB - 1.7, uB - 1.6, -11.6, PW + 2, BZ + 0.5, 2.3);
      box2(glass, uB + 1.6, uB + 1.7, -11.6, PW + 2, BZ + 0.5, 2.3);
      box2(fascia, uB - 1.8, uB + 1.8, -11.7, PW + 2.1, BZ + 2.8, 0.35);
      for (let w = -11; w <= PW + 2; w += 2.2) {
        for (const du of [-1.66, 1.66])
          box2(steel, uB + du - 0.05, uB + du + 0.05, w - 0.05, w + 0.05, BZ + 0.5, 2.3);
      }
      // Stair / lift tower on the east platform.
      box2(granite, uB - 2, uB + 2.5, -12.6, -9.6, 0, 0.6);
      box2(glass, uB - 2, uB + 2.5, -12.6, -9.6, 0.6, BZ + 2.2);
      box2(fascia, uB - 2.2, uB + 2.7, -12.8, -9.4, BZ + 2.8, 0.4);
      // Stair flight down onto the east platform.
      for (let k = 0; k < 14; k++)
        box2(plat, uB + 2.5 + k * 0.6, uB + 3.1 + k * 0.6, -11.4, -9.6, 0.95, BZ - 0.95 - k * 0.37);
      roundel(overR, ...L(uB, -11.8).slice(0, 2), BZ + 3.3, OA + Math.PI / 2, 1.2);
    }
    // Entrance roundel totem at Uxbridge Road and the station name on the fascia.
    {
      const p = L(3, 12);
      totem(overR, p[0] - Math.cos(OA) * 2, p[1] - Math.sin(OA) * 2, OA + Math.PI / 2);
      const q = L(-1.7, 10);
      roundel(overR, q[0], q[1], OH + 0.05, OA - Math.PI / 2, 0.9, false);
    }
    // Remaining footprint north of the building: paved approach with benches.
    g.add(
      placeAssets(
        'bench',
        [20, 26, 32].map((u) => {
          const p = L(u, PW - 0.9);
          return [p[0], p[1], OA - Math.PI / 2];
        }),
        { z: 0.95 },
      ),
    );

    g.add(batch.toGroup('shepherds_bush_stations'));
    return g;
  },
};
