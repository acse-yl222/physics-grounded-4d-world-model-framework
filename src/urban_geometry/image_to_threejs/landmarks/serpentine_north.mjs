// Serpentine North (former Serpentine Sackler Gallery), Kensington Gardens: The
// Magazine, an 1805 gunpowder store - two brick barrel-vaulted powder stores inside
// a lower square surrounding range with a frontal colonnade - converted in 2013 by
// Zaha Hadid Architects, who added the undulating white tensile-fabric extension
// (restaurant) on the west side, carried on five tapered steel columns over a
// curved glass wall; plus the small north wing (offices).
export default {
  id: 'serpentine_north',
  name: 'Serpentine North Gallery (The Magazine)',
  claims: [
    '6900669a-b73e-4741-b402-4833ac1fbf3d', // The Magazine
    'addf86c6-1704-44cb-b6a7-51088e15b851', // Zaha Hadid extension ("Chucs Serpentine" restaurant)
    '5c826e8b-419c-4a4f-bdf2-f456a7891245', // north wing
  ],
  references: [
    {
      title: 'Serpentine North Gallery - Zaha Hadid Architects',
      url: 'https://www.zha.com/projects/architecture/serpentine-north-gallery',
      used_for:
        'two raw-brick barrel-vaulted stores, lower square surrounding structure with frontal colonnade; tensile extension on the west side',
    },
    {
      title: 'Serpentine Sackler Gallery - arqa',
      url: 'https://arqa.com/en/architecture/serpentine-sackler-gallery.html',
      used_for: '1805 gunpowder store joined with a 21st century tensile structure',
    },
    {
      title: "Zaha Hadid's Serpentine Sackler Gallery to open in September - Dezeen",
      url: 'https://www.dezeen.com/2013/07/31/zaha-hadids-serpentine-sackler-gallery-to-open-in-september/amp/',
      used_for: 'undulating white canopy beside the Grade II listed building',
    },
    {
      title: 'The Magazine restaurant - Zaha Hadid Architects',
      url: 'https://www.zha.com/projects/interior-architecture/the-magazine-restaurant',
      used_for: 'fabric as load-bearing structure held up by five tapered steel columns',
    },
    {
      title: "Magazine project - Liam O'Connor Architects",
      url: 'https://www.liamoconnor.com/project-magazine',
      used_for: 'new north wing housing Serpentine offices',
    },
  ],
  notes:
    'Membrane surface is an analytic height field (peaks over five columns placed along the long axis of the ' +
    'extension outline), not the real form-found geometry. Colonnade assumed on the south (lake-facing) end; ' +
    'barrel-vault store sizes proportioned within the footprint. Magazine brick colour approximated as stock brick.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const brickC = '#a68c69';
    const brickMat = kit.mat(brickC, { roughness: 0.95 });
    const stone = kit.mat('portland_stone');
    const slate = kit.roof('slate', 0);
    const lead = kit.mat('lead');
    const white = kit.mat('#f4f4f1', { roughness: 0.55, side: THREE.DoubleSide });
    const steel = kit.mat('white_steel');
    const glass = kit.mat('glass', { transparent: true, opacity: 0.55 });
    const dark = kit.mat('dark_glass');
    const brickTex = kit.paintedMaterial('serpentine_north:brick', 256, 256, (c, w, h) => {
      const r = kit.rng(0.551);
      c.fillStyle = '#8f7a5c';
      c.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
          const col = new THREE.Color(brickC).multiplyScalar(0.86 + r() * 0.26);
          c.fillStyle = '#' + col.getHexString();
          c.fillRect(x + 0.5, y + 0.5, 11, 3);
        }
    });

    // ---- The Magazine --------------------------------------------------------
    const mag = byId['6900669a-b73e-4741-b402-4833ac1fbf3d'];
    const ring = mag.polys[0][0];
    const fr = kit.ringFrame(ring);
    const A = fr.angle,
      ca = Math.cos(A),
      sa = Math.sin(A);
    const L = (x, y) => [fr.cx + x * ca - y * sa, fr.cy + x * sa + y * ca];
    const lbox = (m, x, y, z0, w, d, h, rz = 0) => {
      const p = L(x, y);
      kit.box(batch, m, p[0], p[1], z0, w, d, h, A + rz);
    };
    const hl = fr.length / 2,
      hw = fr.width / 2;
    // which end of the long axis faces south
    const southSign = sa > 0 ? -1 : 1; // local +x points north when sin(A) > 0
    // lower surrounding range (perimeter wall with stone coping)
    const H1 = 4.6;
    kit.walls(batch, brickTex, [[ring]], 0, H1, { bay: 3, storey: 3 });
    {
      const inner = kit.offsetRing(ring, -0.45);
      kit.walls(batch, stone, [[kit.offsetRing(ring, 0.1)]], H1, H1 + 0.35);
      kit.cap(batch, stone, [[kit.offsetRing(ring, 0.1), inner.slice().reverse()]], H1 + 0.35);
      kit.cap(batch, lead, [[inner]], H1 + 0.1);
    }
    // two barrel-vaulted powder stores side by side along the long axis
    const storeL = fr.length * 0.6,
      storeW = fr.width * 0.3;
    for (const s of [-1, 1]) {
      const y = s * (storeW / 2 + 0.4);
      const r4 = [
        L(-storeL / 2, y - storeW / 2),
        L(storeL / 2, y - storeW / 2),
        L(storeL / 2, y + storeW / 2),
        L(-storeL / 2, y + storeW / 2),
      ];
      kit.walls(batch, brickTex, [[r4]], H1, 6.4, { bay: 3, storey: 3 });
      kit.walls(batch, stone, [[kit.offsetRing(r4, 0.2)]], 6.2, 6.5);
      // barrel vault expressed as a segmental lead/slate roof
      const vault = new THREE.CylinderGeometry(
        storeW / 2 + 0.3,
        storeW / 2 + 0.3,
        storeL + 0.4,
        16,
        1,
        false,
        -Math.PI / 2,
        Math.PI,
      ).rotateZ(Math.PI / 2);
      const m4 = new THREE.Matrix4().makeRotationZ(A).setPosition(...L(0, y), 6.5);
      const sc = new THREE.Matrix4().makeScale(1, 1, 0.55);
      batch.addGeometry(slate, vault, m4.multiply(sc));
      vault.dispose();
    }
    // frontal Tuscan colonnade on the south end
    {
      const x = southSign * (hl + 0.05);
      const xc = southSign * (hl + 1.6);
      lbox(stone, xc, 0, 0, 3.2, hw * 1.3, 0.3);
      lbox(stone, xc, 0, H1 - 0.8, 3.2, hw * 1.3 + 0.4, 0.8);
      lbox(stone, xc, 0, H1 - 0.05, 3.4, hw * 1.3 + 0.6, 0.4);
      const n = 6;
      for (let k = 0; k < n; k++) {
        const y = -hw * 0.6 + (k * hw * 1.2) / (n - 1);
        const col = new THREE.CylinderGeometry(0.32, 0.38, H1 - 1.1, 12).rotateX(Math.PI / 2);
        const m4 = new THREE.Matrix4().setPosition(
          ...L(southSign * (hl + 2.6), y),
          0.3 + (H1 - 1.1) / 2,
        );
        batch.addGeometry(stone, col, m4);
        col.dispose();
      }
      lbox(dark, x, 0, 0.3, 0.1, hw * 0.5, 2.8);
    }

    // ---- Zaha Hadid tensile extension ------------------------------------------------
    const ext = byId['addf86c6-1704-44cb-b6a7-51088e15b851'];
    if (ext) {
      const er = ext.polys[0][0];
      const ef = kit.ringFrame(er);
      const ec = Math.cos(ef.angle),
        es = Math.sin(ef.angle);
      // five columns along the long axis of the extension
      const inside = (x, y) => {
        let c = false;
        for (let i = 0, j = er.length - 1; i < er.length; j = i++) {
          const [xi, yi] = er[i],
            [xj, yj] = er[j];
          if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
        }
        return c;
      };
      const cols = [];
      for (let k = 0; k < 5; k++) {
        let t = (k / 4 - 0.5) * ef.length * 0.7;
        const off = (k % 2 ? 1 : -1) * ef.width * 0.1;
        let p = [ef.cx + t * ec - off * es, ef.cy + t * es + off * ec];
        // pull columns that fall outside the curved outline back toward the centre
        for (let it = 0; it < 12 && !inside(p[0], p[1]); it++) {
          t *= 0.85;
          p = [ef.cx + t * ec - off * 0.5 * es, ef.cy + t * es + off * 0.5 * ec];
        }
        cols.push(p);
      }
      const rad = Math.max(4.0, ef.width * 0.4);
      const height = (x, y) => {
        let z = 2.4;
        for (const [cx, cy] of cols) {
          const d2 = ((x - cx) ** 2 + (y - cy) ** 2) / (rad * rad);
          z += 4.6 * Math.exp(-d2 * 2.2);
        }
        return Math.min(z, 7.6);
      };
      // Triangulate the outline, then subdivide and lift the vertices.
      const contour = er.map(([x, y]) => new THREE.Vector2(x, y));
      const tris = THREE.ShapeUtils.triangulateShape(contour, []);
      let faces = tris.map((t) => t.map((i) => [contour[i].x, contour[i].y]));
      for (let it = 0; it < 4; it++) {
        const next = [];
        for (const [a, b, c] of faces) {
          const ab = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2],
            bc = [(b[0] + c[0]) / 2, (b[1] + c[1]) / 2],
            caM = [(c[0] + a[0]) / 2, (c[1] + a[1]) / 2];
          const big = Math.max(
            Math.hypot(a[0] - b[0], a[1] - b[1]),
            Math.hypot(b[0] - c[0], b[1] - c[1]),
            Math.hypot(c[0] - a[0], c[1] - a[1]),
          );
          if (big < 2.2) next.push([a, b, c]);
          else next.push([a, ab, caM], [ab, b, bc], [caM, bc, c], [ab, bc, caM]);
        }
        faces = next;
      }
      // Edge drop: the membrane dips toward the glazed perimeter.
      const edgeDist = (x, y) => {
        let d = Infinity;
        for (let k = 0; k < er.length; k++) {
          const p = er[k],
            q = er[(k + 1) % er.length];
          const vx = q[0] - p[0],
            vy = q[1] - p[1];
          const t = Math.max(
            0,
            Math.min(1, ((x - p[0]) * vx + (y - p[1]) * vy) / (vx * vx + vy * vy || 1)),
          );
          d = Math.min(d, Math.hypot(x - p[0] - t * vx, y - p[1] - t * vy));
        }
        return d;
      };
      const Z = (x, y) => {
        const d = edgeDist(x, y);
        return height(x, y) * (0.72 + 0.28 * Math.min(1, d / 3)) + Math.min(d, 3) * 0.12;
      };
      const verts = [],
        uvs = [],
        idx = [];
      const ccw = THREE.ShapeUtils.isClockWise(contour) ? -1 : 1;
      for (const f of faces) {
        const base = verts.length;
        const order = ccw > 0 ? f : [f[0], f[2], f[1]];
        for (const [x, y] of order) {
          verts.push([x, y, Z(x, y)]);
          uvs.push([x / 4, y / 4]);
        }
        idx.push(base, base + 1, base + 2);
      }
      batch.add(white, verts, uvs, idx);
      // Glass perimeter wall following the membrane edge, with a white edge beam.
      for (let k = 0; k < er.length; k++) {
        const p = er[k],
          q = er[(k + 1) % er.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        const n = Math.max(1, Math.ceil(len / 1.5));
        for (let i = 0; i < n; i++) {
          const a = [p[0] + ((q[0] - p[0]) * i) / n, p[1] + ((q[1] - p[1]) * i) / n],
            b = [p[0] + ((q[0] - p[0]) * (i + 1)) / n, p[1] + ((q[1] - p[1]) * (i + 1)) / n];
          const za = Z(...a),
            zb = Z(...b);
          batch.quad(
            glass,
            [a[0], a[1], 0],
            [b[0], b[1], 0],
            [b[0], b[1], zb - 0.3],
            [a[0], a[1], za - 0.3],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
          batch.quad(
            white,
            [a[0], a[1], za - 0.35],
            [b[0], b[1], zb - 0.35],
            [b[0], b[1], zb],
            [a[0], a[1], za],
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 1],
          );
        }
      }
      // floor and tapered steel columns flaring into the membrane
      kit.cap(batch, kit.mat('paving'), [[er]], 0.05);
      for (const [cx, cy] of cols) {
        const top = Z(cx, cy);
        const c = new THREE.CylinderGeometry(0.9, 0.18, top, 10).rotateX(Math.PI / 2);
        batch.addGeometry(steel, c, new THREE.Matrix4().setPosition(cx, cy, top / 2));
        c.dispose();
        // small rooflight ring at each peak
        const o = new THREE.CylinderGeometry(0.7, 0.9, 0.35, 10).rotateX(Math.PI / 2);
        batch.addGeometry(steel, o, new THREE.Matrix4().setPosition(cx, cy, top + 0.1));
        o.dispose();
      }
    }

    // ---- North wing (single-storey brick offices) ---------------------------------------
    const nw = byId['5c826e8b-419c-4a4f-bdf2-f456a7891245'];
    if (nw) {
      kit.walls(batch, kit.facade('london_stock', 1), nw.polys, 0, 3.6, { bay: 3.2, storey: 3.2 });
      for (const ring2 of nw.polys[0]) {
        kit.walls(batch, stone, [[kit.offsetRing(ring2, 0.1)]], 3.6, 4.0);
        kit.cap(batch, stone, [[kit.offsetRing(ring2, 0.1)]], 4.0);
      }
    }
    g.add(batch.toGroup('serpentine_north'));
    return g;
  },
};
