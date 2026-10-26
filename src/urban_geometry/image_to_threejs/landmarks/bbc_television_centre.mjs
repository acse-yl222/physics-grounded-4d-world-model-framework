// BBC Television Centre, Wood Lane, White City (Graham Dawbarn / Norman & Dawbarn,
// opened 1960; Grade II 2009; converted 2013-2018 by AHMM, Maccreanor Lavington,
// Duggan Morris, drmm and others). The "question mark" main block is an
// eight-storey drum around the circular Helios Courtyard, whose lower walls are
// faced in sea-green mosaic with a stepped pattern picked out in red; at the
// centre the 3 m gilded Helios (T. B. Huxley-Jones, 1960) on a tall column over
// a raised fountain bowl with the reclining figures of Sound and Vision. A glazed
// full-height stair tower stands proud of the drum; the studio ring (TC1-TC3,
// BBC Studioworks) wraps it, Studio 1 fronted by a blind brick wall with 26 white
// "atomic" discs. The Rotunda (Endo) crowns the north side; 2 Television Centre
// (AHMM offices) and The Crescent residential range complete the site.
export default {
  id: 'bbc_television_centre',
  name: 'BBC Television Centre',
  claims: [
    'ce7e9a82-4a6e-4a89-83be-731f0979dadd', // The Helios Courtyard (main drum)
    '9bcde68a-4dad-4732-a9dd-f58c0c2ce473', // Endo at the Rotunda
    '141f12da-152d-4b90-b12d-c4dcde5e7710', // TC1
    '14dc4fae-9f26-4c16-8b94-51eedd6b1aee', // TC2
    '5349aecc-0f9b-4b10-81fc-64e8aa470aba', // TC3
    'bb7c2a95-2aca-4a2e-bf90-388606f5aa25', // BBC Studioworks (studio ring)
    '57b2711d-3c29-4489-872e-76d314cdb46e', // 2 Television Centre
    'c685cd6f-495b-41fe-8288-45cb604f2647', // The Crescent
  ],
  references: [
    {
      title: 'BBC Television Centre listing - British Listed Buildings (Historic England)',
      url: 'https://britishlistedbuildings.co.uk/101393371-bbc-television-centre-including-the-main-circular-range-excluding-the-spur-the-original-scenery-block-and-the-former-canteen-shepherds-bush-green-ward',
      used_for:
        'eight-storey drum, sea-green mosaic with red stepped pattern in the courtyard, glazed full-height stair tower, Studio 1 blind brick wall with 26 white discs; Helios a gilded figure on a slightly tapered column rising through a shallow bowl set on four legs',
    },
    {
      title: 'Helios (statue) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Helios_(statue)',
      used_for: '3 m gilded bronze Helios by Huxley-Jones on the central column',
    },
    {
      title: 'Television Centre - RIBA London Award 2019 (riba.org)',
      url: 'https://www.riba.org/explore/awards/uk-awards/regional-awards/2019/london/television-centre/',
      used_for:
        'circular mosaic-lined Helios Courtyard; refurbished 3 m gilded bronze Helios on a tall column with a water feature',
    },
    {
      title: 'Former BBC Television Centre - Heidelberg Materials',
      url: 'https://www.heidelbergmaterials.com/en/bbc',
      used_for:
        'fountain bowl and obelisk recreated in self-compacting concrete; obelisk an 11 m slender tapering form',
    },
    {
      title: 'Helios Returned to Courtyard at Television Centre',
      url: 'https://new.actonw3.com/page/shared/common/bbc1702.htm',
      used_for: 'fountain bowl with two reclining figures representing sound and vision',
    },
    {
      title: "Television Centre, Shepherd's Bush - manchesterhistory.net",
      url: 'https://manchesterhistory.net/architecture/1960/bbctv.html',
      used_for: 'Dawbarn question-mark plan curling round the inner courtyard',
    },
    {
      title: 'Television Centre - RIBA London Award 2019',
      url: 'https://ribaj.com/buildings/regional-awards-2019-television-centre-ahmm-maccreanor-lavington-morris-drmm-mikhail-riches-piercy-haptic-archer-humphreys-coffey-architects-stanhop-mitsui-fudosan-aimco-bbc-studioworks-homes-refurbishment',
      used_for: 'redevelopment team; Helios, Piper murals and Studio 1 atomic dots retained',
    },
    {
      title: 'Television Centre - The Spaces',
      url: 'https://thespaces.com/londons-television-centre-emerges-from-a-1bn-revamp/',
      used_for: 'AHMM restored the green mosaics, fin walls and sweeping staircases',
    },
    {
      title: 'Television Centre 2TVC - SCP',
      url: 'https://professional.scp.co.uk/?p=191483',
      used_for: '2 Television Centre as the new office building',
    },
  ],
  notes:
    'Massing follows the Overture footprints and heights. The outer drum elevation (cream slab bands and mullions, pale blue mosaic spandrels, ribbon glazing), the courtyard curtain walling, the 2TVC fin facade and the Crescent window rhythm are inferred from descriptions, not traced from photos; window and fin pitches are generic. Helios follows the listing (gilded figure on a slightly tapered column rising through a shallow bowl on four legs, ~11 m obelisk) with simplified anatomy; Sound and Vision are stand-in reclining forms. The 26 Studio 1 discs are placed in a stylised scatter. The question-mark tail (spur) and the newer residential blocks to the south/east are left to the generic layer.',
  build({ THREE, kit, byId, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const B = (id) => byId[id];
    const drum = B('ce7e9a82-4a6e-4a89-83be-731f0979dadd');
    const outer = drum.polys[0][0],
      inner = drum.polys[0][1];
    // Courtyard centre.
    let cx = 0,
      cy = 0;
    for (const p of inner) {
      cx += p[0] / inner.length;
      cy += p[1] / inner.length;
    }
    // Distance from the courtyard centre to the outer drum wall along a bearing.
    const rayR = (t) => {
      const dx = Math.cos(t),
        dy = Math.sin(t);
      let best = 0;
      for (let k = 0; k < outer.length; k++) {
        const a = outer[k],
          b = outer[(k + 1) % outer.length];
        const ex = b[0] - a[0],
          ey = b[1] - a[1];
        const den = dx * ey - dy * ex;
        if (Math.abs(den) < 1e-9) continue;
        const ax = a[0] - cx,
          ay = a[1] - cy;
        const r = (ax * ey - ay * ex) / den,
          u = (ax * dy - ay * dx) / den;
        if (r > 0 && u >= 0 && u <= 1 && (best === 0 || r < best)) best = r;
      }
      return best;
    };
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
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
            ux: len ? (b[0] - a[0]) / len : 0,
            uy: len ? (b[1] - a[1]) / len : 0,
            nx: len ? (b[1] - a[1]) / len : 0,
            ny: len ? -(b[0] - a[0]) / len : 0,
          };
        })
        .filter((e) => e.len > 0.05);
    const wallQ = (m, a, b, z0, z1, su = 4, sv = 4, u0 = 0) => {
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      batch.quad(
        m,
        [a[0], a[1], z0],
        [b[0], b[1], z0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [u0 / su, z0 / sv],
        [(u0 + len) / su, z0 / sv],
        [(u0 + len) / su, z1 / sv],
        [u0 / su, z1 / sv],
      );
    };
    // Projecting band (slab edge) along a ring of any orientation: outer face,
    // top and soffit as plain quads (offset towards the right of each edge).
    const band = (m, r, z, h, p) => {
      const o = kit.offsetRing(r, p);
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length],
          A = o[k],
          Bq = o[(k + 1) % r.length];
        batch.quad(
          m,
          [A[0], A[1], z],
          [Bq[0], Bq[1], z],
          [Bq[0], Bq[1], z + h],
          [A[0], A[1], z + h],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.quad(
          m,
          [a[0], a[1], z + h],
          [A[0], A[1], z + h],
          [Bq[0], Bq[1], z + h],
          [b[0], b[1], z + h],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        batch.quad(
          m,
          [a[0], a[1], z],
          [b[0], b[1], z],
          [Bq[0], Bq[1], z],
          [A[0], A[1], z],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
    };
    // Mullions every `pitch` metres along each edge (outward offset `off`).
    const mullions = (m, r, z, h, pitch, off = 0.06, w = 0.08, d = 0.14) => {
      for (const e of edgesOf(r)) {
        const n = Math.max(1, Math.round(e.len / pitch));
        for (let i = 0; i < n; i++) {
          const t = (e.len * i) / n;
          kit.box(
            batch,
            m,
            e.a[0] + e.ux * t + e.nx * off,
            e.a[1] + e.uy * t + e.ny * off,
            z,
            w,
            d,
            h,
            e.f,
          );
        }
      }
    };
    // Ribbon-window storeys: spandrel, glazing, mullions and slab-edge band.
    const ribbon = (
      r,
      z0,
      storeys,
      st,
      { spandrel, glass, mull, slab, sp = 0.95, pitch = 1.6, proj = 0.22 },
    ) => {
      for (const e of edgesOf(r)) {
        for (let s = 0; s < storeys; s++) {
          const z = z0 + s * st;
          wallQ(spandrel, e.a, e.b, z, z + sp, 2, 2);
          wallQ(glass, e.a, e.b, z + sp, z + st, 3, st);
        }
      }
      for (let s = 0; s < storeys; s++) {
        const z = z0 + s * st;
        mullions(mull, r, z + sp, st - sp - 0.02, pitch);
        band(slab, r, z + sp - 0.12, 0.12, 0.08); // sill
        band(slab, r, z, 0.24, proj); // floor slab edge
      }
    };

    // ---------- materials ----------
    const mosaicBlue = kit.paintedMaterial(
      'tvc:spandrel',
      128,
      128,
      (x, w, h) => {
        x.fillStyle = '#8fb3c8';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.81);
        for (let i = 0; i < w; i += 8)
          for (let j = 0; j < h; j += 8) {
            const t = 0.9 + r() * 0.18;
            x.fillStyle = `rgb(${Math.round(143 * t)},${Math.round(179 * t)},${Math.round(200 * t)})`;
            x.fillRect(i + 1, j + 1, 7, 7);
          }
      },
      DS,
    );
    const mosaic = kit.paintedMaterial(
      'tvc:mosaic',
      512,
      128,
      (x, w, h) => {
        x.fillStyle = '#4f9a87';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(255,255,255,0.12)';
        for (let k = 0; k < w; k += 5) x.fillRect(k, 0, 1, h);
        for (let k = 0; k < h; k += 5) x.fillRect(0, k, w, 1);
        // Stepped pattern picked out in red tiles.
        x.fillStyle = '#b3423a';
        for (let k = 0; k < w; k += 128)
          for (let st = 0; st < 5; st++) x.fillRect(k + st * 16, 96 - st * 16, 18, 6);
      },
      DS,
    );
    const brick = kit.paintedMaterial(
      'tvc:studio_brick',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#93583f';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(240,220,200,0.15)';
        for (let r = 0; r < h; r += 4) x.fillRect(0, r, w, 1);
        x.fillStyle = 'rgba(0,0,0,0.06)';
        for (let r = 0; r < h; r += 8)
          for (let k = (r / 8) % 2 ? 0 : 6; k < w; k += 12) x.fillRect(k, r, 1, 4);
      },
      DS,
    );
    const stock = kit.paintedMaterial(
      'tvc:crescent_brick',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#b9a989';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.17);
        for (let row = 0; row < 32; row++)
          for (let k = (row % 2) * -8; k < w; k += 16) {
            const t = 0.85 + r() * 0.25;
            x.fillStyle = `rgb(${Math.round(176 * t)},${Math.round(156 * t)},${Math.round(120 * t)})`;
            x.fillRect(k + 1, row * 8 + 1, 14, 6);
          }
      },
      DS,
    );
    const cream = kit.mat('#ece6d6', { roughness: 0.6, side: THREE.DoubleSide });
    const concrete = kit.mat('#d8d3c6', DS);
    const roofM = kit.roof('flat', 0);
    const gold = kit.mat('gold', DS);
    const bronzeM = kit.mat('bronze', DS);
    const glassM = kit.mat('#34444f', { roughness: 0.12, metalness: 0.35, side: THREE.DoubleSide });
    const glassL = kit.mat('#4b6574', { roughness: 0.1, metalness: 0.3, side: THREE.DoubleSide });
    const dark = kit.mat('dark_steel', DS);
    const alu = kit.mat('#c9cdcf', { roughness: 0.35, metalness: 0.6, side: THREE.DoubleSide });
    const plant = kit.mat('#8d9396', DS);
    const water = kit.mat('water', DS);
    const paving = kit.paintedMaterial(
      'tvc:court_paving',
      512,
      512,
      (x, w, h) => {
        x.fillStyle = '#cfc8b8';
        x.fillRect(0, 0, w, h);
        x.strokeStyle = 'rgba(90,80,70,0.25)';
        x.lineWidth = 2;
        for (let r = 20; r < w / 2; r += 22) {
          x.beginPath();
          x.arc(w / 2, h / 2, r, 0, Math.PI * 2);
          x.stroke();
        }
        for (let k = 0; k < 48; k++) {
          const t = (k / 48) * Math.PI * 2;
          x.beginPath();
          x.moveTo(w / 2 + Math.cos(t) * 60, h / 2 + Math.sin(t) * 60);
          x.lineTo(w / 2 + Math.cos(t) * w, h / 2 + Math.sin(t) * w);
          x.stroke();
        }
      },
      DS,
    );

    // ---------- main drum ----------
    const H = drum.h; // 27 m, eight storeys
    const st = H / 8;
    const setback = kit.offsetRing(outer, -1.5);
    // Outer face: ground floor glazed behind a plinth, seven ribbon storeys.
    for (const e of edgesOf(outer)) {
      wallQ(concrete, e.a, e.b, 0, 0.5);
      wallQ(glassL, e.a, e.b, 0.5, st);
    }
    mullions(dark, outer, 0.5, st - 0.5, 2.4, 0.06, 0.12, 0.12);
    ribbon(outer, st, 6, st, { spandrel: mosaicBlue, glass: glassM, mull: cream, slab: cream });
    band(cream, outer, H - st - 0.1, 1.0, 0.3); // parapet / balcony edge of the set-back storey
    // Set-back top storey on the outer face.
    for (const e of edgesOf(setback)) wallQ(glassM, e.a, e.b, H - st, H, 3, st);
    mullions(cream, setback, H - st, st, 1.6);
    kit.cap(batch, concrete, [[outer, setback.slice().reverse()]], H - st + 0.9);
    // Courtyard face (CW hole: right of each edge faces into the courtyard):
    // green mosaic lower level, curtain walling above.
    for (const e of edgesOf(inner)) {
      wallQ(mosaic, e.a, e.b, 0, 4.2, 4.2, 2.1);
      for (let s = 0; s < 7; s++) {
        const z = 4.2 + s * ((H - 4.2) / 7);
        wallQ(glassM, e.a, e.b, z, z + (H - 4.2) / 7, 3, 3);
      }
    }
    {
      const cst = (H - 4.2) / 7;
      for (let s = 0; s < 7; s++) {
        const z = 4.2 + s * cst;
        mullions(cream, inner, z, cst, 1.5, 0.08, 0.1, 0.2);
        band(cream, inner, z, 0.3, 0.3);
        band(cream, inner, z + 1.0, 0.08, 0.1); // transom
      }
      band(cream, inner, H, 0.9, 0.2); // parapet
    }
    kit.cap(batch, roofM, [[setback, inner]], H, { scale: 6 });
    band(cream, setback, H, 0.9, 0.2);
    // Rooftop plant on the drum roof.
    {
      const rnd = kit.rng(0.913);
      for (let k = 0; k < 14; k++) {
        const t = (k / 14) * Math.PI * 2 + rnd() * 0.2;
        const R0 = rayR(t);
        const rr = (R0 + 23) / 2;
        const x = cx + Math.cos(t) * rr,
          y = cy + Math.sin(t) * rr;
        kit.box(batch, plant, x, y, H, 3 + rnd() * 3, 2 + rnd() * 2, 1.4 + rnd() * 1.5, t);
      }
    }
    // Courtyard paving, Helios fountain.
    {
      const pr = inner.slice().reverse(); // CCW
      batch.add(
        paving,
        pr.map((p) => [p[0], p[1], 0.12]),
        pr.map((p) => [(p[0] - cx) / 46 + 0.5, (p[1] - cy) / 46 + 0.5]),
        THREE.ShapeUtils.triangulateShape(
          pr.map((p) => new THREE.Vector2(p[0], p[1])),
          [],
        ).flat(),
      );
    }
    const addG = (geo, m, x, y, z, rx = Math.PI / 2) => {
      if (rx) geo.rotateX(rx);
      batch.addGeometry(m, geo, new THREE.Matrix4().makeTranslation(x, y, z));
      geo.dispose();
    };
    {
      // Raised circular pool with mosaic kerb and stone coping.
      addG(new THREE.CylinderGeometry(7.5, 7.5, 0.7, 48, 1, true), mosaic, cx, cy, 0.47);
      addG(new THREE.CylinderGeometry(7.1, 7.1, 0.7, 48, 1, true), mosaic, cx, cy, 0.47);
      addG(new THREE.TorusGeometry(7.3, 0.25, 4, 48), concrete, cx, cy, 0.82, 0);
      addG(new THREE.CylinderGeometry(7.1, 7.1, 0.05, 48), water, cx, cy, 0.55);
      // Shallow bowl on four legs, the column rising through it.
      for (let k = 0; k < 4; k++) {
        const t = (k * Math.PI) / 2 + Math.PI / 4;
        const leg = new THREE.CylinderGeometry(0.12, 0.2, 2.3, 8);
        leg.rotateX(Math.PI / 2);
        const m = new THREE.Matrix4().makeTranslation(
          cx + Math.cos(t) * 1.7,
          cy + Math.sin(t) * 1.7,
          1.7,
        );
        m.multiply(
          new THREE.Matrix4().makeRotationAxis(
            new THREE.Vector3(-Math.sin(t), Math.cos(t), 0),
            -0.18,
          ),
        );
        batch.addGeometry(concrete, leg, m);
        leg.dispose();
      }
      g.add(
        kit.lathe(
          concrete,
          [
            [0.6, 2.75],
            [2.0, 2.85],
            [3.1, 3.15],
            [3.6, 3.5],
            [3.45, 3.55],
            [2.9, 3.3],
            [1.9, 3.05],
            [0.6, 3.0],
          ],
          { x: cx, y: cy, z: 0, segments: 40 },
        ),
      );
      addG(new THREE.CylinderGeometry(3.25, 3.25, 0.04, 40), water, cx, cy, 3.3);
      // Slightly tapered column (~11 m obelisk) and the gilded Helios.
      addG(new THREE.CylinderGeometry(0.32, 0.55, 10.4, 16), concrete, cx, cy, 0.6 + 5.2);
      addG(new THREE.CylinderGeometry(0.55, 0.38, 0.35, 16), concrete, cx, cy, 11.15);
      const z0 = 11.35;
      const limb = (m, x0, y0, z0_, x1, y1, z1_, r0, r1) => {
        const dir = new THREE.Vector3(x1 - x0, y1 - y0, z1_ - z0_);
        const len = dir.length();
        const geo = new THREE.CylinderGeometry(r1, r0, len, 10);
        const mm = new THREE.Matrix4().makeRotationFromQuaternion(
          new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize()),
        );
        mm.setPosition((x0 + x1) / 2, (y0 + y1) / 2, (z0_ + z1_) / 2);
        batch.addGeometry(m, geo, mm);
        geo.dispose();
      };
      // Figure faces the main entrance (north-east).
      const fa = 0.6,
        fx = Math.cos(fa),
        fy = Math.sin(fa),
        sx = -fy,
        sy = fx;
      const P = (s, f, z) => [cx + sx * s + fx * f, cy + sy * s + fy * f, z];
      for (const sg of [-1, 1]) {
        const hip = P(sg * 0.16, 0, z0 + 1.35),
          knee = P(sg * 0.2, 0.08, z0 + 0.7),
          foot = P(sg * 0.18, 0, z0);
        limb(gold, ...foot, ...knee, 0.09, 0.12);
        limb(gold, ...knee, ...hip, 0.12, 0.16);
        // Arms raised to the sky.
        const sh = P(sg * 0.33, 0, z0 + 2.35),
          el = P(sg * 0.62, 0.05, z0 + 2.85),
          hand = P(sg * 0.8, 0.1, z0 + 3.35);
        limb(gold, ...sh, ...el, 0.09, 0.08);
        limb(gold, ...el, ...hand, 0.08, 0.06);
        addG(new THREE.SphereGeometry(0.08, 8, 6), gold, ...hand);
      }
      g.add(
        kit.lathe(
          gold,
          [
            [0.01, 1.3],
            [0.2, 1.3],
            [0.24, 1.55],
            [0.2, 1.8],
            [0.27, 2.1],
            [0.33, 2.3],
            [0.18, 2.42],
            [0.08, 2.48],
            [0.01, 2.48],
          ],
          { x: cx, y: cy, z: z0, segments: 14 },
        ),
      );
      addG(new THREE.SphereGeometry(0.14, 12, 10), gold, ...P(0, 0.02, z0 + 2.62));
      // Sound and Vision: two reclining bronze figures at the foot of the column.
      for (const sg of [-1, 1]) {
        const bx = cx + sx * sg * 1.2,
          by = cy + sy * sg * 1.2;
        kit.box(batch, concrete, bx, by, 0.5, 2.4, 1.0, 0.5, fa + (sg > 0 ? 0.2 : -0.2));
        const body = new THREE.CapsuleGeometry(0.3, 1.4, 4, 10);
        const m = new THREE.Matrix4().makeRotationZ(fa + (sg > 0 ? 0.2 : -0.2));
        m.multiply(new THREE.Matrix4().makeRotationY(Math.PI / 2 - 0.35 * sg));
        m.setPosition(bx, by, 1.05);
        batch.addGeometry(bronzeM, body, m);
        body.dispose();
        addG(
          new THREE.SphereGeometry(0.22, 10, 8),
          bronzeM,
          bx + fx * 0.9 * sg,
          by + fy * 0.9 * sg,
          1.45,
        );
      }
    }
    // Benches and lamps round the pool, facing Helios.
    {
      const benches = [],
        lamps = [];
      for (let k = 0; k < 12; k++) {
        const t = (k / 12) * Math.PI * 2;
        benches.push([cx + Math.cos(t) * 10.5, cy + Math.sin(t) * 10.5, t + Math.PI / 2]);
        if (k % 3 === 1)
          lamps.push([
            cx + Math.cos(t + 0.26) * 13.5,
            cy + Math.sin(t + 0.26) * 13.5,
            t + Math.PI / 2,
          ]);
      }
      g.add(placeAssets('bench', benches, { z: 0.12 }));
      g.add(placeAssets('street_lamp', lamps, { z: 0.12 }));
    }

    // Glazed full-height stair tower proud of the drum (south-east).
    {
      const a = -0.5;
      const R = rayR(a) + 2;
      const tx = cx + Math.cos(a) * R,
        ty = cy + Math.sin(a) * R;
      const ta = a + Math.PI / 2;
      kit.box(batch, glassL, tx, ty, 0, 8, 4.5, H + 1.5, ta);
      kit.box(batch, concrete, tx, ty, H + 1.5, 8.6, 5, 0.6, ta);
      // Mullion grid on the glass.
      const ux = Math.cos(ta),
        uy = Math.sin(ta),
        nx = Math.cos(a),
        ny = Math.sin(a);
      for (let i = 0; i <= 5; i++) {
        const o = -4 + i * 1.6;
        kit.box(
          batch,
          alu,
          tx + ux * o + nx * 2.28,
          ty + uy * o + ny * 2.28,
          0,
          0.08,
          0.1,
          H + 1.5,
          ta,
        );
      }
      for (let z = 0; z <= H + 1.5; z += st / 2)
        kit.box(batch, alu, tx + nx * 2.28, ty + ny * 2.28, z, 8, 0.1, 0.08, ta);
      for (let z = 1.5; z < H; z += st / 2) {
        const off = ((z / (st / 2)) % 2 ? 1 : -1) * 1.6;
        kit.box(batch, cream, tx + ux * off, ty + uy * off, z, 3.4, 3.6, 0.25, ta + 0.18);
      }
    }
    // BBC lettering band on the drum facing the forecourt.
    {
      const sign = kit.paintedMaterial(
        'tvc:sign',
        1024,
        128,
        (x, w, h) => {
          x.fillStyle = '#f2eee2';
          x.fillRect(0, 0, w, h);
          x.fillStyle = '#1b1b1b';
          x.font = 'bold 78px sans-serif';
          x.textAlign = 'center';
          x.textBaseline = 'middle';
          x.fillText('TELEVISION CENTRE', w / 2, h / 2 + 4);
        },
        DS,
      );
      const a0 = 0.25,
        a1 = 0.75,
        n = 8,
        z0 = H - st - 1.3,
        z1 = H - st - 0.1;
      for (let k = 0; k < n; k++) {
        const t0 = a0 + ((a1 - a0) * k) / n,
          t1 = a0 + ((a1 - a0) * (k + 1)) / n;
        const R0 = rayR(t0) + 0.35,
          R1 = rayR(t1) + 0.35;
        const P0 = [cx + Math.cos(t0) * R0, cy + Math.sin(t0) * R0],
          P1 = [cx + Math.cos(t1) * R1, cy + Math.sin(t1) * R1];
        batch.quad(
          sign,
          [P0[0], P0[1], z0],
          [P1[0], P1[1], z0],
          [P1[0], P1[1], z1],
          [P0[0], P0[1], z1],
          [k / n, 0],
          [(k + 1) / n, 0],
          [(k + 1) / n, 1],
          [k / n, 1],
        );
      }
      // Main entrance: glazed doors under a cantilevered canopy.
      const am = 0.5,
        Rm = rayR(am);
      const ex = cx + Math.cos(am) * Rm,
        ey = cy + Math.sin(am) * Rm;
      const ta = am + Math.PI / 2;
      const nx = Math.cos(am),
        ny = Math.sin(am);
      kit.box(batch, cream, ex + nx * 2.2, ey + ny * 2.2, 3.9, 14, 4.6, 0.45, ta);
      kit.box(
        batch,
        kit.mat('#fff4d6', { emissive: '#8a7a50' }),
        ex + nx * 2.2,
        ey + ny * 2.2,
        3.86,
        12,
        3.6,
        0.04,
        ta,
      );
      for (const o of [-6.5, 6.5])
        kit.box(
          batch,
          dark,
          ex + nx * 4.1 + Math.cos(ta) * o,
          ey + ny * 4.1 + Math.sin(ta) * o,
          0,
          0.25,
          0.25,
          3.9,
          ta,
        );
      kit.windowRow(
        batch,
        [ex - Math.cos(ta) * 5 + nx * 0.1, ey - Math.sin(ta) * 5 + ny * 0.1],
        [ex + Math.cos(ta) * 5 + nx * 0.1, ey + Math.sin(ta) * 5 + ny * 0.1],
        0.1,
        {
          glass: glassL,
          frame: dark,
          sill: dark,
          count: 4,
          width: 2.0,
          height: 2.6,
          margin: 0.4,
          head: 'none',
          bars: 1,
        },
      );
    }

    // ---------- Rotunda (Endo) ----------
    {
      const rot = B('9bcde68a-4dad-4732-a9dd-f58c0c2ce473');
      const rr = rot.polys[0][0];
      for (const e of edgesOf(rr)) wallQ(concrete, e.a, e.b, 0, st);
      ribbon(rr, st, 6, st, {
        spandrel: mosaicBlue,
        glass: glassM,
        mull: cream,
        slab: cream,
        pitch: 1.2,
      });
      for (const e of edgesOf(rr)) wallQ(glassL, e.a, e.b, H - st, rot.h);
      mullions(alu, rr, H - st, rot.h - H + st, 1.1, 0.05, 0.07, 0.1);
      const capR = kit.offsetRing(rr, 0.9);
      kit.cap(batch, roofM, [[capR]], rot.h + 0.4);
      kit.cap(batch, cream, [[capR]], rot.h, { down: true });
      kit.walls(batch, cream, [[capR]], rot.h, rot.h + 0.4, { bay: 1e6 });
      band(alu, rr, H + 0.9, 0.06, 0.6); // terrace rail line
    }

    // ---------- Studio ring ----------
    const studioBox = (b, h) => {
      for (const e of edgesOf(ccw(b.polys[0][0]))) wallQ(brick, e.a, e.b, 0, h, 8, 8);
      kit.cap(batch, roofM, b.polys, h, { scale: 6 });
      kit.cornice(batch, concrete, ccw(b.polys[0][0]), h - 0.6, { height: 1.0, projection: 0.15 });
      // Lighting-grid penthouse with louvres, and cooling plant.
      const r = ccw(b.polys[0][0]);
      const fr = kit.ringFrame(r);
      kit.box(batch, concrete, fr.cx, fr.cy, h, fr.length * 0.55, fr.width * 0.55, 2.8, fr.angle);
      const c = Math.cos(fr.angle),
        s = Math.sin(fr.angle);
      for (let i = -3; i <= 3; i++) {
        const o = (i / 7) * fr.length * 0.55;
        kit.box(
          batch,
          dark,
          fr.cx + c * o + -s * (fr.width * 0.275 + 0.02),
          fr.cy + s * o + c * (fr.width * 0.275 + 0.02),
          h + 0.6,
          fr.length * 0.06,
          0.05,
          1.8,
          fr.angle,
        );
      }
      for (const o of [-0.35, 0.35])
        kit.box(
          batch,
          plant,
          fr.cx + c * fr.length * o,
          fr.cy + s * fr.length * o + 0,
          h,
          3,
          2.4,
          1.6,
          fr.angle,
        );
      // Scenery dock doors at ground level.
      for (const e of edgesOf(r))
        if (e.len > 15)
          kit.windowRow(batch, e.a, e.b, 0, {
            glass: kit.mat('#5d6468'),
            frame: dark,
            sill: dark,
            count: 1,
            width: 5,
            height: 5.5,
            margin: e.len / 2 - 3,
            head: 'none',
            bars: 4,
            depth: 0.2,
          });
    };
    // TC1 (Studio 1): blind brick wall with the 26 white "atomic" discs to Wood Lane.
    {
      const b = B('141f12da-152d-4b90-b12d-c4dcde5e7710');
      studioBox(b, b.h);
      const r = ccw(b.polys[0][0]);
      const east = edgesOf(r).reduce((m, e) =>
        (e.a[0] + e.b[0]) / 2 > (m.a[0] + m.b[0]) / 2 ? e : m,
      );
      const white = kit.mat('#f4f2ec', { roughness: 0.5 });
      const rnd = kit.rng(0.26);
      const disc = new THREE.CylinderGeometry(0.7, 0.7, 0.18, 20);
      const orbit = new THREE.TorusGeometry(1.25, 0.05, 4, 24);
      for (let k = 0; k < 26; k++) {
        const row = Math.floor(k / 9),
          col = k % 9;
        const t = 2.2 + col * ((east.len - 4.4) / 8.5) + (row % 2) * 1.6 + (rnd() - 0.5) * 0.8;
        const z = 7 + row * 5 + (rnd() - 0.5) * 1.2;
        const x = east.a[0] + east.ux * t + east.nx * 0.12,
          y = east.a[1] + east.uy * t + east.ny * 0.12;
        const m = new THREE.Matrix4().makeRotationZ(east.f);
        m.setPosition(x, y, z);
        batch.addGeometry(white, disc, m);
        for (const tilt of [0.9, -0.9]) {
          const m2 = new THREE.Matrix4().makeRotationZ(east.f);
          m2.multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
          m2.multiply(new THREE.Matrix4().makeRotationZ(tilt + rnd() * 0.3));
          m2.multiply(new THREE.Matrix4().makeScale(1, 0.45, 1));
          m2.setPosition(x + east.nx * 0.08, y + east.ny * 0.08, z);
          batch.addGeometry(white, orbit, m2);
        }
      }
      disc.dispose();
      orbit.dispose();
    }
    studioBox(B('14dc4fae-9f26-4c16-8b94-51eedd6b1aee'), 20);
    studioBox(B('5349aecc-0f9b-4b10-81fc-64e8aa470aba'), 20);
    // BBC Studioworks: curved studio ring corridor block, cream with ribbon windows.
    {
      const b = B('bb7c2a95-2aca-4a2e-bf90-388606f5aa25');
      const r = ccw(b.polys[0][0]);
      for (const e of edgesOf(r)) wallQ(concrete, e.a, e.b, 0, 4);
      for (const e of edgesOf(r))
        if (e.len > 6)
          kit.windowRow(batch, e.a, e.b, 0.3, {
            glass: glassL,
            frame: dark,
            sill: dark,
            bay: 3.2,
            width: 2.6,
            height: 3.0,
            margin: 0.6,
            head: 'none',
            bars: 1,
          });
      ribbon(r, 4, 3, 4, {
        spandrel: mosaicBlue,
        glass: glassM,
        mull: cream,
        slab: cream,
        sp: 1.2,
      });
      kit.cap(batch, roofM, [[r]], b.h, { scale: 6 });
      band(cream, r, b.h, 0.8, 0.2);
    }

    // ---------- 2 Television Centre (offices): glass behind vertical fins ----------
    {
      const b = B('57b2711d-3c29-4489-872e-76d314cdb46e');
      const r = ccw(b.polys[0][0]);
      const fl = 3.6;
      const nf = Math.round(b.h / fl);
      for (const e of edgesOf(r)) {
        wallQ(concrete, e.a, e.b, 0, 0.5);
        wallQ(glassM, e.a, e.b, 0.5, b.h, 3, fl);
      }
      for (let s = 1; s < nf; s++) band(alu, r, s * fl - 0.15, 0.3, 0.25);
      mullions(
        kit.mat('#d9d7d0', { roughness: 0.5, side: THREE.DoubleSide }),
        r,
        0.5,
        b.h - 0.5,
        1.5,
        0.35,
        0.12,
        0.7,
      );
      kit.cap(batch, roofM, [[r]], b.h, { scale: 6 });
      band(alu, r, b.h, 1.1, 0.15);
      // Lower wings with planted roof terraces and glass balustrades.
      for (const p of b.parts ?? []) {
        const pr = ccw(p.polys[0][0]);
        kit.cap(batch, kit.mat('#7f9a6a', DS), [[kit.offsetRing(pr, -0.3)]], p.h + 0.05, {
          scale: 4,
        });
        band(glassL, pr, p.h, 1.1, 0.05);
        const fr = kit.ringFrame(pr);
        const trees = [];
        for (let i = -2; i <= 2; i++)
          trees.push([
            fr.cx + Math.cos(fr.angle) * fr.length * 0.18 * i,
            fr.cy + Math.sin(fr.angle) * fr.length * 0.18 * i,
            0,
            3.2,
          ]);
        g.add(placeAssets('lime_tree', trees, { z: p.h, scaleOf: (q) => q[3] }));
      }
      const fr = kit.ringFrame(r);
      kit.box(
        batch,
        kit.mat('#5c6266', DS),
        fr.cx,
        fr.cy,
        b.h,
        fr.length * 0.35,
        fr.width * 0.3,
        3.2,
        fr.angle,
      );
      // Entrance canopy on the long north-east face.
      const ne = edgesOf(r).reduce((m, e) => (e.len > m.len ? e : m));
      const mx = (ne.a[0] + ne.b[0]) / 2,
        my = (ne.a[1] + ne.b[1]) / 2;
      kit.box(batch, alu, mx + ne.nx * 2.5, my + ne.ny * 2.5, 4.2, 16, 5, 0.4, ne.f);
    }

    // ---------- The Crescent (residential) ----------
    {
      const b = B('c685cd6f-495b-41fe-8288-45cb604f2647');
      const r = ccw(b.polys[0][0]);
      const top = b.h - 3.2;
      for (const e of edgesOf(r)) {
        wallQ(concrete, e.a, e.b, 0, 0.6);
        wallQ(stock, e.a, e.b, 0.6, top, 4, 4);
      }
      kit.cornice(batch, concrete, r, 3.0, { height: 0.3, projection: 0.12 });
      kit.cornice(batch, concrete, r, top - 0.5, { height: 0.5, projection: 0.25 });
      const frameM = kit.mat('#3c3f41', { roughness: 0.5, metalness: 0.4 });
      kit.windowGrid(batch, r, 0.9, 7, 3.2, (s) => ({
        glass: kit.mat('dark_glass'),
        frame: frameM,
        sill: concrete,
        bay: 3.6,
        width: s === 0 ? 2.2 : 1.6,
        height: s === 0 ? 2.4 : 2.0,
        margin: 1.0,
        head: 'none',
        bars: 0,
        depth: 0.18,
      }));
      // Projecting balconies on alternate bays of the longer elevations.
      for (const e of edgesOf(r)) {
        if (e.len < 12) continue;
        const n = Math.floor(e.len / 7.2);
        for (let i = 0; i < n; i++) {
          const t = (e.len * (i + 0.5)) / n;
          for (let s = 1; s < 7; s += 1) {
            if ((s + i) % 2) continue;
            const x = e.a[0] + e.ux * t + e.nx * 0.75,
              y = e.a[1] + e.uy * t + e.ny * 0.75;
            kit.box(batch, concrete, x, y, s * 3.2 + 0.6, 3.2, 1.5, 0.18, e.f);
            kit.box(
              batch,
              glassL,
              x + e.nx * 0.72,
              y + e.ny * 0.72,
              s * 3.2 + 0.78,
              3.2,
              0.05,
              1.0,
              e.f,
            );
          }
        }
      }
      const sb = kit.offsetRing(r, -1.2);
      for (const e of edgesOf(sb)) wallQ(kit.mat('#7b8084', DS), e.a, e.b, top, b.h, 2, 3.2);
      mullions(alu, sb, top, 3.2, 2.4, 0.05, 0.1, 0.12);
      kit.cap(batch, concrete, [[r, sb.slice().reverse()]], top);
      band(glassL, r, top, 1.0, -0.05);
      kit.cap(batch, roofM, [[sb]], b.h, { scale: 6 });
    }

    // ---------- forecourt between the drum, TC1 and Wood Crescent (trees are mapped) ----------
    {
      g.add(
        placeAssets('bench', [
          [-1727.5, 407, 0],
          [-1716.5, 407, 0],
          [-1705.5, 406, 0],
        ]),
      );
      g.add(
        placeAssets('street_lamp', [
          [-1738, 404, 0],
          [-1717, 404, 0],
          [-1698, 403, 0],
        ]),
      );
    }

    g.add(batch.toGroup('bbc_television_centre'));
    return g;
  },
};
