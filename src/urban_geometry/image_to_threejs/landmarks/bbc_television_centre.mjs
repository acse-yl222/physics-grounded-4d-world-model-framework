// BBC Television Centre, Wood Lane, White City (Graham Dawbarn / Norman & Dawbarn,
// opened 1960; Grade II 2009; converted 2013-2018 by AHMM, Maccreanor Lavington,
// Duggan Morris, drmm and others). The "question mark" main block is an
// eight-storey drum around the circular Helios Courtyard, whose lower walls are
// faced in sea-green mosaic with a stepped pattern picked out in red; at the
// centre the 3 m gilded Helios (T. B. Huxley-Jones, 1960) on a tall column over
// a raised fountain bowl with the reclining figures of Sound and Vision. A glazed
// full-height stair tower stands proud of the drum; the studio ring (TC1-TC3,
// BBC Studioworks) wraps it, Studio 1 fronted by a blind brick wall with 26 white
// "atomic" discs. The Rotunda (Endo) crowns the north side; 2 Television Centre
// (AHMM offices) and The Crescent residential range complete the site.
export default {
  id: 'bbc_television_centre',
  name: 'BBC Television Centre',
  claims: [
    'ce7e9a82-4a6e-4a89-83be-731f0979dadd', // The Helios Courtyard (main drum)
    '9bcde68a-4dad-4732-a9dd-f58c0c2ce473', // Endo at the Rotunda
    '141f12da-152d-4b90-b12d-c4dcde5e7710', // TC1
    '14dc4fae-9f26-4c16-8b94-51eedd6b1aee', // TC2
    '5349aecc-0f9b-4b10-81fc-64e8aa470aba', // TC3
    'bb7c2a95-2aca-4a2e-bf90-388606f5aa25', // BBC Studioworks (studio ring)
    '57b2711d-3c29-4489-872e-76d314cdb46e', // 2 Television Centre
    'c685cd6f-495b-41fe-8288-45cb604f2647', // The Crescent
  ],
  references: [
    {
      title: 'BBC Television Centre listing - British Listed Buildings (Historic England)',
      url: 'https://britishlistedbuildings.co.uk/101393371-bbc-television-centre-including-the-main-circular-range-excluding-the-spur-the-original-scenery-block-and-the-former-canteen-shepherds-bush-green-ward',
      used_for:
        'eight-storey drum, sea-green mosaic with red stepped pattern in the courtyard, glazed full-height stair tower, Studio 1 blind brick wall with 26 white discs',
    },
    {
      title: 'Helios (statue) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Helios_(statue)',
      used_for: '3 m gilded bronze Helios by Huxley-Jones on the central column',
    },
    {
      title: 'Helios Returned to Courtyard at Television Centre',
      url: 'https://new.actonw3.com/page/shared/common/bbc1702.htm',
      used_for: 'fountain bowl with two reclining figures representing sound and vision',
    },
    {
      title: "Television Centre, Shepherd's Bush - manchesterhistory.net",
      url: 'https://manchesterhistory.net/architecture/1960/bbctv.html',
      used_for: 'Dawbarn question-mark plan curling round the inner courtyard',
    },
    {
      title: 'Television Centre - RIBA London Award 2019',
      url: 'https://ribaj.com/buildings/regional-awards-2019-television-centre-ahmm-maccreanor-lavington-morris-drmm-mikhail-riches-piercy-haptic-archer-humphreys-coffey-architects-stanhop-mitsui-fudosan-aimco-bbc-studioworks-homes-refurbishment',
      used_for: 'redevelopment team; Helios, Piper murals and Studio 1 atomic dots retained',
    },
    {
      title: 'Television Centre - The Spaces',
      url: 'https://thespaces.com/londons-television-centre-emerges-from-a-1bn-revamp/',
      used_for: 'AHMM restored the green mosaics, fin walls and sweeping staircases',
    },
    {
      title: 'Television Centre 2TVC - SCP',
      url: 'https://professional.scp.co.uk/?p=191483',
      used_for: '2 Television Centre as the new office building',
    },
  ],
  notes:
    'Massing follows the Overture footprints and heights. Outer drum elevation (cream frame, pale blue tiled spandrels, ribbon windows) and the modern 2TVC / Crescent elevations are inferred, not traced from photos. Helios and the Sound/Vision figures are simplified stand-ins. The question-mark tail (spur) and the newer residential blocks to the south/east are left to the generic layer.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const DS = { side: THREE.DoubleSide };
    const B = (id) => byId[id];
    const drum = B('ce7e9a82-4a6e-4a89-83be-731f0979dadd');
    const outer = drum.polys[0][0],
      inner = drum.polys[0][1];
    // Courtyard centre and radius.
    let cx = 0,
      cy = 0;
    for (const p of inner) {
      cx += p[0] / inner.length;
      cy += p[1] / inner.length;
    }
    // Distance from the courtyard centre to the outer drum wall along a bearing.
    const rayR = (t) => {
      const dx = Math.cos(t),
        dy = Math.sin(t);
      let best = 0;
      for (let k = 0; k < outer.length; k++) {
        const a = outer[k],
          b = outer[(k + 1) % outer.length];
        const ex = b[0] - a[0],
          ey = b[1] - a[1];
        const den = dx * ey - dy * ex;
        if (Math.abs(den) < 1e-9) continue;
        const ax = a[0] - cx,
          ay = a[1] - cy;
        const r = (ax * ey - ay * ex) / den,
          u = (ax * dy - ay * dx) / den;
        if (r > 0 && u >= 0 && u <= 1 && (best === 0 || r < best)) best = r;
      }
      return best;
    };

    // ---------- materials ----------
    const outerF = kit.paintedMaterial(
      'tvc:outer',
      512,
      256,
      (x, w, h) => {
        for (let s = 0; s < 2; s++) {
          const y0 = s * 128;
          x.fillStyle = '#e9e3d3';
          x.fillRect(0, y0, w, 128);
          // Ribbon windows.
          x.fillStyle = '#2f404c';
          x.fillRect(0, y0 + 12, w, 66);
          x.fillStyle = 'rgba(200,215,225,0.25)';
          x.fillRect(0, y0 + 12, w, 20);
          x.fillStyle = '#e9e3d3';
          for (let k = 0; k < w; k += 32) x.fillRect(k, y0 + 12, 4, 66);
          // Pale blue mosaic spandrel panel.
          x.fillStyle = '#8fb3c8';
          x.fillRect(0, y0 + 82, w, 38);
          x.fillStyle = 'rgba(255,255,255,0.18)';
          for (let k = 0; k < w; k += 6) x.fillRect(k, y0 + 82, 1, 38);
          for (let k = y0 + 82; k < y0 + 120; k += 6) x.fillRect(0, k, w, 1);
          x.fillStyle = '#d6cfbd';
          x.fillRect(0, y0 + 120, w, 8);
        }
        // Fin walls between bays.
        x.fillStyle = '#f2eee2';
        for (let k = 0; k < 4; k++) x.fillRect(k * 128, 0, 10, h);
      },
      DS,
    );
    const courtF = kit.paintedMaterial(
      'tvc:court',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#ece6d6';
        x.fillRect(0, 0, w, h);
        for (let s = 0; s < 2; s++) {
          const y0 = s * 128;
          x.fillStyle = '#34444f';
          x.fillRect(8, y0 + 14, w - 16, 86);
          x.fillStyle = '#ece6d6';
          for (let k = 0; k < w; k += 64) x.fillRect(k, y0 + 14, 6, 86);
          x.fillRect(0, y0 + 56, w, 3);
        }
      },
      DS,
    );
    const mosaic = kit.paintedMaterial(
      'tvc:mosaic',
      512,
      128,
      (x, w, h) => {
        x.fillStyle = '#4f9a87';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(255,255,255,0.12)';
        for (let k = 0; k < w; k += 5) x.fillRect(k, 0, 1, h);
        for (let k = 0; k < h; k += 5) x.fillRect(0, k, w, 1);
        // Stepped pattern picked out in red tiles.
        x.fillStyle = '#b3423a';
        for (let k = 0; k < w; k += 128)
          for (let st = 0; st < 5; st++) x.fillRect(k + st * 16, 96 - st * 16, 18, 6);
      },
      DS,
    );
    const brick = kit.paintedMaterial(
      'tvc:studio_brick',
      256,
      256,
      (x, w, h) => {
        x.fillStyle = '#93583f';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(240,220,200,0.15)';
        for (let r = 0; r < h; r += 4) x.fillRect(0, r, w, 1);
        x.fillStyle = 'rgba(0,0,0,0.06)';
        for (let r = 0; r < h; r += 8)
          for (let k = (r / 8) % 2 ? 0 : 6; k < w; k += 12) x.fillRect(k, r, 1, 4);
      },
      DS,
    );
    const atoms = kit.paintedMaterial(
      'tvc:atoms',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#93583f';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(240,220,200,0.15)';
        for (let r = 0; r < h; r += 4) x.fillRect(0, r, w, 1);
        // 26 white atom-like discs with orbit rings.
        const r = kit.rng(0.26);
        for (let k = 0; k < 26; k++) {
          const px = 30 + (k % 9) * 56 + (Math.floor(k / 9) % 2) * 26 + r() * 8,
            py = 46 + Math.floor(k / 9) * 72 + r() * 10;
          x.fillStyle = '#f4f2ec';
          x.beginPath();
          x.arc(px, py, 8, 0, Math.PI * 2);
          x.fill();
          x.strokeStyle = '#f4f2ec';
          x.lineWidth = 2;
          x.beginPath();
          x.ellipse(px, py, 20, 7, 0.5 + k, 0, Math.PI * 2);
          x.stroke();
        }
      },
      DS,
    );
    const office = kit.paintedMaterial(
      'tvc:2tvc',
      512,
      256,
      (x, w, h) => {
        x.fillStyle = '#35495a';
        x.fillRect(0, 0, w, h);
        x.fillStyle = 'rgba(210,225,235,0.22)';
        x.fillRect(0, 0, w, h * 0.3);
        x.fillStyle = '#d9d7d0';
        for (let s = 0; s < 2; s++) x.fillRect(0, s * 128, w, 16);
        for (let k = 0; k < w; k += 32) x.fillRect(k, 0, 8, h); // vertical fins
      },
      DS,
    );
    const concrete = kit.mat('#d8d3c6', DS);
    const roofM = kit.mat('#8d9091', DS);
    const gold = kit.mat('gold', DS);
    const glassM = kit.mat('glass', DS);
    const dark = kit.mat('dark_steel', DS);

    // ---------- main drum ----------
    const H = drum.h; // 27 m, eight storeys
    const st = H / 8;
    kit.walls(batch, outerF, [[outer]], 0, H - st, { bay: 3.2, storey: st });
    // Set-back top storey on the outer face.
    kit.walls(batch, courtF, [[kit.offsetRing(outer, -1.5)]], H - st, H, { bay: 3.2, storey: st });
    kit.cap(
      batch,
      concrete,
      [[outer, kit.offsetRing(outer, -1.5).slice()].map((r, k) => (k ? r.slice().reverse() : r))],
      H - st,
    );
    // Courtyard face: green mosaic lower level, glazed curtain walling above.
    const innerRing = inner; // CW hole: walls face into the courtyard
    kit.walls(batch, mosaic, [[innerRing]], 0, 4.2, { bay: 4.2, storey: 2.1 });
    kit.walls(batch, courtF, [[innerRing]], 4.2, H, { bay: 3.2, storey: st, uvBase: 4.2 });
    kit.cap(batch, roofM, [[kit.offsetRing(outer, -1.5), innerRing]], H);
    kit.walls(batch, concrete, [[outer]], H - st - 0.1, H - st + 1.0);
    kit.walls(batch, concrete, [[innerRing]], H, H + 1.0);
    // Courtyard paving.
    kit.cap(batch, kit.mat('#c9c3b5', DS), [[innerRing.slice().reverse()]], 0.12);

    // Glazed full-height stair tower proud of the drum (south-east, facing the plaza).
    {
      const a = -0.5; // bearing from the courtyard centre
      const R = rayR(a) + 2;
      const tx = cx + Math.cos(a) * R,
        ty = cy + Math.sin(a) * R;
      const ta = a + Math.PI / 2;
      kit.box(
        batch,
        kit.mat('#4b6574', { roughness: 0.1, metalness: 0.3, side: THREE.DoubleSide }),
        tx,
        ty,
        0,
        8,
        4.5,
        H + 1.5,
        ta,
      );
      kit.box(batch, concrete, tx, ty, H + 1.5, 8.6, 5, 0.6, ta);
      // Cantilevered stair flights visible behind the glass.
      for (let z = 1.5; z < H; z += st / 2) {
        const off = ((z / (st / 2)) % 2 ? 1 : -1) * 1.6;
        kit.box(
          batch,
          kit.mat('#f0ece2', DS),
          tx + Math.cos(ta) * off,
          ty + Math.sin(ta) * off,
          z,
          3.4,
          3.6,
          0.25,
          ta + 0.18,
        );
      }
    }
    // BBC lettering band on the drum facing Wood Lane (east).
    {
      const sign = kit.paintedMaterial(
        'tvc:sign',
        1024,
        128,
        (x, w, h) => {
          x.clearRect(0, 0, w, h);
          x.fillStyle = '#f2eee2';
          x.fillRect(0, 0, w, h);
          x.fillStyle = '#1b1b1b';
          x.font = 'bold 78px sans-serif';
          x.textAlign = 'center';
          x.textBaseline = 'middle';
          x.fillText('TELEVISION CENTRE', w / 2, h / 2 + 4);
        },
        DS,
      );
      const a0 = 0.25,
        a1 = 0.75,
        n = 8,
        z0 = H - st - 1.3,
        z1 = H - st - 0.1;
      for (let k = 0; k < n; k++) {
        const t0 = a0 + ((a1 - a0) * k) / n,
          t1 = a0 + ((a1 - a0) * (k + 1)) / n;
        const R0 = rayR(t0) + 0.15,
          R1 = rayR(t1) + 0.15;
        const P0 = [cx + Math.cos(t0) * R0, cy + Math.sin(t0) * R0],
          P1 = [cx + Math.cos(t1) * R1, cy + Math.sin(t1) * R1];
        batch.quad(
          sign,
          [P0[0], P0[1], z0],
          [P1[0], P1[1], z0],
          [P1[0], P1[1], z1],
          [P0[0], P0[1], z1],
          [k / n, 0],
          [(k + 1) / n, 0],
          [(k + 1) / n, 1],
          [k / n, 1],
        );
      }
    }

    // ---------- Helios ----------
    {
      const add = (geo, m, x, y, z, rx = Math.PI / 2) => {
        geo.rotateX(rx);
        batch.addGeometry(m, geo, new THREE.Matrix4().makeTranslation(x, y, z));
        geo.dispose();
      };
      // Raised circular pool with mosaic kerb.
      add(new THREE.CylinderGeometry(7.5, 7.5, 0.7, 40, 1, true), mosaic, cx, cy, 0.35);
      add(new THREE.CylinderGeometry(7.4, 7.4, 0.05, 40), kit.mat('water', DS), cx, cy, 0.6);
      // Fountain bowl on a stem, two reclining figures beneath it.
      add(new THREE.CylinderGeometry(0.8, 1.0, 2.2, 16), concrete, cx, cy, 1.7);
      add(new THREE.CylinderGeometry(3.0, 1.2, 0.7, 24), concrete, cx, cy, 3.1);
      for (const s of [-1, 1]) {
        const fx = cx + s * 2.0,
          fy = cy;
        const body = new THREE.CapsuleGeometry(0.32, 1.5, 4, 8);
        body.rotateZ(Math.PI / 2 + s * 0.25);
        batch.addGeometry(gold, body, new THREE.Matrix4().makeTranslation(fx, fy, 1.1));
        body.dispose();
        add(new THREE.SphereGeometry(0.26, 10, 8), gold, fx + s * 0.95, fy, 1.55);
      }
      // Tall slender column and the 3 m gilded figure, arm raised.
      add(new THREE.CylinderGeometry(0.42, 0.5, 9.5, 16), mosaic, cx, cy, 3.45 + 4.75);
      add(new THREE.CylinderGeometry(0.75, 0.55, 0.5, 16), concrete, cx, cy, 13.45);
      const z0 = 13.7;
      for (const s of [-1, 1])
        add(new THREE.CylinderGeometry(0.13, 0.11, 1.4, 8), gold, cx + s * 0.16, cy, z0 + 0.7); // legs
      add(new THREE.CapsuleGeometry(0.3, 0.75, 4, 10), gold, cx, cy, z0 + 1.75); // torso
      add(new THREE.SphereGeometry(0.2, 12, 10), gold, cx, cy, z0 + 2.55); // head
      const arm = new THREE.CylinderGeometry(0.08, 0.08, 1.1, 6);
      arm.rotateX(Math.PI / 2);
      batch.addGeometry(
        gold,
        arm,
        new THREE.Matrix4().makeRotationY(0.5).setPosition(cx + 0.45, cy, z0 + 2.65),
      );
      batch.addGeometry(
        gold,
        arm,
        new THREE.Matrix4().makeRotationY(-1.1).setPosition(cx - 0.55, cy, z0 + 1.75),
      );
      arm.dispose();
    }

    // ---------- Rotunda (Endo) ----------
    {
      const rot = B('9bcde68a-4dad-4732-a9dd-f58c0c2ce473');
      const rr = rot.polys[0][0];
      kit.walls(batch, outerF, [[rr]], 0, H - st, { bay: 3.2, storey: st });
      kit.walls(batch, glassM, [[rr]], H - st, rot.h);
      kit.cap(batch, concrete, [[kit.offsetRing(rr, 0.8)]], rot.h);
      kit.walls(batch, concrete, [[kit.offsetRing(rr, 0.8)]], rot.h - 0.5, rot.h);
    }

    // ---------- Studio ring ----------
    const studio = (id, wallM, h, opts = {}) => {
      const b = B(id);
      kit.walls(batch, wallM, b.polys, 0, h, { bay: opts.bay ?? 4, storey: opts.storey ?? 4 });
      kit.cap(batch, roofM, b.polys, h);
      kit.walls(batch, concrete, b.polys, h - 0.6, h + 0.4);
      // Lighting-grid penthouse / plant.
      if (opts.penthouse) {
        const r = b.polys[0][0];
        const fr = kit.ringFrame(r);
        kit.box(batch, concrete, fr.cx, fr.cy, h, fr.length * 0.6, fr.width * 0.6, 2.8, fr.angle);
      }
    };
    // TC1 (Studio 1): atoms on the Wood Lane face, brick elsewhere.
    {
      const b = B('141f12da-152d-4b90-b12d-c4dcde5e7710');
      const r = b.polys[0][0];
      for (let k = 0; k < r.length; k++) {
        const a = r[k],
          c = r[(k + 1) % r.length];
        const len = Math.hypot(c[0] - a[0], c[1] - a[1]);
        const east = (a[0] + c[0]) / 2 > -1712;
        batch.quad(
          east ? atoms : brick,
          [a[0], a[1], 0],
          [c[0], c[1], 0],
          [c[0], c[1], b.h],
          [a[0], a[1], b.h],
          [0, 0],
          east ? [1, 0] : [len / 8, 0],
          east ? [1, 1] : [len / 8, b.h / 8],
          east ? [0, 1] : [0, b.h / 8],
        );
      }
      kit.cap(batch, roofM, b.polys, b.h);
      kit.walls(batch, concrete, b.polys, b.h - 0.6, b.h + 0.4);
      const fr = kit.ringFrame(r);
      kit.box(batch, concrete, fr.cx, fr.cy, b.h, fr.length * 0.55, fr.width * 0.55, 2.8, fr.angle);
    }
    studio('14dc4fae-9f26-4c16-8b94-51eedd6b1aee', brick, 20, {
      penthouse: true,
      bay: 8,
      storey: 8,
    });
    studio('5349aecc-0f9b-4b10-81fc-64e8aa470aba', brick, 20, {
      penthouse: true,
      bay: 8,
      storey: 8,
    });
    // BBC Studioworks: curved studio ring corridor block, cream with ribbon windows.
    {
      const b = B('bb7c2a95-2aca-4a2e-bf90-388606f5aa25');
      kit.walls(batch, outerF, b.polys, 0, b.h, { bay: 3.2, storey: 4 });
      kit.cap(batch, roofM, b.polys, b.h);
      kit.walls(batch, concrete, b.polys, b.h - 0.3, b.h + 0.8);
    }

    // ---------- 2 Television Centre (offices) ----------
    {
      const b = B('57b2711d-3c29-4489-872e-76d314cdb46e');
      kit.walls(batch, office, b.polys, 0, b.h, { bay: 3, storey: 3.6 });
      kit.cap(batch, roofM, b.polys, b.h);
      kit.walls(batch, concrete, b.polys, b.h, b.h + 1.1);
      for (const p of b.parts ?? []) {
        kit.walls(batch, office, p.polys, p.minh, p.h, { bay: 3, storey: 3.6 });
        kit.cap(batch, kit.mat('#7f9a6a', DS), p.polys, p.h + 0.05); // roof terraces
      }
      const fr = kit.ringFrame(b.polys[0][0]);
      kit.box(
        batch,
        kit.mat('#5c6266', DS),
        fr.cx,
        fr.cy,
        b.h,
        fr.length * 0.35,
        fr.width * 0.3,
        3.2,
        fr.angle,
      );
    }

    // ---------- The Crescent (residential) ----------
    {
      const b = B('c685cd6f-495b-41fe-8288-45cb604f2647');
      kit.walls(batch, kit.facade('london_stock', 3), b.polys, 0, b.h - 3.2, {
        bay: 3.4,
        storey: 3.2,
      });
      kit.walls(
        batch,
        kit.facade('metal_clad', 1),
        [[kit.offsetRing(b.polys[0][0], -1.2)]],
        b.h - 3.2,
        b.h,
        { bay: 3.4, storey: 3.2 },
      );
      kit.cap(batch, concrete, [[b.polys[0][0]]], b.h - 3.2);
      kit.cap(batch, roofM, [[kit.offsetRing(b.polys[0][0], -1.2)]], b.h);
    }
    g.add(batch.toGroup('bbc_television_centre'));
    return g;
  },
};
