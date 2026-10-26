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
      title: 'The Magazine - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101278154-the-magazine-knightsbridge-and-belgravia-ward',
      used_for:
        'Grade II*, 1805 (rainwater heads); one storey with attic, brown stock brick with stone dressings, pedimented attic rising above the portico roof',
    },
    {
      title: "Magazine project - Liam O'Connor Architects",
      url: 'https://www.liamoconnor.com/project-magazine',
      used_for: 'new north wing housing Serpentine offices',
    },
  ],
  notes:
    'Magazine: brown stock brick with stone dressings, portico with pedimented attic above its roof (listing); ' +
    'portico order drawn as Tuscan/Doric with six columns, window count and round-headed sash form estimated; ' +
    'barrel vaults shown lead-covered with rolls. Membrane surface is an analytic height field (peaks over five columns placed along the long axis of the ' +
    'extension outline), not the real form-found geometry. Colonnade assumed on the south (lake-facing) end; ' +
    'barrel-vault store sizes proportioned within the footprint. Magazine brick colour approximated as stock brick.',
  build(ctx) {
    const { THREE, kit, byId } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const brickC = '#9a7f5e';
    const brickMat = kit.mat(brickC, { roughness: 0.95 });
    const stone = kit.mat('portland_stone');
    const leadRoof = kit.roof('lead', 0);
    const lead = kit.mat('lead');
    const white = kit.mat('#f4f4f1', { roughness: 0.55, side: THREE.DoubleSide });
    const steel = kit.mat('white_steel');
    const glass = kit.mat('glass', { transparent: true, opacity: 0.55 });
    const dark = kit.mat('dark_glass');
    const brickTex = kit.paintedMaterial('serpentine_north:brick', 256, 256, (c, w, h) => {
      const r = kit.rng(0.551);
      c.fillStyle = '#86725a';
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
    const lgeo = (geo, m, x, y, z, rz = 0) => {
      const p = L(x, y);
      batch.addGeometry(
        m,
        geo,
        new THREE.Matrix4().makeRotationZ(A + rz).setPosition(p[0], p[1], z),
      );
      geo.dispose();
    };
    const rect = (x0, y0, x1, y1) => [L(x0, y0), L(x1, y0), L(x1, y1), L(x0, y1)];
    const hl = fr.length / 2,
      hw = fr.width / 2;
    // which end of the long axis faces south
    const ss = sa > 0 ? -1 : 1; // local +x points north when sin(A) > 0
    const sashGlass = kit.mat('#3c4a55', { roughness: 0.2, metalness: 0.15 });
    const sashFrame = kit.mat('#f1efe8', { roughness: 0.55 });
    const doorM = kit.mat('#2e3a35', { roughness: 0.6 });
    const paving = kit.mat('#c4bdae', { roughness: 0.95 });
    // forecourt / terrace paving round the Magazine
    {
      const outer = rect(-hl - 7, -hw - 3, hl + 3, hw + 3);
      kit.cap(batch, paving, [[outer, rect(-hl, -hw, hl, hw).reverse()]], 0.03);
    }
    // lower surrounding range: brown stock brick, stone plinth, cornice and coping
    const H1 = 4.6;
    const body = rect(-hl, -hw, hl, hw);
    kit.walls(batch, brickTex, [[body]], 0, H1, { bay: 1, storey: 2 });
    kit.cornice(batch, stone, body, 0, { height: 0.45, projection: 0.12 });
    kit.cornice(batch, stone, body, H1 - 0.45, { height: 0.45, projection: 0.3, steps: 2 });
    {
      const inner = kit.offsetRing(body, -0.45);
      kit.walls(batch, brickMat, [[body]], H1, H1 + 0.45, { bay: 1e6 });
      kit.walls(batch, brickMat, [[inner.slice().reverse()]], H1, H1 + 0.45, { bay: 1e6 });
      kit.cap(
        batch,
        stone,
        [[kit.offsetRing(body, 0.08), kit.offsetRing(inner, -0.05).reverse()]],
        H1 + 0.58,
      );
      kit.walls(batch, stone, [[kit.offsetRing(body, 0.08)]], H1 + 0.45, H1 + 0.58, { bay: 1e6 });
      kit.cap(batch, lead, [[inner]], H1 + 0.1);
    }
    // windows: round-headed recessed arches with sashes on the long sides and the rear,
    // stone sills; plain on the face against the Hadid extension (it is glazed into it)
    const win = {
      width: 1.3,
      height: 2.2,
      bay: 3.6,
      margin: 1.6,
      depth: 0.14,
      glass: sashGlass,
      frame: sashFrame,
      sill: stone,
      head: 'arch',
      bars: 2,
      surround: 0.22,
      surroundMat: kit.mat('#8a6f4f', { roughness: 0.95 }),
    };
    const sides = [
      [L(-hl, -hw), L(hl, -hw)],
      [L(hl, -hw), L(hl, hw)],
      [L(hl, hw), L(-hl, hw)],
      [L(-hl, hw), L(-hl, -hw)],
    ];
    // Round-arched window row: kit.windowRow for the rectangular part, plus the arch
    // frame ring and a half-disc of glass in the wall plane for the head.
    const archRow = (a, b, z, o) => {
      kit.windowRow(batch, a, b, z, { ...o, head: 'none' });
      const dx = b[0] - a[0],
        dy = b[1] - a[1],
        len = Math.hypot(dx, dy),
        ux = dx / len,
        uy = dy / len,
        ang = Math.atan2(dy, dx);
      const margin = o.margin ?? 0.6,
        bay = o.bay ?? 3.6,
        depth = o.depth ?? 0.12;
      const usable = len - 2 * margin;
      const n = o.count ?? Math.max(0, Math.floor(usable / bay + 0.35));
      const r = o.width / 2;
      const rot = new THREE.Matrix4()
        .makeRotationZ(ang)
        .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2));
      for (let k = 0; k < n; k++) {
        const t = margin + (usable * (k + 0.5)) / n;
        const cx = a[0] + ux * t,
          cy = a[1] + uy * t;
        const disc = new THREE.CircleGeometry(r, 12, 0, Math.PI).rotateX(Math.PI / 2);
        batch.addGeometry(
          o.glass,
          disc,
          new THREE.Matrix4()
            .makeRotationZ(ang)
            .setPosition(cx + uy * 0.03, cy - ux * 0.03, z + o.height),
        );
        disc.dispose();
        const ringG = new THREE.TorusGeometry(r + 0.04, 0.07, 4, 12, Math.PI);
        const m = rot
          .clone()
          .setPosition(cx + uy * depth * 0.9, cy - ux * depth * 0.9, z + o.height);
        batch.addGeometry(o.sill ?? o.frame, ringG, m);
        ringG.dispose();
        if (o.bars) {
          kit.box(
            batch,
            o.frame,
            cx + uy * depth * 0.5,
            cy - ux * depth * 0.5,
            z + o.height,
            0.05,
            depth * 0.6,
            r,
            ang,
          );
        }
        if (o.surround) {
          const sr = new THREE.TorusGeometry(
            r + o.surround * 0.6,
            o.surround * 0.5,
            3,
            12,
            Math.PI,
          );
          batch.addGeometry(
            o.surroundMat,
            sr,
            rot.clone().setPosition(cx + uy * depth * 0.5, cy - ux * depth * 0.5, z + o.height),
          );
          sr.dispose();
        }
      }
    };
    // west long side faces the extension: is it the -y or +y side?
    const ext0 = byId['addf86c6-1704-44cb-b6a7-51088e15b851'];
    let extSide = -1;
    if (ext0) {
      const ec = ext0.c ?? ext0.polys[0][0][0];
      const v = -(ec[0] - fr.cx) * sa + (ec[1] - fr.cy) * ca;
      extSide = v > 0 ? 1 : -1;
    }
    sides.forEach(([a, b], k) => {
      const isSouth = (k === 3 && ss < 0) || (k === 1 && ss > 0);
      const isExt = (k === 0 && extSide < 0) || (k === 2 && extSide > 0);
      if (isSouth || isExt) return;
      archRow(a, b, 1.1, win);
    });
    // two barrel-vaulted powder stores side by side along the long axis
    const storeL = fr.length * 0.6,
      storeW = fr.width * 0.3;
    for (const s of [-1, 1]) {
      const y = s * (storeW / 2 + 0.4);
      const r4 = rect(-storeL / 2, y - storeW / 2, storeL / 2, y + storeW / 2);
      kit.walls(batch, brickTex, [[r4]], H1, 6.4, { bay: 1, storey: 2 });
      kit.cornice(batch, stone, r4, 6.1, { height: 0.35, projection: 0.22 });
      // barrel vault, lead covered, with rolls
      const R = storeW / 2 + 0.3;
      const vault = new THREE.CylinderGeometry(
        R,
        R,
        storeL + 0.4,
        20,
        1,
        false,
        -Math.PI / 2,
        Math.PI,
      ).rotateZ(Math.PI / 2);
      const m4 = new THREE.Matrix4().makeRotationZ(A).setPosition(...L(0, y), 6.45);
      batch.addGeometry(leadRoof, vault, m4.multiply(new THREE.Matrix4().makeScale(1, 1, 0.55)));
      vault.dispose();
      for (let i = 1; i < 8; i++) {
        const t = -storeL / 2 + (i * storeL) / 8;
        const roll = new THREE.TorusGeometry(R + 0.03, 0.06, 3, 16, Math.PI)
          .rotateX(Math.PI / 2)
          .rotateZ(Math.PI / 2);
        const mm = new THREE.Matrix4()
          .makeRotationZ(A)
          .setPosition(...L(t, y), 6.45)
          .multiply(new THREE.Matrix4().makeScale(1, 1, 0.55));
        batch.addGeometry(lead, roll, mm);
        roll.dispose();
      }
      // gable-end lunettes (semicircular windows in the vault ends)
      for (const ex of [-1, 1]) {
        const lun = new THREE.CircleGeometry(R * 0.98, 16, 0, Math.PI).rotateX(Math.PI / 2);
        lgeo(
          lun.scale(1, 1, 0.55),
          brickMat,
          ex * (storeL / 2 + 0.01),
          y,
          6.45,
          ex > 0 ? Math.PI / 2 : -Math.PI / 2,
        );
        const lg = new THREE.CircleGeometry(R * 0.45, 12, 0, Math.PI).rotateX(Math.PI / 2);
        lgeo(lg, sashGlass, ex * (storeL / 2 + 0.03), y, 6.5, ex > 0 ? Math.PI / 2 : -Math.PI / 2);
      }
    }
    // frontal portico on the south end: Tuscan columns, entablature, lead roof, and the
    // pedimented brick attic rising above it
    {
      const fx = ss * hl;
      const depth = 3.4;
      const xc = fx + ss * (depth / 2);
      const pw = hw * 1.3;
      lbox(stone, xc, 0, 0, depth + 0.4, pw + 0.6, 0.35);
      lbox(stone, xc + ss * (depth / 2 + 0.5), 0, 0, 0.7, pw - 1.0, 0.18);
      const zc = 0.35,
        hc = H1 - 1.15;
      kit.colonnade(
        batch,
        stone,
        L(fx + ss * (depth - 0.5), -pw / 2 + 0.6),
        L(fx + ss * (depth - 0.5), pw / 2 - 0.6),
        zc,
        hc,
        {
          count: 6,
          radius: 0.32,
          capital: 'doric',
        },
      );
      lbox(stone, xc, 0, H1 - 0.8, depth + 0.2, pw + 0.2, 0.55); // architrave + frieze
      lbox(stone, xc, 0, H1 - 0.25, depth + 0.6, pw + 0.6, 0.4); // cornice
      kit.pitchedRoof(
        batch,
        leadRoof,
        stone,
        rect(fx - ss * 0.3, -pw / 2, fx + ss * (depth + 0.2), pw / 2).map((p) => p),
        A,
        H1 + 0.15,
        0.6,
        'hipped',
        {
          overhang: 0.1,
        },
      );
      // doors and windows inside the portico
      const wa = L(fx + ss * 0.02, ss < 0 ? hw - 1 : -hw + 1),
        wb = L(fx + ss * 0.02, ss < 0 ? -hw + 1 : hw - 1);
      kit.windowRow(batch, wa, wb, 0.35, {
        width: 1.7,
        height: 2.7,
        count: 3,
        margin: 4,
        glass: doorM,
        frame: sashFrame,
        sill: stone,
        head: 'lintel',
        bars: 1,
        surround: 0.2,
        surroundMat: stone,
      });
      // attic with pediment above the portico roof
      const ax = fx - ss * 0.6;
      lbox(brickMat, ax, 0, H1 + 0.45, 1.2, pw * 0.75, 2.3);
      lbox(stone, ax, 0, H1 + 2.75, 1.4, pw * 0.75 + 0.3, 0.35);
      const hwp = pw * 0.375 + 0.15;
      const ped = new THREE.Shape();
      ped.moveTo(-hwp, 0);
      ped.lineTo(hwp, 0);
      ped.lineTo(0, 1.6);
      ped.lineTo(-hwp, 0);
      const pg = new THREE.ExtrudeGeometry(ped, { depth: 1.4, bevelEnabled: false })
        .rotateX(Math.PI / 2)
        .translate(0, 0.7, 0);
      lgeo(pg, stone, ax, 0, H1 + 3.1, Math.PI / 2);
      const tym = new THREE.Shape();
      tym.moveTo(-hwp + 0.6, 0.15);
      tym.lineTo(hwp - 0.6, 0.15);
      tym.lineTo(0, 1.25);
      tym.lineTo(-hwp + 0.6, 0.15);
      const tg = new THREE.ExtrudeGeometry(tym, { depth: 0.1, bevelEnabled: false })
        .rotateX(Math.PI / 2)
        .translate(0, 0.05, 0);
      lgeo(tg, brickMat, ax + ss * 0.72, 0, H1 + 3.1, Math.PI / 2);
    }
    // rainwater heads dated 1805 and downpipes at the corners
    for (const [sx, sy] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ]) {
      lbox(kit.mat('black'), sx * (hl - 0.6), sy * (hw + 0.12), 0, 0.12, 0.12, H1 - 0.5);
      lbox(kit.mat('black'), sx * (hl - 0.6), sy * (hw + 0.18), H1 - 0.9, 0.45, 0.3, 0.45);
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
          kit.box(
            batch,
            steel,
            a[0],
            a[1],
            0,
            0.09,
            0.09,
            za - 0.3,
            Math.atan2(b[1] - a[1], b[0] - a[0]),
          );
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

    // ---- North wing (single-storey brick offices, Liam O'Connor) -------------------------
    const nw = byId['5c826e8b-419c-4a4f-bdf2-f456a7891245'];
    if (nw) {
      for (const poly of nw.polys) {
        const r0 = poly[0];
        kit.walls(batch, brickTex, [[r0]], 0, 3.6, { bay: 1, storey: 2 });
        kit.cornice(batch, stone, r0, 0, { height: 0.35, projection: 0.08 });
        kit.cornice(batch, stone, r0, 3.3, { height: 0.3, projection: 0.2 });
        const inner = kit.offsetRing(r0, -0.3);
        kit.walls(batch, brickMat, [[r0]], 3.6, 4.1, { bay: 1e6 });
        kit.walls(batch, brickMat, [[inner.slice().reverse()]], 3.6, 4.1, { bay: 1e6 });
        kit.cap(
          batch,
          stone,
          [[kit.offsetRing(r0, 0.06), kit.offsetRing(inner, -0.04).reverse()]],
          4.2,
        );
        kit.walls(batch, stone, [[kit.offsetRing(r0, 0.06)]], 4.1, 4.2, { bay: 1e6 });
        kit.cap(batch, lead, [[r0]], 3.7);
        for (let k = 0; k < r0.length; k++)
          kit.windowRow(batch, r0[k], r0[(k + 1) % r0.length], 0.9, {
            width: 1.2,
            height: 2.0,
            bay: 3.2,
            margin: 0.8,
            glass: sashGlass,
            frame: sashFrame,
            sill: stone,
            head: 'lintel',
            bars: 2,
          });
      }
    }
    g.add(batch.toGroup('serpentine_north'));
    return g;
  },
};
