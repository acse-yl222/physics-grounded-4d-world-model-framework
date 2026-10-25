// Wood Lane station (Hammersmith & City / Circle), Ian Ritchie Architects, 2008.
// A two-storey steel and glass building squeezed between neighbours around the
// 19th-century brick viaduct, with a suspended 25 m glass screen facade to Wood
// Lane, shot-peened stainless steel cladding and gold anodised aluminium soffits.
// Platforms above on the viaduct (not modelled separately).
export default {
  id: 'wood_lane_station',
  name: 'Wood Lane station',
  claims: ['e3f1fac8-65cb-4472-bf6b-f4423e2264cc'],
  references: [
    {
      title: 'Wood Lane Station - Ritchie Studio',
      url: 'https://www.ritchie.studio/projects/wood_lane_station/',
      used_for:
        'shot peened stainless steel cladding, gold anodised aluminium ceiling panels, site between owners around the brick viaduct',
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
      used_for: 'opening October 2008, Westfield-funded',
    },
  ],
  notes:
    'Height reduced from 17.4 m (OSM) to ~11 m for a two-storey station. Canopy curvature, viaduct arch rhythm and platform canopy form are inferred from text descriptions; no photos could be viewed.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const ring = buildings[0].polys[0][0].slice();
    if (kit.ringArea(ring) < 0) ring.reverse();
    const steel = kit.paintedMaterial(
      'wood_lane:steel',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#b8bcbd';
        x.fillRect(0, 0, w, h);
        const r = kit.rng(0.51);
        for (let k = 0; k < 1500; k++) {
          x.fillStyle = `rgba(${r() > 0.5 ? 255 : 90},${r() > 0.5 ? 255 : 95},${r() > 0.5 ? 255 : 100},0.08)`;
          x.fillRect(r() * w, r() * h, 2, 2);
        }
        x.fillStyle = '#9ea2a4';
        for (let k = 0; k < w; k += 64) x.fillRect(k, 0, 2, h);
        for (let k = 0; k < h; k += 128) x.fillRect(0, k, w, 2);
      },
      { metalness: 0.6, roughness: 0.4, side: THREE.DoubleSide },
    );
    const glass = kit.paintedMaterial(
      'wood_lane:glass',
      256,
      256,
      (x, w, h) => {
        const gr = x.createLinearGradient(0, 0, 0, h);
        gr.addColorStop(0, '#6f8a99');
        gr.addColorStop(1, '#2f4250');
        x.fillStyle = gr;
        x.fillRect(0, 0, w, h);
        x.fillStyle = '#d8d6cf';
        for (let k = 0; k < w; k += 64) x.fillRect(k, 0, 3, h);
        for (let k = 0; k < h; k += 85) x.fillRect(0, k, w, 2);
        // Warm interior glow with gold ceiling seen through the screen.
        x.fillStyle = 'rgba(214,176,76,0.35)';
        x.fillRect(0, 86, w, 12);
        x.fillStyle = 'rgba(255,230,170,0.18)';
        x.fillRect(0, 170, w, 86);
      },
      { roughness: 0.1, metalness: 0.3, side: THREE.DoubleSide },
    );
    const gold = kit.mat('#cfa54f', {
      roughness: 0.4,
      metalness: 0.5,
      emissive: '#5a4318',
      side: THREE.DoubleSide,
    });
    const roofM = kit.mat('#c9cdd0', { roughness: 0.5, metalness: 0.4, side: THREE.DoubleSide });
    const dark = kit.mat('dark_steel', DS);

    // Front edge = the westernmost (Wood Lane) edge.
    let fi = 0,
      best = 1e9;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const mx = (a[0] + b[0]) / 2;
      if (len > 15 && mx < best) {
        best = mx;
        fi = k;
      }
    }
    const FA = ring[fi],
      FB = ring[(fi + 1) % ring.length];
    const flen = Math.hypot(FB[0] - FA[0], FB[1] - FA[1]);
    const ux = (FB[0] - FA[0]) / flen,
      uy = (FB[1] - FA[1]) / flen;
    const nx = uy,
      ny = -ux; // outward (west) for CCW ring
    const fAng = Math.atan2(uy, ux);
    const at = (t, d, z) => [FA[0] + ux * t - nx * d, FA[1] + uy * t - ny * d, z]; // d inward

    const H = 9.5;
    // Steel-clad body; glass screen on the front edge.
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const m = k === fi ? glass : steel;
      const z1 = k === fi ? 11 : H;
      batch.quad(
        m,
        [a[0], a[1], 0],
        [b[0], b[1], 0],
        [b[0], b[1], z1],
        [a[0], a[1], z1],
        [0, 0],
        [len / 6, 0],
        [len / 6, z1 / 6],
        [0, z1 / 6],
      );
    }
    kit.cap(batch, roofM, [[ring]], H);
    // Curved roof canopy over the front: a shallow barrel sweeping out over the
    // pavement, gold anodised soffit underneath.
    const segs = 14,
      D0 = -4,
      D1 = 12;
    for (let k = 0; k < segs; k++) {
      const d0 = D0 + ((D1 - D0) * k) / segs,
        d1 = D0 + ((D1 - D0) * (k + 1)) / segs;
      const zf = (d) =>
        11.6 -
        2.2 * ((d - D0) / (D1 - D0)) ** 1.6 +
        0.8 * Math.sin(((d - D0) / (D1 - D0)) * Math.PI);
      const z0 = zf(d0),
        z1 = zf(d1);
      for (const [m, dz] of [
        [roofM, 0.35],
        [gold, 0],
      ]) {
        batch.quad(
          m,
          at(-1.5, d0, z0 + dz),
          at(flen + 1.5, d0, z0 + dz),
          at(flen + 1.5, d1, z1 + dz),
          at(-1.5, d1, z1 + dz),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      if (k === 0)
        batch.quad(
          dark,
          at(-1.5, d0, z0),
          at(flen + 1.5, d0, z0),
          at(flen + 1.5, d0, z0 + 0.35),
          at(-1.5, d0, z0 + 0.35),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
    }
    // Slender steel columns carrying the canopy edge.
    for (const t of [2, flen / 2, flen - 2]) {
      const p = at(t, -3.4, 0);
      kit.box(batch, dark, p[0], p[1], 0, 0.3, 0.3, 11.2, fAng);
    }
    // Underground roundel and name board on the screen.
    const roundel = kit.paintedMaterial(
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
    {
      const p0 = at(flen * 0.3 - 1.6, -0.25, 0),
        p1 = at(flen * 0.3 + 1.6, -0.25, 0);
      batch.quad(
        roundel,
        [p0[0], p0[1], 5.4],
        [p1[0], p1[1], 5.4],
        [p1[0], p1[1], 8.6],
        [p0[0], p0[1], 8.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    // Glazed rooflight strip over the platform stair along the long diagonal.
    {
      const tip = ring.reduce((m, p) => (p[0] > m[0] ? p : m), ring[0]);
      const vb = ring.reduce((m, p) => (p[1] < m[1] ? p : m), ring[0]);
      const vx = tip[0] - vb[0],
        vy = tip[1] - vb[1],
        vl = Math.hypot(vx, vy);
      const vAng = Math.atan2(vy, vx);
      const nx2 = -vy / vl,
        ny2 = vx / vl;
      const cxx = (tip[0] + vb[0]) / 2 + nx2 * 4.5,
        cyy = (tip[1] + vb[1]) / 2 + ny2 * 4.5;
      kit.box(batch, kit.mat('glass', DS), cxx, cyy, H, vl * 0.7, 2.6, 0.8, vAng);
      kit.box(batch, steel, cxx, cyy, H, vl * 0.7 + 0.4, 3.0, 0.3, vAng);
    }
    g.add(batch.toGroup('wood_lane_station'));
    return g;
  },
};
