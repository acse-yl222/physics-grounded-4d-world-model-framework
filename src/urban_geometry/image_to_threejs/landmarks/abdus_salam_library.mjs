// Abdus Salam Library (former Central Library), Imperial College South Kensington.
// Opened August 1969 on the west side of Queen's Lawn beside Imperial College Road;
// a 1960s concrete-panelled block, reconfigured 1993-97 by John McAslan + Partners
// with a two-storey glazed roof extension that brings daylight deep into the plan
// and contrasts with the concrete below.
export default {
  id: 'abdus_salam_library',
  name: 'Abdus Salam Library',
  claims: ['9aff3388-d165-426e-96b2-eaaa63ff9a95'],
  references: [
    {
      title: 'Abdus Salam Library - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Abdus_Salam_Library',
      used_for:
        "opening 1969, site on Queen's Lawn next to Imperial College Road opposite Queen's Tower",
    },
    {
      title: 'Imperial College Libraries - John McAslan + Partners',
      url: 'https://mcaslan.co.uk/Imperial-College-Libraries',
      used_for: '1960s concrete-panelled structure; two-storey glazed roof extension (1993-97)',
    },
    {
      title: "Queen's Lawn - Wikipedia",
      url: 'https://en.wikipedia.org/wiki/Queen%27s_Lawn',
      used_for: "library as one of the buildings framing Queen's Lawn",
    },
  ],
  notes:
    'Concrete panel pattern (vertical fins with deep-set strip windows), ground-floor recess and the ' +
    'setback/height of the glazed roof storeys are proportioned, not measured: concrete block to 15 m, ' +
    'glazed extension to ~22 m (footprint height 16.8 m). The entrance on the lawn side uses the notch in the outline.',
  build({ THREE, kit, buildings }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ring = buildings[0].polys[0][0];

    const panels = kit.paintedMaterial('abdus_salam_library:panels', 512, 512, (c, w, h) => {
      c.fillStyle = '#c2bdb1';
      c.fillRect(0, 0, w, h);
      const sh = h / 2;
      for (let s = 0; s < 2; s++) {
        const y0 = s * sh;
        // deep-set glazing between projecting fins
        c.fillStyle = '#2d3840';
        for (let k = 0; k < 8; k++) c.fillRect(k * 64 + 14, y0 + sh * 0.18, 36, sh * 0.55);
        c.fillStyle = 'rgba(170,185,195,0.3)';
        for (let k = 0; k < 8; k++) c.fillRect(k * 64 + 14, y0 + sh * 0.18, 36, sh * 0.18);
        // fin shadows
        c.fillStyle = '#9d988c';
        for (let k = 0; k < 8; k++) c.fillRect(k * 64 + 50, y0 + sh * 0.18, 5, sh * 0.55);
        // panel joints / floor band
        c.fillStyle = '#aaa599';
        c.fillRect(0, y0 + sh * 0.8, w, 4);
        c.fillRect(0, y0 + 2, w, 3);
      }
      // weathering streaks
      c.fillStyle = 'rgba(110,105,95,0.12)';
      for (let k = 0; k < 16; k++) c.fillRect(k * 32 + 8, 0, 6, h);
    });
    const ground = kit.paintedMaterial('abdus_salam_library:ground', 256, 256, (c, w, h) => {
      c.fillStyle = '#28343c';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(180,195,200,0.28)';
      c.fillRect(0, 0, w, h * 0.5);
      c.fillStyle = '#585e62';
      for (let k = 0; k <= 4; k++) c.fillRect((k * w) / 4 - 3, 0, 6, h);
      c.fillRect(0, 0, w, 10);
    });
    const glazing = kit.paintedMaterial(
      'abdus_salam_library:glazing',
      512,
      512,
      (c, w, h) => {
        const grd = c.createLinearGradient(0, 0, 0, h);
        grd.addColorStop(0, '#9fb6c3');
        grd.addColorStop(0.5, '#5f7987');
        grd.addColorStop(1, '#8fa8b5');
        c.fillStyle = grd;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d9dddd';
        for (let k = 0; k <= 8; k++) c.fillRect((k * w) / 8 - 3, 0, 6, h);
        for (let k = 0; k <= 4; k++) c.fillRect(0, (k * h) / 4 - 3, w, 6);
      },
      { roughness: 0.15, metalness: 0.3 },
    );
    const concrete = kit.mat('#c2bdb1');
    const dark = kit.mat('#8e8a83');
    const metal = kit.mat('#d6d9da', { roughness: 0.45 });

    const zG = 3.6,
      zC = 15,
      zTop = 22;
    // Ground floor recessed 1.5 m behind the concrete edge with columns.
    const inner = kit.offsetRing(ring, -1.5);
    kit.walls(batch, ground, [[inner]], 0, zG, { bay: 3.6, storey: zG / 2 });
    kit.cap(batch, concrete, [[ring]], zG, { down: true });
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 7) continue;
      const n = Math.round(len / 7.2);
      const nx = (b[1] - a[1]) / len,
        ny = -(b[0] - a[0]) / len;
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        kit.box(
          batch,
          concrete,
          a[0] + (b[0] - a[0]) * t - nx * 0.45,
          a[1] + (b[1] - a[1]) * t - ny * 0.45,
          0,
          0.7,
          0.7,
          zG,
          Math.atan2(b[1] - a[1], b[0] - a[0]),
        );
      }
    }
    // Concrete-panelled upper floors with a deep fascia at the top.
    kit.walls(batch, panels, [[ring]], zG, zC - 1.2, { bay: 3.6, storey: 3.4, uvBase: zG });
    kit.walls(batch, concrete, [[kit.offsetRing(ring, 0.3)]], zC - 1.2, zC);
    kit.cap(batch, concrete, [[kit.offsetRing(ring, 0.3)]], zC);
    // Horizontal floor-edge ribs.
    for (const z of [zG, zG + 3.4, zG + 6.8])
      kit.walls(batch, dark, [[kit.offsetRing(ring, 0.18)]], z - 0.25, z);

    // Two-storey glazed roof extension on the simplified rectangle, set back ~4 m.
    const fr = kit.ringFrame(ring);
    const ca = Math.cos(fr.angle),
      sa = Math.sin(fr.angle);
    const at = (u, v) => [fr.cx + u * ca - v * sa, fr.cy + u * sa + v * ca];
    const hl = fr.length / 2 - 5,
      hw = fr.width / 2 - 5;
    const top = [at(-hl, -hw), at(hl, -hw), at(hl, hw), at(-hl, hw)];
    if (kit.ringArea(top) < 0) top.reverse();
    kit.walls(batch, glazing, [[top]], zC, zTop - 0.8, { bay: 3, storey: 3.1, uvBase: zC });
    // Intermediate floor edge and projecting metal roof.
    kit.walls(batch, metal, [[kit.offsetRing(top, 0.1)]], zC + 3.3, zC + 3.6);
    const roofR = kit.offsetRing(top, 0.9);
    kit.walls(batch, metal, [[roofR]], zTop - 0.8, zTop);
    kit.cap(batch, kit.mat('#b9bcbc'), [[roofR]], zTop);
    kit.cap(batch, metal, [[roofR]], zTop - 0.8, { down: true });
    // Rooflight strips across the extension roof (daylight deep into the plan).
    const sky = kit.mat('#8fb0c0', { roughness: 0.15, metalness: 0.3 });
    for (let u = -hl + 6; u < hl - 4; u += 9) {
      const [x, y] = at(u, 0);
      kit.box(batch, sky, x, y, zTop, 3.2, hw * 2 - 6, 0.9, fr.angle);
      kit.box(batch, metal, x, y, zTop + 0.9, 3.5, hw * 2 - 5.6, 0.12, fr.angle);
    }
    // Entrance canopy on the Queen's Lawn side (east) at the notch in the outline.
    let best = null;
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k],
        b = ring[(k + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const mx = (a[0] + b[0]) / 2;
      if (len > 5 && (!best || mx > best.mx)) best = { a, b, len, mx };
    }
    if (best) {
      const { a, b, len } = best;
      const nx = (b[1] - a[1]) / len,
        ny = -(b[0] - a[0]) / len;
      const t = 0.5;
      const cx = a[0] + (b[0] - a[0]) * t + nx * 1.6,
        cy = a[1] + (b[1] - a[1]) * t + ny * 1.6;
      kit.box(
        batch,
        metal,
        cx,
        cy,
        3.4,
        3.2,
        8,
        0.35,
        Math.atan2(b[1] - a[1], b[0] - a[0]) + Math.PI / 2,
      );
    }
    g.add(batch.toGroup('abdus_salam_library'));
    return g;
  },
};
