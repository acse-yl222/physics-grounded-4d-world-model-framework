// Holy Trinity Brompton (Thomas Leverton Donaldson, consecrated 1829; chancel and
// extensions by Arthur Blomfield 1879-82). Commissioners' Gothic church in stock /
// gault brick with Bath stone dressings: clerestoried five-bay nave with aisles and
// lancet windows, a west tower with corner pinnacles flanked by stair lobbies, and a
// later chancel with vestries at the east end.
export default {
  id: 'holy_trinity_brompton',
  name: 'Holy Trinity Brompton',
  claims: ['c83e542e-228e-4da2-b3a7-6197242c810f'],
  references: [
    {
      title: 'Holy Trinity Brompton - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Holy_Trinity_Brompton',
      used_for: "Donaldson design, consecrated 1829, Commissioners' church; 1879-82 extension",
    },
    {
      title: 'Parish of Holy Trinity, Brompton - AIM25',
      url: 'https://atom.aim25.com/index.php/parish-of-holy-trinity-brompton-church-of-england-2',
      used_for:
        '5-bay clerestoried nave with two aisles, sanctuary with vestries, west tower with stair lobbies; stock brick, Suffolk facings, Bath stone dressings, lancets',
    },
    {
      title: 'Holy Trinity Church, Brompton - DBR',
      url: 'https://dbrlimited.com/projects/holy-trinity-church-brompton',
      used_for: 'gault brickwork and Bath stone dressings on the tower',
    },
    {
      title: 'Churches in Kensington and Chelsea - RBKC',
      url: 'https://www.rbkc.gov.uk/node/160',
      used_for: 'plain Gothic style',
    },
  ],
  notes:
    'Volumes follow the Overture building parts (tower 29.6 m incl. pinnacles, nave ridge 20 m, aisles 13.6 m, ' +
    'chancel 16.8 m); wall/eave splits within each part, tower stage heights and pinnacle form are estimated.',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const brickC = '#b6a681';
    const brick = kit.mat(brickC, { roughness: 0.95 });
    const bath = kit.mat('bath_stone');
    const slate = kit.roof('slate', 2);
    const dark = kit.mat('#2c333b');
    const A = (24.25 * Math.PI) / 180;
    const lancet = kit.paintedMaterial('holy_trinity_brompton:lancet', 512, 256, (c, w, h) => {
      const r = kit.rng(0.4242);
      c.fillStyle = brickC;
      c.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 4)
        for (let x = (y / 4) % 2 ? -6 : 0; x < w; x += 12) {
          const col = new THREE.Color(brickC).multiplyScalar(0.88 + r() * 0.22);
          c.fillStyle = '#' + col.getHexString();
          c.fillRect(x + 0.5, y + 0.5, 11, 3);
        }
      const bw = w / 4;
      // one tall lancet per bay spanning both "storeys" of the tile
      for (let k = 0; k < 4; k++) {
        const x = k * bw + bw / 2,
          ww = bw * 0.26;
        const top = h * 0.12,
          bot = h * 0.86;
        c.fillStyle = '#d9c79e';
        c.beginPath();
        c.moveTo(x - ww / 2 - 5, bot + 5);
        c.lineTo(x - ww / 2 - 5, top + ww);
        c.quadraticCurveTo(x - ww / 2 - 5, top - 6, x, top - 12);
        c.quadraticCurveTo(x + ww / 2 + 5, top - 6, x + ww / 2 + 5, top + ww);
        c.lineTo(x + ww / 2 + 5, bot + 5);
        c.fill();
        c.fillStyle = '#39424c';
        c.beginPath();
        c.moveTo(x - ww / 2, bot);
        c.lineTo(x - ww / 2, top + ww);
        c.quadraticCurveTo(x - ww / 2, top, x, top - 6);
        c.quadraticCurveTo(x + ww / 2, top, x + ww / 2, top + ww);
        c.lineTo(x + ww / 2, bot);
        c.fill();
        c.fillStyle = '#d9c79e';
        c.fillRect(x - 1.5, top + 6, 3, bot - top - 6);
        // buttress between bays
        c.fillStyle = '#b3a37e';
        c.fillRect(k * bw - 6, 0, 12, h);
      }
      c.fillStyle = '#d9c79e';
      c.fillRect(0, h - 6, w, 6);
    });

    const parts = (b.parts?.length ? b.parts : [{ polys: b.polys, h: b.h, minh: 0 }]).map((p) => {
      const r = p.polys[0][0];
      return { ...p, ring: kit.ringArea(r) < 0 ? r.slice().reverse() : r };
    });
    const parapet = (ring, z) => {
      const o = kit.offsetRing(ring, 0.15),
        inner = kit.offsetRing(ring, -0.3);
      kit.walls(batch, bath, [[o]], z, z + 0.4);
      kit.walls(batch, bath, [[inner.slice().reverse()]], z, z + 0.4);
      kit.cap(batch, bath, [[o, inner.slice().reverse()]], z + 0.4);
      kit.cap(batch, bath, [[o, ring.slice().reverse()]], z, { down: true });
    };
    for (const p of parts) {
      const { ring, h } = p;
      const area = Math.abs(kit.ringArea(ring));
      if (h > 25) {
        // ---- west tower with stair lobbies ----
        const e = kit.orientedExtent(ring, A);
        const cu = (e.u0 + e.u1) / 2,
          cv = (e.v0 + e.v1) / 2;
        const depth = e.u1 - e.u0;
        const T = Math.min(depth, 7.4);
        const at = (u, v) => e.at(u, v, 0);
        // lobbies (lower) on the full part outline
        kit.walls(batch, lancet, [[ring]], 0, 11.5, { bay: 3.4, storey: 5.75 });
        parapet(ring, 11.5);
        kit.cap(batch, kit.mat('lead'), [[ring]], 11.6);
        // tower shaft
        const tr = [
          at(cu - T / 2, cv - T / 2),
          at(cu + T / 2, cv - T / 2),
          at(cu + T / 2, cv + T / 2),
          at(cu - T / 2, cv + T / 2),
        ];
        kit.walls(batch, brick, [[tr]], 11.5, 24.5);
        for (const z of [11.5, 17.5]) {
          const o = kit.offsetRing(tr, 0.2);
          kit.walls(batch, bath, [[o]], z, z + 0.45);
          kit.cap(batch, bath, [[o, tr.slice().reverse()]], z + 0.45);
        }
        // belfry lancets and clock-stage roundels on each face
        for (let s = 0; s < 4; s++) {
          const a = A + (s * Math.PI) / 2;
          const nx = Math.cos(a - Math.PI / 2),
            ny = Math.sin(a - Math.PI / 2);
          const [cx, cy] = at(cu, cv);
          const fx = cx + nx * (T / 2 + 0.03),
            fy = cy + ny * (T / 2 + 0.03);
          for (const d of [-1.1, 1.1]) {
            kit.box(
              batch,
              bath,
              fx + Math.cos(a) * d,
              fy + Math.sin(a) * d,
              19.0,
              1.3,
              0.12,
              4.4,
              a,
            );
            kit.box(
              batch,
              dark,
              fx + Math.cos(a) * d + nx * 0.04,
              fy + Math.sin(a) * d + ny * 0.04,
              19.2,
              0.85,
              0.1,
              3.9,
              a,
            );
          }
          const ring2 = new THREE.CircleGeometry(0.9, 14).rotateX(Math.PI / 2);
          batch.addGeometry(
            bath,
            ring2,
            new THREE.Matrix4().makeRotationZ(a).setPosition(fx + nx * 0.05, fy + ny * 0.05, 15.0),
          );
          ring2.dispose();
        }
        // corner buttresses rising into octagonal pinnacles
        for (const [su, sv] of [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
        ]) {
          const [x, y] = at(cu + (su * T) / 2, cv + (sv * T) / 2);
          kit.box(batch, brick, x, y, 11.5, 1.3, 1.3, 13.6, A);
          const sh = new THREE.CylinderGeometry(0.55, 0.6, 2.2, 8).rotateX(Math.PI / 2);
          batch.addGeometry(bath, sh, new THREE.Matrix4().setPosition(x, y, 26.2));
          sh.dispose();
          const cone = new THREE.ConeGeometry(0.62, 2.4, 8).rotateX(Math.PI / 2);
          batch.addGeometry(bath, cone, new THREE.Matrix4().setPosition(x, y, 28.4));
          cone.dispose();
        }
        // pierced parapet (merlons)
        const o = kit.offsetRing(tr, 0.1);
        kit.walls(batch, bath, [[o]], 24.5, 25.0);
        for (let k = 0; k < 4; k++) {
          const p0 = o[k],
            p1 = o[(k + 1) % 4];
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          const ang = Math.atan2(p1[1] - p0[1], p1[0] - p0[0]);
          const n = 5;
          for (let i = 0; i < n; i++) {
            const t = (i + 0.5) / n;
            kit.box(
              batch,
              bath,
              p0[0] + (p1[0] - p0[0]) * t,
              p0[1] + (p1[1] - p0[1]) * t,
              25.0,
              (len / n) * 0.55,
              0.3,
              0.8,
              ang,
            );
          }
        }
        kit.cap(batch, kit.mat('lead'), [[tr]], 24.6);
        // west door
        const [wx, wy] = at(e.u0, cv);
        kit.box(batch, bath, wx - Math.cos(A) * 0.1, wy - Math.sin(A) * 0.1, 0, 0.3, 2.8, 4.6, A);
        kit.box(batch, dark, wx - Math.cos(A) * 0.2, wy - Math.sin(A) * 0.2, 0, 0.1, 2.0, 3.8, A);
        continue;
      }
      if (h >= 19) {
        // clerestoried nave: walls to 16 m, slate roof to the part height, ridge along the axis
        kit.walls(batch, lancet, [[ring]], 0, 16, { bay: 5.4, storey: 8 });
        parapet(ring, 16);
        kit.pitchedRoof(batch, slate, brick, ring, A, 16.4, h - 16.4, 'gabled', { overhang: 0.2 });
        continue;
      }
      if (area > 60 && h >= 13) {
        // aisles or chancel: gabled / lean-to style roofs
        const e = kit.orientedExtent(ring, A);
        const len = e.u1 - e.u0,
          wid = e.v1 - e.v0;
        const along = len >= wid ? A : A + Math.PI / 2;
        const eave = h - (Math.min(len, wid) / 2) * 0.7;
        kit.walls(batch, lancet, [[ring]], 0, eave, { bay: 5.4, storey: eave / 2 });
        parapet(ring, eave);
        kit.pitchedRoof(
          batch,
          slate,
          brick,
          ring,
          along,
          eave + 0.4,
          Math.max(1, h - eave - 0.4),
          'gabled',
          { overhang: 0.2 },
        );
        continue;
      }
      // small annexes, porches, vestries: flat roofs behind a stone coping
      kit.walls(batch, h > 8 ? lancet : brick, [[ring]], 0, h, { bay: 3.4, storey: h / 2 });
      parapet(ring, h);
      kit.cap(batch, kit.mat('lead'), [[ring]], h + 0.1);
    }
    g.add(batch.toGroup('holy_trinity_brompton'));
    return g;
  },
};
