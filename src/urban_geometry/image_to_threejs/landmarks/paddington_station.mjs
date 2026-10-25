// London Paddington station (I. K. Brunel with M. Digby Wyatt, 1851-54; fourth
// span 1913-16) and the Great Western Royal Hotel (P. C. Hardwick, 1851-54) on
// Praed Street. Three wrought-iron and glass barrel-vaulted spans of 68 ft,
// 102 ft 6 in and 70 ft crossed by two transepts, plus the later 109 ft fourth
// span on the London Street side; arched end screens with iron tracery; the
// Lawn concourse between shed and hotel; the Platform 1 office range along
// Eastbourne Terrace. The hotel is a stuccoed French Second Empire block with a
// pedimented centre, steep pavilion roofs with dormers and two projecting
// six-storey angle towers with ogee roofs.
export default {
  id: 'paddington_station',
  name: 'London Paddington station and Great Western Royal Hotel',
  claims: [
    'cacd5f93-024a-4c87-a69d-cbcf76a4f82f', // train shed, Lawn, north-west platforms
    '360408b3-6867-4a89-9cc6-8e3548e0ffe1', // Great Western Royal Hotel (Hilton London Paddington)
    '5c55db4c-2e46-4a30-9cd6-95ab5c5fb5e2', // Platform 1 office range / MacMillan House
  ],
  references: [
    {
      title: 'The history of London Paddington station - Network Rail',
      url: 'https://www.networkrail.co.uk/who-we-are/our-history/iconic-infrastructure/the-history-of-london-paddington-station/',
      used_for:
        'span widths 68 ft / 102 ft 6 in / 70 ft, two transepts, wrought iron and glass, Digby Wyatt tracery, oriels on platform 1',
    },
    {
      title: 'London Paddington station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/London_Paddington_station',
      used_for: '1854 train shed, fourth span, the Lawn, overall layout',
    },
    {
      title: 'Hilton London Paddington - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hilton_London_Paddington',
      used_for:
        'Great Western Royal Hotel by P. C. Hardwick, French Second Empire, pediment sculpture',
    },
    {
      title: 'Great Western Hotel - Historic England list entry 1227144',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1227144',
      used_for:
        'stuccoed brick, 4 storeys and attic, 7-bay centre and side ranges, 6-storey angle towers, steep pavilion roof, pedimented dormers, ogee tower roofs',
    },
  ],
  notes:
    'Shed placed in the Overture station outline (217 m from the Lawn to the north-west screens, spans 20.7/31.2/21.3/33.2 m). ' +
    'Springing (9.5 m) and crown heights (16.5-20.5 m), transept positions and roof glazing pattern are estimates; ' +
    'the 1999 Lawn roof is shown as a plain glazed canopy. Hotel heights (eaves 20 m, towers 28 m + ogee roofs) ' +
    'are estimated from the storey counts in the listing; dormer and window counts approximate. The Platform 1 range ' +
    'is lowered to 13 m except the MacMillan House end; north-west platform canopies and the outer station strip are flat roofs.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const O = [1654, 1043],
      A = (132 * Math.PI) / 180,
      ca = Math.cos(A),
      sa = Math.sin(A);
    // local frame: u along the shed towards the north-west, v towards the south-west (Eastbourne Terrace)
    const W = (u, v) => [O[0] + u * ca - v * sa, O[1] + u * sa + v * ca];
    const toL = ([x, y]) => [(x - O[0]) * ca + (y - O[1]) * sa, -(x - O[0]) * sa + (y - O[1]) * ca];
    const b = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };

    // ---------- helpers ----------
    // Sutherland-Hodgman clip of a local ring against f(p) >= 0 (f linear).
    const clip = (ring, f) => {
      const out = [];
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const fp = f(p),
          fq = f(q);
        if (fp >= 0) out.push(p);
        if (fp >= 0 !== fq >= 0) {
          const t = fp / (fp - fq);
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
      }
      return out;
    };
    const ringArea = (r) =>
      r.reduce((a, p, k) => {
        const q = r[(k + 1) % r.length];
        return a + p[0] * q[1] - q[0] * p[1];
      }, 0) / 2;
    const toWorldRing = (r) => r.map(([u, v]) => W(u, v));
    const capLocal = (m, r, z, down = false) => {
      if (r.length < 3 || Math.abs(ringArea(r)) < 1) return;
      let wr = toWorldRing(r);
      if (kit.ringArea(wr) < 0) wr = wr.slice().reverse();
      kit.cap(b, m, [[wr]], z, { down });
    };
    const quad = (m, p, q, z0, z1, ur, v0, v1, col) =>
      b.quad(
        m,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], z1],
        [p[0], p[1], z1],
        [0, v0],
        [ur, v0],
        [ur, v1],
        [0, v1],
        col,
      );
    const lbox = (u0, u1, v0, v1, z0, z1, m, capM) => {
      const c = [W(u0, v0), W(u1, v0), W(u1, v1), W(u0, v1)];
      for (let k = 0; k < 4; k++) {
        const len = Math.hypot(c[(k + 1) % 4][0] - c[k][0], c[(k + 1) % 4][1] - c[k][1]);
        quad(m, c[k], c[(k + 1) % 4], z0, z1, len / 4, z0 / 4, z1 / 4);
      }
      if (capM !== null)
        capLocal(
          capM ?? m,
          [
            [u0, v0],
            [u1, v0],
            [u1, v1],
            [u0, v1],
          ],
          z1,
        );
    };
    const box = (u, v, z0, du, dv, h, m) => {
      const [x, y] = W(u, v);
      kit.box(b, m, x, y, z0, du, dv, h, A);
    };
    const add = (geo, m, u, v, z, rotZ = 0) => {
      const [x, y] = W(u, v);
      const mx = new THREE.Matrix4().makeRotationZ(A + rotZ).setPosition(x, y, z);
      b.addGeometry(m, geo, mx);
      geo.dispose();
    };

    // ---------- materials ----------
    const ironM = kit.mat('#3c4a52', { roughness: 0.6, metalness: 0.4 });
    const creamM = kit.mat('#e4dac6');
    const stoneM = kit.mat('portland_stone');
    const slateM = kit.mat('#4b5258', { roughness: 0.75 });
    const brickM = kit.mat('#8d6e58');
    const flatRoof = kit.mat('#6d6c68');
    const darkM = kit.mat('dark_glass');
    const roofGlass = kit.paintedMaterial(
      'paddington_station:vault',
      128,
      512,
      (c, w, h) => {
        // v across the arch profile (0..1), u along the shed = one rib bay
        c.fillStyle = '#9fb3bf';
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.42);
        for (let y = 0; y < h; y += 16) {
          c.fillStyle = `rgba(255,255,255,${0.05 + r() * 0.12})`;
          c.fillRect(0, y, w, 15);
        }
        c.fillStyle = '#5d676d';
        for (const [a, z] of [
          [0, 0.07],
          [0.29, 0.33],
          [0.48, 0.52],
          [0.67, 0.71],
          [0.93, 1],
        ])
          c.fillRect(0, a * h, w, (z - a) * h);
        c.fillStyle = '#3b464d';
        c.fillRect(0, 0, 6, h); // rib
        c.fillStyle = 'rgba(60,70,78,0.7)';
        for (let x = 32; x < w; x += 32) c.fillRect(x, 0, 2, h); // glazing bars
      },
      DS,
    );
    const screenM = kit.paintedMaterial(
      'paddington_station:screen',
      512,
      256,
      (c, w, h) => {
        c.fillStyle = '#b9c6cc';
        c.fillRect(0, 0, w, h);
        c.strokeStyle = '#3c4a52';
        c.lineWidth = 3;
        for (let x = 0; x <= w; x += 32) {
          c.beginPath();
          c.moveTo(x, 0);
          c.lineTo(x, h);
          c.stroke();
        }
        for (let y = h; y > 0; y -= 40) {
          c.beginPath();
          c.moveTo(0, y);
          c.lineTo(w, y);
          c.stroke();
        }
        // Digby Wyatt style tracery: concentric arcs and roundels
        c.lineWidth = 5;
        for (const rr of [0.98, 0.8, 0.55]) {
          c.beginPath();
          c.ellipse(w / 2, h, (w / 2) * rr, h * rr, 0, Math.PI, 2 * Math.PI);
          c.stroke();
        }
        c.lineWidth = 3;
        for (let k = 1; k < 12; k++) {
          const a = Math.PI + (k * Math.PI) / 12;
          c.beginPath();
          c.moveTo(w / 2, h);
          c.lineTo(w / 2 + (Math.cos(a) * w) / 2, h + Math.sin(a) * h);
          c.stroke();
        }
        for (let k = 0; k < 7; k++) {
          const a = Math.PI + ((k + 0.5) * Math.PI) / 7;
          c.beginPath();
          c.arc(w / 2 + Math.cos(a) * w * 0.34, h + Math.sin(a) * h * 0.68, 12, 0, 2 * Math.PI);
          c.stroke();
        }
        c.fillStyle = '#3c4a52';
        c.fillRect(0, h - 10, w, 10);
      },
      DS,
    );
    const trackM = kit.paintedMaterial('paddington_station:tracks', 256, 512, (c, w, h) => {
      // across the shed (x) : platform / two tracks / platform ... one tile = 16 m
      c.fillStyle = '#6a5d4f';
      c.fillRect(0, 0, w, h);
      const pl = (x, ww) => {
        c.fillStyle = '#a9a49a';
        c.fillRect(x, 0, ww, h);
        c.fillStyle = '#e7d36a';
        c.fillRect(x + 2, 0, 3, h);
        c.fillRect(x + ww - 5, 0, 3, h);
      };
      pl(0, 60);
      pl(w - 60, 60);
      c.fillStyle = '#8f8f8f';
      for (const x of [78, 104, 150, 176]) c.fillRect(x, 0, 3, h);
      c.fillStyle = 'rgba(40,30,25,0.5)';
      for (let y = 0; y < h; y += 12) {
        c.fillRect(70, y, 42, 4);
        c.fillRect(142, y, 42, 4);
      }
    });

    // ---------- Train shed ----------
    const U0 = 28,
      U1 = 245;
    const SPRING = 9.5;
    const spans = [
      { va: 0, vb: -20.7, rise: 7 },
      { va: -20.7, vb: -51.9, rise: 11 },
      { va: -51.9, vb: -73.2, rise: 7 },
      { va: -73.2, vb: -106.4, rise: 9.5 },
    ];
    const N = 20;
    const prof = (s, t) => [s.va + (s.vb - s.va) * t, SPRING + s.rise * Math.sin(Math.PI * t)];
    for (const s of spans) {
      // vault: strip along u
      const pts = [];
      for (let k = 0; k <= N; k++) pts.push(prof(s, k / N));
      const ur = (U1 - U0) / 3.05;
      for (let k = 0; k < N; k++) {
        const [va, za] = pts[k],
          [vb, zb] = pts[k + 1];
        const p0 = W(U0, va),
          p1 = W(U1, va),
          p2 = W(U1, vb),
          p3 = W(U0, vb);
        b.quad(
          roofGlass,
          [p0[0], p0[1], za],
          [p1[0], p1[1], za],
          [p2[0], p2[1], zb],
          [p3[0], p3[1], zb],
          [0, k / N],
          [ur, k / N],
          [ur, (k + 1) / N],
          [0, (k + 1) / N],
        );
      }
      // ridge capping and eaves gutters
      box((U0 + U1) / 2, (s.va + s.vb) / 2, SPRING + s.rise, U1 - U0, 0.8, 0.35, ironM);
      // end screens (lunettes) at both ends
      for (const ue of [U0, U1]) {
        const verts = [],
          uvs = [],
          tris = [];
        const mid = (s.va + s.vb) / 2;
        const c0 = W(ue, mid);
        verts.push([c0[0], c0[1], SPRING]);
        uvs.push([0.5, 0]);
        for (let k = 0; k <= N; k++) {
          const [v, z] = pts[k];
          const p = W(ue, v);
          verts.push([p[0], p[1], z]);
          uvs.push([(v - s.va) / (s.vb - s.va), (z - SPRING) / s.rise]);
          if (k > 0) tris.push(0, k, k + 1);
        }
        b.add(screenM, verts, uvs, tris);
        // decorative valance / girder under the screen
        box(ue, mid, SPRING - 1.2, 0.6, Math.abs(s.vb - s.va), 1.2, ironM);
      }
    }
    // Transepts crossing the three original spans (estimated positions), crown 20.5 m.
    for (const uc of [U0 + 0.36 * (U1 - U0), U0 + 0.62 * (U1 - U0)]) {
      const half = 7.6,
        rise = 11,
        va = 0,
        vb = -73.2;
      const pts = [];
      for (let k = 0; k <= N; k++)
        pts.push([uc - half + 2 * half * (k / N), SPRING + rise * Math.sin((Math.PI * k) / N)]);
      const ur = Math.abs(vb - va) / 3.05;
      for (let k = 0; k < N; k++) {
        const [ua, za] = pts[k],
          [ub, zb] = pts[k + 1];
        const p0 = W(ub, va),
          p1 = W(ub, vb),
          p2 = W(ua, vb),
          p3 = W(ua, va);
        b.quad(
          roofGlass,
          [p0[0], p0[1], zb],
          [p1[0], p1[1], zb],
          [p2[0], p2[1], za],
          [p3[0], p3[1], za],
          [0, (k + 1) / N],
          [ur, (k + 1) / N],
          [ur, k / N],
          [0, k / N],
        );
      }
      box(uc, (va + vb) / 2, SPRING + rise, 0.8, Math.abs(vb - va), 0.35, ironM);
      for (const ve of [va, vb]) {
        const verts = [],
          uvs = [],
          tris = [];
        const c0 = W(uc, ve);
        verts.push([c0[0], c0[1], SPRING]);
        uvs.push([0.5, 0]);
        for (let k = 0; k <= N; k++) {
          const [u, z] = pts[k];
          const p = W(u, ve);
          verts.push([p[0], p[1], z]);
          uvs.push([k / N, (z - SPRING) / rise]);
          if (k > 0) tris.push(0, k, k + 1);
        }
        b.add(screenM, verts, uvs, tris);
      }
    }
    // Columns and longitudinal girders on the span lines; side walls.
    const colGeo = () => new THREE.CylinderGeometry(0.32, 0.4, SPRING, 8).rotateX(Math.PI / 2);
    for (const v of [-20.7, -51.9, -73.2]) {
      for (let u = U0 + 3; u <= U1 - 2; u += 9.15) add(colGeo(), ironM, u, v, SPRING / 2);
      box((U0 + U1) / 2, v, SPRING - 1.4, U1 - U0, 0.7, 1.4, ironM);
    }
    // London Street side wall of span 4 (brick with arched openings) and gutter beam on the Eastbourne side.
    const sideWall = kit.paintedMaterial('paddington_station:sidewall', 256, 128, (c, w, h) => {
      c.fillStyle = '#8f705a';
      c.fillRect(0, 0, w, h);
      c.fillStyle = '#d9d1c2';
      c.fillRect(0, 0, w, 10);
      for (let k = 0; k < 2; k++) {
        const x = 24 + k * 128;
        c.fillStyle = '#2f3a40';
        c.beginPath();
        c.moveTo(x, h - 8);
        c.lineTo(x, 50);
        c.arc(x + 40, 50, 40, Math.PI, 0);
        c.lineTo(x + 80, h - 8);
        c.fill();
        c.strokeStyle = '#d9d1c2';
        c.lineWidth = 4;
        c.beginPath();
        c.arc(x + 40, 50, 42, Math.PI, 0);
        c.stroke();
      }
    });
    {
      const p = W(U0, -106.4),
        q = W(U1, -106.4);
      quad(sideWall, q, p, 0, SPRING, (U1 - U0) / 10, 0, 1);
      quad(sideWall, p, q, 0, SPRING, (U1 - U0) / 10, 0, 1);
    }
    box((U0 + U1) / 2, -0.3, SPRING - 1, U1 - U0, 0.8, 1.2, ironM);
    // Platforms and tracks under the shed.
    {
      const p0 = W(U0, 0),
        p1 = W(U1, 0),
        p2 = W(U1, -106.4),
        p3 = W(U0, -106.4);
      const vr = 106.4 / 16,
        ur = (U1 - U0) / 32;
      b.add(
        trackM,
        [
          [p0[0], p0[1], 0.12],
          [p1[0], p1[1], 0.12],
          [p2[0], p2[1], 0.12],
          [p3[0], p3[1], 0.12],
        ],
        [
          [0, 0],
          [0, ur],
          [vr, ur],
          [vr, 0],
        ],
        [0, 1, 2, 0, 2, 3],
      );
    }

    // ---------- Rest of the station outline ----------
    const st = byId['cacd5f93-024a-4c87-a69d-cbcf76a4f82f'];
    const ring = st.polys[0][0].map(toL);
    // outer screen walls
    const ringW = st.polys[0][0];
    const wallMat = kit.facade('london_stock', 1);
    kit.walls(b, wallMat, [[ringW]], 0, 6.5, { bay: 4.5, storey: 3.25 });
    // Lawn concourse roof (u < U0): glazed canopy on slender columns.
    const lawn = clip(ring, (p) => U0 - p[0]);
    const lawnGlass = kit.paintedMaterial(
      'paddington_station:lawn',
      128,
      128,
      (c, w, h) => {
        c.fillStyle = '#a6b9c3';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#e8ecee';
        c.fillRect(0, 0, w, 6);
        c.fillRect(0, 0, 6, h);
        c.fillStyle = 'rgba(255,255,255,0.18)';
        c.fillRect(8, 8, w / 2, h / 2);
      },
      DS,
    );
    capLocal(lawnGlass, lawn, 10.5);
    capLocal(lawnGlass, lawn, 10.5, true);
    for (let v = -6; v > -58; v -= 12) box(U0 - 0.5, v, 6.5, 0.4, 0.4, 4, kit.mat('white_steel'));
    // north-west platform canopies (u > U1) and outer strip on the London Street side
    for (const reg of [
      clip(ring, (p) => p[0] - U1),
      clip(
        clip(
          clip(ring, (p) => p[0] - U0),
          (p) => U1 - p[0],
        ),
        (p) => -106.4 - p[1],
      ),
    ]) {
      capLocal(flatRoof, reg, 6.5);
    }

    // ---------- Platform 1 office range (Eastbourne Terrace) ----------
    const mh = byId['5c55db4c-2e46-4a30-9cd6-95ab5c5fb5e2'];
    const rangeFacade = kit.facade('stucco', 2);
    for (const poly of mh.polys) {
      const lr = poly[0].map(toL);
      for (const [f, h, mat] of [
        [(p) => 46 - p[0], 20, kit.facade('portland_stone', 1)],
        [(p) => p[0] - 46, 13, rangeFacade],
      ]) {
        const r = clip(lr, f);
        if (r.length < 3 || Math.abs(ringArea(r)) < 2) continue;
        let wr = toWorldRing(r);
        if (kit.ringArea(wr) < 0) wr = wr.slice().reverse();
        kit.walls(b, mat, [[wr]], 0, h, { bay: 3.6, storey: 3.4 });
        kit.cap(b, flatRoof, [[wr]], h);
        // cornice
        kit.walls(b, stoneM, [[kit.offsetRing(wr, 0.35)]], h - 0.6, h);
      }
    }
    // Three oriel windows overlooking the transepts on the platform 1 side.
    for (const uc of [U0 + 0.36 * (U1 - U0), U0 + 0.49 * (U1 - U0), U0 + 0.62 * (U1 - U0)]) {
      box(uc, -0.9, 7, 6, 1.8, 4.5, creamM);
      box(uc, -1.85, 7.6, 4.6, 0.1, 3.3, darkM);
    }

    // ---------- Great Western Royal Hotel ----------
    const hot = byId['360408b3-6867-4a89-9cc6-8e3548e0ffe1'];
    const hotW = hot.polys[0][0];
    kit.walls(b, kit.facade('stucco', 0), [[hotW]], 0, 20, { bay: 3.2, storey: 3.6 });
    kit.cap(b, flatRoof, [[hotW]], 20);
    // Front (Praed Street) facade drawn bay by bay: rusticated stone ground floor
    // with arched openings, three stuccoed storeys with pedimented windows, attic.
    const bayTex = (key, storeys, attic) =>
      kit.paintedMaterial(key, 128, 64 * (storeys + 1), (c, w, h) => {
        const sh = h / (storeys + 1);
        c.fillStyle = '#e5dccb';
        c.fillRect(0, 0, w, h);
        // ground floor: rusticated, arched opening
        const gy = h - sh * 1.25;
        c.fillStyle = '#d8d0bf';
        c.fillRect(0, gy, w, h - gy);
        c.fillStyle = 'rgba(120,110,95,0.5)';
        for (let y = gy + 10; y < h; y += 12) c.fillRect(0, y, w, 2);
        c.fillStyle = '#2b3439';
        c.beginPath();
        c.moveTo(34, h - 4);
        c.lineTo(34, gy + 34);
        c.arc(64, gy + 34, 30, Math.PI, 0);
        c.lineTo(94, h - 4);
        c.fill();
        // upper storeys
        for (let s = 0; s < storeys - 1; s++) {
          const y = gy - (s + 1) * sh;
          c.fillStyle = '#2b3439';
          c.fillRect(42, y + 18, 44, sh - 26);
          c.fillStyle = 'rgba(170,190,200,0.3)';
          c.fillRect(42, y + 18, 44, 10);
          c.fillStyle = '#f2ebde';
          c.fillRect(36, y + sh - 10, 56, 6); // sill
          if (s === 0) {
            c.beginPath();
            c.moveTo(34, y + 16);
            c.lineTo(64, y + 4);
            c.lineTo(94, y + 16);
            c.fill();
          } else c.fillRect(36, y + 10, 56, 6);
          c.fillStyle = 'rgba(150,135,110,0.5)';
          c.fillRect(0, y + sh - 3, w, 3);
        }
        if (attic) {
          c.fillStyle = '#d6ccb9';
          c.fillRect(0, 0, w, 14);
        }
        c.fillStyle = '#f4eee3';
        c.fillRect(0, 0, w, 6);
      });
    const frontTex = bayTex('paddington_station:hotel_bay', 5, true);
    const towerTex = bayTex('paddington_station:hotel_tower', 7, true);
    const UF = -48.1,
      UB = -31;
    // front range
    {
      const corners = [
        [UF, -63.7],
        [UB, -63.7],
        [UB, 0.2],
        [UF, 0.2],
      ].map(([u, v]) => W(u, v));
      for (let k = 0; k < 4; k++) {
        const p = corners[k],
          q = corners[(k + 1) % 4];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        quad(frontTex, p, q, 0, 21, Math.round(len / 3.05), 0, 1);
      }
      // cornice and steep pavilion roof with pedimented dormers
      box((UF + UB) / 2, -31.75, 20.6, UB - UF + 1.2, 65.1, 0.8, creamM);
      const rr = [
        [UF, -63.7],
        [UB, -63.7],
        [UB, 0.2],
        [UF, 0.2],
      ].map(([u, v]) => W(u, v));
      kit.pitchedRoof(b, slateM, creamM, rr, A + Math.PI / 2, 21.4, 6.5, 'hipped', {
        overhang: 0.2,
      });
      for (let v = -60.5; v <= -2; v += 3.05) {
        if (v > -40.5 && v < -23) continue;
        box(UF + 2.2, v, 21.2, 1.6, 1.6, 2.6, creamM);
        box(UF + 1.39, v, 21.6, 0.05, 1.0, 1.7, darkM);
        add(
          new THREE.CylinderGeometry(1.15, 1.15, 1.7, 3).rotateZ(Math.PI / 2).rotateY(Math.PI / 2),
          creamM,
          UF + 2.2,
          v,
          24.0,
          Math.PI / 2,
        );
      }
    }
    // 7-bay centre breaking forward, with pediment and sculpture panel; porte-cochere
    {
      const v0 = -42.5,
        v1 = -21.2,
        u0 = UF - 1.6;
      const cs = [
        [u0, v0],
        [UF, v0],
        [UF, v1],
        [u0, v1],
      ].map(([u, v]) => W(u, v));
      for (let k = 0; k < 4; k++) {
        const p = cs[k],
          q = cs[(k + 1) % 4];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        quad(frontTex, p, q, 0, 22, Math.max(1, Math.round(len / 3.05)), 0, 22 / 21);
      }
      // attic storey over the centre
      lbox(u0 + 0.3, UB - 4, v0 + 0.5, v1 - 0.5, 22, 25.5, creamM, slateM);
      box(u0 + 0.3, (v0 + v1) / 2, 24.2, 0.1, v1 - v0 - 3, 0.6, darkM);
      // pediment (triangular prism)
      const pg = new THREE.BufferGeometry();
      const pw = (v1 - v0) / 2,
        ph = 5;
      const pa = [
        [0, -pw, 0],
        [0, pw, 0],
        [0, 0, ph],
        [3, -pw, 0],
        [3, pw, 0],
        [3, 0, ph],
      ];
      const idx = [0, 2, 1, 3, 4, 5, 0, 1, 4, 0, 4, 3, 1, 2, 5, 1, 5, 4, 2, 0, 3, 2, 3, 5];
      pg.setAttribute(
        'position',
        new THREE.Float32BufferAttribute(
          idx.flatMap((i) => pa[i]),
          3,
        ),
      );
      pg.setAttribute(
        'uv',
        new THREE.Float32BufferAttribute(
          idx.flatMap(() => [0, 0]),
          2,
        ),
      );
      add(pg, creamM, u0 - 0.2, (v0 + v1) / 2, 25.5);
      // sculpted tympanum (Peace, Plenty, Science, Industry) as a darker relief panel
      const tym = kit.paintedMaterial('paddington_station:tympanum', 256, 64, (c, w, h) => {
        c.fillStyle = '#e5dccb';
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#b9ad98';
        c.beginPath();
        c.moveTo(10, h - 4);
        c.lineTo(w / 2, 6);
        c.lineTo(w - 10, h - 4);
        c.fill();
        c.fillStyle = '#8f8471';
        for (let k = 0; k < 4; k++) {
          c.beginPath();
          c.ellipse(70 + k * 38, h - 18, 9, 14, 0, 0, 2 * Math.PI);
          c.fill();
        }
      });
      {
        const p = W(u0 - 0.25, v0 + 1.5),
          q = W(u0 - 0.25, v1 - 1.5);
        b.add(
          tym,
          [
            [q[0], q[1], 25.6],
            [p[0], p[1], 25.6],
            [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2, 25.6 + ph * 0.86],
          ],
          [
            [0, 0],
            [1, 0],
            [0.5, 1],
          ],
          [0, 1, 2],
        );
      }
      // entrance canopy
      box(u0 - 2.5, (v0 + v1) / 2, 4.2, 5, 12, 0.6, kit.mat('#2e3a33'));
      for (const v of [v0 + 4, v1 - 4]) box(u0 - 4.6, v, 0, 0.3, 0.3, 4.2, kit.mat('#2e3a33'));
    }
    // Projecting angle towers: 6 storeys, pierced parapet, ogee roofs with finials.
    const towers = [
      { u0: -53.2, u1: -40, v0: -74.2, v1: -63.7 },
      { u0: -52.2, u1: -40, v0: 0.2, v1: 9.0 },
    ];
    for (const t of towers) {
      const H = 28;
      const cs = [
        [t.u0, t.v0],
        [t.u1, t.v0],
        [t.u1, t.v1],
        [t.u0, t.v1],
      ].map(([u, v]) => W(u, v));
      for (let k = 0; k < 4; k++) {
        const p = cs[k],
          q = cs[(k + 1) % 4];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        quad(towerTex, p, q, 0, H, Math.max(1, Math.round(len / 4.5)), 0, 1);
      }
      capLocal(
        flatRoof,
        [
          [t.u0, t.v0],
          [t.u1, t.v0],
          [t.u1, t.v1],
          [t.u0, t.v1],
        ],
        H,
      );
      const uc = (t.u0 + t.u1) / 2,
        vc = (t.v0 + t.v1) / 2,
        du = t.u1 - t.u0,
        dv = t.v1 - t.v0;
      box(uc, vc, H - 0.6, du + 1.0, dv + 1.0, 0.8, creamM);
      // pierced parapet: posts and rail
      for (const [pu, pv, lu, lv] of [
        [uc, t.v0 - 0.4, du + 0.8, 0.3],
        [uc, t.v1 + 0.4, du + 0.8, 0.3],
        [t.u0 - 0.4, vc, 0.3, dv + 0.8],
        [t.u1 + 0.4, vc, 0.3, dv + 0.8],
      ])
        box(pu, pv, H + 1.1, lu, lv, 0.3, creamM);
      for (let k = 0; k <= 6; k++) {
        for (const v of [t.v0 - 0.4, t.v1 + 0.4])
          box(t.u0 + (du * k) / 6, v, H + 0.2, 0.35, 0.35, 0.9, creamM);
        for (const u of [t.u0 - 0.4, t.u1 + 0.4])
          box(u, t.v0 + (dv * k) / 6, H + 0.2, 0.35, 0.35, 0.9, creamM);
      }
      // ogee roof: square lathe (4 segments) scaled to the tower plan
      const pr = [];
      const R = 1,
        RH = 8;
      for (let k = 0; k <= 12; k++) {
        const t2 = k / 12;
        const r =
          R *
          (t2 < 0.5
            ? 1 - 0.25 * Math.sin(Math.PI * t2)
            : 0.75 * (1 - (t2 - 0.5) * 2) ** 1.6 + 0.02);
        pr.push(new THREE.Vector2(Math.max(0.02, r), t2 * RH));
      }
      const og = new THREE.LatheGeometry(pr, 4, Math.PI / 4).rotateX(Math.PI / 2);
      og.scale((du - 0.6) / Math.SQRT2, (dv - 0.6) / Math.SQRT2, 1);
      add(og, slateM, uc, vc, H + 0.2);
      add(
        new THREE.CylinderGeometry(0.08, 0.2, 3, 6).rotateX(Math.PI / 2),
        kit.mat('#2e3a33'),
        uc,
        vc,
        H + RH + 1.3,
      );
      add(new THREE.SphereGeometry(0.35, 8, 6), kit.mat('gold'), uc, vc, H + RH + 0.4);
    }
    g.add(b.toGroup('paddington_station'));
    return g;
  },
};
