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
      title: 'Church of the Holy Trinity - Historic England list entry',
      url: 'https://www.historicengland.org.uk/listing/the-list/list-entry/1189293',
      used_for:
        'Gothic, gault brick with stone dressings, slate roof; west tower with battlements and pinnacles',
    },
    {
      title: 'Holy Trinity Churchyard - London Gardens Trust',
      url: 'https://londongardenstrust.org/conservation/inventory/site-record/?ID=KAC079',
      used_for: 'churchyard garden setting',
    },
    {
      title: 'Churches in Kensington and Chelsea - RBKC',
      url: 'https://www.rbkc.gov.uk/node/160',
      used_for: 'plain Gothic style',
    },
  ],
  notes:
    'Volumes follow the Overture building parts (tower 29.6 m incl. pinnacles, nave ridge 20 m, aisles 13.6 m, ' +
    'chancel 16.8 m); wall/eave splits within each part, tower stage heights and pinnacle form are estimated. ' +
    'Lancets (pointed heads, Bath stone surrounds, single mullion), buttresses, battlements, crocketed ' +
    'pinnacles and the west doors are real geometry with an estimated rhythm (one lancet per 5.4 m bay); the ' +
    'triple east window, clerestory heights and the churchyard path/lamps are approximations.',
  build(ctx) {
    const { THREE, kit, buildings } = ctx;
    const b = buildings[0];
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const brickC = '#bcae8a';
    const brick = kit.mat(brickC, { roughness: 0.95 });
    const bath = kit.mat('bath_stone');
    const bathD = kit.mat('#c9b68b', { roughness: 0.85 });
    const slate = kit.roof('slate', 2);
    const dark = kit.mat('#2c333b');
    const glass = kit.mat('#3d4a52', { roughness: 0.25, metalness: 0.2 });
    const leadM = kit.mat('lead');
    const doorM = kit.mat('#4a2f22', { roughness: 0.7 });
    const A = (24.25 * Math.PI) / 180;
    // plain gault / stock brick (the openings are real geometry)
    const wallTex = kit.paintedMaterial(
      'holy_trinity_brompton:brick2',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.4242);
        c.fillStyle = '#a99d82';
        c.fillRect(0, 0, w, h);
        for (let y = 0, row = 0; y < h; y += 4, row++)
          for (let x = row % 2 ? -6 : 0; x < w; x += 12) {
            const col = new THREE.Color(brickC).multiplyScalar(0.86 + r() * 0.24);
            c.fillStyle = '#' + col.getHexString();
            c.fillRect(x + 0.5, y + 0.5, 11, 3);
          }
        for (let i = 0; i < 40; i++) {
          c.fillStyle = `rgba(60,55,40,${0.03 + r() * 0.04})`;
          c.fillRect(r() * w, r() * h, 10 + r() * 40, 6 + r() * 30);
        }
      },
      { vertexColors: true },
    );

    // ---- pointed lancet (Bath stone surround, glass, mullion, hood) -------------------
    const lancetShape = (w, h) => {
      const s = new THREE.Shape();
      const hw = w / 2,
        hs = h - w * 0.87;
      s.moveTo(-hw, 0);
      s.lineTo(hw, 0);
      s.lineTo(hw, hs);
      s.quadraticCurveTo(hw, hs + w * 0.5, 0, h);
      s.quadraticCurveTo(-hw, hs + w * 0.5, -hw, hs);
      s.lineTo(-hw, 0);
      return s;
    };
    const lancetGeo = new Map();
    const lancetParts = (w, h) => {
      const key = `${w.toFixed(2)}:${h.toFixed(2)}`;
      if (lancetGeo.has(key)) return lancetGeo.get(key);
      const sr = 0.22;
      const outer = lancetShape(w + 2 * sr, h + sr);
      outer.holes.push(new THREE.Path(lancetShape(w, h).getPoints(8)));
      const surround = new THREE.ExtrudeGeometry(outer, {
        depth: 0.16,
        bevelEnabled: false,
        curveSegments: 6,
      })
        .rotateX(Math.PI / 2)
        .translate(0, 0, -0.0);
      const gl = new THREE.ShapeGeometry(lancetShape(w, h), 6).rotateX(Math.PI / 2);
      const parts = { surround, gl };
      lancetGeo.set(key, parts);
      return parts;
    };
    // windows on wall edge a -> b (outward normal on the right), sill z
    const lancets = (
      a,
      bb,
      z,
      { w = 1.2, h = 5, bay = 5.4, margin = 1.2, count, mullion = true, buttress = 0 } = {},
    ) => {
      const dx = bb[0] - a[0],
        dy = bb[1] - a[1],
        len = Math.hypot(dx, dy);
      if (len < 2 * margin + w) return;
      const ux = dx / len,
        uy = dy / len,
        nx = uy,
        ny = -ux,
        ang = Math.atan2(dy, dx);
      const n = count ?? Math.max(1, Math.round((len - 2 * margin) / bay));
      const usable = len - 2 * margin;
      const { surround, gl } = lancetParts(w, h);
      for (let k = 0; k < n; k++) {
        const t = margin + (usable * (k + 0.5)) / n;
        const cx = a[0] + ux * t,
          cy = a[1] + uy * t;
        const m = new THREE.Matrix4().makeRotationZ(ang);
        batch.addGeometry(
          bath,
          surround,
          m.clone().setPosition(cx + nx * 0.0, cy + ny * 0.0, z - 0.1),
        );
        batch.addGeometry(glass, gl, m.clone().setPosition(cx + nx * 0.03, cy + ny * 0.03, z));
        if (mullion)
          kit.box(batch, bath, cx + nx * 0.06, cy + ny * 0.06, z, 0.1, 0.08, h - w * 0.45, ang);
        kit.box(batch, bath, cx + nx * 0.12, cy + ny * 0.12, z - 0.3, w + 0.6, 0.26, 0.2, ang); // sill
        // glazing transoms
        for (let j = 1; j < Math.floor(h / 1.4); j++)
          kit.box(
            batch,
            kit.mat('#55595c'),
            cx + nx * 0.05,
            cy + ny * 0.05,
            z + j * 1.4,
            w,
            0.04,
            0.04,
            ang,
          );
        // buttresses between windows (and at the ends)
        if (buttress) {
          const bt = margin + (usable * k) / n;
          for (const tt of k === n - 1 ? [bt, margin + usable] : [bt]) {
            const bx = a[0] + ux * tt + nx * 0.35,
              by = a[1] + uy * tt + ny * 0.35;
            kit.box(batch, brick, bx, by, 0, 0.7, 0.7, buttress * 0.6, ang);
            kit.box(
              batch,
              bath,
              bx + nx * 0.05,
              by + ny * 0.05,
              buttress * 0.6,
              0.8,
              0.8,
              0.15,
              ang,
            );
            kit.box(
              batch,
              brick,
              bx - nx * 0.1,
              by - ny * 0.1,
              buttress * 0.6 + 0.15,
              0.6,
              0.5,
              buttress * 0.4 - 0.15,
              ang,
            );
            kit.box(batch, bath, bx - nx * 0.1, by - ny * 0.1, buttress, 0.7, 0.6, 0.2, ang);
          }
        }
      }
    };

    const parts = (b.parts?.length ? b.parts : [{ polys: b.polys, h: b.h, minh: 0 }]).map((p) => {
      const r = p.polys[0][0];
      return { ...p, ring: kit.ringArea(r) < 0 ? r.slice().reverse() : r };
    });
    // parapet with Bath stone coping; battlemented when crenel > 0
    const parapet = (ring, z, crenel = 0) => {
      const o = kit.offsetRing(ring, 0.15),
        inner = kit.offsetRing(ring, -0.3);
      kit.walls(batch, bath, [[o]], z, z + 0.45, { bay: 1e6 });
      kit.walls(batch, bath, [[inner.slice().reverse()]], z, z + 0.45, { bay: 1e6 });
      kit.cap(batch, bath, [[o, inner.slice().reverse()]], z + 0.45);
      kit.cap(batch, bath, [[o, ring.slice().reverse()]], z, { down: true });
      if (crenel)
        for (let k = 0; k < o.length; k++) {
          const p0 = o[k],
            p1 = o[(k + 1) % o.length];
          const len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
          const n = Math.max(1, Math.round(len / crenel));
          const ang = Math.atan2(p1[1] - p0[1], p1[0] - p0[0]);
          for (let i = 0; i < n; i++) {
            const t = (i + 0.5) / n;
            const x = p0[0] + (p1[0] - p0[0]) * t - Math.sin(ang) * 0.2,
              y = p0[1] + (p1[1] - p0[1]) * t + Math.cos(ang) * 0.2;
            kit.box(batch, bath, x, y, z + 0.45, (len / n) * 0.5, 0.42, 0.55, ang);
          }
        }
    };
    const edges = (ring, fn) => {
      for (let k = 0; k < ring.length; k++) fn(ring[k], ring[(k + 1) % ring.length], k);
    };
    // crocketed octagonal pinnacle
    const pinnacle = (x, y, z, r) => {
      const prof = [
        [0, 0],
        [r * 1.1, 0],
        [r * 1.1, 0.25],
        [r, 0.3],
        [r, 2.0],
        [r * 1.15, 2.1],
        [r * 1.15, 2.3],
        [r * 0.9, 2.35],
        [0.05, 4.6],
        [0.12, 4.7],
        [0, 4.95],
      ];
      batch.addGeometry(
        bath,
        new THREE.LatheGeometry(
          prof.map(([a, c]) => new THREE.Vector2(a, c)),
          8,
        ).rotateX(Math.PI / 2),
        new THREE.Matrix4().makeRotationZ(A + Math.PI / 8).setPosition(x, y, z),
      );
      // crockets up the spirelet
      for (let k = 0; k < 4; k++)
        for (const t of [0.3, 0.6]) {
          const a = A + (k * Math.PI) / 2 + Math.PI / 4;
          const rr = r * 0.9 * (1 - t);
          kit.box(
            batch,
            bath,
            x + Math.cos(a) * rr,
            y + Math.sin(a) * rr,
            z + 2.35 + t * 2.25,
            0.18,
            0.18,
            0.18,
            a,
          );
        }
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
        kit.walls(batch, wallTex, [[ring]], 0, 11.5, { bay: 1, storey: 2 });
        kit.cornice(batch, bathD, ring, 0, { height: 0.5, projection: 0.12 });
        parapet(ring, 11.5);
        kit.cap(batch, leadM, [[ring]], 11.6);
        const tr = [
          at(cu - T / 2, cv - T / 2),
          at(cu + T / 2, cv - T / 2),
          at(cu + T / 2, cv + T / 2),
          at(cu - T / 2, cv + T / 2),
        ];
        kit.walls(batch, wallTex, [[tr]], 11.5, 24.5, { bay: 1, storey: 2 });
        for (const z of [11.5, 17.5])
          kit.cornice(batch, bath, tr, z, { height: 0.45, projection: 0.2 });
        kit.cornice(batch, bath, tr, 24.1, { height: 0.4, projection: 0.25 });
        // belfry lancets (louvred) and clock-stage roundels on each face
        edges(tr, (a, bb) => {
          lancets(a, bb, 19.1, { w: 0.9, h: 4.2, count: 2, margin: 1.6, mullion: false });
          const dx = bb[0] - a[0],
            dy = bb[1] - a[1],
            l = Math.hypot(dx, dy);
          const ang = Math.atan2(dy, dx);
          const mx = (a[0] + bb[0]) / 2 + (dy / l) * 0.05,
            my = (a[1] + bb[1]) / 2 - (dx / l) * 0.05;
          for (const off of [-1.15, 1.15])
            for (let j = 0; j < 7; j++)
              kit.box(
                batch,
                dark,
                mx + (dx / l) * off + (dy / l) * 0.05,
                my + (dy / l) * off - (dx / l) * 0.05,
                19.4 + j * 0.45,
                0.8,
                0.12,
                0.08,
                ang,
              );
          const ring2 = new THREE.TorusGeometry(0.85, 0.12, 4, 16);
          batch.addGeometry(
            bath,
            ring2,
            new THREE.Matrix4()
              .makeRotationZ(ang)
              .multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2))
              .setPosition(mx + (dy / l) * 0.05, my - (dx / l) * 0.05, 15.0),
          );
          ring2.dispose();
          const disc = new THREE.CircleGeometry(0.8, 16).rotateX(Math.PI / 2);
          batch.addGeometry(
            dark,
            disc,
            new THREE.Matrix4().makeRotationZ(ang).setPosition(mx, my, 15.0),
          );
          disc.dispose();
          lancets(a, bb, 12.4, { w: 0.6, h: 1.8, count: 1, margin: 0.5, mullion: false });
        });
        // corner buttresses rising into crocketed pinnacles
        for (const [su, sv] of [
          [-1, -1],
          [1, -1],
          [1, 1],
          [-1, 1],
        ]) {
          const [x, y] = at(cu + (su * T) / 2, cv + (sv * T) / 2);
          kit.box(batch, wallTex, x, y, 11.5, 1.3, 1.3, 13.6, A, [0.98, 0.98, 0.98]);
          for (const z of [15, 19, 23]) kit.box(batch, bath, x, y, z, 1.45, 1.45, 0.25, A);
          pinnacle(x, y, 25.1, 0.6);
        }
        // battlemented parapet
        const o = kit.offsetRing(tr, 0.1);
        kit.walls(batch, bath, [[o]], 24.5, 25.0, { bay: 1e6 });
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
        kit.cap(batch, leadM, [[tr]], 24.6);
        // flagpole on the tower roof
        const [fx, fy] = at(cu, cv);
        batch.addGeometry(
          kit.mat('white'),
          new THREE.CylinderGeometry(0.05, 0.07, 5, 6).rotateX(Math.PI / 2),
          new THREE.Matrix4().makeTranslation(fx, fy, 27.1),
        );
        // west door: pointed arch doorway with timber doors, hood mould and steps
        const [wx, wy] = at(e.u0, cv);
        const nx = -Math.cos(A),
          ny = -Math.sin(A);
        const dl = [wx - ny * 1.6, wy + nx * 1.6],
          dr = [wx + ny * 1.6, wy - nx * 1.6];
        // edge from dr to dl has outward normal (nx, ny) on its right
        const dA = Math.atan2(dl[1] - dr[1], dl[0] - dr[0]);
        const { surround } = lancetParts(2.2, 4.2);
        batch.addGeometry(
          bath,
          surround,
          new THREE.Matrix4().makeRotationZ(dA).setPosition(wx + nx * 0.02, wy + ny * 0.02, 0),
        );
        const dg = new THREE.ShapeGeometry(lancetShape(2.2, 4.2), 6).rotateX(Math.PI / 2);
        batch.addGeometry(
          doorM,
          dg,
          new THREE.Matrix4().makeRotationZ(dA).setPosition(wx + nx * 0.03, wy + ny * 0.03, 0),
        );
        dg.dispose();
        kit.box(batch, kit.mat('#2a1d15'), wx + nx * 0.05, wy + ny * 0.05, 0, 0.06, 0.05, 3.4, dA);
        for (let s2 = 0; s2 < 2; s2++)
          kit.box(
            batch,
            bathD,
            wx + nx * (0.6 + s2 * 0.4),
            wy + ny * (0.6 + s2 * 0.4),
            0,
            3.6 - s2 * 0.4,
            1.2 - s2 * 0.4,
            0.16 * (2 - s2),
            dA,
          );
        lancets(dr, dl, 6.2, { w: 1.6, h: 4.0, count: 1, margin: 0.8 });
        continue;
      }
      if (h >= 19) {
        // clerestoried nave: walls to 16 m, slate roof to the part height, ridge along the axis
        kit.walls(batch, wallTex, [[ring]], 0, 16, { bay: 1, storey: 2 });
        parapet(ring, 16);
        kit.pitchedRoof(batch, slate, brick, ring, A, 16.4, h - 16.4, 'gabled', { overhang: 0.2 });
        edges(ring, (a, bb) => {
          const len = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
          if (len > 20)
            lancets(a, bb, 12.5, { w: 1.1, h: 2.8, bay: 5.4, margin: 1.4, mullion: false });
        });
        continue;
      }
      if (area > 60 && h >= 13) {
        // aisles or chancel
        const e = kit.orientedExtent(ring, A);
        const len = e.u1 - e.u0,
          wid = e.v1 - e.v0;
        const along = len >= wid ? A : A + Math.PI / 2;
        const eave = h - (Math.min(len, wid) / 2) * 0.7;
        kit.walls(batch, wallTex, [[ring]], 0, eave, { bay: 1, storey: 2 });
        kit.cornice(batch, bathD, ring, 0, { height: 0.6, projection: 0.12 });
        kit.cornice(batch, bath, ring, 3.0, { height: 0.18, projection: 0.08 }); // sill course
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
          {
            overhang: 0.2,
          },
        );
        const chancel = wid > 7 && len < 12;
        edges(ring, (a, bb) => {
          const l = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
          if (chancel) {
            // triple east window and side lancets
            if (l > 7)
              lancets(a, bb, 3.4, {
                w: 1.3,
                h: Math.min(7.5, eave - 4),
                count: 3,
                margin: l / 2 - 2.6,
              });
            else if (l > 4) lancets(a, bb, 3.4, { w: 1.0, h: 5.0, count: 1, margin: 1 });
            return;
          }
          if (l > 10)
            lancets(a, bb, 3.4, {
              w: 1.3,
              h: Math.min(6.5, eave - 4.4),
              bay: 5.4,
              margin: 1.0,
              buttress: eave - 1.5,
            });
          else if (l > 4)
            lancets(a, bb, 3.4, { w: 1.2, h: Math.min(6.0, eave - 4.4), count: 1, margin: 1 });
        });
        continue;
      }
      // small annexes, porches, vestries: flat roofs behind a stone coping
      kit.walls(batch, wallTex, [[ring]], 0, h, { bay: 1, storey: 2 });
      kit.cornice(batch, bathD, ring, 0, { height: 0.5, projection: 0.1 });
      parapet(ring, h, h > 9 ? 1.4 : 0);
      kit.cap(batch, leadM, [[ring]], h + 0.1);
      edges(ring, (a, bb) => {
        const l = Math.hypot(bb[0] - a[0], bb[1] - a[1]);
        if (l > 3.2)
          lancets(a, bb, 1.8, { w: 0.9, h: Math.min(h - 3.4, 4.5), bay: 3.4, margin: 0.9 });
      });
    }
    g.add(batch.toGroup('holy_trinity_brompton'));
    for (const v of lancetGeo.values()) {
      v.surround.dispose();
      v.gl.dispose();
    }
    return g;
  },
};
