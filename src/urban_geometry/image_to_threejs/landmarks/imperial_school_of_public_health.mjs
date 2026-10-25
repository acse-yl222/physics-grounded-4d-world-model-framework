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
    'and storey heights are estimates; sources disagree on 8/9/10 storeys.',
  build({ THREE, kit }) {
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
    const G = 5,
      ST = 3.8;
    const hOf = (n) => G + (n - 1) * ST;

    const lattice = (key, panel) =>
      kit.paintedMaterial(
        key,
        512,
        512,
        (c, w, h) => {
          // 6 m x 2 storeys: two 3 m bays per storey. White precast lattice, pink metal
          // reveals around large windows.
          c.fillStyle = '#ece9e2';
          c.fillRect(0, 0, w, h);
          const bw = w / 2,
            sh = h / 2;
          for (let s = 0; s < 2; s++)
            for (let k = 0; k < 2; k++) {
              const x = k * bw + 26,
                y = s * sh + 28,
                ww = bw - 52,
                hh = sh - 52;
              c.fillStyle = '#dba08f';
              c.fillRect(x, y, ww, hh);
              if (panel) {
                // screened (east) bays: mostly solid pink panel with a slot window
                c.fillStyle = '#d9a493';
                c.fillRect(x + 12, y + 12, ww - 24, hh - 24);
                c.fillStyle = '#34434e';
                c.fillRect(x + ww - 40, y + 14, 24, hh - 28);
              } else {
                const grd = c.createLinearGradient(x, y, x + ww, y + hh);
                grd.addColorStop(0, '#5a7282');
                grd.addColorStop(1, '#30414d');
                c.fillStyle = grd;
                c.fillRect(x + 24, y + 24, ww - 48, hh - 48);
                c.fillStyle = '#dba08f';
                c.fillRect(x + ww / 2 - 3, y + 14, 6, hh - 28);
                c.fillStyle = 'rgba(220,235,245,0.18)';
                c.fillRect(x + 28, y + 28, (ww - 56) * 0.25, hh - 56);
              }
            }
          c.fillStyle = 'rgba(0,0,0,0.06)';
          c.fillRect(0, sh - 3, w, 3);
        },
        { roughness: 0.75 },
      );
    const open = lattice('sph:lattice', false);
    const screened = lattice('sph:screened', true);
    const precast = kit.mat('#ece9e2', { roughness: 0.8 });
    const roofM = kit.mat('#8f918e');
    const green = kit.mat('#6f8f55', { roughness: 0.95 });
    const glass = kit.mat('dark_glass');

    // Wall with per-face material: east faces (v+) screened, others open.
    const block = (u0, u1, v0, v1, n, roofGreen) => {
      const r = rect(u0, u1, v0, v1); // n storeys including the ground floor
      const z1 = G + (n - 1) * ST;
      for (let k = 0; k < 4; k++) {
        const a = r[k],
          b = r[(k + 1) % 4];
        const ex = b[0] - a[0],
          ey = b[1] - a[1],
          len = Math.hypot(ex, ey);
        const nx = ey / len,
          ny = -ex / len;
        const east = nx * dv[0] + ny * dv[1] > 0.7;
        const m = east ? screened : open;
        batch.quad(
          m,
          [a[0], a[1], G],
          [b[0], b[1], G],
          [b[0], b[1], z1],
          [a[0], a[1], z1],
          [0, 0],
          [len / 6, 0],
          [len / 6, (z1 - G) / (2 * ST)],
          [0, (z1 - G) / (2 * ST)],
        );
      }
      kit.walls(batch, precast, [[r]], z1, z1 + 0.9);
      kit.cap(batch, roofGreen ? green : roofM, [[r]], z1 + 0.3);
      return { r, z1 };
    };
    // Ground floor: glazed, colonnade recess on the north (entrance) side.
    const base = rect(-17, 13.5, -12, 12);
    kit.walls(batch, glass, [[base]], 0, G);
    kit.cap(batch, precast, [[rect(-17, 17, -12, 12)]], G, { down: true });
    kit.walls(batch, precast, [[rect(-17, 17, -12, 12)]], G - 0.8, G);
    for (let v = -11.5; v <= 11.6; v += 23 / 7) {
      const p = P(16.6, v);
      kit.box(batch, precast, p[0], p[1], 0, 0.8, 0.8, G - 0.8, Math.atan2(du[1], du[0]));
    }
    // Massing.
    block(-5, 7, -12, 12, 10, false); // main
    block(7, 17, 0, 12, 10, false); // main, north-east
    block(7, 17, -12, 0, 4, true); // 4-storey corner towards the terrace
    block(-11, -5, -12, 12, 8, true); // stepped south terraces
    block(-17, -11, -12, 12, 6, true);
    // Rooftop plant on the main block.
    const pr = rect(-2, 12, -6, 8);
    kit.walls(batch, kit.mat('#b7bab9'), [[pr]], hOf(10), hOf(10) + 3.2);
    kit.cap(batch, roofM, [[pr]], hOf(10) + 3.2);
    // Projecting precast piers on the Wood Lane (west) and north faces for lattice depth.
    const ang = Math.atan2(du[1], du[0]);
    for (let u = -16.5; u <= 16.6; u += 3) {
      const n = u > 7 ? 4 : u > -5 ? 10 : u > -11 ? 8 : 6;
      const p = P(u, -12.2);
      kit.box(batch, precast, p[0], p[1], G, 0.45, 0.5, hOf(n) - G, ang);
    }
    for (let v = -12; v <= 12.1; v += 3) {
      const n = v < 0 ? 4 : 10;
      const p = P(17.2, v);
      kit.box(batch, precast, p[0], p[1], G, 0.5, 0.45, hOf(n) - G, ang);
    }
    g.add(batch.toGroup('imperial_school_of_public_health'));
    return g;
  },
};
