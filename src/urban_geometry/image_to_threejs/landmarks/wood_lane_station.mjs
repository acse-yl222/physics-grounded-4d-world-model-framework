// Wood Lane station (Hammersmith & City / Circle), Ian Ritchie Architects, 2008.
// A two-storey steel and glass building that wraps the 19th-century brick
// railway viaduct: a suspended 25 m glass screen facade to Wood Lane in front of
// the platforms, shot-peened stainless steel cladding, gold anodised aluminium
// ceiling / soffit panels and granite floors. The ticket hall sits beside the
// viaduct, whose brick arches are kept inside it; stairs and lifts rise either
// side of the arches to the two platforms on the viaduct.
export default {
  id: 'wood_lane_station',
  name: 'Wood Lane station',
  claims: ['e3f1fac8-65cb-4472-bf6b-f4423e2264cc'],
  references: [
    {
      title: 'Wood Lane Station - Ritchie Studio',
      url: 'https://www.ritchie.studio/projects/wood_lane_station/',
      used_for:
        'shot peened stainless steel cladding, gold anodised aluminium ceiling panels, granite flooring, site between owners around the brick viaduct',
    },
    {
      title: 'Wood Lane Station - e-architect',
      url: 'https://www.e-architect.co.uk/london/wood-lane-station',
      used_for:
        'two-storey steel and glass structure with a suspended 25 m glass screen facade to Wood Lane',
    },
    {
      title: 'Gold anodised aluminium at Wood Lane - John Desmond',
      url: 'https://www.johndesmond.com/case-studies/wood-lane/',
      used_for: 'gold anodised aluminium, stainless steel and mesh finishes',
    },
    {
      title: 'New Wood Lane Underground station opens - TfL',
      url: 'https://tfl.gov.uk/info-for/media/press-releases/2008/october/new-wood-lane-underground-station-opens',
      used_for:
        'opening October 2008, Westfield-funded; old viaduct arches incorporated into the stainless steel and glass ticket hall',
    },
    {
      title: 'Wood Lane tube station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Wood_Lane_tube_station',
      used_for:
        'two platforms; building encases the viaduct, platforms reached by stairs and lifts either side of the brick arches',
    },
  ],
  notes:
    'The viaduct is assumed to run north-south along the Wood Lane edge of the footprint (the rail layer has no H&C track here), so the glass screen fronts the platforms and the ticket hall fills the wedge to the east with its entrance on the south-east side facing White City Place. Height reduced from 17.4 m (OSM) to ~13 m. Arch rhythm, canopy depths, fin spacing and roundel positions are inferred from text descriptions; no photos could be viewed.',
  build({ THREE, kit, buildings, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();

    // ---------- materials ----------
    const steelTex = kit.paintedMaterial(
      'wood_lane:steel',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#b9bdbe';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.51);
        for (let k = 0; k < 2500; k++) {
          const v = r() > 0.5 ? 255 : 80;
          x.fillStyle = `rgba(${v},${v},${v},0.07)`;
          x.fillRect(r() * w, r() * h, 2, 2);
        }
        // Panel joints: 1.5 m x 1 m shot-peened panels (tile = 6 m x 4 m).
        x.fillStyle = '#8f9496';
        for (let k = 0; k < w; k += 64) x.fillRect(k, 0, 2, h);
        for (let k = 0; k < h; k += 64) x.fillRect(0, k, w, 2);
      },
      { metalness: 0.65, roughness: 0.38, side: THREE.DoubleSide },
    );
    const screenGlass = kit.mat('#8fb0bf', {
      roughness: 0.05,
      metalness: 0.2,
      transparent: true,
      opacity: 0.32,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const doorGlass = kit.mat('#3c5260', { roughness: 0.08, metalness: 0.3 });
    const gold = kit.mat('#cfa54f', {
      roughness: 0.35,
      metalness: 0.6,
      emissive: '#4a3712',
      side: THREE.DoubleSide,
    });
    const steel = kit.mat('#d5d9db', { roughness: 0.3, metalness: 0.7, side: THREE.DoubleSide });
    const dark = kit.mat('dark_steel', DS);
    const roofM = kit.mat('#aeb3b6', { roughness: 0.5, metalness: 0.4, side: THREE.DoubleSide });
    const granite = kit.mat('#5f5d5a', { roughness: 0.5, side: THREE.DoubleSide });
    const brick = kit.paintedMaterial(
      'wood_lane:viaduct',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#7a5a48';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.27);
        for (let row = 0; row < 32; row++)
          for (let k = (row % 2) * -8; k < w; k += 16) {
            const t = 0.8 + r() * 0.35;
            x.fillStyle = `rgb(${Math.round(128 * t)},${Math.round(72 * t)},${Math.round(52 * t)})`;
            x.fillRect(k + 1, row * 8 + 1, 14, 6);
          }
      },
      DS,
    );
    const archDark = kit.mat('#2a2320', DS);
    const ballast = kit.mat('#6e675e', { roughness: 1, side: THREE.DoubleSide });
    const platM = kit.mat('#a7a39b', DS);
    const yellow = kit.mat('#e2c02c', DS);

    // ---------- local frame ----------
    // u along the Wood Lane edge (south -> north), w into the building (east).
    const O = [-1660, 388];
    const ANG = 1.5852;
    const c = Math.cos(ANG),
      s = Math.sin(ANG);
    const L = (u, w, z = 0) => [O[0] + u * c + w * s, O[1] + u * s - w * c, z];
    const toL = ([x, y]) => [(x - O[0]) * c + (y - O[1]) * s, (x - O[0]) * s - (y - O[1]) * c];
    const LEN = 34.8;
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
    const wallQ = (m, a, b, z0, z1, su = 6, sv = 4) => {
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

    const VW = 10.6; // viaduct / platform zone width from the screen
    const HT = 13; // glass screen and platform roof
    const HH = 8.6; // ticket hall roof
    const DECK = 6.3,
      PLAT = 7.3;

    // ---------- walls ----------
    const edges = [];
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const la = toL(a),
        lb = toL(b);
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const front = Math.abs(la[1]) < 0.5 && Math.abs(lb[1]) < 0.5;
      const se = la[0] < 0 && lb[1] > 30; // south-east entrance front
      edges.push({ a, b, la, lb, len, front, se });
    }
    // Platform zone (w < VW) rises to HT; hall wedge beyond to HH.
    const zone = clip(ring, (p) => VW - toL(p)[1]);
    const hall = clip(ring, (p) => toL(p)[1] - VW);
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const edgesOf = (r) => r.map((a, k) => [a, r[(k + 1) % r.length]]);

    for (const [a, b] of edgesOf(ccw(zone))) {
      const la = toL(a),
        lb = toL(b);
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      if (Math.abs(la[1]) < 0.5 && Math.abs(lb[1]) < 0.5) continue; // screen, below
      if (Math.abs(la[1] - VW) < 0.05 && Math.abs(lb[1] - VW) < 0.05) {
        // Internal face above the hall roof: clerestory glazing to the platforms.
        wallQ(steelTex, a, b, HH, HT);
        kit.windowRow(batch, a, b, HH + 0.8, {
          glass: doorGlass,
          frame: steel,
          sill: steel,
          bay: 2,
          width: 1.8,
          height: HT - HH - 1.5,
          margin: 0.5,
          head: 'none',
          bars: 1,
        });
        continue;
      }
      wallQ(granite, a, b, 0, 0.5);
      wallQ(steelTex, a, b, 0.5, HT);
    }
    for (const [a, b] of edgesOf(ccw(hall))) {
      const la = toL(a),
        lb = toL(b);
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.05) continue;
      if (Math.abs(la[1] - VW) < 0.05 && Math.abs(lb[1] - VW) < 0.05) continue;
      const se = Math.abs(lb[1] - la[1]) > 2 && la[0] < lb[0] && la[1] < lb[1];
      wallQ(granite, a, b, 0, 0.5);
      if (se) {
        // Entrance front: full-height glazing between stainless piers.
        wallQ(steelTex, a, b, 5.6, HH);
        kit.windowRow(batch, a, b, 0.5, {
          glass: doorGlass,
          frame: steel,
          sill: steel,
          bay: 3,
          width: 2.6,
          height: 4.9,
          margin: 0.6,
          head: 'none',
          bars: 1,
          depth: 0.16,
        });
        const f = Math.atan2(b[1] - a[1], b[0] - a[0]);
        for (let t = 0; t <= len; t += 3) {
          const p = [a[0] + Math.cos(f) * t, a[1] + Math.sin(f) * t];
          kit.box(batch, steelTex, p[0], p[1], 0.5, 0.4, 0.5, 5.1, f);
        }
        wallQ(steelTex, a, b, 0.5, 0.6);
        // Gold-soffit canopy over the entrance.
        const nx = Math.sin(f),
          ny = -Math.cos(f);
        const cp = ccw([
          [a[0] - Math.cos(f) * 0.5, a[1] - Math.sin(f) * 0.5],
          [b[0] + Math.cos(f) * 0.5, b[1] + Math.sin(f) * 0.5],
          [b[0] + Math.cos(f) * 0.5 + nx * 3.6, b[1] + Math.sin(f) * 0.5 + ny * 3.6],
          [a[0] - Math.cos(f) * 0.5 + nx * 3.6, a[1] - Math.sin(f) * 0.5 + ny * 3.6],
        ]);
        kit.cap(batch, roofM, [[cp]], 6.15);
        kit.cap(batch, gold, [[cp]], 5.6, { down: true });
        kit.walls(batch, steel, [[cp]], 5.6, 6.15, { bay: 1e6 });
        // Roundel + name board on the canopy fascia.
        const mid = [(a[0] + b[0]) / 2 + nx * 3.65, (a[1] + b[1]) / 2 + ny * 3.65];
        roundelAt(mid[0], mid[1], 6.4, f, 2.4);
        continue;
      }
      wallQ(steelTex, a, b, 0.5, HH);
      // North-east flank: horizontal louvre band.
      if (len > 8)
        kit.windowRow(batch, a, b, 5.0, {
          glass: dark,
          frame: steel,
          sill: steel,
          bay: 1.5,
          width: 1.3,
          height: 1.6,
          margin: 1.5,
          head: 'none',
          bars: 3,
          depth: 0.1,
        });
    }
    // Roofs.
    kit.cap(batch, roofM, [[ccw(hall)]], HH, { scale: 4 });
    kit.cornice(batch, steel, ccw(hall), HH - 0.4, { height: 0.5, projection: 0.15 });
    // Glazed rooflight strip over the hall stairs along the long diagonal.
    {
      const p0 = L(2, 16),
        p1 = L(16, 28);
      const f = Math.atan2(p1[1] - p0[1], p1[0] - p0[0]);
      const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
      const cx = (p0[0] + p1[0]) / 2,
        cy = (p0[1] + p1[1]) / 2;
      kit.box(batch, steel, cx, cy, HH, len + 0.5, 3.1, 0.3, f);
      for (const sg of [-1, 1]) {
        const geo = new THREE.BoxGeometry(len, 1.6, 0.04);
        const m = new THREE.Matrix4().makeRotationZ(f);
        m.multiply(new THREE.Matrix4().makeRotationX(sg * 0.5));
        m.setPosition(cx - Math.sin(f) * sg * 0.7, cy + Math.cos(f) * sg * 0.7, HH + 0.7);
        batch.addGeometry(kit.mat('glass'), geo, m);
        geo.dispose();
      }
      for (let t = 0; t <= len; t += 1.6) {
        const p = [p0[0] + Math.cos(f) * t, p0[1] + Math.sin(f) * t];
        kit.box(batch, dark, p[0], p[1], HH + 0.3, 0.06, 3.0, 0.9, f);
      }
    }

    // ---------- the viaduct, tracks and platforms (inside the screen) ----------
    const vz = clip(
      clip(ring, (p) => toL(p)[1] - 0.6),
      (p) => VW - 0.2 - toL(p)[1],
    );
    {
      const vr = ccw(kit.offsetRing(ccw(vz), -0.3));
      // Viaduct body.
      for (const [a, b] of edgesOf(vr)) wallQ(brick, a, b, 0, DECK, 4, 4);
      kit.cap(batch, ballast, [[vr]], DECK, { scale: 3 });
      // Brick arches on the hall side (east face of the viaduct).
      const aE = L(-1, VW - 0.2),
        bE = L(LEN * 0.8, VW - 0.2);
      // windowRow on b -> a so the recesses face the hall (+w).
      kit.windowRow(batch, [bE[0], bE[1]], [aE[0], aE[1]], 0, {
        glass: archDark,
        frame: brick,
        sill: brick,
        bay: 5.2,
        width: 3.8,
        height: 3.2,
        margin: 1.2,
        head: 'arch',
        bars: 0,
        depth: 0.3,
      });
      // Arches on the screen side too (seen through the glass).
      const aW = L(0.5, 0.35),
        bW = L(LEN - 0.5, 0.35);
      kit.windowRow(batch, [aW[0], aW[1]], [bW[0], bW[1]], 0, {
        glass: archDark,
        frame: brick,
        sill: brick,
        bay: 5.2,
        width: 3.8,
        height: 3.2,
        margin: 1.2,
        head: 'arch',
        bars: 0,
        depth: 0.3,
      });
      kit.cornice(batch, brick, vr, DECK - 0.5, { height: 0.5, projection: 0.15 });
      // Platforms: west (against the screen) and east, track bed between.
      const strip = (w0, w1) =>
        ccw(
          clip(
            clip(vr, (p) => toL(p)[1] - w0),
            (p) => w1 - toL(p)[1],
          ),
        );
      for (const [w0, w1] of [
        [0.6, 3.4],
        [7.2, VW - 0.2],
      ]) {
        const pr = strip(w0, w1);
        if (pr.length < 3) continue;
        kit.cap(batch, platM, [[pr]], PLAT, { scale: 2 });
        for (const [a, b] of edgesOf(pr)) wallQ(platM, a, b, DECK, PLAT, 2, 2);
        // Yellow safety line along the platform edge.
        const we = w0 < 2 ? w1 - 0.5 : w0 + 0.5;
        const p0 = L(1, we, PLAT + 0.01),
          p1 = L(we > 5 ? LEN * 0.72 : LEN - 1, we, PLAT + 0.01);
        kit.box(
          batch,
          yellow,
          (p0[0] + p1[0]) / 2,
          (p0[1] + p1[1]) / 2,
          PLAT,
          Math.hypot(p1[0] - p0[0], p1[1] - p0[1]),
          0.12,
          0.02,
          ANG,
        );
      }
      // Rails (two tracks).
      for (const wr of [4.0, 5.5, 6.0, 7.5].map((v, i) => v - (i % 2 ? 0 : 0))) {
        const p0 = L(-6, wr),
          p1 = L(LEN * 0.75, wr);
        kit.box(
          batch,
          steel,
          (p0[0] + p1[0]) / 2,
          (p0[1] + p1[1]) / 2,
          DECK,
          Math.hypot(p1[0] - p0[0], p1[1] - p0[1]),
          0.08,
          0.17,
          ANG,
        );
      }
      // Platform furniture: benches, signs, roof columns.
      for (let u = 3; u < LEN - 2; u += 6.5) {
        for (const wc of [2.0, 8.8]) {
          if (wc > 5 && u > LEN * 0.68) continue;
          const p = L(u, wc);
          kit.box(batch, dark, p[0], p[1], PLAT, 0.22, 0.22, HT - PLAT, ANG);
        }
      }
    }

    // ---------- glass screen facade to Wood Lane ----------
    {
      const front = edges.find((e) => e.front);
      const { a, b, len } = front;
      const f = Math.atan2(b[1] - a[1], b[0] - a[0]);
      wallQ(granite, a, b, 0, 0.5);
      wallQ(screenGlass, a, b, 0.5, HT);
      const nx = Math.sin(f),
        ny = -Math.cos(f); // outward (west)
      // Vertical glass fins / steel mullions every 1.8 m, transoms every 2.5 m.
      const nf = Math.round(len / 1.8);
      for (let i = 0; i <= nf; i++) {
        const t = (len * i) / nf;
        const p = [a[0] + Math.cos(f) * t - nx * 0.25, a[1] + Math.sin(f) * t - ny * 0.25];
        kit.box(batch, steel, p[0], p[1], 0.5, 0.06, 0.5, HT - 0.5, f);
      }
      for (let z = 0.5; z <= HT; z += 2.5) {
        const m = [(a[0] + b[0]) / 2 + nx * 0.02, (a[1] + b[1]) / 2 + ny * 0.02];
        kit.box(batch, steel, m[0], m[1], z - 0.04, len, 0.06, 0.08, f);
        // Spider fixings at the panel corners.
        for (let i = 0; i <= nf; i += 1) {
          const t = (len * i) / nf;
          const p = [a[0] + Math.cos(f) * t + nx * 0.04, a[1] + Math.sin(f) * t + ny * 0.04];
          kit.box(batch, steel, p[0], p[1], z - 0.15, 0.3, 0.05, 0.3, f);
        }
      }
      // Big roundel high on the screen facing Wood Lane.
      const rp = [
        a[0] + Math.cos(f) * len * 0.35 + nx * 0.35,
        a[1] + Math.sin(f) * len * 0.35 + ny * 0.35,
      ];
      roundelAt(rp[0], rp[1], 8.2, f, 3.4);
    }

    // ---------- platform roof: thin steel deck oversailing the screen ----------
    {
      const big = clip(ccw(kit.offsetRing(ccw(zone), 0.2)), (p) => VW + 0.2 - toL(p)[1]);
      const roof = ccw(big);
      // Extend 1.8 m over Wood Lane.
      const ext = roof.map((p) => {
        const l = toL(p);
        return l[1] < 0.5 ? L(l[0], l[1] - 1.8).slice(0, 2) : p;
      });
      const r2 = ccw(ext);
      kit.cap(batch, roofM, [[r2]], HT + 0.7, { scale: 4 });
      kit.cap(batch, gold, [[r2]], HT, { down: true });
      kit.walls(batch, steel, [[r2]], HT, HT + 0.7, { bay: 1e6 });
      // Roof ribs.
      for (let u = 1; u < LEN; u += 3) {
        const wmax = Math.min(VW - 0.2, ((LEN - u) * 25.5) / 18.4 - 0.4);
        const p0 = L(u, -1.6),
          p1 = L(u, wmax);
        kit.box(
          batch,
          steel,
          (p0[0] + p1[0]) / 2,
          (p0[1] + p1[1]) / 2,
          HT + 0.7,
          0.12,
          wmax + 1.6,
          0.12,
          ANG,
        );
      }
    }

    // ---------- signage ----------
    function roundelAt(x, y, z, faceAng, d) {
      // Disc facing the outward normal of a wall running along faceAng.
      const geo = new THREE.CylinderGeometry(d / 2, d / 2, 0.08, 28).rotateY(Math.PI / 2);
      const m = new THREE.Matrix4().makeRotationZ(faceAng);
      m.multiply(new THREE.Matrix4().makeRotationX(0));
      m.setPosition(x, y, z + d / 2);
      batch.addGeometry(roundelMat(), geo, m);
      geo.dispose();
    }
    function roundelMat() {
      return kit.paintedMaterial(
        'wood_lane:roundel',
        256,
        256,
        (x, w, h) => {
          x.fillStyle = '#ffffff';
          x.fillRect(0, 0, w, h);
          x.strokeStyle = '#dc241f';
          x.lineWidth = 40;
          x.beginPath();
          x.arc(w / 2, h / 2, 90, 0, Math.PI * 2);
          x.stroke();
          x.fillStyle = '#0019a8';
          x.fillRect(10, h / 2 - 26, w - 20, 52);
          x.fillStyle = '#ffffff';
          x.font = 'bold 34px sans-serif';
          x.textAlign = 'center';
          x.textBaseline = 'middle';
          x.fillText('WOOD LANE', w / 2, h / 2 + 2);
        },
        DS,
      );
    }

    // ---------- forecourt ----------
    const se = edges.find((e) => e.se) ?? edges[1];
    {
      const f = Math.atan2(se.b[1] - se.a[1], se.b[0] - se.a[0]);
      const nx = Math.sin(f),
        ny = -Math.cos(f);
      const bol = [],
        bikes = [];
      for (let t = 2; t < se.len - 1; t += 2.4) {
        const p = [se.a[0] + Math.cos(f) * t + nx * 5.2, se.a[1] + Math.sin(f) * t + ny * 5.2];
        bol.push([p[0], p[1], f]);
      }
      for (let t = 4; t < 14; t += 1.2) {
        const p = [se.a[0] + Math.cos(f) * t + nx * 7.5, se.a[1] + Math.sin(f) * t + ny * 7.5];
        bikes.push([p[0], p[1], f + Math.PI / 2]);
      }
      g.add(placeAssets('bollard', bol));
      g.add(placeAssets('bicycle_stand', bikes));
    }

    g.add(batch.toGroup('wood_lane_station'));
    return g;
  },
};
