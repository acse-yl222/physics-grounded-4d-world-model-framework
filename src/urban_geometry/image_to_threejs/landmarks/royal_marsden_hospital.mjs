// The Royal Marsden Hospital, Fulham Road, Chelsea - the world's first hospital dedicated
// to cancer (founded by William Marsden in 1851 as the Cancer Hospital; moved to Fulham
// Road in 1862, funded by Baroness Burdett-Coutts; enlarged in the 1880s to designs by
// Alexander Graham). The Victorian Fulham Road range stands behind a forecourt between
// two projecting pavilions; Granard House closes the corner with Dovehouse Street and the
// Wallace Wing runs down Dovehouse Street.
export default {
  id: 'royal_marsden_hospital',
  name: 'Royal Marsden Hospital',
  claims: [
    '996fe2fe-07d3-4e22-a8b6-ecfcaf367726',
    'eb3786ed-a82f-4af4-b093-bb2e2654748f',
    'f971668e-fc32-4e45-9daf-c55902b5303f',
  ],
  references: [
    {
      title: 'Royal Marsden Hospital - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Royal_Marsden_Hospital',
      used_for: 'history, move to Fulham Road in 1862, original architects',
    },
    {
      title:
        'Exterior view from the north-west of the entrance front of the Cancer Hospital - Historic England',
      url: 'https://historicengland.org.uk/images-books/photos/item/BL08600',
      used_for: 'Bedford Lemere 1888 photograph of the entrance front; architect Alexander Graham',
    },
    {
      title: 'William Marsden - English Heritage blue plaques',
      url: 'https://www.english-heritage.org.uk/visit/blue-plaques/william-marsden',
      used_for: 'founding of the Cancer Hospital, Fulham Road 1862',
    },
    {
      title: 'Fulham Road - Hidden London',
      url: 'https://hidden-london.com/?p=38187',
      used_for: 'hospitals along Fulham Road',
    },
  ],
  notes:
    'Facade materials were not described by any source found: the Victorian range is modelled in red brick ' +
    'with stone bands and slate pavilion roofs (typical of the 1880s; unverified). U-shaped front from the ' +
    'Overture footprint (central range set back behind the forecourt). Heights: main range 4 storeys + roof ' +
    '(~19 m to the ridge), Granard House 6 storeys (20 m), Wallace Wing 4 storeys (16 m). Window rhythm, ' +
    'porch, gables and signage are interpretive.',
  build({ THREE, kit, byId }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ringOf = (id) => {
      const r = byId[id].polys[0][0].slice();
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const frameOf = (deg, cx, cy) => {
      const a = (deg * Math.PI) / 180,
        c = Math.cos(a),
        s = Math.sin(a);
      return { a, L: (u, v) => [cx + u * c - v * s, cy + u * s + v * c] };
    };
    const rectOf = (F, u0, u1, v0, v1) => {
      const r = [F.L(u0, v0), F.L(u1, v0), F.L(u1, v1), F.L(u0, v1)];
      return kit.ringArea(r) < 0 ? r.reverse() : r;
    };
    const red = kit.mat('#9b4f3a', { roughness: 0.9 });
    const stone = kit.mat('#ddd4bf', { roughness: 0.8 });
    const slate = kit.mat('#50565c', { roughness: 0.75 });
    const glass = kit.mat('#2b353d', { roughness: 0.3, metalness: 0.2 });
    const frameW = kit.mat('#efece4');
    const stock = kit.mat('#b9a27c', { roughness: 0.9 });
    const roofM = kit.mat('#7f8384');
    const windows = (ring, z0, n, st, o = {}) =>
      kit.windowGrid(batch, ring, z0, n, st, () => ({
        glass,
        frame: frameW,
        sill: stone,
        head: 'lintel',
        width: 1.2,
        height: 2.1,
        bay: 3.2,
        margin: 1.0,
        bars: 2,
        ...o,
      }));

    // ---- Victorian Fulham Road range (Marsden Wing) ----------------------------------------
    {
      const F = frameOf(43.99, 1910.78, -1732.19); // u: north-east along Fulham Road; v+: towards Fulham Road
      const ring = ringOf('996fe2fe-07d3-4e22-a8b6-ecfcaf367726');
      const E = 15.8;
      kit.walls(batch, red, [[ring]], 0, E, { bay: 1e6 });
      kit.cap(batch, roofM, [[ring]], E);
      for (const z of [0, 4.2, 8.1, 12.0])
        kit.cornice(batch, stone, ring, z, { height: z ? 0.25 : 0.8, projection: z ? 0.08 : 0.1 });
      kit.cornice(batch, stone, ring, E - 0.6, { height: 0.6, projection: 0.4, steps: 2 });
      windows(ring, 1.2, 4, 3.9, { head: 'segment' });
      // slate roofs: pavilion roofs over the two projecting wings, a long roof over the range
      const wings = [rectOf(F, -32.4, -17.2, 2.0, 10.7), rectOf(F, 13.0, 32.4, 2.6, 10.2)];
      for (const w of wings)
        kit.pitchedRoof(batch, slate, red, w, F.a, E, 4.2, 'pyramidal', { overhang: 0.2 });
      const range = rectOf(F, -32.4, 30.4, -9.8, 2.6);
      kit.pitchedRoof(batch, slate, red, range, F.a, E, 3.6, 'hipped', { overhang: 0.2 });
      // dormers and chimney stacks
      for (let u = -26; u <= 26; u += 6.5) {
        const p = F.L(u, 1.2);
        kit.box(batch, red, p[0], p[1], E, 1.6, 1.4, 2.0, F.a);
        kit.box(batch, slate, p[0], p[1], E + 2.0, 1.9, 1.7, 0.3, F.a);
        const q = F.L(u + 3.2, -3.5);
        if (Math.abs(u) > 4) kit.box(batch, red, q[0], q[1], E + 1.5, 0.9, 2.4, 3.6, F.a);
      }
      // gabled entrance porch in the centre of the recessed front
      {
        const pr = rectOf(F, -4.0, 4.0, 3.8, 7.6);
        kit.walls(batch, stone, [[pr]], 0, 4.4, { bay: 1e6 });
        kit.pitchedRoof(batch, slate, stone, pr, F.a + Math.PI / 2, 4.4, 2.2, 'gabled', {
          overhang: 0.2,
        });
        const d = F.L(0, 7.65);
        kit.box(batch, kit.mat('#2a2f33'), d[0], d[1], 0, 3.2, 0.06, 3.2, F.a);
        const sign = kit.paintedMaterial(
          'royal_marsden:sign',
          1024,
          96,
          (c, w, h) => {
            c.fillStyle = '#ffffff';
            c.fillRect(0, 0, w, h);
            c.fillStyle = '#0d1f4f';
            c.font = 'bold 60px serif';
            c.textAlign = 'center';
            c.textBaseline = 'middle';
            c.fillText('THE ROYAL MARSDEN', w / 2, h / 2 + 3);
          },
          { roughness: 0.6 },
        );
        const p = F.L(6, 4.1),
          q = F.L(-6, 4.1);
        // p -> q runs along -u, so the quad faces +v (Fulham Road)
        batch.quad(
          sign,
          [p[0], p[1], 12.5],
          [q[0], q[1], 12.5],
          [q[0], q[1], 13.6],
          [p[0], p[1], 13.6],
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
        );
      }
      // forecourt paving and carriage drive
      const fc = rectOf(F, -17.0, 13.0, 3.0, 12.0);
      kit.cap(batch, kit.mat('#bcb5a6', { roughness: 0.95 }), [[fc]], 0.05);
    }

    // ---- Granard House (corner of Dovehouse Street) -----------------------------------------
    {
      const ring = ringOf('eb3786ed-a82f-4af4-b093-bb2e2654748f');
      const H = 20;
      kit.walls(batch, red, [[ring]], 0, H, { bay: 1e6 });
      kit.cap(batch, roofM, [[ring]], H);
      kit.cornice(batch, stone, ring, 0, { height: 3.6, projection: 0.12 });
      kit.cornice(batch, stone, ring, H - 0.7, { height: 0.7, projection: 0.25 });
      windows(ring, 1.0, 6, 3.2, {
        head: 'none',
        width: 1.4,
        height: 1.9,
        bay: 2.8,
        bars: 2,
        frame: kit.mat('#3c4246'),
      });
    }

    // ---- Wallace Wing (Dovehouse Street) -------------------------------------------------------
    {
      const ring = ringOf('f971668e-fc32-4e45-9daf-c55902b5303f');
      const H = 13.2;
      kit.walls(batch, stock, [[ring]], 0, H, { bay: 1e6 });
      kit.cornice(batch, stone, ring, H - 0.5, { height: 0.5, projection: 0.25 });
      const inner = kit.offsetRing(ring, -2.2);
      kit.cap(batch, slate, [[ring, inner.slice().reverse()]], H);
      kit.walls(batch, slate, [[inner]], H, H + 2.9, { bay: 1e6 });
      kit.cap(batch, roofM, [[inner]], H + 2.9);
      windows(ring, 1.1, 4, 3.2, { head: 'segment', width: 1.1 });
    }

    g.add(batch.toGroup('royal_marsden_hospital'));
    return g;
  },
};
