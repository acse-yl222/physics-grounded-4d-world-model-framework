// Shepherd's Bush stations at the east end of Shepherd's Bush Green.
// Central line: surface building replaced in 2008 (Westfield s106) by a light
// glass, steel and granite pavilion with a deep flat roof; London Overground
// (West London line) station opened 28 September 2008, designed and funded by
// Westfield, a low glazed entrance building with a canopy by the Westfield
// southern entrance.
export default {
  id: 'shepherds_bush_stations',
  name: "Shepherd's Bush stations (Central line and Overground)",
  claims: [
    'f8566caf-5b2b-4bf3-bbd4-606701a7f5ef', // Shepherd's Bush tube station
    '1ffe4a65-4bba-42e1-9081-78102c9b81a3', // Shepherd's Bush Railway Station
  ],
  references: [
    {
      title: "Modernisation complete as Shepherd's Bush Tube station re-opens - TfL",
      url: 'https://tfl.gov.uk/info-for/media/press-releases/2008/october/modernisation-complete-as-shepherds-bush-tube-station-reopens',
      used_for: 'new building in glass, steel and granite, modern and light, 2008',
    },
    {
      title: "Shepherd's Bush tube station - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Shepherd%27s_Bush_tube_station',
      used_for: 'surface building completely replaced in 2008, Westfield section 106',
    },
    {
      title: "Shepherd's Bush railway station - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Shepherd%27s_Bush_railway_station',
      used_for: 'Overground station opened 28 September 2008, designed and funded by Westfield',
    },
  ],
  notes:
    'Pavilion height (~7 m) replaces the OSM 11.9 m; roof overhang, glazing grid and signage are generic for the 2008 TfL/Westfield station style. Overground station modelled as a glazed entrance with a canopy; platforms and tracks are not modelled.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const glass = kit.paintedMaterial(
      'sbs:glass',
      256,
      256,
      (x, w, h) => {
        const gr = x.createLinearGradient(0, 0, 0, h);
        gr.addColorStop(0, '#6d8796');
        gr.addColorStop(1, '#30424f');
        x.fillStyle = gr;
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(255,238,200,0.22)';
        x.fillRect(0, h * 0.55, w, h * 0.45);
        x.fillStyle = '#d5d8d9';
        for (let k = 0; k < w; k += 64) x.fillRect(k, 0, 4, h);
        x.fillRect(0, h * 0.5, w, 3);
      },
      { roughness: 0.1, metalness: 0.3, side: THREE.DoubleSide },
    );
    const granite = kit.mat('#6a6763', { roughness: 0.5, side: THREE.DoubleSide });
    const roofM = kit.mat('#d3d6d8', { roughness: 0.5, metalness: 0.3, side: THREE.DoubleSide });
    const soffit = kit.mat('#eef0f0', { emissive: '#3a3c3e', side: THREE.DoubleSide });
    const dark = kit.mat('dark_steel', DS);
    const roundel = kit.paintedMaterial(
      'sbs:roundel',
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
        x.fillRect(4, h / 2 - 26, w - 8, 52);
        x.fillStyle = '#ffffff';
        x.font = 'bold 22px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText("SHEPHERD'S BUSH", w / 2, h / 2 + 1);
      },
      DS,
    );
    const ovRoundel = kit.paintedMaterial(
      'sbs:overground',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#ffffff';
        x.fillRect(0, 0, w, h);
        x.strokeStyle = '#ee7c0e';
        x.lineWidth = 40;
        x.beginPath();
        x.arc(w / 2, h / 2, 90, 0, Math.PI * 2);
        x.stroke();
        x.fillStyle = '#0019a8';
        x.fillRect(4, h / 2 - 26, w - 8, 52);
        x.fillStyle = '#ffffff';
        x.font = 'bold 22px sans-serif';
        x.textAlign = 'center';
        x.textBaseline = 'middle';
        x.fillText('OVERGROUND', w / 2, h / 2 + 1);
      },
      DS,
    );

    const pavilion = (ring, H, overhang) => {
      const r = ring.slice();
      if (kit.ringArea(r) < 0) r.reverse();
      kit.walls(batch, granite, [[r]], 0, 0.6);
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          b = r[(k + 1) % r.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        batch.quad(
          glass,
          [a[0], a[1], 0.6],
          [b[0], b[1], 0.6],
          [b[0], b[1], H],
          [a[0], a[1], H],
          [0, 0],
          [len / 6, 0],
          [len / 6, (H - 0.6) / 6],
          [0, (H - 0.6) / 6],
        );
        // Granite-clad piers at every 6 m.
        const n = Math.max(1, Math.round(len / 6));
        const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        for (let j = 0; j <= n; j++) {
          const t = j / n;
          kit.box(
            batch,
            granite,
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            0,
            0.7,
            0.7,
            H,
            ang,
          );
        }
      }
      kit.cap(batch, kit.mat('#9a9fa2', DS), [[r]], H);
      const big = kit.offsetRing(r, overhang);
      kit.cap(batch, roofM, [[big]], H + 1.0);
      kit.cap(batch, soffit, [[big]], H, { down: true });
      kit.walls(batch, kit.mat('white_steel', DS), [[big]], H, H + 1.0);
      return r;
    };
    // Central line pavilion.
    const t = pavilion(byId['f8566caf-5b2b-4bf3-bbd4-606701a7f5ef'].polys[0][0], 6.2, 2.2);
    // Rooflights.
    const fr = kit.ringFrame(t);
    for (const off of [-0.25, 0, 0.25]) {
      const cx = fr.cx + Math.cos(fr.angle) * fr.length * off,
        cy = fr.cy + Math.sin(fr.angle) * fr.length * off;
      kit.box(
        batch,
        kit.mat('glass', DS),
        cx,
        cy,
        7.2,
        4,
        fr.width * 0.6,
        0.7,
        fr.angle + Math.PI / 2,
      );
    }
    // Totem roundels at the corners facing the Green (west side).
    const west = t
      .slice()
      .sort((p, q) => p[0] - q[0])
      .slice(0, 2);
    for (const p of west) {
      const x = p[0] - 4,
        y = p[1];
      kit.box(batch, dark, x, y, 0, 0.25, 0.25, 4.2, 0);
      batch.quad(
        roundel,
        [x - 0.15, y - 0.9, 4.2],
        [x - 0.15, y + 0.9, 4.2],
        [x - 0.15, y + 0.9, 6.0],
        [x - 0.15, y - 0.9, 6.0],
        [1, 0],
        [0, 0],
        [0, 1],
        [1, 1],
      );
      batch.quad(
        roundel,
        [x + 0.15, y + 0.9, 4.2],
        [x + 0.15, y - 0.9, 4.2],
        [x + 0.15, y - 0.9, 6.0],
        [x + 0.15, y + 0.9, 6.0],
        [1, 0],
        [0, 0],
        [0, 1],
        [1, 1],
      );
    }
    // Overground entrance with its canopy.
    const o = pavilion(byId['1ffe4a65-4bba-42e1-9081-78102c9b81a3'].polys[0][0], 4.2, 2.5);
    const op = o.reduce((m, p) => (p[1] < m[1] ? p : m), o[0]);
    kit.box(batch, dark, op[0] - 3, op[1] - 3, 0, 0.25, 0.25, 4.0, 0);
    batch.quad(
      ovRoundel,
      [op[0] - 3.9, op[1] - 3.15, 4.0],
      [op[0] - 2.1, op[1] - 3.15, 4.0],
      [op[0] - 2.1, op[1] - 3.15, 5.8],
      [op[0] - 3.9, op[1] - 3.15, 5.8],
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    );
    g.add(batch.toGroup('shepherds_bush_stations'));
    return g;
  },
};
