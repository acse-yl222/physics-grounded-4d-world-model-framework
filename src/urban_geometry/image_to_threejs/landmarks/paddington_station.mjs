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
    {
      title: 'Paddington Station including the Lawn - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101066881-paddington-station-including-the-lawn-gwr-office-block-on-london-street-and-offices-along-eastbourne-terrace-hyde-park-ward',
      used_for:
        'listed extent: shed, the Lawn, GWR office block on London Street, offices along Eastbourne Terrace',
    },
    {
      title: "Brunel's starting point - Mike Higginbottom Interesting Times",
      url: 'https://www.mikehigginbottominterestingtimes.co.uk/2024/10/09/brunels-starting-point/',
      used_for:
        'wrought-iron ribs (span 4 in steel), columns originally cast iron replaced in steel 1922-24, span 4 without transepts',
    },
    {
      title: 'Great Western Hotel - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101227144-great-western-hotel-hyde-park-ward',
      used_for:
        'stone-faced ground and first floor of the centre, 5-bay pedimented break, pedimented dormers above the attic',
    },
  ],
  notes:
    'Shed placed in the Overture station outline (217 m from the Lawn to the north-west screens, spans 20.7/31.2/21.3/33.2 m). ' +
    'Springing (9.5 m) and crown heights (16.5-20.5 m), transept positions and roof glazing pattern are estimates; ' +
    'ribs are modelled in 3D at 10 ft (3.05 m) centres with every third on a column (spacing assumed, not sourced), ' +
    'with capping bars, ridge ventilators, arched column brackets and 3D end-screen tracery (arcs, spokes, roundels, ' +
    'mullions) in the spirit of Digby Wyatt; tracery pattern is schematic. The 1999 Lawn roof is a plain glazed canopy. ' +
    'Hotel: 4 storeys (rusticated ground floor, arched/pedimented/segmental/plain window heads per storey), 7-bay centre ' +
    'with 5-bay pedimented break, attic, steep pavilion roof with pedimented dormers, chimneys and cresting, 6-storey ' +
    'angle towers with quoins, balustraded parapets, ogee roofs and lucarnes; heights (eaves 20 m, towers 28 m) estimated ' +
    'from storey counts, window and dormer counts approximate, entrance canopy and pediment figures schematic. Platform 1 ' +
    'range has 3D windows on the Eastbourne Terrace face (13 m, MacMillan House end 20 m). Lamps and bollards on Praed ' +
    'Street / Eastbourne Terrace are generic resources assets at assumed positions.',
  build({ THREE, kit, byId, placeAssets }) {
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
    const louvreM = kit.mat('#7d8a90', { roughness: 0.6, metalness: 0.3 });
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

    // ---------- 3D helpers ----------
    // kit.windowRow with round / segmental heads built as vertical glass sectors and
    // projecting archivolts with a keystone (lintel, pediment and plain heads pass through).
    const archRow = (batch, a, c, z, opts) => {
      const head = opts.head;
      if (head !== 'arch' && head !== 'segment') return kit.windowRow(batch, a, c, z, opts);
      const cs = kit.windowRow(batch, a, c, z, { ...opts, head: 'none' });
      const w = opts.width ?? 1.2,
        h = opts.height ?? 2.0,
        d = opts.depth ?? 0.12;
      const glassM = opts.glass ?? kit.mat('dark_glass'),
        trimM = opts.sill ?? opts.frame ?? kit.mat('white');
      const L = Math.hypot(c[0] - a[0], c[1] - a[1]) || 1;
      const ux = (c[0] - a[0]) / L,
        uy = (c[1] - a[1]) / L;
      const seg = head === 'arch' ? Math.PI : Math.PI / 2.5;
      const R = head === 'arch' ? w / 2 : w / 2 / Math.sin(seg / 2);
      const zc = z + h - (head === 'arch' ? 0 : R * Math.cos(seg / 2));
      const X = new THREE.Vector3(ux, uy, 0),
        Y = new THREE.Vector3(0, 0, 1),
        Z = new THREE.Vector3(uy, -ux, 0);
      const gl = new THREE.CircleGeometry(R, 12, Math.PI / 2 - seg / 2, seg);
      const tor = new THREE.TorusGeometry(R + 0.06, 0.08, 4, 12, seg).rotateZ(
        Math.PI / 2 - seg / 2,
      );
      const key = new THREE.BoxGeometry(0.28, 0.34, d * 1.6);
      const m = new THREE.Matrix4();
      for (const [cx, cy] of cs) {
        m.makeBasis(X, Y, Z).setPosition(cx + Z.x * 0.03, cy + Z.y * 0.03, zc);
        batch.addGeometry(glassM, gl, m);
        m.makeBasis(X, Y, Z).setPosition(cx + Z.x * d * 0.8, cy + Z.y * d * 0.8, zc);
        batch.addGeometry(trimM, tor, m);
        m.makeBasis(X, Y, Z).setPosition(cx + Z.x * d * 0.8, cy + Z.y * d * 0.8, zc + R + 0.08);
        batch.addGeometry(trimM, key, m);
      }
      [gl, tor, key].forEach((q) => q.dispose());
      return cs;
    };
    const uDir = new THREE.Vector3(ca, sa, 0),
      vDir = new THREE.Vector3(-sa, ca, 0),
      zDir = new THREE.Vector3(0, 0, 1);
    const V3 = (u, v, z) => {
      const [x, y] = W(u, v);
      return new THREE.Vector3(x, y, z);
    };
    const unitBox = new THREE.BoxGeometry(1, 1, 1);
    const bm = new THREE.Matrix4();
    // Rectangular bar from P to Q; ty along the hint direction, tz perpendicular to both.
    const beam = (P, Q, ty, tz, hint, m) => {
      const x = Q.clone().sub(P);
      const len = x.length();
      if (len < 1e-3) return;
      x.divideScalar(len);
      const y = hint.clone().addScaledVector(x, -hint.dot(x));
      if (y.lengthSq() < 1e-6) y.copy(zDir).addScaledVector(x, -x.z);
      y.normalize();
      const z = new THREE.Vector3().crossVectors(x, y);
      bm.makeBasis(x.multiplyScalar(len), y.multiplyScalar(ty), z.multiplyScalar(tz));
      bm.setPosition(P.clone().add(Q).multiplyScalar(0.5));
      b.addGeometry(m, unitBox, bm);
    };
    // Windows on a local wall edge (outward normal on the right of a -> b).
    const rowL = (a, c, z, opts) => archRow(b, W(...a), W(...c), z, opts);
    const corniceL = (u0, u1, v0, v1, z, opts, m = creamM) => {
      let r = [W(u0, v0), W(u1, v0), W(u1, v1), W(u0, v1)];
      if (kit.ringArea(r) < 0) r = r.reverse();
      kit.cornice(b, m, r, z, opts);
    };
    const castM = kit.mat('#2f3b42', { roughness: 0.55, metalness: 0.45 });
    const screenGlass = kit.mat('#aebfc8', {
      roughness: 0.2,
      metalness: 0.15,
      side: THREE.DoubleSide,
    });

    // ---------- Train shed ----------
    const U0 = 28,
      U1 = 245;
    const SPRING = 9.5;
    const spans = [
      { va: 0, vb: -20.7, rise: 7 },
      { va: -20.7, vb: -51.9, rise: 11 },
      { va: -51.9, vb: -73.2, rise: 7 },
      { va: -73.2, vb: -106.4, rise: 9.5, steel: true },
    ];
    const N = 20,
      NR = 12; // vault facets / rib segments
    const prof = (s, t) => [s.va + (s.vb - s.va) * t, SPRING + s.rise * Math.sin(Math.PI * t)];
    // unit normal of the arch profile in the (v, z) plane, pointing out of the vault
    const profN = (s, t) => {
      const dv = s.vb - s.va,
        dz = s.rise * Math.PI * Math.cos(Math.PI * t);
      let nv = -dz,
        nz = dv;
      if (nz < 0 || (Math.abs(nz) < 1e-6 && nv * (t - 0.5) * dv < 0)) {
        nv = -nv;
        nz = -nz;
      }
      const l = Math.hypot(nv, nz);
      return [nv / l, nz / l];
    };
    const RIB = 3.05; // ribs at 10 ft centres, every third one on a column (estimate)
    const ribUs = [];
    for (let u = U0 + 3; u <= U1 - 1; u += RIB) ribUs.push(u);
    for (const s of spans) {
      // vault skin: strip along u
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
      // wrought-iron (span 4: steel) arched ribs under the skin and capping bars over it
      const depth = s.steel ? 1.0 : 0.75;
      for (const u of ribUs) {
        let prevIn = null,
          prevOut = null;
        for (let k = 0; k <= NR; k++) {
          const t = k / NR;
          const [v, z] = prof(s, t);
          const [nv, nz] = profN(s, t);
          const pin = V3(u, v - nv * (depth / 2 + 0.05), z - nz * (depth / 2 + 0.05));
          const pout = V3(u, v + nv * 0.09, z + nz * 0.09);
          if (prevIn) {
            beam(prevIn, pin, 0.22, depth, uDir, castM);
            beam(prevOut, pout, 0.12, 0.14, uDir, ironM);
          }
          prevIn = pin;
          prevOut = pout;
        }
      }
      // ridge ventilator: raised louvred lantern along the crown
      {
        const vm = (s.va + s.vb) / 2,
          zc = SPRING + s.rise;
        const wv = Math.abs(s.vb - s.va) * 0.06;
        box((U0 + U1) / 2, vm, zc - 0.1, U1 - U0, wv, 0.9, louvreM);
        box((U0 + U1) / 2, vm, zc + 0.8, U1 - U0 + 0.4, wv + 1.0, 0.18, ironM);
        box((U0 + U1) / 2, vm, zc + 0.98, U1 - U0 + 0.2, 0.4, 0.2, ironM);
      }
      // eaves gutters on each span line
      for (const v of [s.va, s.vb]) box((U0 + U1) / 2, v, SPRING - 0.2, U1 - U0, 0.9, 0.5, ironM);
      // end screens (lunettes): glazing plus 3D Digby Wyatt style iron tracery
      const vm = (s.va + s.vb) / 2;
      for (const ue of [U0, U1]) {
        const verts = [],
          uvs = [],
          tris = [];
        const c0 = W(ue, vm);
        verts.push([c0[0], c0[1], SPRING]);
        uvs.push([0.5, 0]);
        for (let k = 0; k <= N; k++) {
          const [v, z] = pts[k];
          const p = W(ue, v);
          verts.push([p[0], p[1], z]);
          uvs.push([(v - s.va) / (s.vb - s.va), (z - SPRING) / s.rise]);
          if (k > 0) tris.push(0, k, k + 1);
        }
        b.add(screenGlass, verts, uvs, tris);
        const ue2 = ue + (ue === U0 ? -0.12 : 0.12);
        // outer arch frame and two inner concentric arcs
        for (const sc of [1, 0.78, 0.52]) {
          let prev = null;
          for (let k = 0; k <= NR; k++) {
            const [v, z] = prof(s, k / NR);
            const P = V3(ue2, vm + (v - vm) * sc, SPRING + (z - SPRING) * sc);
            if (prev) beam(prev, P, 0.3, sc === 1 ? 0.45 : 0.22, uDir, castM);
            prev = P;
          }
        }
        // radial spokes between the arcs and vertical mullions below the inner arc
        const nSp = 12;
        for (let k = 1; k < nSp; k++) {
          const t = k / nSp;
          const [v, z] = prof(s, t);
          beam(
            V3(ue2, vm + (v - vm) * 0.52, SPRING + (z - SPRING) * 0.52),
            V3(ue2, v, z),
            0.25,
            0.14,
            uDir,
            castM,
          );
        }
        for (let k = 1; k < 8; k++) {
          const t = 0.24 + (0.52 * k) / 8;
          const [v, z] = prof(s, t);
          const zz = SPRING + (z - SPRING) * 0.52;
          beam(
            V3(ue2, v * 0 + vm + (v - vm) * 0.52, SPRING),
            V3(ue2, vm + (v - vm) * 0.52, zz),
            0.2,
            0.12,
            uDir,
            castM,
          );
        }
        // roundels between the middle and outer arcs
        for (let k = 0; k < 7; k++) {
          const t = (k + 0.5) / 7;
          const [v, z] = prof(s, t);
          const P = V3(ue2, vm + (v - vm) * 0.89, SPRING + (z - SPRING) * 0.89);
          const tor = new THREE.TorusGeometry(Math.abs(s.vb - s.va) * 0.025 + 0.25, 0.07, 4, 12);
          const m = new THREE.Matrix4().makeBasis(vDir, zDir, uDir).setPosition(P);
          b.addGeometry(castM, tor, m);
          tor.dispose();
        }
        // decorative valance girder under the screen
        box(ue, vm, SPRING - 1.2, 0.6, Math.abs(s.vb - s.va), 1.2, ironM);
        for (let v = Math.max(s.va, s.vb) - 0.6; v > Math.min(s.va, s.vb); v -= 1.2)
          box(ue2, v, SPRING - 1.5, 0.12, 0.5, 0.35, castM);
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
      box(uc, (va + vb) / 2, SPRING + rise - 0.1, 1.4, Math.abs(vb - va), 0.8, louvreM);
      box(uc, (va + vb) / 2, SPRING + rise + 0.7, 2.2, Math.abs(vb - va), 0.18, ironM);
      // transverse ribs of the transept vault
      for (let v = va - 1.5; v > vb + 0.5; v -= RIB) {
        let prev = null,
          prevO = null;
        for (let k = 0; k <= NR; k++) {
          const t = k / NR;
          const u = uc - half + 2 * half * t,
            z = SPRING + rise * Math.sin(Math.PI * t);
          const du = 2 * half,
            dz = rise * Math.PI * Math.cos(Math.PI * t);
          const l = Math.hypot(dz, du);
          const nu = -dz / l,
            nz = du / l;
          const P = V3(u - nu * 0.4, v, z - nz * 0.4),
            Po = V3(u + nu * 0.09, v, z + nz * 0.09);
          if (prev) {
            beam(prev, P, 0.2, 0.65, vDir, castM);
            beam(prevO, Po, 0.12, 0.14, vDir, ironM);
          }
          prev = P;
          prevO = Po;
        }
      }
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
        b.add(screenGlass, verts, uvs, tris);
        const ve2 = ve + (ve === va ? 0.12 : -0.12);
        for (const sc of [1, 0.6]) {
          let prev = null;
          for (let k = 0; k <= NR; k++) {
            const [u, z] = pts[Math.round((k / NR) * N)];
            const P = V3(uc + (u - uc) * sc, ve2, SPRING + (z - SPRING) * sc);
            if (prev) beam(prev, P, 0.3, 0.3, vDir, castM);
            prev = P;
          }
        }
        for (let k = 1; k < 8; k++) {
          const [u, z] = pts[Math.round((k / 8) * N)];
          beam(
            V3(uc + (u - uc) * 0.6, ve2, SPRING + (z - SPRING) * 0.6),
            V3(u, ve2, z),
            0.22,
            0.14,
            vDir,
            castM,
          );
        }
        for (let k = 1; k < 6; k++) {
          const u = uc - half * 0.6 + (1.2 * half * k) / 6;
          const zz = SPRING + rise * 0.6 * Math.sin((Math.PI * (u - uc + half)) / (2 * half));
          beam(V3(u, ve2, SPRING), V3(u, ve2, zz), 0.2, 0.12, vDir, castM);
        }
      }
    }
    // Columns (cast iron, replaced in steel 1922-24) with capitals and arched
    // brackets carrying the longitudinal girders on the span lines.
    const shaftG = new THREE.CylinderGeometry(0.3, 0.36, SPRING - 2.2, 8).rotateX(Math.PI / 2);
    const baseG = new THREE.CylinderGeometry(0.55, 0.62, 1.1, 8).rotateX(Math.PI / 2);
    const capG = new THREE.CylinderGeometry(0.62, 0.34, 0.9, 8).rotateX(Math.PI / 2);
    const colM = new THREE.Matrix4();
    for (const v of [-20.7, -51.9, -73.2]) {
      for (let k = 0; k < ribUs.length; k += 3) {
        const u = ribUs[k];
        const [x, y] = W(u, v);
        b.addGeometry(castM, baseG, colM.makeTranslation(x, y, 0.55));
        b.addGeometry(ironM, shaftG, colM.makeTranslation(x, y, 1.1 + (SPRING - 2.2) / 2));
        b.addGeometry(castM, capG, colM.makeTranslation(x, y, SPRING - 1.55));
        // arched spandrel brackets towards the neighbouring columns
        for (const sgn of [-1, 1]) {
          let prev = null;
          for (let j = 0; j <= 5; j++) {
            const a = (j / 5) * (Math.PI / 2);
            const P = V3(
              u + sgn * (1 - Math.cos(a)) * 2.6,
              v,
              SPRING - 1.1 - (1 - Math.sin(a)) * 2.0,
            );
            if (prev) beam(prev, P, 0.16, 0.2, vDir, castM);
            prev = P;
          }
        }
      }
      box((U0 + U1) / 2, v, SPRING - 1.4, U1 - U0, 0.7, 1.4, ironM);
      box((U0 + U1) / 2, v, SPRING - 1.5, U1 - U0, 0.9, 0.12, castM);
    }
    [shaftG, baseG, capG].forEach((q) => q.dispose());
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
      // brick pilasters and coping on the London Street side wall
      for (let u = U0 + 5; u < U1; u += 10) box(u, -106.9, 0, 1.2, 1.0, SPRING - 0.2, brickM);
      box((U0 + U1) / 2, -106.7, SPRING - 0.6, U1 - U0, 1.3, 0.6, stoneM);
    }
    box((U0 + U1) / 2, -0.3, SPRING - 1, U1 - U0, 0.8, 1.2, ironM);
    // Platforms and tracks under the shed: track bed plus raised platform slabs.
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
      const platM = kit.mat('#a9a49a');
      for (let v = -1.9; v > -106; v -= 8.0)
        box((U0 + 8 + U1) / 2, v, 0.12, U1 - U0 - 8, 3.6, 0.8, platM);
    }

    // ---------- Rest of the station outline ----------
    const st = byId['cacd5f93-024a-4c87-a69d-cbcf76a4f82f'];
    const ring = st.polys[0][0].map(toL);
    // outer screen walls
    const ringW = st.polys[0][0];
    const wallMat = kit.facade('london_stock', 1);
    kit.walls(b, wallMat, [[ringW]], 0, 6.5, { bay: 4.5, storey: 3.25 });
    kit.cornice(b, stoneM, kit.ringArea(ringW) < 0 ? ringW.slice().reverse() : ringW, 6.1, {
      height: 0.4,
      projection: 0.25,
    });
    // Lawn concourse roof (u < U0): glazed canopy on slender columns with roof beams.
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
    const wsteel = kit.mat('white_steel');
    for (let v = -6; v > -58; v -= 12) box(U0 - 0.5, v, 6.5, 0.4, 0.4, 4, wsteel);
    for (let u = 2; u < U0; u += 4.5) box(u, -30, 10.5, 0.25, 59, 0.35, wsteel);
    for (let v = -3; v > -60; v -= 9) box(U0 / 2, v, 10.2, U0 - 1, 0.25, 0.3, wsteel);
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
    const rangeFacade = kit.mat('#e2d9c6');
    const stoneFacade = kit.mat('#d9d2c1');
    const winDark = kit.mat('#2a3439', { roughness: 0.2, metalness: 0.2 });
    for (const poly of mh.polys) {
      const lr = poly[0].map(toL);
      for (const [f, h, mat, storeys, sz] of [
        [(p) => 46 - p[0], 20, stoneFacade, 5, 3.7],
        [(p) => p[0] - 46, 13, rangeFacade, 3, 4.0],
      ]) {
        const r = clip(lr, f);
        if (r.length < 3 || Math.abs(ringArea(r)) < 2) continue;
        let wr = toWorldRing(r);
        if (kit.ringArea(wr) < 0) wr = wr.slice().reverse();
        kit.walls(b, mat, [[wr]], 0, h, { bay: 3.6, storey: 3.4 });
        kit.cap(b, flatRoof, [[wr]], h);
        kit.cornice(b, stoneM, wr, h - 0.7, { height: 0.7, projection: 0.45, steps: 2 });
        kit.cornice(b, stoneM, wr, 0, { height: 0.6, projection: 0.15 });
        kit.cornice(b, stoneM, wr, sz + 0.3, { height: 0.3, projection: 0.15 });
        kit.cornice(b, creamM, kit.offsetRing(wr, -0.1), h, { height: 0.9, projection: 0.12 });
        // 3D windows on the Eastbourne Terrace (and Praed Street end) faces
        for (let k = 0; k < wr.length; k++) {
          const a = wr[k],
            c = wr[(k + 1) % wr.length];
          const al = toL(a),
            cl = toL(c);
          const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
          const outerV = al[1] > 7 && cl[1] > 7 && cl[0] < al[0];
          const praedEnd = al[0] < -20 && cl[0] < -20 && Math.abs(cl[1] - al[1]) > 5;
          if (len < 5 || !(outerV || praedEnd)) continue;
          for (let s = 0; s < storeys; s++)
            archRow(b, a, c, s === 0 ? 1.0 : sz * s + 0.9, {
              width: s === 0 ? 1.6 : 1.3,
              height: s === 0 ? 2.8 : sz - 1.6,
              bay: 3.6,
              margin: 0.8,
              glass: winDark,
              frame: kit.mat('white'),
              sill: stoneM,
              head: s === 0 ? 'arch' : s === 1 ? 'pediment' : 'lintel',
              bars: 1,
            });
        }
      }
    }
    // Three oriel windows overlooking the transepts on the platform 1 side.
    for (const uc of [U0 + 0.36 * (U1 - U0), U0 + 0.49 * (U1 - U0), U0 + 0.62 * (U1 - U0)]) {
      box(uc, -0.9, 7, 6, 1.8, 4.5, creamM);
      box(uc, -1.85, 7.6, 4.6, 0.1, 3.3, darkM);
      for (const du of [-1.5, 0, 1.5]) box(uc + du, -1.92, 7.6, 0.15, 0.12, 3.3, creamM);
      box(uc, -1.0, 6.6, 6.6, 2.1, 0.4, stoneM);
      box(uc, -1.0, 11.5, 6.6, 2.1, 0.5, stoneM);
    }

    // ---------- Great Western Royal Hotel ----------
    const hot = byId['360408b3-6867-4a89-9cc6-8e3548e0ffe1'];
    const hotW = hot.polys[0][0];
    // rear parts of the hotel (towards the Lawn): stucco with painted windows; the
    // Praed Street range and towers are modelled below with real window openings.
    {
      const hr = kit.ringArea(hotW) < 0 ? hotW.slice().reverse() : hotW;
      for (let k = 0; k < hr.length; k++) {
        const a = hr[k],
          c = hr[(k + 1) % hr.length];
        if (toL(a)[0] < -40 && toL(c)[0] < -40) continue;
        kit.walls(b, kit.facade('stucco', 0), [[[a, c]]], 0, 20, { bay: 3.2, storey: 3.6 });
      }
      kit.cap(b, flatRoof, [[hr]], 20);
      kit.cornice(b, creamM, hr, 19.2, { height: 0.8, projection: 0.4, steps: 2 });
    }
    const stuccoM = kit.paintedMaterial('paddington_station:stucco', 256, 256, (c, w, h) => {
      c.fillStyle = '#e6ddcb';
      c.fillRect(0, 0, w, h);
      const r = kit.rng(0.17);
      for (let k = 0; k < 900; k++) {
        c.fillStyle = `rgba(140,125,100,${r() * 0.06})`;
        c.fillRect(r() * w, r() * h, 3, 3);
      }
      c.fillStyle = 'rgba(150,135,110,0.25)';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 1.5); // faint ashlar lining
    });
    const rusticM = kit.paintedMaterial('paddington_station:rustic', 256, 256, (c, w, h) => {
      c.fillStyle = '#d9d0bd';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(105,95,80,0.65)';
      for (let y = 0; y < h; y += 32) c.fillRect(0, y, w, 4); // banded rustication
      for (let y = 0; y < h; y += 64) {
        c.fillRect(0, y, 3, 32);
        c.fillRect(w / 2, y + 32, 3, 32);
      }
    });
    const frameM = kit.mat('#f4efe4');
    const sashGlass = kit.mat('#27323a', { roughness: 0.15, metalness: 0.25 });
    const greenM = kit.mat('#2e3a33', { roughness: 0.5, metalness: 0.3 });
    // rendered wall block in local coords: rustic stone ground floor, stucco above
    const wallL = (u0, u1, v0, v1, z1, skip = []) => {
      const cs = [
        [u0, v0],
        [u1, v0],
        [u1, v1],
        [u0, v1],
      ].map(([u, v]) => W(u, v));
      for (let k = 0; k < 4; k++) {
        if (skip.includes(k)) continue;
        const p = cs[k],
          q = cs[(k + 1) % 4];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        quad(rusticM, p, q, 0, 5.4, len / 8, 0, 5.4 / 8);
        quad(stuccoM, p, q, 5.4, z1, len / 8, 5.4 / 8, z1 / 8);
      }
    };
    // storey scheme of the 4-storey front: sills, heights and heads
    const FLOORS = [
      { z: 0.9, h: 3.1, w: 1.7, head: 'arch', bars: 1 },
      { z: 6.3, h: 3.0, w: 1.35, head: 'pediment', bars: 2, surround: 0.16 },
      { z: 11.0, h: 2.7, w: 1.3, head: 'segment', bars: 2, surround: 0.14 },
      { z: 15.4, h: 2.3, w: 1.25, head: 'lintel', bars: 2 },
    ];
    const winOpts = (f, extra = {}) => ({
      width: f.w,
      height: f.h,
      head: f.head,
      bars: f.bars,
      surround: f.surround ?? 0,
      surroundMat: creamM,
      glass: sashGlass,
      frame: frameM,
      sill: creamM,
      depth: 0.16,
      ...extra,
    });
    // front face (u = const, outward -u): edge runs from high v to low v
    const frontRow = (u, va, vb, n, f, extra) =>
      rowL(
        [u, Math.max(va, vb)],
        [u, Math.min(va, vb)],
        f.z,
        winOpts(f, { count: n, margin: 0.2, ...extra }),
      );
    const UF = -48.1,
      UB = -31;
    // side ranges (7 bays each) and the centre (7 bays, 5-bay pedimented break)
    const C0 = -42.5,
      C1 = -21.2,
      UC = UF - 1.0,
      UP = UF - 1.8;
    const P0 = C0 + 3.05,
      P1 = C1 - 3.05;
    wallL(UF, UB, -63.7, C0, 21, [0, 1, 2]);
    wallL(UF, UB, C1, 0.2, 21, [0, 1, 2]);
    wallL(UC, UF, C0, C1, 21, [1]);
    wallL(UP, UC, P0, P1, 21, [1]);
    for (const f of FLOORS) {
      frontRow(UF, -63.7, C0, 7, f);
      frontRow(UF, C1, 0.2, 7, f);
      if (f.z > 1) {
        frontRow(UC, C0, P0, 1, f);
        frontRow(UC, P1, C1, 1, f);
        frontRow(UP, P0, P1, 5, f, f.head === 'pediment' ? { head: 'arch', height: 3.2 } : {});
      }
    }
    // centre ground floor: arcaded entrance with five doorways
    frontRow(UC, C0, P0, 1, FLOORS[0]);
    frontRow(UC, P1, C1, 1, FLOORS[0]);
    frontRow(UP, P0, P1, 5, { ...FLOORS[0], z: 0.15 }, { width: 2.0, height: 3.8, bars: 0 });
    // string courses, cornice with blocking course, plinth
    corniceL(UF, UB, -63.7, 0.2, 0, { height: 0.7, projection: 0.15 }, stoneM);
    corniceL(UF, UB, -63.7, 0.2, 5.4, { height: 0.45, projection: 0.25 });
    corniceL(UF, UB, -63.7, 0.2, 10.2, { height: 0.3, projection: 0.15 });
    corniceL(UF, UB, -63.7, 0.2, 19.6, { height: 1.2, projection: 0.75, steps: 3 });
    corniceL(UC, UB, C0, C1, 5.4, { height: 0.45, projection: 0.25 });
    corniceL(UC, UB, C0, C1, 19.6, { height: 1.2, projection: 0.75, steps: 3 });
    corniceL(UP, UC, P0, P1, 5.4, { height: 0.45, projection: 0.25 });
    corniceL(UP, UC, P0, P1, 19.6, { height: 1.2, projection: 0.75, steps: 3 });
    // pilasters between the bays of the centre break
    for (let k = 0; k <= 5; k++) {
      const v = P0 + ((P1 - P0) * k) / 5;
      box(UP - 0.2, v, 5.85, 0.4, 0.75, 13.75, creamM);
      box(UP - 0.3, v, 19.1, 0.6, 1.0, 0.5, creamM); // capital
    }
    // steep pavilion roof with pedimented dormers, chimneys and ridge cresting
    {
      const rr = [
        [UF, -63.7],
        [UB, -63.7],
        [UB, 0.2],
        [UF, 0.2],
      ].map(([u, v]) => W(u, v));
      kit.pitchedRoof(b, slateM, creamM, rr, A + Math.PI / 2, 21.0, 6.5, 'hipped', {
        overhang: 0.2,
      });
      const um = (UF + UB) / 2;
      beam(V3(um, -55, 27.55), V3(um, -8.5, 27.55), 0.12, 0.12, uDir, greenM);
      for (let v = -55; v <= -8.5; v += 1.5) box(um, v, 27.5, 0.08, 0.08, 0.7, greenM);
      for (const v of [-56, -47, -16, -7])
        for (const du of [-2.2, 2.2]) {
          box(um + du, v, 24.5, 1.1, 3.4, 4.4, stuccoM);
          box(um + du, v, 28.9, 1.4, 3.7, 0.3, creamM);
          for (let j = 0; j < 4; j++)
            box(um + du, v - 1.2 + j * 0.8, 29.2, 0.35, 0.35, 0.6, kit.mat('#a5583e'));
        }
      for (let v = -60.5; v <= -2; v += 3.05) {
        if (v > -40.5 && v < -23) continue;
        box(UF + 2.2, v, 21.2, 1.6, 1.8, 2.6, creamM);
        rowL([UF + 1.39, v + 0.6], [UF + 1.39, v - 0.6], 21.6, {
          count: 1,
          margin: 0,
          width: 0.9,
          height: 1.6,
          head: 'pediment',
          bars: 1,
          glass: sashGlass,
          frame: frameM,
          sill: creamM,
          depth: 0.12,
        });
        // small slate roof over the dormer cheeks
        const dg = new THREE.CylinderGeometry(1.15, 1.15, 1.7, 3)
          .rotateZ(Math.PI / 2)
          .rotateY(Math.PI / 2);
        add(dg, slateM, UF + 2.6, v, 24.2, Math.PI / 2);
      }
    }
    // 7-bay centre: attic storey, pediment with sculpture panel, porte-cochere
    {
      const v0 = C0,
        v1 = C1,
        u0 = UC;
      // attic storey over the centre with small square windows and a blocking course
      wallL(u0 + 0.3, UB - 4, v0 + 0.5, v1 - 0.5, 25.5);
      capLocal(
        slateM,
        [
          [u0 + 0.3, v0 + 0.5],
          [UB - 4, v0 + 0.5],
          [UB - 4, v1 - 0.5],
          [u0 + 0.3, v1 - 0.5],
        ],
        25.5,
      );
      rowL([u0 + 0.3, v1 - 0.5], [u0 + 0.3, v0 + 0.5], 22.5, {
        count: 7,
        margin: 0.6,
        width: 1.2,
        height: 1.6,
        head: 'none',
        bars: 1,
        glass: sashGlass,
        frame: frameM,
        sill: creamM,
      });
      corniceL(u0 + 0.3, UB - 4, v0 + 0.5, v1 - 0.5, 24.9, {
        height: 0.6,
        projection: 0.4,
        steps: 2,
      });
      // pediment (triangular prism) over the 5-bay break
      const pg = new THREE.BufferGeometry();
      const pw = (P1 - P0) / 2 + 0.6,
        ph = 4.2;
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
      add(pg, creamM, UP - 0.4, (P0 + P1) / 2, 20.8);
      // raking cornices of the pediment
      const pc = (P0 + P1) / 2;
      for (const sgn of [-1, 1])
        beam(
          V3(UP - 0.7, pc + sgn * (pw + 0.3), 20.75),
          V3(UP - 0.7, pc, 20.8 + ph + 0.35),
          0.7,
          0.45,
          uDir,
          creamM,
        );
      box(UP - 0.4, pc, 20.5, 1.4, 2 * pw + 0.8, 0.4, creamM);
      // sculpted tympanum (Peace, Plenty, Science, Industry by John Thomas) in relief
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
        const p = W(UP - 0.45, pc - pw + 1.0),
          q = W(UP - 0.45, pc + pw - 1.0);
        b.add(
          tym,
          [
            [q[0], q[1], 20.95],
            [p[0], p[1], 20.95],
            [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2, 20.95 + ph * 0.82],
          ],
          [
            [0, 0],
            [1, 0],
            [0.5, 1],
          ],
          [0, 1, 2],
        );
        for (let k = 0; k < 4; k++) {
          const fg = new THREE.SphereGeometry(0.5, 8, 6).scale(0.6, 0.6, 1.6);
          add(fg, stoneM, UP - 0.5, pc - 4.5 + k * 3, 21.6 + (k === 1 || k === 2 ? 0.9 : 0.2));
        }
      }
      // acroteria on the pediment
      for (const [dv, z] of [
        [-pw, 21.2],
        [pw, 21.2],
        [0, 20.8 + ph + 0.7],
      ])
        add(new THREE.SphereGeometry(0.35, 8, 6), creamM, UP - 0.5, pc + dv, z);
      // entrance canopy (glazed, on iron columns) over the pavement
      box(UP - 3.0, pc, 4.4, 5.0, 14, 0.5, greenM);
      box(UP - 3.0, pc, 4.9, 4.6, 13.6, 0.15, kit.mat('#b7c5cc', { roughness: 0.2 }));
      box(UP - 5.45, pc, 4.1, 0.12, 14, 0.4, kit.mat('gold'));
      for (const v of [pc - 6.5, pc - 2.2, pc + 2.2, pc + 6.5]) {
        box(UP - 5.2, v, 0, 0.25, 0.25, 4.4, greenM);
        add(
          new THREE.CylinderGeometry(0.28, 0.32, 0.4, 8).rotateX(Math.PI / 2),
          greenM,
          UP - 5.2,
          v,
          0.2,
        );
      }
      // steps up to the doors
      for (let k = 0; k < 3; k++)
        box(UP - 0.6 - k * 0.35, pc, k * 0.05, 0.6, 2 * pw - 1, 0.15 * (k + 1), stoneM);
    }
    // Projecting angle towers: 6 storeys, pierced parapet, ogee roofs with finials.
    const towers = [
      { u0: -53.35, u1: -40, v0: -74.35, v1: -63.7, out: 'v0' },
      { u0: -52.35, u1: -40, v0: 0.2, v1: 9.15, out: 'v1' },
    ];
    for (const t of towers) {
      const H = 28;
      wallL(t.u0, t.u1, t.v0, t.v1, H);
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
      // windows: 2 bays on Praed Street, 3 bays on the outer return
      const TF = [
        ...FLOORS,
        { z: 21.4, h: 2.1, w: 1.2, head: 'lintel', bars: 2 },
        { z: 24.9, h: 1.9, w: 1.1, head: 'arch', bars: 1 },
      ];
      for (const f of TF) {
        rowL([t.u0, t.v1], [t.u0, t.v0], f.z, winOpts(f, { count: 2, margin: 1.4 }));
        if (t.out === 'v0')
          rowL([t.u0, t.v0], [t.u1, t.v0], f.z, winOpts(f, { count: 3, margin: 1.2 }));
        else rowL([t.u1, t.v1], [t.u0, t.v1], f.z, winOpts(f, { count: 3, margin: 1.2 }));
      }
      // quoins at the tower corners
      for (const [qu, qv] of [
        [t.u0, t.v0],
        [t.u0, t.v1],
        [t.u1, t.v0],
        [t.u1, t.v1],
      ])
        for (let z = 5.8; z < H - 1; z += 1.2)
          box(
            qu,
            qv,
            z,
            ((z / 1.2) | 0) % 2 ? 1.3 : 0.9,
            ((z / 1.2) | 0) % 2 ? 0.9 : 1.3,
            0.55,
            creamM,
          );
      for (const [z, hgt, pr] of [
        [0, 0.7, 0.15],
        [5.4, 0.45, 0.25],
        [19.6, 1.0, 0.5],
        [H - 1.0, 1.0, 0.7],
      ])
        corniceL(
          t.u0,
          t.u1,
          t.v0,
          t.v1,
          z,
          { height: hgt, projection: pr, steps: hgt > 0.8 ? 2 : 1 },
          z === 0 ? stoneM : creamM,
        );
      // pierced parapet (balustrade) round the tower top
      kit.balustrade(
        b,
        creamM,
        [
          [t.u0 - 0.3, t.v0 - 0.3],
          [t.u1 + 0.3, t.v0 - 0.3],
          [t.u1 + 0.3, t.v1 + 0.3],
          [t.u0 - 0.3, t.v1 + 0.3],
          [t.u0 - 0.3, t.v0 - 0.3],
        ].map(([u, v]) => W(u, v)),
        H,
        { height: 1.1, spacing: 0.45 },
      );
      for (const [pu, pv] of [
        [t.u0 - 0.3, t.v0 - 0.3],
        [t.u1 + 0.3, t.v0 - 0.3],
        [t.u1 + 0.3, t.v1 + 0.3],
        [t.u0 - 0.3, t.v1 + 0.3],
      ]) {
        box(pu, pv, H, 0.7, 0.7, 1.5, creamM);
        add(new THREE.SphereGeometry(0.3, 8, 6), creamM, pu, pv, H + 1.8);
      }
      // ogee roof: square lathe (4 segments) scaled to the tower plan
      const pr = [];
      const R = 1,
        RH = 8;
      for (let k = 0; k <= 16; k++) {
        const t2 = k / 16;
        const r =
          R *
          (t2 < 0.5
            ? 1 - 0.25 * Math.sin(Math.PI * t2)
            : 0.75 * (1 - (t2 - 0.5) * 2) ** 1.6 + 0.02);
        pr.push(new THREE.Vector2(Math.max(0.02, r), t2 * RH));
      }
      const og = new THREE.LatheGeometry(pr, 4, Math.PI / 4).rotateX(Math.PI / 2);
      og.scale((du - 1.2) / Math.SQRT2, (dv - 1.2) / Math.SQRT2, 1);
      add(og, slateM, uc, vc, H + 0.2);
      // lucarne (oval dormer) on each face of the ogee roof
      for (const [ou, ov, rot] of [
        [t.u0 + 1.4, vc, 0],
        [t.u1 - 1.4, vc, Math.PI],
        [uc, t.v0 + 1.4, Math.PI / 2],
        [uc, t.v1 - 1.4, -Math.PI / 2],
      ]) {
        box(ou, ov, H + 1.2, rot % Math.PI ? 1.6 : 0.9, rot % Math.PI ? 0.9 : 1.6, 1.8, creamM);
        const og2 = new THREE.CylinderGeometry(0.55, 0.55, 0.95, 10, 1, false, 0, Math.PI).rotateZ(
          Math.PI / 2,
        );
        add(og2, creamM, ou, ov, H + 3.0, rot);
      }
      add(
        new THREE.CylinderGeometry(0.08, 0.2, 3, 6).rotateX(Math.PI / 2),
        greenM,
        uc,
        vc,
        H + RH + 1.3,
      );
      add(new THREE.SphereGeometry(0.35, 8, 6), kit.mat('gold'), uc, vc, H + RH + 0.4);
    }

    // paved forecourt / area between the hotel front and the Praed Street kerb
    capLocal(
      kit.mat('paving'),
      [
        [-54.6, -74.3],
        [UF, -74.3],
        [UF, 9.2],
        [-54.6, 9.2],
      ],
      0.05,
    );

    // ---------- Street furniture on Praed Street and Eastbourne Terrace ----------
    if (placeAssets) {
      const head = (du, dv) => {
        const Dx = du * ca - dv * sa,
          Dy = du * sa + dv * ca;
        return Math.atan2(-Dx, Dy);
      };
      const lamps = [];
      for (let v = -68; v <= 6; v += 13) lamps.push([...W(-58.2, v), head(-1, 0)]);
      for (let u = -20; u < 240; u += 22) lamps.push([...W(u, 18.6), head(0, 1)]);
      g.add(placeAssets('street_lamp', lamps, { name: 'paddington_station:lamps' }));
      const bollards = [];
      for (let v = -42; v <= -20; v += 1.8) bollards.push([...W(UP - 6.4, v), head(-1, 0)]);
      g.add(placeAssets('bollard', bollards, { name: 'paddington_station:bollards' }));
    }
    g.add(b.toGroup('paddington_station'));
    return g;
  },
};
