// Chelsea Academy, Lots Road, Chelsea (Feilden Clegg Bradley Studios for LDBS, opened
// 2009-10; RIBA Award and Building Awards Public Building Project of the Year 2011). A
// Church of England academy on a tight site opposite Lots Road Power Station: three
// linked teaching blocks stepping down from five storeys next to Lots Road to two storeys
// beside the Upcerne Road terraces, joined by an atrium, built up to the boundary on
// almost every side, with every roof used for play - a semi-enclosed multi-use games
// area above the sports hall and a training pitch on the roof of the activity hall.
export default {
  id: 'chelsea_academy',
  name: 'Chelsea Academy',
  claims: ['8585fd40-3ba7-47f6-86c9-efbca4de68ba'],
  references: [
    {
      title: 'Chelsea Academy - Time Out',
      url: 'https://www.timeout.com/london/learning-centres/chelsea-academy',
      used_for:
        'FCBS; built to the boundary; roofs for play: semi-enclosed MUGA above the sports hall, training pitch above the activity hall',
    },
    {
      title: 'Chelsea Academy London - e-architect',
      url: 'https://e-architect.com/london/chelsea-academy',
      used_for: 'two to four floors in linking blocks with atrium and open spaces; RIBA award 2011',
    },
    {
      title: 'Building Awards 2011: Public Building Project of the Year - Chelsea Academy',
      url: 'https://building.co.uk/building-awards-2011-public-building-project-of-the-year-chelsea-academy/5016494.article',
      used_for:
        'tight urban site opposite Lots Road power station; massing relating to two-storey terraces; Wates, Price & Myers',
    },
    {
      title: 'RBKC information page on the Chelsea Academy (Grenfell Tower Inquiry exhibit)',
      url: 'https://assets.grenfelltowerinquiry.org.uk/IWS00002082_Exhibit%20ED2_19%20-%20RBKC%20website%20information%20page%20on%20the%20Chelsea%20Academy.pdf',
      used_for:
        'three teaching blocks stepping down from five storeys by Lots Road Power Station to two storeys at Upcerne Road',
    },
  ],
  notes:
    'Block extents from the Overture parts (5-storey 17.5 m block nearest Lots Road, 3-storey 11 m middle ' +
    'block, 2-storey 7.6 m block to the north-west, the low part as the 7 m activity/sports hall wing with ' +
    'pitches on its roof). Facade materials were not found: pale brick with large windows, coloured spandrel ' +
    'panels and a glazed atrium are assumptions. Roof pitch markings and fence heights are estimates.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const a = (-61.09 * Math.PI) / 180,
      CX = 1194.9,
      CY = -3138.58;
    const ca = Math.cos(a),
      sa = Math.sin(a);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca]; // u+: towards Lots Road (SE)
    const R = (pts) => {
      const r = pts.map(([u, v]) => L(u, v));
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const brick = kit.mat('#d3c3a4', { roughness: 0.9 });
    const brickD = kit.mat('#9a8466', { roughness: 0.9 });
    const glass = kit.mat('#2e3f4a', { roughness: 0.15, metalness: 0.4 });
    const glassL = kit.mat('#8aa6b4', { roughness: 0.12, metalness: 0.4 });
    const frameM = kit.mat('#3b4144', { roughness: 0.5, metalness: 0.4 });
    const roofM = kit.mat('#8a8d8c');
    const turf = kit.mat('#3f8f4a', { roughness: 0.95 });
    const muga = kit.mat('#2d5e8c', { roughness: 0.9 });
    const fence = kit.mat('#2b2f31', {
      roughness: 0.5,
      metalness: 0.5,
      transparent: true,
      opacity: 0.55,
    });
    const colours = ['#c8553d', '#e0a43a', '#4f8a8b', '#d7d1c4'].map((c) =>
      kit.mat(c, { roughness: 0.6 }),
    );

    const block = (ring, storeys, st, colourIdx) => {
      const H = storeys * st + 0.9;
      kit.walls(batch, brick, [[ring]], 0, H, { bay: 1e6 });
      kit.cap(batch, roofM, [[ring]], H);
      kit.cornice(batch, brickD, ring, H - 0.5, { height: 0.5, projection: 0.12 });
      kit.cornice(batch, brickD, ring, 0, { height: 0.5, projection: 0.06 });
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]),
          ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
        if (len < 5) continue;
        for (let s = 0; s < storeys; s++) {
          kit.windowRow(batch, p, q, s * st + 0.8, {
            glass,
            frame: frameM,
            sill: brickD,
            head: 'none',
            width: 2.2,
            height: st - 1.3,
            bay: 3.0,
            margin: 0.9,
            bars: 1,
            depth: 0.1,
          });
          // coloured spandrel panels under every other window
          const n = Math.max(0, Math.floor((len - 1.8) / 3.0 + 0.35));
          for (let i = 0; i < n; i += 2) {
            const t = (0.9 + ((len - 1.8) * (i + 0.5)) / n) / len;
            const nx = (q[1] - p[1]) / len,
              ny = -(q[0] - p[0]) / len;
            kit.box(
              batch,
              colours[(colourIdx + i + s) % colours.length],
              p[0] + (q[0] - p[0]) * t + nx * 0.06,
              p[1] + (q[1] - p[1]) * t + ny * 0.06,
              s * st + 0.05,
              2.2,
              0.06,
              0.7,
              ang,
            );
          }
        }
      }
      return H;
    };
    // teaching blocks
    const tall = R([
      [29.0, 0.7],
      [49.8, 0.1],
      [51.0, 41.0],
      [30.4, 41.8],
    ]);
    const mid = R([
      [16.4, 6.8],
      [17.4, 29.8],
      [-14.6, 30.9],
      [-15.1, 7.1],
      [5.4, 7.1],
    ]);
    const low = R([
      [-15.1, 7.1],
      [-14.6, 30.9],
      [-14.3, 39.0],
      [-25.6, 39.3],
      [-25.9, 31.3],
      [-51.9, 40.1],
      [-53.4, 8.4],
    ]);
    const hT = block(tall, 5, 3.4, 0);
    block(mid, 3, 3.4, 1);
    block(low, 2, 3.4, 2);
    // glazed atrium between the middle and tall blocks
    {
      const at = R([
        [17.4, 6.8],
        [29.0, 6.8],
        [29.9, 26.4],
        [17.3, 27.2],
      ]);
      kit.walls(batch, glassL, [[at]], 0, 13.0, { bay: 1e6 });
      kit.cap(batch, glassL, [[at]], 13.0);
      for (let u = 18; u <= 29; u += 1.8) {
        const p = L(u, 17);
        kit.box(batch, frameM, p[0], p[1], 13.0, 0.12, 20.5, 0.25, a);
      }
    }
    // activity / sports hall wing (low part) with pitches on its roof
    {
      const hall = R([
        [49.8, 0.1],
        [29.0, 0.7],
        [29.0, 6.8],
        [17.9, 6.8],
        [17.6, -4.6],
        [7.3, -4.3],
        [6.1, -41.5],
        [25.2, -41.8],
        [25.9, -20.7],
        [52.9, -21.5],
        [53.4, -7.2],
        [49.6, -7.0],
      ]);
      const H = 7.2;
      kit.walls(batch, brickD, [[hall]], 0, H, { bay: 1e6 });
      kit.cap(batch, roofM, [[hall]], H);
      for (let k = 0; k < hall.length; k++) {
        const p = hall[k],
          q = hall[(k + 1) % hall.length];
        if (Math.hypot(q[0] - p[0], q[1] - p[1]) < 6) continue;
        kit.windowRow(batch, p, q, 4.6, {
          glass,
          frame: frameM,
          head: 'none',
          width: 3.0,
          height: 1.6,
          bay: 4.0,
          margin: 1.0,
          bars: 0,
          depth: 0.1,
        });
      }
      // training pitch (west arm) and MUGA (east arm), each fenced
      const pitches = [
        [
          [7.8, -40.8],
          [24.6, -41.0],
          [25.2, -5.0],
          [8.4, -4.8],
        ],
        [
          [26.6, -20.8],
          [52.3, -21.2],
          [52.8, -1.0],
          [27.2, -0.4],
        ],
      ];
      pitches.forEach((pp, i) => {
        const r = R(pp);
        kit.cap(batch, i ? muga : turf, [[r]], H + 0.12);
        kit.walls(batch, fence, [[r]], H, H + (i ? 5.0 : 3.5), { bay: 1e6 });
        for (let k = 0; k < 4; k++) {
          const p = r[k],
            q = r[(k + 1) % 4];
          const len = Math.hypot(q[0] - p[0], q[1] - p[1]),
            ang = Math.atan2(q[1] - p[1], q[0] - p[0]);
          for (let s = 0; s <= len; s += 3) {
            const t = s / len;
            kit.box(
              batch,
              frameM,
              p[0] + (q[0] - p[0]) * t,
              p[1] + (q[1] - p[1]) * t,
              H,
              0.1,
              0.1,
              i ? 5.0 : 3.5,
              ang,
            );
          }
        }
        // pitch lines
        const c = L((pp[0][0] + pp[2][0]) / 2, (pp[0][1] + pp[2][1]) / 2);
        const lenU = Math.abs(pp[1][0] - pp[0][0]),
          lenV = Math.abs(pp[2][1] - pp[1][1]);
        kit.box(batch, kit.mat('#f2f2ee'), c[0], c[1], H + 0.13, lenU - 1, 0.1, 0.02, a);
        kit.box(batch, kit.mat('#f2f2ee'), c[0], c[1], H + 0.13, 0.1, lenV - 1, 0.02, a);
      });
      // semi-enclosure canopy over the MUGA
      for (let u = 28; u <= 52; u += 4) {
        const p = L(u, -10.9);
        kit.box(batch, frameM, p[0], p[1], H + 5.0, 0.25, 20.6, 0.3, a);
      }
    }
    // roof terrace on the tall block: planting/play deck with balustrade
    kit.walls(batch, fence, [[kit.offsetRing(tall, -0.2)]], hT, hT + 1.2, { bay: 1e6 });
    // name sign on the Lots Road front
    {
      const sign = kit.paintedMaterial(
        'chelsea_academy:sign',
        512,
        64,
        (c, w, h) => {
          c.fillStyle = '#1f2f4a';
          c.fillRect(0, 0, w, h);
          c.fillStyle = '#ffffff';
          c.font = 'bold 38px sans-serif';
          c.textAlign = 'center';
          c.textBaseline = 'middle';
          c.fillText('CHELSEA ACADEMY', w / 2, h / 2 + 2);
        },
        { roughness: 0.5 },
      );
      const p = L(50.6, 12),
        q = L(51.1, 30);
      batch.quad(
        sign,
        [p[0], p[1], 3.6],
        [q[0], q[1], 3.6],
        [q[0], q[1], 4.6],
        [p[0], p[1], 4.6],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }
    g.add(batch.toGroup('chelsea_academy'));
    return g;
  },
};
