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
    'from drawings. Facade detail is a reading of "unitised glazing + terracotta + metal sun-shading": recessed ' +
    'glass, terracotta piers every 3 m and floor spandrels, slim mullions, cantilevered aluminium blades on ' +
    'brackets; pier pitch, colours, blade depth, the west atrium entrance (canopy, revolving door, sign), ' +
    'louvred rooftop plant, flues and forecourt furniture are assumptions.',
  build({ THREE, kit, buildings, placeAssets }) {
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
        return {
          a,
          b,
          len,
          dx: dx / len,
          dy: dy / len,
          nx: dy / len,
          ny: -dx / len,
          ang: Math.atan2(dy, dx),
        };
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

    const at = (e, s, d) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    const ebox = (mat, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, mat, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const shrink = (r, d) => {
      const o = kit.offsetRing(r, -d);
      return kit.ringArea(o) > 0 ? o : r;
    };

    // ---- materials -----------------------------------------------------------
    const glassTex = kit.paintedMaterial(
      'ihub:glass',
      256,
      512,
      (c, w, h) => {
        for (let s = 0; s < 2; s++) {
          const y0 = (s * h) / 2,
            sh = h / 2;
          const grd = c.createLinearGradient(0, y0, 0, y0 + sh);
          grd.addColorStop(0, '#93a3ab');
          grd.addColorStop(0.1, '#4f6676');
          grd.addColorStop(0.6, '#2f404d');
          grd.addColorStop(1, '#3c4f5c');
          c.fillStyle = grd;
          c.fillRect(0, y0, w, sh);
          c.fillStyle = 'rgba(210,225,235,0.12)';
          c.fillRect(w * 0.15, y0 + sh * 0.2, w * 0.2, sh * 0.7);
        }
      },
      { roughness: 0.18, metalness: 0.35 },
    );
    const terra = kit.mat('#b9714b', { roughness: 0.72 });
    const terraDark = kit.mat('#a7623f', { roughness: 0.75 });
    const shade = kit.mat('#d3d6d7', { roughness: 0.35, metalness: 0.55 });
    const frameM = kit.mat('#5b6166', { roughness: 0.4, metalness: 0.5 });
    const roofM = kit.mat('#8e908d');
    const darkGlass = kit.mat('#25323b', { roughness: 0.12, metalness: 0.4 });
    const atriumGlass = kit.mat('#7d98a8', {
      roughness: 0.15,
      metalness: 0.4,
      transparent: true,
      opacity: 0.7,
    });
    const steel = kit.mat('white_steel');
    const louvreM = kit.mat('#b8bcbd', { roughness: 0.5, metalness: 0.3 });
    const paving = kit.mat('#c6c0b3', { roughness: 0.9 });

    // ---- massing ---------------------------------------------------------------
    // Axis along the Westway frontage (longest south-ish edge).
    const E = edgesOf(ring);
    const front = E.filter((e) => e.ny < -0.8).sort((p, q) => q.len - p.len)[0];
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
    // Edges of a part that lie on the atrium cut lines face into the atrium.
    const onCut = (e) => {
      const da = nx * e.a[0] + ny * e.a[1],
        db = nx * e.b[0] + ny * e.b[1];
      return [d0 + 15, d0 + 24].some((d) => Math.abs(da - d) < 0.05 && Math.abs(db - d) < 0.05);
    };

    // Unitised facade: recessed glass, terracotta piers every 3 m with slim aluminium
    // mullions between, terracotta spandrels at each floor and cantilevered blades.
    const facadeOf = (part, top, nFloors, blades) => {
      for (const e of edgesOf(part)) {
        if (e.len < 0.3) continue;
        const inner = onCut(e);
        const p = at(e, 0, -0.35),
          q = at(e, e.len, -0.35);
        batch.quad(
          glassTex,
          [p[0], p[1], G],
          [q[0], q[1], G],
          [q[0], q[1], top],
          [p[0], p[1], top],
          [0, 0],
          [e.len / 3, 0],
          [e.len / 3, (top - G) / (2 * ST)],
          [0, (top - G) / (2 * ST)],
        );
        // spandrels / floor bands
        for (let k = 0; k <= nFloors - 1; k++) {
          const z = G + k * ST;
          ebox(k % 2 ? terra : terraDark, e, 0, e.len, -0.35, 0.12, z - 0.15, z + 0.75);
        }
        if (e.len < 1.2) continue;
        const n = Math.max(1, Math.round(e.len / 3));
        for (let k = 0; k <= n; k++) {
          const s = Math.min(e.len - 0.2, Math.max(0.2, (k * e.len) / n));
          ebox(terra, e, s - 0.2, s + 0.2, -0.35, 0.25, G, top);
          if (k < n) {
            const sm = ((k + 0.5) * e.len) / n;
            ebox(frameM, e, sm - 0.04, sm + 0.04, -0.35, -0.15, G, top);
          }
        }
        // window transom at 1.1 m above each floor
        for (let k = 0; k < nFloors - 1; k++)
          ebox(frameM, e, 0, e.len, -0.35, -0.22, G + k * ST + 1.9, G + k * ST + 1.96);
        if (!blades || inner || e.len < 3) continue;
        // Cantilevered aluminium sun-shade blades with brackets at the piers.
        for (let k = 1; k < nFloors; k++) {
          const z = G + k * ST - 0.75;
          ebox(shade, e, 0.1, e.len - 0.1, 0.25, 1.3, z - 0.06, z + 0.06);
          ebox(shade, e, 0.1, e.len - 0.1, 1.22, 1.3, z - 0.2, z + 0.06);
          for (let j = 0; j <= n; j++) {
            const s = Math.min(e.len - 0.2, Math.max(0.2, (j * e.len) / n));
            ebox(frameM, e, s - 0.03, s + 0.03, 0.25, 1.25, z - 0.25, z);
          }
        }
      }
      // parapet with aluminium coping, roof
      kit.walls(batch, terra, [[part]], top, top + 1.1);
      kit.cornice(batch, steel, part, top + 1.1, { height: 0.12, projection: 0.15 });
      kit.cap(batch, roofM, [[part]], top + 0.3);
      const pin = shrink(part, 0.35);
      kit.walls(batch, terra, [[pin.slice().reverse()]], top + 0.3, top + 1.1);
      kit.cap(batch, steel, [[part, pin.slice().reverse()]], top + 1.1);
    };

    // Ground floor: recessed glazing with mullions under a soffit, columns on the line.
    for (const part of [wing, tower]) {
      const gr = shrink(part, 1.2);
      for (const e of edgesOf(gr)) {
        if (e.len < 0.3) continue;
        batch.quad(
          darkGlass,
          [e.a[0], e.a[1], 0],
          [e.b[0], e.b[1], 0],
          [e.b[0], e.b[1], G - 0.5],
          [e.a[0], e.a[1], G - 0.5],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(frameM, e, s - 0.04, s + 0.04, 0, 0.15, 0, G - 0.5);
        }
        ebox(frameM, e, 0, e.len, 0, 0.12, 3.2, 3.3);
      }
      kit.cap(batch, steel, [[part]], G - 0.5, { down: true });
      kit.walls(batch, terra, [[part]], G - 0.5, G);
      for (const e of edgesOf(part)) {
        if (e.len < 7 || onCut(e)) continue;
        const n = Math.round(e.len / 6);
        for (let k = 0; k <= n; k++) {
          const s = 0.5 + ((e.len - 1) * k) / n;
          ebox(terra, e, s - 0.3, s + 0.3, -0.9, -0.3, 0, G - 0.5);
        }
      }
      kit.cornice(batch, kit.mat('#9a958c'), gr, 0, { height: 0.15, projection: 0.12 });
    }
    facadeOf(wing, zW, 7, true);
    facadeOf(tower, zT, 13, true);

    // Roof plant on the tower: real louvre blades around a plant deck, flues.
    {
      const louvred = (pr, z0, h) => {
        kit.walls(batch, kit.mat('#6c7174'), [[shrink(pr, 0.3)]], z0, z0 + h - 0.3);
        kit.cap(batch, roofM, [[shrink(pr, 0.3)]], z0 + h - 0.3);
        for (const e of edgesOf(pr)) {
          if (e.len < 0.5) continue;
          for (let z = z0 + 0.2; z < z0 + h; z += 0.3)
            ebox(louvreM, e, 0, e.len, -0.2, 0.0, z, z + 0.06);
          for (let s = 0; s <= e.len; s += 3)
            ebox(frameM, e, s - 0.05, s + 0.05, -0.25, 0.02, z0, z0 + h + 0.1);
        }
      };
      const plant = shrink(tower, 5);
      louvred(plant, zT + 0.3, 4);
      const fr = kit.ringFrame(plant);
      const flue = new THREE.CylinderGeometry(0.4, 0.4, 3.5, 12).rotateX(Math.PI / 2);
      for (let k = -2; k <= 2; k++) {
        const u = (k / 5.5) * fr.length,
          v = fr.width * 0.25;
        const x = fr.cx + Math.cos(fr.angle) * u - Math.sin(fr.angle) * v,
          y = fr.cy + Math.sin(fr.angle) * u + Math.cos(fr.angle) * v;
        batch.addGeometry(steel, flue, new THREE.Matrix4().makeTranslation(x, y, zT + 5.7));
      }
      flue.dispose();
      // lift overrun and a wing-roof plant enclosure
      const wr = kit.ringFrame(wing);
      const wrect = [
        [-0.2, -0.22],
        [0.2, -0.22],
        [0.2, 0.22],
        [-0.2, 0.22],
      ].map(([u, v]) => [
        wr.cx + Math.cos(wr.angle) * u * wr.length - Math.sin(wr.angle) * v * wr.width,
        wr.cy + Math.sin(wr.angle) * u * wr.length + Math.cos(wr.angle) * v * wr.width,
      ]);
      louvred(kit.ringArea(wrect) < 0 ? wrect.reverse() : wrect, zW + 0.3, 3);
    }

    // Atrium: mullioned glazed ends, asymmetric glass roof on steel rafters.
    const zLow = zW + 1,
      zHigh = zW + 12;
    const ex = kit.orientedExtent(atrium, Math.atan2(uy, ux));
    {
      for (const e of edgesOf(atrium)) {
        if (e.len < 0.3 || onCut(e)) continue;
        batch.quad(
          atriumGlass,
          [e.a[0], e.a[1], 0],
          [e.b[0], e.b[1], 0],
          [e.b[0], e.b[1], zW],
          [e.a[0], e.a[1], zW],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        const n = Math.max(1, Math.round(e.len / 1.5));
        for (let k = 0; k <= n; k++) {
          const s = (k * e.len) / n;
          ebox(steel, e, s - 0.06, s + 0.06, -0.1, 0.25, 0, zW);
        }
        for (let z = G; z <= zW; z += ST) ebox(steel, e, 0, e.len, -0.1, 0.2, z - 0.08, z + 0.08);
      }
      const v0 = ex.v0,
        v1 = ex.v1;
      const P = (u, v) => {
        const z = zLow + ((v - v0) / (v1 - v0)) * (zHigh - zLow);
        return [...ex.at(u, v, 0).slice(0, 2), z];
      };
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
      const beam = (a, b, w, h) => {
        const len = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
        const Y = new THREE.Vector3((b[0] - a[0]) / len, (b[1] - a[1]) / len, (b[2] - a[2]) / len);
        const X = new THREE.Vector3(ux, uy, 0);
        if (Math.abs(X.dot(Y)) > 0.9) X.set(-uy, ux, 0);
        const Z = new THREE.Vector3().crossVectors(X, Y).normalize();
        X.crossVectors(Y, Z);
        const m = new THREE.Matrix4()
          .makeBasis(X, Y, Z)
          .setPosition((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2 + h / 2);
        const geo = new THREE.BoxGeometry(w, len, h);
        batch.addGeometry(steel, geo, m);
        geo.dispose();
      };
      for (let u = ex.u0; u <= ex.u1 + 0.01; u += (ex.u1 - ex.u0) / 18)
        beam(P(u, v0), P(u, v1), 0.3, 0.5);
      // purlins / glazing bars across the rafters
      for (let k = 0; k <= 6; k++) {
        const v = v0 + ((v1 - v0) * k) / 6;
        beam(P(ex.u0, v), P(ex.u1, v), 0.12, 0.15);
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
        for (let k = 1; k < 6; k++) {
          const t = k / 6;
          const p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
          beam([p[0], p[1], zW], [p[0], p[1], zLow + (zHigh - zLow) * t], 0.15, 0.15);
        }
      }
    }

    // Entrance at the west end of the atrium: canopy, revolving door, name sign, forecourt.
    {
      const ends = edgesOf(atrium).filter((e) => !onCut(e) && e.len > 4);
      const west = ends.sort((p, q) => p.nx - q.nx)[0];
      if (west) {
        const e = west,
          sm = e.len / 2;
        ebox(steel, e, sm - 4.5, sm + 4.5, 0, 3.5, 4.2, 4.5);
        ebox(frameM, e, sm - 4.5, sm + 4.5, 3.4, 3.5, 3.9, 4.5);
        const c = at(e, sm, 0.3);
        const drum = new THREE.CylinderGeometry(1.3, 1.3, 2.6, 16, 1, true).rotateX(Math.PI / 2);
        batch.addGeometry(darkGlass, drum, new THREE.Matrix4().makeTranslation(c[0], c[1], 1.3));
        drum.dispose();
        const lid = new THREE.CylinderGeometry(1.4, 1.4, 0.3, 16).rotateX(Math.PI / 2);
        batch.addGeometry(frameM, lid, new THREE.Matrix4().makeTranslation(c[0], c[1], 2.75));
        lid.dispose();
        const sign = kit.paintedMaterial(
          'ihub:sign',
          512,
          64,
          (cx, w, h) => {
            cx.fillStyle = '#e8e9e8';
            cx.fillRect(0, 0, w, h);
            cx.fillStyle = '#0f2f5a';
            cx.font = 'bold 30px sans-serif';
            cx.textAlign = 'center';
            cx.textBaseline = 'middle';
            cx.fillText('TRANSLATION & INNOVATION HUB', w / 2, h / 2 + 2);
          },
          { roughness: 0.6 },
        );
        const a = at(e, sm - 4, 3.52),
          b = at(e, sm + 4, 3.52);
        batch.quad(
          sign,
          [a[0], a[1], 4.2],
          [b[0], b[1], 4.2],
          [b[0], b[1], 4.5],
          [a[0], a[1], 4.5],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        const fc = [at(e, -6, 0.05), at(e, e.len + 6, 0.05), at(e, e.len + 6, 10), at(e, -6, 10)];
        if (kit.ringArea(fc) < 0) fc.reverse();
        kit.cap(batch, paving, [[fc]], 0.04);
        const bol = [];
        for (let s = -5; s <= e.len + 5; s += 2.2)
          if (Math.abs(s - sm) > 3) bol.push([...at(e, s, 6), e.ang]);
        g.add(placeAssets('bollard', bol));
        g.add(
          placeAssets('bench', [
            [...at(e, -3, 8.5), e.ang + Math.PI],
            [...at(e, e.len + 3, 8.5), e.ang + Math.PI],
          ]),
        );
        g.add(
          placeAssets(
            'bicycle_stand',
            [0, 1, 2, 3].map((k) => [...at(e, e.len + 1 + k * 1.2, 3), e.ang + Math.PI / 2]),
          ),
        );
      }
    }
    g.add(batch.toGroup('imperial_i_hub'));
    return g;
  },
};
