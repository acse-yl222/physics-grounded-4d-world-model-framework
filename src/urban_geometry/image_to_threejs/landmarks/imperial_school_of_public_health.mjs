// School of Public Health, Imperial College White City Campus (Allies and Morrison,
// Graham, completed 2023, officially opened 2024). Ten-storey, 7,940 m2 building that
// marks the Wood Lane entrance to the North Campus, between the Wood Lane Studios
// accommodation and the Victorian terraces of Shinfield Street. White precast concrete
// lattice framing large windows with pale terracotta / pink sand-textured metal
// cladding; stepped massing down towards the neighbours; open, transparent north side
// with an entrance colonnade; east windows screened from the residences opposite.
export default {
  id: 'imperial_school_of_public_health',
  name: 'Imperial College School of Public Health',
  claims: [],
  references: [
    {
      title: 'Allies and Morrison completes School of Public Health building at White City - BD',
      url: 'https://www.bdonline.co.uk/news/allies-and-morrison-completes-school-of-public-health-building-at-white-city/5135165.article',
      used_for:
        'ten storeys, 7,940 m2, pale terracotta-toned metal cladding with white precast panels',
    },
    {
      title:
        'School of Public Health, Imperial College London by Allies and Morrison - RIBA Journal',
      url: 'https://www.ribaj.com/buildings/school-of-public-health-london-allies-and-morrison/',
      used_for:
        'pink metal cladding framing large windows in a precast concrete lattice; steps down to four storeys in one corner; between an accommodation block and a Victorian terrace',
    },
    {
      title: 'School of Public Health - Jidipi (architect text)',
      url: 'https://architectures.jidipi.com/j00107125/en/school-of-public-health',
      used_for:
        'stepped south facade, east windows concealed from residential building opposite, transparent north facade with entrance colonnade',
    },
    {
      title: 'Imperial College School of Public Health - New London Architecture',
      url: 'https://nla.london/projects/imperial-college-school-of-public-health',
      used_for: 'Wood Lane address, entrance to the North Campus, public square on its east side',
    },
    {
      title:
        'About our building - Imperial College London (Campaign for the School of Public Health)',
      url: 'https://imperial.ac.uk/giving/discover/campaign-for-the-school-of-public-health/about-our-building',
      used_for: 'nine storeys, nearly 58,000 sq ft',
    },
    {
      title: 'Imperial opens major new building for School of Public Health - Imperial News',
      url: 'https://www.imperial.ac.uk/news/251877/imperial-opens-major-building-school-public/',
      used_for: 'opening, ten-storey description',
    },
  ],
  notes:
    'Not in the Overture footprints used by this scene (completed 2023), so claims are empty and the plan is ' +
    'a reconstruction: a 34 m x 24 m block on the vacant plot between Wood Lane, Shinfield Street and Wood ' +
    'Lane Studios, matching the descriptions (Wood Lane entrance, square to the east, accommodation and ' +
    'terrace neighbours). Exact plan, step positions (south terraces at 8 and 6 storeys, 4-storey NW corner) ' +
    'and storey heights are estimates; sources disagree on 8/9/10 storeys. The precast lattice (3 m bays, ' +
    '0.6 m piers and floor bands) framing pink metal reveals is modelled in 3D; the east-face screening ' +
    '(alternate storeys of solid pink panels with slot windows), sedum terraces with glass balustrades, ' +
    'louvred plant, sign and the furnished east square (lime trees, benches, cycle stands) are assumptions.',
  build({ THREE, kit, placeAssets }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    // Local frame: u along Wood Lane (towards NNW), v towards the east (campus square).
    const C = [-1809.2, 1117.0];
    const du = [-0.397, 0.918],
      dv = [0.918, 0.397];
    const P = (u, v) => [C[0] + du[0] * u + dv[0] * v, C[1] + du[1] * u + dv[1] * v];
    const rect = (u0, u1, v0, v1) => {
      const r = [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)];
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const angU = Math.atan2(du[1], du[0]);
    const G = 5,
      ST = 3.8;
    const top = (n) => G + (n - 1) * ST;

    // ---- materials ---------------------------------------------------------------
    const precast = kit.mat('#ece9e2', { roughness: 0.8 });
    const precast2 = kit.mat('#e3dfd6', { roughness: 0.85 });
    const pink = kit.mat('#e2ac99', { roughness: 0.55, metalness: 0.2 });
    const pinkPanel = kit.mat('#dca592', { roughness: 0.6, metalness: 0.15 });
    const glassTex = kit.paintedMaterial(
      'sph:glass',
      128,
      256,
      (c, w, h) => {
        const grd = c.createLinearGradient(0, 0, 0, h);
        grd.addColorStop(0, '#9eabb0');
        grd.addColorStop(0.12, '#5a7282');
        grd.addColorStop(1, '#30414d');
        c.fillStyle = grd;
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(220,235,245,0.14)';
        c.fillRect(w * 0.12, h * 0.2, w * 0.25, h * 0.7);
      },
      { roughness: 0.18, metalness: 0.35 },
    );
    const roofM = kit.mat('#8f918e');
    const green = kit.mat('#6f8f55', { roughness: 0.95 });
    const sedum = kit.mat('#8a9a5a', { roughness: 0.95 });
    const darkGlass = kit.mat('#26333c', { roughness: 0.12, metalness: 0.4 });
    const mull = kit.mat('#5d6266', { roughness: 0.4, metalness: 0.5 });
    const balGlass = kit.mat('#a9c3cf', {
      roughness: 0.1,
      metalness: 0.3,
      transparent: true,
      opacity: 0.45,
    });
    const lou = kit.mat('#b7bab9', { roughness: 0.5, metalness: 0.3 });
    const paving = kit.mat('#cdc7ba', { roughness: 0.9 });

    // Blocks: [u0, u1, v0, v1, storeys, green roof]
    const B = [
      [-5, 7, -12, 12, 10, false], // main
      [7, 17, 0, 12, 10, false], // main, north-east
      [7, 17, -12, 0, 4, true], // 4-storey corner towards the terrace
      [-11, -5, -12, 12, 8, true], // stepped south terraces
      [-17, -11, -12, 12, 6, true],
    ];
    // Box in (u, v, z) local space.
    const lbox = (mat, u0, u1, v0, v1, z0, z1) => {
      const c = P((u0 + u1) / 2, (v0 + v1) / 2);
      kit.box(batch, mat, c[0], c[1], z0, u1 - u0, v1 - v0, z1 - z0, angU);
    };
    // Faces of a block: fixed coordinate, axis, outward sign, span.
    const faces = (b) => [
      { axis: 'u', at: b[1], sgn: 1, s0: b[2], s1: b[3] },
      { axis: 'u', at: b[0], sgn: -1, s0: b[2], s1: b[3] },
      { axis: 'v', at: b[3], sgn: 1, s0: b[0], s1: b[1] },
      { axis: 'v', at: b[2], sgn: -1, s0: b[0], s1: b[1] },
    ];
    // Height up to which a face is hidden by an abutting block at position s along it.
    const hiddenTo = (f, s) => {
      let z = 0;
      for (const o of B) {
        const touch =
          f.axis === 'u'
            ? (f.sgn > 0 ? o[0] : o[1]) === f.at && s > o[2] && s < o[3]
            : (f.sgn > 0 ? o[2] : o[3]) === f.at && s > o[0] && s < o[1];
        if (touch) z = Math.max(z, top(o[4]) + 0.9);
      }
      return z;
    };
    // Box on a face: along s0..s1, out d0..d1 (outward from the face), z0..z1.
    const fbox = (mat, f, s0, s1, d0, d1, z0, z1) => {
      const a = f.at + f.sgn * d0,
        b2 = f.at + f.sgn * d1;
      if (f.axis === 'u') lbox(mat, Math.min(a, b2), Math.max(a, b2), s0, s1, z0, z1);
      else lbox(mat, s0, s1, Math.min(a, b2), Math.max(a, b2), z0, z1);
    };
    const fquad = (mat, f, s0, s1, d, z0, z1) => {
      const p = f.axis === 'u' ? P(f.at + f.sgn * d, s0) : P(s0, f.at + f.sgn * d);
      const q = f.axis === 'u' ? P(f.at + f.sgn * d, s1) : P(s1, f.at + f.sgn * d);
      // orient so the quad faces outward
      const out = f.axis === 'u' ? -f.sgn : f.sgn;
      const [A, Bq] = out > 0 ? [p, q] : [q, p];
      batch.quad(
        mat,
        [A[0], A[1], z0],
        [Bq[0], Bq[1], z0],
        [Bq[0], Bq[1], z1],
        [A[0], A[1], z1],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    };
    const isEast = (f) => f.axis === 'v' && f.sgn > 0;

    // ---- ground floor --------------------------------------------------------------
    {
      const base = rect(-17, 13.5, -12, 12);
      kit.walls(batch, darkGlass, [[base]], 0, G - 0.8);
      const bf = faces([-17, 13.5, -12, 12]);
      for (const f of bf) {
        const n = Math.round((f.s1 - f.s0) / 1.5);
        for (let k = 0; k <= n; k++) {
          const s = f.s0 + ((f.s1 - f.s0) * k) / n;
          fbox(mull, f, s - 0.04, s + 0.04, 0, 0.15, 0, G - 0.8);
        }
        fbox(mull, f, f.s0, f.s1, 0, 0.12, 3.0, 3.1);
      }
      kit.cap(batch, precast, [[rect(-17, 17, -12, 12)]], G - 0.8, { down: true });
      kit.walls(batch, precast, [[rect(-17, 17, -12, 12)]], G - 0.8, G);
      // precast columns: entrance colonnade on the north side and piers at 3 m elsewhere
      for (let v = -11.5; v <= 11.6; v += 23 / 7)
        lbox(precast, 16.2, 17, v - 0.4, v + 0.4, 0, G - 0.8);
      for (let u = -16.5; u <= 13.5; u += 3) {
        lbox(precast, u - 0.25, u + 0.25, -12.4, -12, 0, G - 0.8);
        lbox(precast, u - 0.25, u + 0.25, 12, 12.4, 0, G - 0.8);
      }
      // entrance doors in the colonnade
      for (const v of [-2.2, 0, 2.2]) lbox(mull, 13.5, 13.7, v - 1, v + 1, 0, 2.7);
      lbox(precast2, -17.3, 17.2, -12.3, 12.3, 0, 0.12);
    }

    // ---- upper storeys: precast lattice framing pink metal reveals --------------------
    for (const b of B) {
      const [u0, u1, v0, v1, n, gr] = b;
      const z1 = top(n);
      const r = rect(u0, u1, v0, v1);
      for (const f of faces(b)) {
        const len = f.s1 - f.s0;
        const nb = Math.max(1, Math.round(len / 3));
        const bw = len / nb;
        for (let k = 0; k < nb; k++) {
          const s0 = f.s0 + k * bw,
            s1 = s0 + bw,
            sm = (s0 + s1) / 2;
          const zh = hiddenTo(f, sm);
          for (let st = 0; st < n - 1; st++) {
            const z0 = G + st * ST;
            if (z0 + ST <= zh) continue;
            // recessed glass + pink reveals (jambs, head, sill); east face screened
            if (isEast(f) && st % 2 === 0) {
              fquad(pinkPanel, f, s0 + 0.3, s1 - 0.3, -0.25, z0 + 0.35, z0 + ST - 0.35);
              fquad(glassTex, f, s1 - 0.9, s1 - 0.45, -0.2, z0 + 0.5, z0 + ST - 0.5);
            } else {
              fquad(glassTex, f, s0 + 0.3, s1 - 0.3, -0.35, z0 + 0.35, z0 + ST - 0.35);
              fbox(pink, f, s0 + 0.3, s0 + 0.5, -0.35, 0.05, z0 + 0.35, z0 + ST - 0.35);
              fbox(pink, f, s1 - 0.5, s1 - 0.3, -0.35, 0.05, z0 + 0.35, z0 + ST - 0.35);
              fbox(pink, f, s0 + 0.3, s1 - 0.3, -0.35, 0.05, z0 + ST - 0.6, z0 + ST - 0.35);
              fbox(pink, f, s0 + 0.3, s1 - 0.3, -0.35, 0.1, z0 + 0.35, z0 + 0.55);
              fbox(mull, f, sm - 0.04, sm + 0.04, -0.35, -0.25, z0 + 0.55, z0 + ST - 0.6);
            }
            // back-up wall behind the lattice
            fquad(precast2, f, s0, s1, -0.36, z0, z0 + 0.35);
          }
          // lattice piers (full height of the visible part)
          const zs = Math.max(G, zh);
          if (zs < z1) {
            fbox(precast, f, s0 - 0.3, s0 + 0.3, -0.36, 0.3, zs, z1);
            if (k === nb - 1) fbox(precast, f, s1 - 0.3, s1 + 0.3, -0.36, 0.3, zs, z1);
          }
        }
        // lattice floor bands
        for (let st = 0; st <= n - 1; st++) {
          const z = G + st * ST;
          const zb = st === n - 1 ? z + 0.9 : z + 0.35;
          // split band where hidden
          for (let k = 0; k < nb; k++) {
            const s0 = f.s0 + k * bw;
            if (zb <= hiddenTo(f, s0 + bw / 2)) continue;
            fbox(precast, f, s0, s0 + bw, -0.36, 0.3, z - 0.2, zb);
          }
        }
      }
      // roofs: parapet coping, green / sedum roofs on the steps, plain roof on the top
      kit.cap(batch, gr ? green : roofM, [[r]], z1 + 0.3);
      kit.cornice(batch, precast, r, z1 + 0.9, { height: 0.12, projection: 0.35 });
      if (gr) {
        // terrace: paved strip, glass balustrade, planters on the sedum roof
        const t = rect(u0 + 1.2, u1 - 1.2, v0 + 1.2, v1 - 1.2);
        kit.cap(batch, sedum, [[t]], z1 + 0.35);
        for (const f of faces([u0 + 0.6, u1 - 0.6, v0 + 0.6, v1 - 0.6])) {
          const s0 = f.s0,
            s1 = f.s1;
          const zh = hiddenTo({ ...f, at: f.at + f.sgn * 0.6 }, (s0 + s1) / 2);
          if (zh > z1 + 1) continue;
          fquad(balGlass, f, s0, s1, 0, z1 + 0.9, z1 + 2.0);
          fquad(balGlass, { ...f, sgn: -f.sgn }, s0, s1, 0, z1 + 0.9, z1 + 2.0);
          fbox(mull, f, s0, s1, -0.04, 0.04, z1 + 2.0, z1 + 2.06);
        }
      }
    }
    // Rooftop plant on the main block: louvred screen and flues.
    {
      const zr = top(10) + 0.3;
      const pf = faces([-2, 12, -6, 8]);
      lbox(kit.mat('#6c7073'), -1.7, 11.7, -5.7, 7.7, zr, zr + 3.0);
      for (const f of pf) {
        for (let z = zr + 0.2; z < zr + 3.2; z += 0.3)
          fbox(lou, f, f.s0, f.s1, 0, 0.12, z, z + 0.06);
        for (let s = f.s0; s <= f.s1 + 0.01; s += 2)
          fbox(mull, f, s - 0.05, s + 0.05, 0, 0.16, zr, zr + 3.3);
      }
      const flue = new THREE.CylinderGeometry(0.35, 0.35, 2.4, 10).rotateX(Math.PI / 2);
      for (const [u, v] of [
        [1, 0],
        [4, 0],
        [7, 0],
      ]) {
        const c = P(u, v);
        batch.addGeometry(
          kit.mat('steel'),
          flue,
          new THREE.Matrix4().makeTranslation(c[0], c[1], zr + 4.2),
        );
      }
      flue.dispose();
    }

    // ---- public square on the east side: paving, trees, benches, cycle stands ---------
    {
      const sq = rect(-17, 17, 12.4, 22);
      kit.cap(batch, paving, [[sq]], 0.05, { scale: 3 });
      for (let u = -15; u <= 15.1; u += 3)
        lbox(kit.mat('#b3ada0'), u - 0.04, u + 0.04, 12.4, 22, 0.05, 0.062);
      const trees = [],
        benches = [];
      const rr = kit.rng(0.2024);
      for (const u of [-13, -5, 3, 11]) {
        trees.push([...P(u, 18.5), rr() * 6, 7 + rr() * 2]);
        lbox(kit.mat('#5b4a3a'), u - 0.9, u + 0.9, 17.6, 19.4, 0.05, 0.08);
        benches.push([...P(u + 4, 18.5), angU + Math.PI]);
      }
      g.add(placeAssets('lime_tree', trees, { scaleOf: (p) => p[3] }));
      g.add(placeAssets('bench', benches));
      g.add(
        placeAssets(
          'bicycle_stand',
          [0, 1, 2, 3, 4, 5].map((k) => [...P(-16 + k * 1.1, 14), angU]),
        ),
      );
      g.add(
        placeAssets(
          'bollard',
          [-2, 0, 2].map((v) => [...P(18.2, v), 0]),
        ),
      );
      // name sign on the colonnade fascia
      const sign = kit.paintedMaterial(
        'sph:sign',
        512,
        64,
        (cx, w, h) => {
          cx.fillStyle = '#ece9e2';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#0f2f5a';
          cx.font = 'bold 32px sans-serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('SCHOOL OF PUBLIC HEALTH', w / 2, h / 2 + 2);
        },
        { roughness: 0.6 },
      );
      fquad(sign, { axis: 'u', at: 17, sgn: 1, s0: 0, s1: 0 }, -6, 6, 0.02, G - 0.75, G - 0.1);
    }
    g.add(batch.toGroup('imperial_school_of_public_health'));
    return g;
  },
};
