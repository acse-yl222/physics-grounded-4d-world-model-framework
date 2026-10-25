// Westfield London, White City (Benoy / Westfield Design, Buchan Group executive
// architects, Ian Ritchie masterplan; opened 30 October 2008; northern extension
// with John Lewis by Allies & Morrison, opened March 2018).
// A vast retail box whose malls run in a figure-of-eight under a curving,
// freeform steel-and-glass grid-shell roof (about 18-20,000 m2, spans ~24-25 m,
// Knippers Helbig / seele), with large elliptical voids over the nodes. The
// John Lewis block in the north-west is white precast concrete with a repeating
// pattern of glazed embrasures; the southern terrace has a 170 m living wall.
export default {
  id: 'westfield_london',
  name: 'Westfield London',
  claims: ['6c18544a-24db-473e-a017-c708daf43a05'],
  references: [
    {
      title: 'Westfield London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Westfield_London',
      used_for: 'architects, opening date, extension',
    },
    {
      title: 'Roof construction Westfield - Knippers Helbig',
      url: 'https://www.knippershelbig.com/en/projects/dachkonstruktion-westfield/',
      used_for: 'freeform steel-glass roof of ~18,000 m2, mesh segmentation, ~25 m span',
    },
    {
      title: 'Westfield London - Buchan',
      url: 'https://www.buchan.com.au/project/westfield-london/',
      used_for:
        'curving glass roof over a figure-eight layout, two levels plus mezzanine, elliptical voids above the nodes, The Atrium at the core',
    },
    {
      title: 'Westfield London - Benoy',
      url: 'https://benoy.com/projects/westfield-london-1',
      used_for: 'distinct food / leisure / retail zones, integration with public transport',
    },
    {
      title: 'If you build it, will they shop? - V&A blog',
      url: 'https://www.vam.ac.uk/blog/sketch-product/if-you-build-it-will-they-shop',
      used_for: 'The Village luxury area in an irregular part of the plan',
    },
    {
      title: 'Westfield London - malls.com',
      url: 'https://malls.com/uk/malls/westfield_london.html',
      used_for: 'Southern Terrace living wall, ~170 m long (low-reliability source)',
    },
    {
      title: 'John Lewis, White City - Allies and Morrison',
      url: 'https://www.alliesandmorrison.com/projects/john-lewis-white-city',
      used_for:
        'white precast concrete facade with repeating glazed embrasures, glazed ground-floor ribbon',
    },
  ],
  notes:
    'Mall street layout is taken from the Overture building parts that trace the figure-of-eight (they are unroofed inside the 13.6 m box), so the glass vaults follow those outlines; vault rise (4-5 m), node domes and the lattice pattern are stylised. Upper volumes in the northern extension other than John Lewis are drawn as clad decks. External cladding colours, entrance positions and signage are approximate.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const b = buildings[0];
    const parts = Object.fromEntries((b.parts ?? []).map((p) => [p.id.slice(0, 4), p]));
    const MALL = ['4a66', '5331', 'd278', 'd7a3', '9354', '869d', '9dd8'];
    const SKIP = ['5b59', '6231']; // low sub-volumes enclosed by the main box
    const rnd = kit.rng(0.4108);

    // ---------- materials ----------
    const clad = kit.paintedMaterial(
      'westfield:clad',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#c9ced2';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(0,0,0,0.06)';
        for (let k = 0; k < w; k += 32) x.fillRect(k, 0, 2, h);
        for (let k = 0; k < h; k += 42) x.fillRect(0, k, w, 2);
        x.fillStyle = '#e6e9ea';
        x.fillRect(0, 0, w, 14);
        // Ground-floor glazing / service doors.
        x.fillStyle = '#3a4a55';
        x.fillRect(0, h - 70, w, 62);
        x.fillStyle = '#cfd3d6';
        for (let k = 0; k < w; k += 64) x.fillRect(k, h - 70, 4, 62);
        x.fillStyle = '#9aa2a8';
        x.fillRect(0, h - 74, w, 4);
      },
      DS,
    );
    const entrance = kit.paintedMaterial(
      'westfield:entrance',
      512,
      256,
      (x, w, h) => {
        const gr = x.createLinearGradient(0, 0, 0, h);
        gr.addColorStop(0, '#7f98a6');
        gr.addColorStop(1, '#344652');
        x.fillStyle = gr;
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(255,236,190,0.25)';
        x.fillRect(0, h * 0.55, w, h * 0.45);
        x.fillStyle = '#e3e6e8';
        for (let k = 0; k < w; k += 42) x.fillRect(k, 0, 3, h);
        for (let k = 0; k < h; k += 64) x.fillRect(0, k, w, 3);
      },
      DS,
    );
    const johnLewis = kit.paintedMaterial(
      'westfield:john_lewis',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#efede6';
        x.fillRect(0, 0, w, h);
        // Repeating deep glazed embrasures in white precast.
        for (let r = 0; r < 4; r++)
          for (let c = 0; c < 8; c++) {
            const x0 = c * 64 + 14 + (r % 2) * 18,
              y0 = r * 64 + 12;
            x.fillStyle = '#bfbab0';
            x.fillRect(x0 - 3, y0 - 3, 30, 46);
            x.fillStyle = '#33424d';
            x.fillRect(x0, y0, 24, 40);
          }
      },
      DS,
    );
    const deck = kit.paintedMaterial(
      'westfield:deck',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#b9bdbf';
        x.fillRect(0, 0, w, h);
        for (let r = 0; r < 4; r++) {
          x.fillStyle = '#2b3136';
          x.fillRect(0, r * 64 + 22, w, 26);
          x.fillStyle = '#8f969b';
          for (let k = 0; k < w; k += 8) x.fillRect(k, r * 64 + 22, 2, 26);
        }
      },
      DS,
    );
    const living = kit.paintedMaterial(
      'westfield:living_wall',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#4c7a37';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.77);
        const greens = ['#3f6b2e', '#5d8f40', '#6fa04a', '#386226', '#7aa856', '#8a9c3e'];
        for (let k = 0; k < 2600; k++) {
          x.fillStyle = greens[Math.floor(r() * greens.length)];
          x.beginPath();
          x.arc(r() * w, r() * h * 0.72, 3 + r() * 6, 0, Math.PI * 2);
          x.fill();
        }
        x.fillStyle = '#3a4a55';
        x.fillRect(0, h * 0.74, w, h * 0.26);
        x.fillStyle = '#d8dcde';
        for (let k = 0; k < w; k += 64) x.fillRect(k, h * 0.74, 4, h * 0.26);
      },
      DS,
    );
    const glassRoof = kit.paintedMaterial(
      'westfield:gridshell',
      256,
      256,
      (x, w, h) => {
        const gr = x.createLinearGradient(0, 0, w, h);
        gr.addColorStop(0, '#a9c2cf');
        gr.addColorStop(1, '#7f9eae');
        x.fillStyle = gr;
        x.fillRect(0, 0, w, h);
        // Triangulated lattice of the grid shell (rod-node mesh).
        x.strokeStyle = '#eef1f2';
        x.lineWidth = 5;
        x.beginPath();
        for (let k = 0; k <= w; k += 64) {
          x.moveTo(k, 0);
          x.lineTo(k, h);
          x.moveTo(0, k);
          x.lineTo(w, k);
        }
        for (let k = -w; k <= w; k += 64) {
          x.moveTo(k, 0);
          x.lineTo(k + w, h);
        }
        x.stroke();
        x.fillStyle = 'rgba(255,255,255,0.12)';
        x.fillRect(0, 0, w / 2, h / 2);
      },
      { roughness: 0.15, metalness: 0.4, side: THREE.DoubleSide },
    );
    const roofM = kit.mat('#d7d9d7', { roughness: 0.9, side: THREE.DoubleSide });
    const roofDark = kit.mat('#a6aaa9', { roughness: 0.9, side: THREE.DoubleSide });
    const plant = kit.mat('#8d9396', DS);
    const steel = kit.mat('white_steel', DS);
    const signM = kit.paintedMaterial(
      'westfield:sign',
      512,
      128,
      (x, w, h) => {
        x.fillStyle = '#c8102e';
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#ffffff';
        x.font = 'bold 76px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText('Westfield', w / 2, h / 2 + 4);
      },
      DS,
    );

    // ---------- geometry helpers ----------
    const ccw = (r) => (kit.ringArea(r) < 0 ? r.slice().reverse() : r);
    const inside = (rings, x, y) => {
      let c = false;
      for (const r of rings)
        for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
          const a = r[i],
            q = r[j];
          if (a[1] > y !== q[1] > y && x < ((q[0] - a[0]) * (y - a[1])) / (q[1] - a[1]) + a[0])
            c = !c;
        }
      return c;
    };
    // Nearest boundary point of a set of rings.
    const nearest = (rings, x, y) => {
      let best = 1e9,
        bp = [x, y];
      for (const r of rings)
        for (let k = 0; k < r.length; k++) {
          const a = r[k],
            q = r[(k + 1) % r.length];
          const ex = q[0] - a[0],
            ey = q[1] - a[1];
          const L2 = ex * ex + ey * ey || 1;
          const t = Math.max(0, Math.min(1, ((x - a[0]) * ex + (y - a[1]) * ey) / L2));
          const px = a[0] + t * ex,
            py = a[1] + t * ey,
            d = Math.hypot(x - px, y - py);
          if (d < best) {
            best = d;
            bp = [px, py];
          }
        }
      return bp;
    };
    const segDist = (rings, x, y) => {
      let best = 1e9;
      for (const r of rings)
        for (let k = 0; k < r.length; k++) {
          const a = r[k],
            q = r[(k + 1) % r.length];
          const ex = q[0] - a[0],
            ey = q[1] - a[1];
          const L2 = ex * ex + ey * ey || 1;
          const t = Math.max(0, Math.min(1, ((x - a[0]) * ex + (y - a[1]) * ey) / L2));
          best = Math.min(best, Math.hypot(x - a[0] - t * ex, y - a[1] - t * ey));
        }
      return best;
    };
    // Edges of a ring with outward normals.
    const edges = (r) => {
      const out = [];
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          q = r[(k + 1) % r.length];
        const len = Math.hypot(q[0] - a[0], q[1] - a[1]);
        if (len < 0.05) continue;
        out.push({ a, b: q, len, nx: (q[1] - a[1]) / len, ny: -(q[0] - a[0]) / len });
      }
      return out;
    };
    const wallEdge = (m, e, z0, z1, bay = 3.6, storey = 3.4, base = 0) => {
      const n = Math.max(1, Math.round(e.len / bay));
      batch.quad(
        m,
        [e.a[0], e.a[1], z0],
        [e.b[0], e.b[1], z0],
        [e.b[0], e.b[1], z1],
        [e.a[0], e.a[1], z1],
        [0, (z0 - base) / (2 * storey)],
        [n / 4, (z0 - base) / (2 * storey)],
        [n / 4, (z1 - base) / (2 * storey)],
        [0, (z1 - base) / (2 * storey)],
      );
    };
    // Rooftop plant scattered on a flat roof.
    const plantOn = (r, z, count) => {
      const xs = r.map((p) => p[0]),
        ys = r.map((p) => p[1]);
      const x0 = Math.min(...xs),
        x1 = Math.max(...xs),
        y0 = Math.min(...ys),
        y1 = Math.max(...ys);
      let placed = 0;
      for (let t = 0; t < count * 8 && placed < count; t++) {
        const x = x0 + rnd() * (x1 - x0),
          y = y0 + rnd() * (y1 - y0);
        if (!inside([r], x, y) || segDist([r], x, y) < 6) continue;
        const w = 3 + rnd() * 6,
          d = 2 + rnd() * 4;
        kit.box(batch, plant, x, y, z, w, d, 1.2 + rnd() * 1.8, 0.26);
        placed++;
      }
    };
    // Glass grid-shell vault over a polygon: rises with distance from the edge,
    // modulated so the roof undulates along the malls; domes at the nodes.
    const NODES = [
      [-1455, 178],
      [-1437, 55],
      [-1588, 150],
      [-1520, 22],
      [-1338, 198],
      [-1378, 92],
      [-1505, 245],
    ];
    const vault = (rings, base, rise, cell = 1.6) => {
      const all = rings.flat();
      const xs = all.map((p) => p[0]),
        ys = all.map((p) => p[1]);
      const x0 = Math.min(...xs),
        y0 = Math.min(...ys);
      const nx = Math.ceil((Math.max(...xs) - x0) / cell),
        ny = Math.ceil((Math.max(...ys) - y0) / cell);
      const Z = new Map();
      const zAt = (i, j) => {
        const key = i * 100000 + j;
        if (Z.has(key)) return Z.get(key);
        let x = x0 + i * cell,
          y = y0 + j * cell;
        let z = base;
        if (!inside(rings, x, y)) [x, y] = nearest(rings, x, y);
        else {
          const d = segDist(rings, x, y);
          let node = 0;
          for (const [px, py] of NODES)
            node = Math.max(node, Math.exp(-((x - px) ** 2 + (y - py) ** 2) / (2 * 14 * 14)));
          const wave = 0.82 + 0.18 * Math.sin(x * 0.045 + 1.3) * Math.cos(y * 0.05);
          z = base + Math.sin((Math.min(1, d / 11) * Math.PI) / 2) * (rise * wave + 3.5 * node);
        }
        const v = [x, y, z];
        Z.set(key, v);
        return v;
      };
      for (let i = 0; i < nx; i++)
        for (let j = 0; j < ny; j++) {
          const xc = x0 + (i + 0.5) * cell,
            yc = y0 + (j + 0.5) * cell;
          if (!inside(rings, xc, yc)) continue;
          const P = (a, c) => zAt(a, c);
          const p00 = P(i, j),
            p10 = P(i + 1, j),
            p11 = P(i + 1, j + 1),
            p01 = P(i, j + 1);
          const uv = (p) => [p[0] / 6, p[1] / 6];
          batch.quad(glassRoof, p00, p10, p11, p01, uv(p00), uv(p10), uv(p11), uv(p01));
        }
      // Steel edge beam around the springing line.
      for (const r of rings) for (const e of edges(r)) wallEdge(steel, e, base - 0.6, base + 0.25);
    };

    // ---------- main box and northern extension ----------
    const mainRing = ccw(parts['4622'].polys[0][0]);
    const mainH = parts['4622'].h;
    // West (Wood Lane) and south long edges get glazed entrance bays + signs.
    for (const e of edges(mainRing)) {
      const isEntrance = e.len > 25 && (e.nx < -0.85 || (e.ny < -0.85 && e.a[0] < -1500));
      wallEdge(isEntrance ? entrance : clad, e, 0, mainH, 3.6, mainH / 2);
      if (isEntrance && e.len > 40) {
        const mx = (e.a[0] + e.b[0]) / 2 + e.nx * 0.3,
          my = (e.a[1] + e.b[1]) / 2 + e.ny * 0.3;
        const tx = (e.b[0] - e.a[0]) / e.len,
          ty = (e.b[1] - e.a[1]) / e.len;
        batch.quad(
          signM,
          [mx - tx * 9, my - ty * 9, mainH - 4.2],
          [mx + tx * 9, my + ty * 9, mainH - 4.2],
          [mx + tx * 9, my + ty * 9, mainH - 0.6],
          [mx - tx * 9, my - ty * 9, mainH - 0.6],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
        // Entrance canopy.
        const c0 = [e.a[0] + tx * (e.len / 2 - 14), e.a[1] + ty * (e.len / 2 - 14)],
          c1 = [e.a[0] + tx * (e.len / 2 + 14), e.a[1] + ty * (e.len / 2 + 14)];
        const cp = [
          c0,
          c1,
          [c1[0] + e.nx * 7, c1[1] + e.ny * 7],
          [c0[0] + e.nx * 7, c0[1] + e.ny * 7],
        ];
        kit.cap(batch, steel, [[ccw(cp)]], 6.2);
        kit.cap(
          batch,
          kit.mat('#e8e8e2', { emissive: '#3c3c38', side: THREE.DoubleSide }),
          [[ccw(cp)]],
          5.9,
          { down: true },
        );
      }
    }
    kit.cap(batch, roofM, [[mainRing]], mainH);
    kit.walls(batch, roofDark, [[mainRing]], mainH, mainH + 0.9);
    plantOn(mainRing, mainH, 40);

    for (const [id, p] of Object.entries(parts)) {
      if (id === '4622' || MALL.includes(id) || SKIP.includes(id)) continue;
      const r = ccw(p.polys[0][0]);
      const m = ['bcbe', '0c9f', '8270'].includes(id)
        ? johnLewis
        : ['21ce', '1aef', 'b9ae'].includes(id)
          ? deck
          : clad;
      const z0 = p.minh;
      for (const e of edges(r))
        wallEdge(
          m,
          e,
          z0,
          p.h,
          3.6,
          m === johnLewis ? 2.2 : m === deck ? 1.75 : (p.h - z0) / 2,
          z0,
        );
      kit.cap(batch, id === '0c9f' || id === '8270' ? roofDark : roofM, [[r]], p.h);
      kit.walls(batch, roofDark, [[r]], p.h, p.h + 0.8);
      if (id === '08fa') plantOn(r, p.h, 12);
    }

    // ---------- glass grid-shell roofs over the malls ----------
    for (const id of MALL) {
      const p = parts[id];
      if (!p) continue;
      const base = id === '9dd8' ? parts['08fa'].h + 0.15 : mainH + 0.15;
      vault(
        p.polys[0].map((r, k) => (k ? r : ccw(r))),
        base,
        id === '5331' ? 5.5 : 4.5,
      );
    }

    // ---------- Southern Terrace (polys[0]) ----------
    const south = b.polys.map((p) => ccw(p[0])).find((r) => Math.min(...r.map((q) => q[1])) < -100);
    if (south) {
      const H = 7.9;
      for (const e of edges(south)) {
        const green = e.len > 12 && e.ny < -0.3;
        wallEdge(green ? living : clad, e, 0, H, 3.6, H / 2);
      }
      kit.cap(batch, roofM, [[south]], H);
      // Undulating glazed canopy over the terrace.
      vault([south], H + 0.2, 4.0, 2.0);
    }
    g.add(batch.toGroup('westfield_london'));
    return g;
  },
};
