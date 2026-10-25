// Imperial College Hammersmith Campus at Hammersmith Hospital, Du Cane Road.
// - Commonwealth Building (Lyons Israel & Ellis, 1961-66, opened May 1966): the
//   ten/eleven-storey brutalist slab of the Royal Postgraduate Medical School,
//   linked by a bridge to the low Wolfson lecture/education building to the north.
// - ICTEM, Imperial Centre for Translational and Experimental Medicine (2008):
//   six-storey glazed research block.
// - Burlington Danes Imaging Centre (Sheppard Robson with AKT II, 2007): tiered
//   research building behind perforated stainless steel and glass facades.
export default {
  id: 'hammersmith_campus',
  name: 'Hammersmith Campus: Commonwealth Building, ICTEM, Burlington Danes',
  claims: [
    'f438d558-eec4-4b55-af66-dc5593556773', // Commonwealth Building
    'eee43564-1df1-439c-a52f-1fbc98cc164a', // Wolfson Education Centre (linked lecture building)
    'a6c1df93-98e8-4475-951b-12e3e3bc05f9', // ICTEM
    '19bb2805-2195-4548-8053-3e181fe4f86f', // Burlington Danes
  ],
  references: [
    {
      title: 'Hammersmith Hospital - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Hammersmith_Hospital',
      used_for:
        'Commonwealth Building of the postgraduate medical school opened by the Queen in May 1966',
    },
    {
      title: 'Wolfson Institute & Commonwealth Building - Modernism in Metro-Land',
      url: 'https://www.modernism-in-metroland.co.uk/wolfson-institute.html',
      used_for:
        'Lyons Israel & Ellis 1961-66, brutalist, ten-storey Commonwealth Building linked by a bridge to the lecture block',
    },
    {
      title: 'Wolfson Institute, Hammersmith Hospital - RIBApix',
      url: 'https://www.architecture.com/image-library/ribapix/image-information/poster/wolfson-institute-hammersmith-hospital-du-cane-road-london/posterid/RIBA74626.html',
      used_for: 'exposed concrete construction of the Lyons Israel & Ellis buildings',
    },
    {
      title: 'ICTEM Building at Hammersmith Campus - Imperial College',
      url: 'https://www.imperial.ac.uk/medicine/research-and-impact/facilities/translational-research-imaging/biological-imaging-centre/contact-us/',
      used_for: 'ICTEM (L-Block) on Du Cane Road',
    },
    {
      title: 'Imperial College London opens new research facility - Designcurial',
      url: 'https://old.designcurial.com/news/imperial-college-london-opens-new-research-facility/',
      used_for: 'ICTEM: GBP 73m facility of six floors beside Hammersmith Hospital',
    },
    {
      title: 'Burlington Danes Imaging Centre - AKT II',
      url: 'https://akt-uk.com/projects/burlington-danes-imaging-centre',
      used_for:
        'tiered structure, perforated stainless steel and glass facades, 2007, Sheppard Robson',
    },
  ],
  notes:
    'Footprints and Overture heights (Commonwealth 36 m / 11 floors, ICTEM 20 m, Burlington Danes 19.6 m). ' +
    'Facade patterns are generic interpretations of "brutalist concrete", "six-floor glazed lab" and ' +
    '"perforated stainless steel and glass" (no photographs available); bridge position, ' +
    'Burlington Danes tiering and roof plant are estimates. Historic 1905 hospital blocks are left generic.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const b = new kit.MeshBatch();
    const A = (9 * Math.PI) / 180;
    const ringOf = (id) => {
      let r = byId[id].polys[0][0];
      if (kit.ringArea(r) < 0) r = r.slice().reverse();
      return r;
    };
    const conc = kit.mat('#a7a39a', { roughness: 0.95 });
    const concDark = kit.mat('#7d7a73', { roughness: 0.95 });
    const plant = kit.mat('#8d8f8c');
    const roofM = kit.mat('#6e6d69');
    const glass = kit.mat('dark_glass');
    const steel = kit.mat('#c3c7c9', { roughness: 0.35, metalness: 0.7 });
    const concNoise = (c, w, h, base, seed) => {
      const r = kit.rng(seed);
      c.fillStyle = base;
      c.fillRect(0, 0, w, h);
      for (let k = 0; k < 1800; k++) {
        c.fillStyle = `rgba(60,58,52,${r() * 0.1})`;
        c.fillRect(r() * w, r() * h, 2, 2);
      }
    };
    // tile = 4 bays x 2 storeys (kit.walls UV convention)
    const brutal = kit.paintedMaterial('hammersmith_campus:commonwealth', 512, 256, (c, w, h) => {
      concNoise(c, w, h, '#a8a49a', 0.12);
      for (let s = 0; s < 2; s++) {
        const y0 = s * (h / 2);
        for (let k = 0; k < 4; k++) {
          const x = (k * w) / 4;
          c.fillStyle = '#26323a';
          c.fillRect(x + 12, y0 + 34, w / 4 - 24, h / 2 - 66);
          c.fillStyle = 'rgba(170,190,200,0.25)';
          c.fillRect(x + 12, y0 + 34, w / 4 - 24, 12);
          c.fillStyle = '#8f8b82';
          c.fillRect(x + w / 8 - 2, y0 + 34, 4, h / 2 - 66);
        }
        c.fillStyle = 'rgba(80,76,70,0.5)';
        c.fillRect(0, y0 + h / 2 - 30, w, 3);
      }
      c.fillStyle = '#958f85';
      for (let k = 0; k <= 4; k++) c.fillRect((k * w) / 4 - 6, 0, 12, h); // frame columns
    });
    const labGlass = kit.paintedMaterial('hammersmith_campus:ictem', 512, 256, (c, w, h) => {
      c.fillStyle = '#5f7685';
      c.fillRect(0, 0, w, h);
      for (let s = 0; s < 2; s++) {
        const y0 = s * (h / 2);
        c.fillStyle = '#e7e8e6';
        c.fillRect(0, y0 + h / 2 - 30, w, 30); // white floor band
        for (let x = 0; x < w; x += 32) {
          c.fillStyle = '#c9cfd2';
          c.fillRect(x, y0, 4, h / 2 - 30);
        }
        c.fillStyle = 'rgba(210,230,240,0.18)';
        c.fillRect(0, y0, w, 30);
      }
      c.fillStyle = '#b5493b';
      c.fillRect(w * 0.75, 0, w * 0.25 - 4, h); // coloured accent panel bay
    });
    const perforated = kit.paintedMaterial('hammersmith_campus:burlington', 512, 256, (c, w, h) => {
      c.fillStyle = '#c4c9cb';
      c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(90,100,106,0.55)';
      for (let y = 4; y < h; y += 6)
        for (let x = y % 12 ? 0 : 3; x < w; x += 6) c.fillRect(x, y, 2, 2);
      for (let s = 0; s < 2; s++) {
        const y0 = s * (h / 2);
        c.fillStyle = '#334450';
        c.fillRect(0, y0 + 40, w, 34); // glazed ribbon
        c.fillStyle = '#9aa2a6';
        for (let x = 0; x < w; x += 64) c.fillRect(x, y0 + 40, 3, 34);
      }
      c.fillStyle = '#e1e4e5';
      for (let k = 0; k <= 4; k++) c.fillRect((k * w) / 4 - 2, 0, 4, h);
    });
    const lectureM = kit.facade('concrete', 1);

    // ---------- Commonwealth Building ----------
    const cw = ringOf('f438d558-eec4-4b55-af66-dc5593556773');
    const CH = 36,
      ST = 3.3;
    const inset = kit.offsetRing(cw, -1.2);
    kit.walls(b, glass, [[inset]], 0, 4.2);
    kit.walls(b, brutal, [[cw]], 4.2, CH - 1.4, { bay: 3.5, storey: ST, uvBase: 4.2 });
    kit.walls(b, conc, [[kit.offsetRing(cw, 0.25)]], CH - 1.4, CH);
    kit.cap(b, roofM, [[cw]], CH);
    kit.cap(b, conc, [[cw]], 4.2, { down: true });
    for (let z = 4.2; z < CH - 2; z += ST)
      kit.walls(b, concDark, [[kit.offsetRing(cw, 0.45)]], z - 0.15, z + 0.3);
    // pilotis under the slab
    const fr = kit.ringFrame(cw);
    const P = (u, v) => [
      fr.cx + u * Math.cos(fr.angle) - v * Math.sin(fr.angle),
      fr.cy + u * Math.sin(fr.angle) + v * Math.cos(fr.angle),
    ];
    for (let u = -fr.length / 2 + 0.6; u <= fr.length / 2 - 0.5; u += (fr.length - 1.2) / 8)
      for (const v of [-fr.width / 2 + 0.6, fr.width / 2 - 0.6]) {
        const [x, y] = P(u, v);
        kit.box(b, conc, x, y, 0, 0.9, 0.9, 4.2, fr.angle);
      }
    // roof plant rooms and lift towers
    for (const [u, w, d, h] of [
      [-fr.length / 4, 14, fr.width - 6, 3.6],
      [fr.length / 4 + 2, 9, fr.width - 8, 4.6],
    ]) {
      const [x, y] = P(u, 0);
      kit.box(b, plant, x, y, CH, w, d, h, fr.angle);
    }
    // ---------- Wolfson lecture building and the link bridge ----------
    const wo = ringOf('eee43564-1df1-439c-a52f-1fbc98cc164a');
    kit.walls(b, lectureM, [[wo]], 0, 7.9, { bay: 4, storey: 3.6 });
    kit.walls(b, conc, [[kit.offsetRing(wo, 0.3)]], 6.4, 8.3);
    kit.cap(b, roofM, [[wo]], 8.3);
    {
      // raking lecture-theatre roof block
      const fw = kit.ringFrame(wo);
      kit.box(b, concDark, fw.cx, fw.cy, 8.3, fw.length * 0.45, fw.width * 0.5, 2.2, fw.angle);
      // bridge between the slab's north face and the lecture building
      const bx = -2389,
        by0 = 1236.8,
        by1 = 1247.5;
      const cx = bx,
        cy = (by0 + by1) / 2;
      const len = by1 - by0;
      kit.box(b, conc, cx - (cy - 1236) * Math.tan(A) * 0, cy, 4.2, 4.2, len + 1, 3.4, A);
      kit.box(b, glass, cx, cy, 5.0, 4.3, len, 1.6, A);
    }

    // ---------- ICTEM ----------
    const ic = ringOf('a6c1df93-98e8-4475-951b-12e3e3bc05f9');
    const IH = 20;
    kit.walls(b, glass, [[kit.offsetRing(ic, -0.6)]], 0, 4.4);
    kit.walls(b, labGlass, [[ic]], 4.4, IH, { bay: 3.0, storey: 3.9, uvBase: 4.4 });
    kit.cap(b, roofM, [[ic]], IH);
    kit.cap(b, kit.mat('#e7e8e6'), [[ic]], 4.4, { down: true });
    kit.walls(b, kit.mat('#e7e8e6'), [[kit.offsetRing(ic, 0.4)]], IH - 0.6, IH + 0.6);
    // vertical fins on all faces
    for (let k = 0; k < ic.length; k++) {
      const a = ic[k],
        c = ic[(k + 1) % ic.length];
      const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
      const ang = Math.atan2(c[1] - a[1], c[0] - a[0]);
      const nx = Math.sin(ang),
        ny = -Math.cos(ang);
      for (let t = 1.5; t < len - 1; t += 3) {
        const x = a[0] + ((c[0] - a[0]) * t) / len + nx * 0.35,
          y = a[1] + ((c[1] - a[1]) * t) / len + ny * 0.35;
        kit.box(b, kit.mat('#d9dcdc'), x, y, 4.4, 0.2, 0.7, IH - 4.4, ang);
      }
    }
    {
      const fi = kit.ringFrame(ic);
      kit.box(b, plant, fi.cx, fi.cy, IH, fi.length * 0.55, fi.width * 0.5, 4.0, fi.angle);
      kit.box(
        b,
        kit.mat('#a9b3b8'),
        fi.cx,
        fi.cy,
        IH + 4.0,
        fi.length * 0.5,
        fi.width * 0.45,
        0.4,
        fi.angle,
      );
    }

    // ---------- Burlington Danes (tiered) ----------
    const bd = ringOf('19bb2805-2195-4548-8053-3e181fe4f86f');
    const BH = 19.6;
    kit.walls(b, glass, [[kit.offsetRing(bd, -0.5)]], 0, 4.0);
    kit.walls(b, perforated, [[bd]], 4.0, BH - 7.2, { bay: 3.2, storey: 3.6, uvBase: 4.0 });
    kit.cap(b, roofM, [[bd]], BH - 7.2);
    kit.cap(b, steel, [[bd]], 4.0, { down: true });
    // upper tiers stepping back from the south (Du Cane Road) side
    {
      const tiers = [
        [3.6, BH - 3.6],
        [7.2, BH],
      ];
      for (const [d, top] of tiers) {
        // shrink only on the south side: offset ring, then shift north by d/2
        const sh = kit
          .offsetRing(bd, -d / 2)
          .map(([x, y]) => [x - Math.sin(A) * (d / 2) * -1 * 0, y + (d / 2) * Math.cos(A)]);
        kit.walls(b, perforated, [[sh]], top - 3.6, top, { bay: 3.2, storey: 3.6, uvBase: 4.0 });
        kit.cap(b, roofM, [[sh]], top);
        kit.walls(b, steel, [[kit.offsetRing(sh, 0.15)]], top - 0.3, top + 0.5);
      }
      const fb = kit.ringFrame(bd);
      kit.box(b, plant, fb.cx + 10, fb.cy + 4, BH, 18, 6, 2.6, A);
    }
    g.add(b.toGroup('hammersmith_campus'));
    return g;
  },
};
