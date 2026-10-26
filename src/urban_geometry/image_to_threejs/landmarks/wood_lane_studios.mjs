// Wood Lane Studios (Gradpad), Imperial College postgraduate accommodation, White
// City Campus north site (Imperial West phase one, ISG, completed August 2012).
// 606 self-contained studios in four linked residential blocks (reported as up to ten
// storeys) wrapped around courtyards between Shinfield Street, the MSRH and the
// Hammersmith & City line.
export default {
  id: 'wood_lane_studios',
  name: 'Wood Lane Studios (Gradpad)',
  claims: ['1bb9d556-765b-4913-b2f8-bad00648e5c8'],
  references: [
    {
      title: 'Wood Lane Studios welcomes first residents - Imperial News',
      url: 'https://www.imperial.ac.uk/news/114895/wood-lane-studios-welcomes-first-residents/',
      used_for: '19,500 m2, 606 self-contained studios on the Imperial West site',
    },
    {
      title: 'Wood Lane Studios - TLOTT',
      url: 'https://www.tlottltd.co.uk/wood-lane-studios-west-london',
      used_for: '600 rooms over four blocks, completed August 2012, with ISG',
    },
    {
      title: 'Imperial West masterplan - Aukett Swanke',
      url: 'https://www.aukettswanke.com/projects/imperial-west-masterplan/',
      used_for: 'Wood Lane Studios as phase one of the Imperial West masterplan',
    },
    {
      title: 'Imperial College second campus gets green light - Construction Enquirer',
      url: 'https://constructionenquirer.com/2012/07/26/phase-two-of-imperial-college-campus-approved',
      used_for: 'first phase of four 10-storey accommodation blocks for 600 students',
    },
  ],
  notes:
    'Overture h=6.1 m is wrong. Block heights are estimates: linked blocks at 7 storeys with the railway-side ' +
    'block raised to 10 storeys (the press figure). Facade materials were not found in any source: pale grey ' +
    'rainscreen cassettes with one framed studio window per 2.4 m bay (projecting coloured reveals, mullion, ' +
    'transom, sill), a dark plinth with glazed common rooms, roof cores and plant are assumptions.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    let ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const ST = 3.05,
      G = 3.6;
    const H7 = G + 6 * ST,
      H10 = G + 9 * ST;

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

    const at = (e, s, d) => [e.a[0] + e.dx * s + e.nx * d, e.a[1] + e.dy * s + e.ny * d];
    const ebox = (mat, e, s0, s1, d0, d1, z0, z1) => {
      const c = at(e, (s0 + s1) / 2, (d0 + d1) / 2);
      kit.box(batch, mat, c[0], c[1], z0, s1 - s0, d1 - d0, z1 - z0, e.ang);
    };
    const equad = (mat, e, s0, s1, d, z0, z1, uv = [0, 1, 0, 1]) => {
      const p = at(e, s0, d),
        q = at(e, s1, d);
      batch.quad(
        mat,
        [p[0], p[1], z0],
        [q[0], q[1], z0],
        [q[0], q[1], z1],
        [p[0], p[1], z1],
        [uv[0], uv[2]],
        [uv[1], uv[2]],
        [uv[1], uv[3]],
        [uv[0], uv[3]],
      );
    };

    // Plain rainscreen wall (panel joints only; windows are real geometry).
    const panels = kit.paintedMaterial(
      'wls:panels',
      256,
      256,
      (c, w, h) => {
        // 2.4 m x 1 storey: two cassette panels per studio bay
        c.fillStyle = '#d7d8d4';
        c.fillRect(0, 0, w, h);
        const r = kit.rng(0.2012);
        for (let k = 0; k < 2; k++) {
          const v = 208 + Math.floor(r() * 12);
          c.fillStyle = `rgb(${v},${v + 1},${v - 3})`;
          c.fillRect((k * w) / 2 + 2, 2, w / 2 - 4, h / 2 - 4);
          c.fillRect((k * w) / 2 + 2, h / 2 + 2, w / 2 - 4, h / 2 - 4);
        }
        c.fillStyle = 'rgba(0,0,0,0.18)';
        c.fillRect(0, 0, w, 2);
        c.fillRect(0, h / 2 - 1, w, 2);
        c.fillRect(0, 0, 2, h);
        c.fillRect(w / 2 - 1, 0, 2, h);
      },
      { roughness: 0.8 },
    );
    const glassTex = kit.paintedMaterial(
      'wls:glass',
      128,
      256,
      (c, w, h) => {
        const grd = c.createLinearGradient(0, 0, 0, h);
        grd.addColorStop(0, '#8d9ba2');
        grd.addColorStop(0.15, '#4c6170');
        grd.addColorStop(1, '#2f3d47');
        c.fillStyle = grd;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d9d5c8'; // curtain at one side of the studio window
        c.fillRect(w * 0.72, h * 0.08, w * 0.22, h * 0.86);
      },
      { roughness: 0.2, metalness: 0.3 },
    );
    const reveals = [
      kit.mat('#7d9aa6', { roughness: 0.6, metalness: 0.2 }),
      kit.mat('#c4b48e', { roughness: 0.6, metalness: 0.2 }),
      kit.mat('#8a9e7c', { roughness: 0.6, metalness: 0.2 }),
    ];
    const frameM = kit.mat('#4b5257', { roughness: 0.45, metalness: 0.4 });
    const base = kit.mat('#5f6266', { roughness: 0.85 });
    const darkGlass = kit.mat('#26333c', { roughness: 0.12, metalness: 0.4 });
    const coping = kit.mat('#b9bbb8', { roughness: 0.5, metalness: 0.3 });
    const roofM = kit.mat('#8f918d');
    const lou = kit.mat('#a9adae', { roughness: 0.5, metalness: 0.3 });

    // Wall + studio windows on every edge between z0 and z1 (storey ST).
    const studioWalls = (r, z0, z1, nSt, seed) => {
      let u = 0;
      for (const e of edgesOf(r)) {
        if (e.len < 0.05) continue;
        equad(panels, e, 0, e.len, 0, z0, z1, [
          u / 4.8,
          (u + e.len) / 4.8,
          0,
          (z1 - z0) / (2 * ST),
        ]);
        u += e.len;
        if (e.len < 3) continue;
        const n = Math.floor(e.len / 2.4);
        const off = (e.len - n * 2.4) / 2;
        const col = reveals[(seed + Math.round(e.len)) % 3];
        for (let f = 0; f < nSt; f++) {
          const zs = z0 + f * ST + 0.8;
          for (let k = 0; k < n; k++) {
            const sm = off + (k + 0.5) * 2.4;
            // coloured projecting reveal box, glass, mullion, sill
            ebox(col, e, sm - 0.75, sm + 0.75, -0.02, 0.18, zs - 0.15, zs + 2.0);
            equad(glassTex, e, sm - 0.6, sm + 0.6, 0.185, zs, zs + 1.85);
            ebox(frameM, e, sm + 0.18, sm + 0.23, 0.18, 0.23, zs, zs + 1.85);
            ebox(frameM, e, sm - 0.6, sm + 0.6, 0.18, 0.23, zs + 1.35, zs + 1.4);
            ebox(coping, e, sm - 0.8, sm + 0.8, 0.0, 0.3, zs - 0.2, zs - 0.12);
          }
        }
      }
    };

    // Ground floor: dark plinth with glazed common rooms / entrances.
    {
      let u = 0;
      for (const e of edgesOf(ring)) {
        if (e.len < 0.05) continue;
        equad(base, e, 0, e.len, 0, 0, G, [u / 4, (u + e.len) / 4, 0, 1]);
        u += e.len;
        if (e.len < 3) continue;
        const n = Math.floor(e.len / 2.4);
        const off = (e.len - n * 2.4) / 2;
        for (let k = 0; k < n; k++) {
          const sm = off + (k + 0.5) * 2.4;
          equad(darkGlass, e, sm - 0.95, sm + 0.95, 0.06, 0.3, G - 0.5);
          ebox(frameM, e, sm - 1.0, sm - 0.95, 0, 0.1, 0.3, G - 0.5);
          ebox(frameM, e, sm + 0.95, sm + 1.0, 0, 0.1, 0.3, G - 0.5);
          ebox(frameM, e, sm - 1.0, sm + 1.0, 0, 0.1, G - 0.55, G - 0.5);
        }
      }
      kit.cornice(batch, coping, ring, G - 0.15, { height: 0.3, projection: 0.2 });
      kit.cornice(batch, base, ring, 0, { height: 0.25, projection: 0.1 });
    }
    // Linked 7-storey blocks on the whole footprint.
    studioWalls(ring, G, H7, 6, 0);
    kit.walls(batch, coping, [[ring]], H7, H7 + 0.6);
    kit.cap(batch, roofM, [[ring]], H7 + 0.2);
    kit.cornice(batch, coping, ring, H7 + 0.6, { height: 0.1, projection: 0.08 });
    const pin = kit.offsetRing(ring, -0.3);
    kit.walls(batch, coping, [[pin.slice().reverse()]], H7 + 0.2, H7 + 0.6);
    // Railway-side block (longest straight run of the footprint) raised to 10 storeys.
    const E = edgesOf(ring).sort((p, q) => q.len - p.len);
    const spine = E[0];
    const D = 15.8;
    const ax = spine.a,
      bx = spine.b;
    let blk = [
      ax,
      bx,
      [bx[0] - spine.nx * D, bx[1] - spine.ny * D],
      [ax[0] - spine.nx * D, ax[1] - spine.ny * D],
    ];
    if (kit.ringArea(blk) < 0) blk = blk.reverse();
    studioWalls(blk, H7, H10, 3, 1);
    kit.walls(batch, coping, [[blk]], H10, H10 + 0.6);
    kit.cap(batch, roofM, [[blk]], H10 + 0.2);
    kit.cornice(batch, coping, blk, H10 + 0.6, { height: 0.1, projection: 0.08 });
    // Lift / stair cores and louvred plant enclosures on the roofs, plus roof rails.
    const rr = kit.rng(0.2012);
    const sang = Math.atan2(spine.dy, spine.dx);
    for (let k = 0; k < 3; k++) {
      const t = 0.2 + 0.3 * k;
      const x = ax[0] + (bx[0] - ax[0]) * t - spine.nx * D * 0.5,
        y = ax[1] + (bx[1] - ax[1]) * t - spine.ny * D * 0.5;
      const w = 4 + rr() * 2;
      kit.box(batch, coping, x, y, H10 + 0.2, w, 4, 2.8, sang);
      kit.box(batch, roofM, x, y, H10 + 3.0, w + 0.3, 4.3, 0.15, sang);
    }
    {
      const e = edgesOf(blk).find((q) => Math.abs(q.len - spine.len) < 0.1 && q.a !== ax) ?? spine;
      for (let s = 6; s < e.len - 6; s += 12) {
        const c = at(e, s, 4);
        kit.box(batch, lou, c[0], c[1], H10 + 0.2, 5, 3, 2.2, sang);
      }
    }
    // Lower roofs: stair-core overruns and AOV vents where the roof is at least 9 m deep.
    {
      const inside = (r2, p) => {
        let c2 = false;
        for (let i = 0, j = r2.length - 1; i < r2.length; j = i++) {
          const [xi, yi] = r2[i],
            [xj, yj] = r2[j];
          if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi)
            c2 = !c2;
        }
        return c2;
      };
      const deep = kit.offsetRing(ring, -4.5);
      const inBlk = (p) => inside(blk, p) || inside(kit.offsetRing(blk, 3), p);
      const ex2 = kit.orientedExtent(ring, sang);
      let placed = 0;
      for (let uu = ex2.u0 + 8; uu < ex2.u1 - 4; uu += 19)
        for (let vv = ex2.v0 + 6; vv < ex2.v1 - 4; vv += 13) {
          const p = ex2.at(uu, vv, 0);
          const probe = [-3, 3].every((d) =>
            inside(ring, [p[0] + Math.cos(sang) * d, p[1] + Math.sin(sang) * d]),
          );
          if (!probe || !inside(ring, p) || inBlk(p)) continue;
          if (placed++ % 2) kit.box(batch, coping, p[0], p[1], H7 + 0.2, 3.2, 5, 3.0, sang);
          else kit.box(batch, lou, p[0], p[1], H7 + 0.2, 2.2, 2.2, 1.2, sang);
        }
      void deep;
    }
    g.add(batch.toGroup('wood_lane_studios'));
    return g;
  },
};
