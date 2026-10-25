// Olympia London, Hammersmith Road / Olympia Way (Kensington, W14).
// Grand Hall (1885-86, Henry Edward Coe with James Edmeston; ironwork by Andrew
// Handyside of Derby): red brick with stone dressings under a huge iron-and-glass
// barrel vault, lower glazed side aisles, an Italianate red-brick and Portland stone
// entrance front on Olympia Way facing Kensington (Olympia) station.
// Olympia National (1923, Holman & Goodrham): red brick hall with an arched iron and
// glazed roof in the south-east corner, principal facade on Hammersmith Road with an
// Emberton-era entrance canopy and a corner entrance at Olympia Way.
export default {
  id: 'olympia_london',
  name: 'Olympia London (Grand Hall and National Hall)',
  claims: ['7d7a7e76-085a-4c57-a013-00ede1ae9e26', '1a26fac1-f055-47e7-a119-92b4fe25f1a9'],
  references: [
    {
      title: 'Olympia London - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Olympia_London',
      used_for:
        'architects and dates (Coe 1886 Grand Hall, 1923 National Hall, 1929 Emberton Olympia Central), Olympia signage on Hammersmith Road',
    },
    {
      title: 'Grand Hall and Pillar Hall, Olympia Exhibition Centre - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101096048',
      used_for:
        'red brick with stone dressings, iron glazed roof by Handyside, Italianate entrance front on Olympia Way opposite the station',
    },
    {
      title: 'Olympia National and Olympia Central - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101456674-olympia-national-and-olympia-central-olympia-exhibition-centre-avonmore-and-brook-green-ward',
      used_for:
        'National Hall in the south-east corner, red brick, iron and glazed roof, facade on Hammersmith Road with corner entrance at Olympia Way',
    },
    {
      title: 'Did You Know The Roof Of Olympia Is Retractable? - Londonist',
      url: 'https://londonist.com/2014/08/climbing-to-the-top-of-olympia',
      used_for: 'Grand Hall roof height (about 115 ft) and Victorian ironwork',
    },
    {
      title: 'The Grand Hall - Olympia',
      url: 'https://www.olympia.co.uk/space/the-grand-hall',
      used_for: 'hall dimensions about 137-140 m by 76 m',
    },
    {
      title: "Olympia's National Hall receives £2m upgrade",
      url: 'https://www.olympia.co.uk/press/olympias-national-hall-receives-2m-upgrade',
      used_for: 'National Hall arched roof re-glazed',
    },
  ],
  notes:
    'Grand Hall barrel crown set to 35 m (sources give 115-135 ft), nave span ~50 m within the Overture outline; ' +
    'side aisles 15 m. National Hall barrel assumed parallel to the Grand Hall, crown 26 m. Entrance fronts are ' +
    'painted approximations from listing text (no photos available). The 2026 Heatherwick/SPPARC redevelopment ' +
    '(theatre, hotels, offices, canopy) is not in the footprint data and is not modelled.',
  build(ctx) {
    const { THREE, kit, byId, frame } = ctx;
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const grand = byId['7d7a7e76-085a-4c57-a013-00ede1ae9e26'];
    const national = byId['1a26fac1-f055-47e7-a119-92b4fe25f1a9'];
    const A = frame.angle,
      ca = Math.cos(A),
      sa = Math.sin(A);
    const W = (u, v, z) => [frame.cx + u * ca - v * sa, frame.cy + u * sa + v * ca, z];
    const toLocal = ([x, y]) => [
      (x - frame.cx) * ca + (y - frame.cy) * sa,
      -(x - frame.cx) * sa + (y - frame.cy) * ca,
    ];
    const ext = (ring) => {
      let u0 = 1e9,
        u1 = -1e9,
        v0 = 1e9,
        v1 = -1e9;
      for (const p of ring) {
        const [u, v] = toLocal(p);
        u0 = Math.min(u0, u);
        u1 = Math.max(u1, u);
        v0 = Math.min(v0, v);
        v1 = Math.max(v1, v);
      }
      return { u0, u1, v0, v1 };
    };
    const M = (u, v, z, rot = 0) =>
      new THREE.Matrix4().makeRotationZ(A + rot).setPosition(...W(u, v, z));
    const addGeo = (m, geo, mtx) => {
      batch.addGeometry(m, geo, mtx);
      geo.dispose();
    };
    const lbox = (m, u, v, z0, du, dv, dz) =>
      addGeo(m, new THREE.BoxGeometry(du, dv, dz), M(u, v, z0 + dz / 2));

    // Materials.
    // Hall walls: one texture tile = 4 bays x full wall height; red brick with stone
    // pilasters, plinth and string course, tall round-arched upper windows.
    const brickFacade = kit.paintedMaterial('olympia_london:hallwall', 512, 256, (c, w, h) => {
      c.fillStyle = '#97503a';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(55,20,10,0.22)';
      for (let y = 0; y < h; y += 3) c.fillRect(0, y, w, 1);
      const st = '#d6cdb6';
      c.fillStyle = st;
      c.fillRect(0, 0, w, 10); // cornice band
      c.fillRect(0, 150, w, 7); // string course
      c.fillRect(0, h - 18, w, 18); // plinth
      const bw = w / 4;
      for (let i = 0; i < 4; i++) {
        const x = i * bw;
        c.fillStyle = st;
        c.fillRect(x, 10, 12, h - 28);
        c.fillStyle = '#26313a';
        const ww = bw - 46,
          wx = x + 29;
        c.fillRect(wx, 52, ww, 90);
        c.beginPath();
        c.arc(wx + ww / 2, 52, ww / 2, Math.PI, 0);
        c.fill();
        c.fillStyle = st;
        c.fillRect(wx - 4, 140, ww + 8, 5);
        c.fillRect(wx + ww / 2 - 2, 30, 4, 112);
        c.fillStyle = 'rgba(40,15,8,0.35)';
        c.fillRect(wx, 172, ww, 56); // recessed blind panel
        c.fillStyle = '#2c363e';
        c.fillRect(wx + ww * 0.3, 182, ww * 0.4, 40);
      }
    });
    const brick = kit.mat('red_brick');
    const stone = kit.mat('portland_stone');
    const lead = kit.mat('lead');
    const iron = kit.mat('#7a8489', { roughness: 0.55, metalness: 0.35 });
    const glazing = kit.paintedMaterial(
      'olympia_london:glazing',
      256,
      256,
      (c, w, h) => {
        c.fillStyle = '#a9bcc6';
        c.fillRect(0, 0, w, h);
        // Panes with slight variation, white-ish glazing bars.
        for (let i = 0; i < 8; i++)
          for (let j = 0; j < 4; j++) {
            const t = ((i * 7 + j * 13) % 9) / 9;
            c.fillStyle = `rgb(${150 + t * 30},${172 + t * 25},${185 + t * 20})`;
            c.fillRect(i * 32 + 2, j * 64 + 2, 28, 60);
          }
        c.fillStyle = '#5b646a';
        for (let i = 0; i <= 8; i++) c.fillRect(i * 32 - 1, 0, 3, h);
        c.fillRect(0, 0, w, 4);
        c.fillRect(0, 128, w, 3);
      },
      { roughness: 0.25, metalness: 0.3 },
    );
    const fanGlass = kit.paintedMaterial(
      'olympia_london:fan',
      512,
      256,
      (c, w, h) => {
        // Semicircular gable end glazing with radial and concentric bars.
        c.fillStyle = '#9fb2bd';
        c.fillRect(0, 0, w, h);
        c.strokeStyle = '#4c555a';
        c.lineWidth = 4;
        const cx = w / 2,
          cy = h;
        for (let k = 0; k <= 16; k++) {
          const a = Math.PI + (k / 16) * Math.PI;
          c.beginPath();
          c.moveTo(cx, cy);
          c.lineTo(cx + Math.cos(a) * w, cy + Math.sin(a) * w);
          c.stroke();
        }
        for (const r of [0.25, 0.5, 0.75]) {
          c.beginPath();
          c.ellipse(cx, cy, (w / 2) * r, h * r, 0, Math.PI, 2 * Math.PI);
          c.stroke();
        }
        c.lineWidth = 2;
        for (let x = 0; x < w; x += 16) {
          c.beginPath();
          c.moveTo(x, 0);
          c.lineTo(x, h);
          c.stroke();
        }
      },
      { roughness: 0.3, metalness: 0.2 },
    );
    const entrance = kit.paintedMaterial('olympia_london:entrance', 1024, 256, (c, w, h) => {
      // Italianate front: red brick, stone pilasters, round-arched windows, stone
      // cornice and a central arched entrance with lettering.
      c.fillStyle = '#9a4d38';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(60,20,10,0.25)';
      for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
      const stoneC = '#dcd3bd';
      c.fillStyle = stoneC;
      c.fillRect(0, 0, w, 18); // cornice and balustrade
      c.fillRect(0, 120, w, 9); // string course
      c.fillRect(0, h - 22, w, 22); // plinth
      const bays = 15;
      const bw = w / bays;
      for (let i = 0; i < bays; i++) {
        const x = i * bw;
        c.fillStyle = stoneC;
        c.fillRect(x, 18, 7, h - 40); // pilaster
        if (i === 7) continue;
        c.fillStyle = '#2f3a42';
        // upper arched windows
        c.fillRect(x + 16, 50, bw - 26, 60);
        c.beginPath();
        c.arc(x + 16 + (bw - 26) / 2, 50, (bw - 26) / 2, Math.PI, 0);
        c.fill();
        c.fillStyle = stoneC;
        c.fillRect(x + 12, 108, bw - 18, 4);
        // lower windows
        c.fillStyle = '#2f3a42';
        c.fillRect(x + 16, 150, bw - 26, 70);
        c.beginPath();
        c.arc(x + 16 + (bw - 26) / 2, 150, (bw - 26) / 2, Math.PI, 0);
        c.fill();
      }
      // central entrance arch
      const cx = 7.5 * bw;
      c.fillStyle = stoneC;
      c.fillRect(cx - bw * 0.75, 18, bw * 1.5, h - 40);
      c.fillStyle = '#28323a';
      c.fillRect(cx - bw * 0.48, 120, bw * 0.96, h - 142);
      c.beginPath();
      c.arc(cx, 120, bw * 0.48, Math.PI, 0);
      c.fill();
      c.fillStyle = '#7a2f22';
      c.font = 'bold 22px serif';
      c.textAlign = 'center';
      c.fillText('OLYMPIA', cx, 60);
    });
    const hammersmithFront = kit.paintedMaterial(
      'olympia_london:national_front',
      1024,
      256,
      (c, w, h) => {
        // National Hall front to Hammersmith Road: red brick and stone with tall
        // windows; white OLYMPIA LONDON lettering on a blue band over the canopy.
        c.fillStyle = '#93503a';
        c.fillRect(0, 0, w, h);
        c.fillStyle = 'rgba(50,20,10,0.22)';
        for (let y = 0; y < h; y += 4) c.fillRect(0, y, w, 1);
        c.fillStyle = '#d8cfb8';
        c.fillRect(0, 0, w, 14);
        c.fillRect(0, h - 70, w, 8);
        const bays = 12;
        const bw = w / bays;
        for (let i = 0; i < bays; i++) {
          c.fillStyle = '#d8cfb8';
          c.fillRect(i * bw, 14, 8, h - 84);
          c.fillStyle = '#2c3740';
          c.fillRect(i * bw + 20, 40, bw - 32, 130);
          c.fillStyle = '#d8cfb8';
          for (let k = 1; k < 4; k++) c.fillRect(i * bw + 20, 40 + k * 32, bw - 32, 3);
        }
        c.fillStyle = '#1d3f7a';
        c.fillRect(w * 0.25, 18, w * 0.5, 22);
        c.fillStyle = '#ffffff';
        c.font = 'bold 18px sans-serif';
        c.textAlign = 'center';
        c.fillText('OLYMPIA  LONDON', w / 2, 35);
        // glazed ground floor entrances
        c.fillStyle = '#26313a';
        c.fillRect(0, h - 60, w, 60);
        c.fillStyle = '#c9c4b8';
        for (let x = 0; x < w; x += 42) c.fillRect(x, h - 60, 5, 60);
      },
    );

    // Barrel vault helper: segmental arch across v (centre vc, half-span a, spring
    // zs, rise r) running from u = ua to ub. Glazing quads plus iron ribs.
    const barrel = (
      ua,
      ub,
      vc,
      a,
      zs,
      r,
      { segs = 18, ribStep = 7, ridge = true, endGlass = true } = {},
    ) => {
      const R = (a * a + r * r) / (2 * r),
        zc = zs + r - R,
        th = Math.asin(Math.min(1, a / R));
      const prof = [];
      for (let k = 0; k <= segs; k++) {
        const t = -th + (2 * th * k) / segs;
        prof.push([vc + R * Math.sin(t), zc + R * Math.cos(t), R * t]);
      }
      const L = ub - ua;
      for (let k = 0; k < segs; k++) {
        const [v0, z0, s0] = prof[k],
          [v1, z1, s1] = prof[k + 1];
        batch.quad(
          glazing,
          W(ub, v0, z0),
          W(ub, v1, z1),
          W(ua, v1, z1),
          W(ua, v0, z0),
          [s0 / 8, L / 8],
          [s1 / 8, L / 8],
          [s1 / 8, 0],
          [s0 / 8, 0],
        );
        // underside (visible through ends)
        batch.quad(
          iron,
          W(ua, v0, z0 - 0.05),
          W(ua, v1, z1 - 0.05),
          W(ub, v1, z1 - 0.05),
          W(ub, v0, z0 - 0.05),
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      // Ribs.
      const nr = Math.max(2, Math.round(L / ribStep));
      for (let i = 0; i <= nr; i++) {
        const u = ua + (L * i) / nr;
        for (let k = 0; k < segs; k++) {
          const [v0, z0] = prof[k],
            [v1, z1] = prof[k + 1];
          const len = Math.hypot(v1 - v0, z1 - z0);
          const geo = new THREE.BoxGeometry(0.7, len + 0.05, 0.6);
          const m = new THREE.Matrix4()
            .makeRotationZ(A)
            .multiply(new THREE.Matrix4().makeRotationX(Math.atan2(z1 - z0, v1 - v0)))
            .setPosition(...W(u, (v0 + v1) / 2, (z0 + z1) / 2 + 0.3));
          addGeo(iron, geo, m);
        }
      }
      // Longitudinal purlins at a few heights.
      for (const k of [3, Math.round(segs / 2) - 3, Math.round(segs / 2) + 3, segs - 3]) {
        const [v, z] = prof[k];
        lbox(iron, (ua + ub) / 2, v, z + 0.1, L, 0.35, 0.35);
      }
      // Ridge lantern vent along the crown.
      if (ridge) {
        lbox(kit.mat('#9aa3a6'), (ua + ub) / 2, vc, zs + r - 0.3, L - 2, 3.2, 1.4);
        lbox(iron, (ua + ub) / 2, vc, zs + r + 1.3, L - 2, 5.2, 0.35);
      }
      // Arched end screens (glazed fans) closing the barrel.
      if (endGlass)
        for (const [u, flip] of [
          [ua, -1],
          [ub, 1],
        ]) {
          const verts = [],
            uvs = [],
            tris = [];
          verts.push(W(u, vc, zs));
          uvs.push([0.5, 0]);
          for (const [v, z] of prof) {
            verts.push(W(u, v, z));
            uvs.push([0.5 + (v - vc) / (2 * a), (z - zs) / r]);
          }
          for (let k = 1; k <= segs; k++)
            flip > 0 ? tris.push(0, k + 1, k) : tris.push(0, k, k + 1);
          batch.add(fanGlass, verts, uvs, tris);
          // arch rib on the end
          for (let k = 0; k < segs; k++) {
            const [v0, z0] = prof[k],
              [v1, z1] = prof[k + 1];
            const len = Math.hypot(v1 - v0, z1 - z0);
            const geo = new THREE.BoxGeometry(1.4, len + 0.1, 1.2);
            const m = new THREE.Matrix4()
              .makeRotationZ(A)
              .multiply(new THREE.Matrix4().makeRotationX(Math.atan2(z1 - z0, v1 - v0)))
              .setPosition(...W(u, (v0 + v1) / 2, (z0 + z1) / 2));
            addGeo(iron, geo, m);
          }
        }
      return prof;
    };

    // ---- Grand Hall ----
    const gRing = grand.polys[0][0];
    const ge = ext(gRing);
    const aisleH = 15;
    kit.walls(batch, brickFacade, grand.polys, 0, aisleH, { bay: 6, storey: aisleH / 2 });
    lbox(stone, 0, 0, aisleH - 0.2, 0.01, 0.01, 0.01); // keep material ordering stable
    // stone cornice following the outline
    for (const ring of grand.polys[0])
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 1) continue;
        const geo = new THREE.BoxGeometry(len, 1.0, 0.9);
        const m = new THREE.Matrix4()
          .makeRotationZ(Math.atan2(q[1] - p[1], q[0] - p[0]))
          .setPosition((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, aisleH + 0.2);
        addGeo(stone, geo, m);
      }
    // aisle roofs: glazed lean-to strips over lead
    kit.cap(batch, lead, grand.polys, aisleH, { scale: 6 });
    const gvc = (ge.v0 + ge.v1) / 2;
    const gHalf = Math.min(25.5, (ge.v1 - ge.v0) / 2 - 9);
    const gua = ge.u0 + 6,
      gub = ge.u1 - 6;
    for (const side of [-1, 1]) {
      const vIn = gvc + side * gHalf,
        vOut = gvc + side * (gHalf + 7);
      for (let u = gua + 2; u < gub - 6; u += 9) {
        // ridged aisle lanterns
        const verts = [
          W(u, vOut, aisleH + 0.3),
          W(u + 7, vOut, aisleH + 0.3),
          W(u + 7, vIn, aisleH + 3.2),
          W(u, vIn, aisleH + 3.2),
        ];
        batch.add(
          glazing,
          side > 0 ? verts.slice().reverse() : verts,
          [
            [0, 0],
            [1, 0],
            [1, 0.4],
            [0, 0.4],
          ],
          [0, 1, 2, 0, 2, 3],
        );
      }
    }
    // clerestory wall between aisle roof and the vault springing
    const zs = aisleH + 3.5;
    for (const side of [-1, 1]) {
      const v = gvc + side * gHalf;
      lbox(brick, (gua + gub) / 2, v, aisleH, gub - gua, 0.8, zs - aisleH);
    }
    barrel(gua, gub, gvc, gHalf, zs, 35 - zs, { segs: 20, ribStep: 6.5 });
    // brick end walls up to the springing at both ends
    for (const u of [gua, gub]) lbox(brick, u, gvc, aisleH, 0.8, gHalf * 2, zs - aisleH);

    // Entrance front on Olympia Way (the end nearer Kensington Olympia station, NE).
    const endNE = (() => {
      const a = W(ge.u1, gvc, 0),
        b = W(ge.u0, gvc, 0);
      return a[0] + a[1] > b[0] + b[1] ? 1 : -1;
    })();
    const uF = endNE > 0 ? ge.u1 + 0.6 : ge.u0 - 0.6;
    const fw = Math.min(70, ge.v1 - ge.v0 - 2),
      fh = 20;
    {
      const u = uF,
        s = endNE;
      const v0 = gvc - fw / 2,
        v1 = gvc + fw / 2;
      const a =
        s > 0
          ? [W(u, v0, 0), W(u, v1, 0), W(u, v1, fh), W(u, v0, fh)]
          : [W(u, v1, 0), W(u, v0, 0), W(u, v0, fh), W(u, v1, fh)];
      batch.add(
        entrance,
        a,
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
      lbox(brick, u - s * 0.4, gvc, 0, 0.8, fw, fh);
      lbox(stone, u + s * 0.1, gvc, fh, 1.6, fw + 1, 1.2); // cornice
      // balustrade with urns / statues along the parapet
      for (let k = 0; k <= 14; k++) {
        const v = v0 + (fw * k) / 14;
        lbox(stone, u, v, fh + 1.2, 0.9, 0.9, 1.4);
        if (k % 2 === 0) addGeo(stone, new THREE.SphereGeometry(0.55, 8, 6), M(u, v, fh + 3.0));
      }
      lbox(stone, u, gvc, fh + 1.2, 0.6, fw, 0.25);
      lbox(stone, u, gvc, fh + 2.4, 0.9, fw, 0.25);
      // central pedimented bay rising above the parapet, with sculpture group
      lbox(stone, u + s * 0.5, gvc, fh - 1, 1.2, 13, 5);
      for (const dv of [-6, 6]) lbox(stone, u + s * 0.5, gvc + dv, 0, 1.4, 1.4, fh + 3);
      const ped = new THREE.Shape([
        new THREE.Vector2(-8, 0),
        new THREE.Vector2(8, 0),
        new THREE.Vector2(0, 4.5),
      ]);
      const pg = new THREE.ExtrudeGeometry(ped, { depth: 1.6, bevelEnabled: false });
      pg.rotateX(Math.PI / 2);
      pg.rotateZ(Math.PI / 2);
      addGeo(stone, pg, M(u + s * 0.5 - 0.8, gvc, fh + 4));
      for (const dv of [-3, 0, 3]) {
        addGeo(
          stone,
          new THREE.CylinderGeometry(0.6, 0.8, 3.2, 8).rotateX(Math.PI / 2),
          M(u + s * 0.6, gvc + dv, fh + 10.5),
        );
      }
      // corner pavilions with low domes
      for (const sv of [-1, 1]) {
        const v = gvc + sv * (fw / 2 - 3.5);
        lbox(brick, u + s * 0.6, v, 0, 7, 7, fh + 5);
        lbox(stone, u + s * 0.6, v, fh + 5, 7.8, 7.8, 0.9);
        const dome = new THREE.SphereGeometry(3.3, 14, 7, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(
          Math.PI / 2,
        );
        addGeo(lead, dome, M(u + s * 0.6, v, fh + 5.9));
        addGeo(
          lead,
          new THREE.CylinderGeometry(0.4, 0.4, 2.5, 6).rotateX(Math.PI / 2),
          M(u + s * 0.6, v, fh + 10),
        );
        // quoins
        for (const dz of [2, 6, 10, 14, 18]) lbox(stone, u + s * 0.7, v, dz, 7.3, 7.3, 1.2);
      }
      // entrance canopy
      lbox(kit.mat('dark_steel'), u + s * 3, gvc, 4.5, 6, 16, 0.6);
    }

    // ---- Olympia National ----
    const nRing = national.polys[0][0];
    const ne = ext(nRing);
    const nH = 13;
    kit.walls(batch, brickFacade, national.polys, 0, nH, { bay: 6, storey: nH / 2 });
    for (const ring of national.polys[0])
      for (let k = 0; k < ring.length; k++) {
        const p = ring[k],
          q = ring[(k + 1) % ring.length];
        const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
        if (len < 1) continue;
        const geo = new THREE.BoxGeometry(len, 0.9, 0.8);
        const m = new THREE.Matrix4()
          .makeRotationZ(Math.atan2(q[1] - p[1], q[0] - p[0]))
          .setPosition((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, nH + 0.2);
        addGeo(stone, geo, m);
      }
    kit.cap(batch, lead, national.polys, nH, { scale: 6 });
    // The National's vault: clip its u range to the part of the footprint that is
    // reasonably rectangular (the outline narrows to the south-west).
    const nvc = (ne.v0 + ne.v1) / 2;
    const nHalf = Math.min(22, (ne.v1 - ne.v0) / 2 - 10);
    const nua = ne.u0 + 14,
      nub = ne.u1 - 8;
    for (const side of [-1, 1])
      lbox(brick, (nua + nub) / 2, nvc + side * nHalf, nH, nub - nua, 0.8, 3);
    barrel(nua, nub, nvc, nHalf, nH + 3, 10, { segs: 16, ribStep: 7 });
    for (const u of [nua, nub]) lbox(brick, u, nvc, nH, 0.8, nHalf * 2, 3);

    // Hammersmith Road front: the longest outline edge of the National facing
    // south (smallest mean y) carries the painted front and the canopy.
    let best = null;
    for (let k = 0; k < nRing.length; k++) {
      const p = nRing[k],
        q = nRing[(k + 1) % nRing.length];
      const len = Math.hypot(q[0] - p[0], q[1] - p[1]);
      const ny = -(q[0] - p[0]) / len; // outward normal y for CCW ring
      if (len > 20 && ny < -0.85 && (!best || len > best.len)) best = { p, q, len };
    }
    if (best) {
      const { p, q, len } = best;
      const dx = (q[0] - p[0]) / len,
        dy = (q[1] - p[1]) / len;
      const nx = dy,
        ny = -dx; // outward
      const o = 0.35,
        top = nH + 4;
      const P = (t, z, d = o) => [p[0] + dx * t + nx * d, p[1] + dy * t + ny * d, z];
      batch.add(
        hammersmithFront,
        [P(0, 0), P(len, 0), P(len, top), P(0, top)],
        [
          [0, 0],
          [len / 60, 0],
          [len / 60, 1],
          [0, 1],
        ],
        [0, 1, 2, 0, 2, 3],
      );
      const rot = Math.atan2(dy, dx);
      const at = (t, d, z) => new THREE.Matrix4().makeRotationZ(rot).setPosition(...P(t, z, d));
      addGeo(brick, new THREE.BoxGeometry(len, 0.6, top), at(len / 2, 0.05, top / 2));
      addGeo(stone, new THREE.BoxGeometry(len + 0.6, 1.4, 1.0), at(len / 2, 0.6, top + 0.5));
      // Emberton-style flat entrance canopy.
      addGeo(
        kit.mat('white_render'),
        new THREE.BoxGeometry(Math.min(40, len * 0.6), 4.5, 0.7),
        at(len / 2, 2.6, 4.6),
      );
      addGeo(
        kit.mat('#1d3f7a'),
        new THREE.BoxGeometry(Math.min(40, len * 0.6), 0.2, 0.7),
        at(len / 2, 4.9, 4.6),
      );
    }

    g.add(batch.toGroup('olympia_london'));
    return g;
  },
};
