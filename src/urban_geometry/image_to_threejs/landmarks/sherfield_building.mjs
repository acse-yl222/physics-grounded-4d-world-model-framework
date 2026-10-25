// Sherfield Building, Imperial College South Kensington (opened 1969 as the College
// Block, renamed 1975). Long post-war slab on the north side of Queen's Lawn holding
// the Great Hall, refectories and administration. Modelled as a pale precast-concrete
// slab with continuous horizontal ribbon windows and spandrel bands over a recessed,
// glazed ground floor on pilotis (the Sherfield Walkway level), with rooftop plant.
export default {
  id: 'sherfield_building',
  name: 'Sherfield Building',
  claims: [
    '7dc5fa73-2c5f-4fe1-8da6-4049490f9b37', // Sherfield Building
    '72e1599d-430f-4d4b-9966-ce36593a1036', // unnamed north annex (stair / service block)
  ],
  references: [
    {
      title: 'Sherfield Building - Imperial College events and hospitality',
      url: 'https://www.imperial.ac.uk/events-and-hospitality/venues/sherfield-building/',
      used_for: 'building identity and use (Great Hall, venue levels)',
    },
    {
      title: "Queen's Lawn - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Queen%27s_Lawn',
      used_for: "position on the north side of Queen's Lawn next to the Abdus Salam Library",
    },
    {
      title: 'Campus improvements - Imperial College property',
      url: 'https://www.imperial.ac.uk/admin-services/property/current-projects/campus-improvements/',
      used_for: 'Sherfield Walkway at levels 1-2, levels 3-5 above',
    },
    {
      title: 'South Kensington Campus map (PDF)',
      url: 'https://www.sbg.bio.ic.ac.uk/files/SouthKensingtonCampus.pdf',
      used_for: 'Great Hall and common rooms on level 2 of Sherfield',
    },
  ],
  notes:
    'No architectural description of the facades was found; the precast concrete ribbon-window elevation, ' +
    'recessed glazed ground floor and plant rooms follow the 1960s campus style and are approximate. ' +
    'The elevated walkway linking east to the Main Entrance crosses other footprints and is not modelled. ' +
    'Height kept close to the footprint value (main slab 17.5 m, plant to ~20 m).',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const main = byId['7dc5fa73-2c5f-4fe1-8da6-4049490f9b37'];
    const annex = byId['72e1599d-430f-4d4b-9966-ce36593a1036'];

    // Ribbon-window facade: pale concrete spandrels, dark glazing, slim mullions.
    const ribbon = kit.paintedMaterial('sherfield_building:ribbon', 512, 512, (c, w, h) => {
      const sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        c.fillStyle = '#d7d2c5';
        c.fillRect(0, y0, w, sh);
        // window strip occupies the upper part of each storey band
        const wy = y0 + sh * 0.06,
          wh = sh * 0.56;
        c.fillStyle = '#2f3a42';
        c.fillRect(0, wy, w, wh);
        // reflections
        const grd = c.createLinearGradient(0, wy, 0, wy + wh);
        grd.addColorStop(0, 'rgba(150,170,185,0.35)');
        grd.addColorStop(1, 'rgba(40,50,60,0)');
        c.fillStyle = grd;
        c.fillRect(0, wy, w, wh);
        c.fillStyle = '#8d8f8e';
        for (let k = 0; k <= 16; k++) c.fillRect((k * w) / 16 - 2, wy, 4, wh);
        c.fillRect(0, wy + wh * 0.72, w, 3);
        // shadow line under window head, panel joints on spandrel
        c.fillStyle = '#a9a497';
        c.fillRect(0, wy + wh, w, 5);
        c.fillStyle = '#c4bfb2';
        for (let k = 0; k <= 4; k++) c.fillRect((k * w) / 4 - 1, wy + wh, 2, sh - wh - sh * 0.06);
        c.fillStyle = '#bdb8ab';
        c.fillRect(0, y0, w, sh * 0.06);
      }
    });
    const groundGlass = kit.paintedMaterial('sherfield_building:ground', 256, 256, (c, w, h) => {
      c.fillStyle = '#26323a';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(160,180,190,0.25)';
      c.fillRect(0, 0, w, h * 0.45);
      c.fillStyle = '#6c7174';
      for (let k = 0; k <= 8; k++) c.fillRect((k * w) / 8 - 2, 0, 4, h);
      c.fillRect(0, h * 0.48, w, 4);
      c.fillRect(0, 0, w, 8);
    });
    const concrete = kit.mat('concrete');
    const pale = kit.mat('#d7d2c5');
    const roofMat = kit.mat('#8f8c86');
    const plant = kit.mat('#a7a39a');

    const zG = 4.2; // ground-floor (walkway) level
    const zTop = 17.5;
    const ring = main.polys[0][0];
    // Recessed glazed ground floor.
    const inner = kit.offsetRing(ring, -2.2);
    kit.walls(batch, groundGlass, [[inner]], 0, zG, { bay: 3, storey: zG / 2 });
    kit.cap(batch, concrete, [[ring]], zG, { down: true });
    // Pilotis around the perimeter.
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 6) continue;
      const n = Math.round(len / 6);
      const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const nx = (b[1] - a[1]) / len,
        ny = -(b[0] - a[0]) / len; // outward for CCW
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        const x = a[0] + (b[0] - a[0]) * t - nx * 0.5,
          y = a[1] + (b[1] - a[1]) * t - ny * 0.5;
        kit.box(batch, pale, x, y, 0, 0.8, 0.8, zG, ang);
      }
    }
    // Upper floors.
    kit.walls(batch, ribbon, [[ring]], zG, zTop, { bay: 3.4, storey: 3.33, uvBase: zG });
    // Parapet coping and roof.
    kit.walls(batch, pale, [[kit.offsetRing(ring, 0.25)]], zTop - 0.6, zTop + 0.6);
    kit.cap(batch, roofMat, [[ring]], zTop + 0.35);

    // North annex: same language, slightly taller.
    const aRing = annex.polys[0][0];
    kit.walls(batch, ribbon, [[aRing]], 0, annex.h, { bay: 3.4, storey: 3.33, uvBase: zG });
    kit.walls(batch, pale, [[aRing]], annex.h, annex.h + 0.6);
    kit.cap(batch, roofMat, [[aRing]], annex.h + 0.6);

    // Rooftop plant rooms and lift overruns along the slab axis.
    const fr = kit.ringFrame(ring);
    const ca = Math.cos(fr.angle),
      sa = Math.sin(fr.angle);
    const at = (u, v) => [fr.cx + u * ca - v * sa, fr.cy + u * sa + v * ca];
    const blocks = [
      [-52, 0, 14, 9, 2.8],
      [-18, 1, 22, 11, 3.4],
      [22, -1, 10, 8, 2.6],
      [55, 0, 12, 9, 3.0],
    ];
    for (const [u, v, w, d, h] of blocks) {
      const [x, y] = at(u, v);
      kit.box(batch, plant, x, y, zTop + 0.35, w, d, h, fr.angle);
      kit.box(batch, pale, x, y, zTop + 0.35 + h, w + 0.4, d + 0.4, 0.3, fr.angle);
    }
    // Louvre bands on the plant rooms.
    const louvre = kit.mat('#6d6f70');
    for (const [u, v, w, d, h] of blocks) {
      const [x, y] = at(u, v);
      kit.box(batch, louvre, x, y, zTop + 1.0, w + 0.06, d + 0.06, h * 0.45, fr.angle);
    }
    g.add(batch.toGroup('sherfield'));
    return g;
  },
};
