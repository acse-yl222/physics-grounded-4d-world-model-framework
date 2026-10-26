// West Brompton station, Old Brompton Road (Sir John Fowler for the Metropolitan District
// Railway, opened 1869; Grade II, "the best preserved example of a station on the
// District Line"). A single-storey classical booking hall of white Suffolk brick under a
// slate pavilion roof, with round-arched windows, stone cornice and rusticated quoins,
// beside the cutting; the platforms below are covered by the listed train shed canopies.
export default {
  id: 'west_brompton_station',
  name: 'West Brompton station',
  claims: ['ae4162c9-e46c-4f82-a97c-c97a4c1835f7'],
  references: [
    {
      title:
        'West Brompton Station including Booking Hall and Train Shed - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101385365-west-brompton-station-including-booking-hall-and-train-shed-and-staircases-and-retaining-wall-redcliffe-ward',
      used_for:
        'Sir John Fowler, classical style, white Suffolk brick booking hall with slate pavilion roof, opened 1869, best preserved District station',
    },
    {
      title: 'West Brompton station - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/West_Brompton_station',
      used_for: 'opening dates, District and Overground services',
    },
    {
      title: 'Listed Buildings Search - RBKC',
      url: 'https://www.rbkc.gov.uk/planning/listedbuildings/listeddetails.asp?ID=485827',
      used_for: 'listing record',
    },
  ],
  notes:
    'Booking hall occupies the whole Overture footprint at street level (h 7 m); bay rhythm, quoins, door ' +
    'position and roof pitch are estimates. The platforms are in a cutting in reality; here the platform ' +
    'canopies (iron columns, ridged glazed/slate roofs) stand at ground level along the mapped tracks and are ' +
    'unclaimed geometry. Signage drawn on canvas.',
  build({ THREE, kit, scene }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const ang = (-43.62 * Math.PI) / 180,
      CX = 342.92,
      CY = -2134.46;
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    const L = (u, v) => [CX + u * ca - v * sa, CY + u * sa + v * ca];
    const rect = (u0, u1, v0, v1) => [L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)];
    const brick = kit.paintedMaterial(
      'west_brompton:suffolk',
      256,
      256,
      (c, w, h) => {
        const r = kit.rng(0.913);
        c.fillStyle = '#b8b2a4';
        c.fillRect(0, 0, w, h);
        const rows = 48,
          bw = 21;
        for (let i = 0; i < rows; i++)
          for (let x = -(i % 2) * (bw / 2); x < w; x += bw) {
            const t = 0.9 + r() * 0.16;
            c.fillStyle = `rgb(${Math.round(226 * t)},${Math.round(218 * t)},${Math.round(196 * t)})`;
            c.fillRect(x + 0.6, (i * h) / rows + 0.6, bw - 1.2, h / rows - 1.2);
          }
      },
      { roughness: 0.9 },
    );
    const stone = kit.mat('#e2dccb', { roughness: 0.8 });
    const slate = kit.mat('#4d535a', { roughness: 0.75 });
    const glass = kit.mat('#2b3842', { roughness: 0.3, metalness: 0.2 });
    const green = kit.mat('#2f4f3e', { roughness: 0.6 });
    const iron = kit.mat('#3a4a42', { roughness: 0.5, metalness: 0.4 });
    const H = 6.4;
    const r = rect(-14.6, 14.6, -8.8, 8.8);
    kit.walls(batch, brick, [[r]], 0, H, { bay: 1, storey: 2 });
    kit.cornice(batch, stone, r, 0, { height: 0.6, projection: 0.12 });
    kit.cornice(batch, stone, r, H - 0.5, { height: 0.5, projection: 0.35, steps: 2 });
    kit.cornice(batch, stone, r, 3.9, { height: 0.18, projection: 0.06 });
    kit.pitchedRoof(batch, slate, brick, r, ang, H, 3.6, 'hipped', { overhang: 0.4 });
    // rusticated quoins
    for (const p of r)
      for (let z = 0.6; z < H - 0.5; z += 0.6) {
        const big = Math.round(z / 0.6) % 2;
        kit.box(batch, stone, p[0], p[1], z, big ? 1.1 : 0.8, big ? 1.1 : 0.8, 0.5, ang);
      }
    // round-arched windows on every elevation (outward normal on the right of a->b)
    for (let k = 0; k < 4; k++) {
      const a = r[k],
        b = r[(k + 1) % 4];
      kit.windowRow(batch, a, b, 1.3, {
        glass,
        frame: stone,
        head: 'arch',
        width: 1.5,
        height: 2.5,
        bay: 3.6,
        margin: 1.6,
        bars: 2,
        surround: 0.18,
        surroundMat: stone,
      });
    }
    // entrance on the Old Brompton Road (north-west) front: arched doorway, canopy, sign
    {
      const d = L(-14.75, 0);
      kit.box(batch, kit.mat('#3b2a1f'), d[0], d[1], 0, 0.08, 3.0, 3.2, ang);
      const c = L(-16.2, 0);
      kit.box(batch, iron, c[0], c[1], 3.4, 2.8, 8.5, 0.25, ang);
      for (const v of [-4, 4]) {
        const p = L(-17.4, v);
        kit.box(batch, iron, p[0], p[1], 0, 0.14, 0.14, 3.4, ang);
      }
      const sign = kit.paintedMaterial(
        'west_brompton:sign',
        512,
        64,
        (cx, w, h) => {
          cx.fillStyle = '#21402f';
          cx.fillRect(0, 0, w, h);
          cx.fillStyle = '#f1ead6';
          cx.font = 'bold 36px serif';
          cx.textAlign = 'center';
          cx.textBaseline = 'middle';
          cx.fillText('WEST BROMPTON STATION', w / 2, h / 2 + 2);
        },
        { roughness: 0.6 },
      );
      const a = L(-14.95, 5.5),
        b = L(-14.95, -5.5);
      batch.quad(
        sign,
        [a[0], a[1], 4.3],
        [b[0], b[1], 4.3],
        [b[0], b[1], 5.4],
        [a[0], a[1], 5.4],
        [0, 0],
        [1, 0],
        [1, 1],
        [0, 1],
      );
    }

    // ---- platform canopies along the mapped tracks -------------------------------------
    {
      const near = [];
      for (const rl of scene.rails ?? [])
        for (const p of rl.line) if (Math.hypot(p[0] - CX, p[1] - CY) < 90) near.push(p);
      // track axis: fit a line through the nearby rail points
      let mx = 0,
        my = 0;
      near.forEach((p) => ((mx += p[0]), (my += p[1])));
      mx /= near.length || 1;
      my /= near.length || 1;
      let sxx = 0,
        sxy = 0,
        syy = 0;
      near.forEach(([x, y]) => {
        sxx += (x - mx) ** 2;
        sxy += (x - mx) * (y - my);
        syy += (y - my) ** 2;
      });
      const ta = near.length > 2 ? 0.5 * Math.atan2(2 * sxy, sxx - syy) : ang;
      const tx = Math.cos(ta),
        ty = Math.sin(ta);
      const nx = -ty,
        ny = tx;
      // station-relative position along the track of the booking hall centre
      const s0 = (CX - mx) * tx + (CY - my) * ty;
      const dir = tx * ca + ty * sa >= 0 ? 1 : -1; // away from Old Brompton Road (south-east)
      const P = (s, d) => [mx + tx * s + nx * d, my + ty * s + ny * d];
      const LEN = 62;
      for (const off of [-6.2, 6.2]) {
        // timber-valanced canopy on cast-iron columns
        const sA = s0 + dir * 15.5,
          sB = sA + dir * LEN;
        const ms = (sA + sB) / 2;
        const c = P(ms, off);
        kit.box(batch, slate, c[0], c[1], 4.2, Math.abs(sB - sA), 4.6, 0.18, ta);
        const ridge = new THREE.CylinderGeometry(2.4, 2.4, Math.abs(sB - sA), 3, 1).rotateZ(
          Math.PI / 2,
        );
        ridge.scale(1, 1, 0.25);
        batch.addGeometry(
          kit.mat('#7d8c94', { roughness: 0.3, metalness: 0.3 }),
          ridge,
          new THREE.Matrix4().makeRotationZ(ta).setPosition(c[0], c[1], 4.65),
        );
        ridge.dispose();
        for (const side of [-2.3, 2.3]) {
          const e = P(ms, off + side);
          kit.box(batch, green, e[0], e[1], 3.6, Math.abs(sB - sA), 0.06, 0.6, ta);
        }
        for (let s = Math.min(sA, sB) + 2; s <= Math.max(sA, sB) - 2; s += 6) {
          const p = P(s, off);
          kit.box(batch, iron, p[0], p[1], 0, 0.22, 0.22, 4.2, ta);
        }
        // platform edge
        const pe = P(ms, off - Math.sign(off) * 0.4);
        kit.box(batch, kit.mat('#bdb6a8'), pe[0], pe[1], 0, Math.abs(sB - sA) + 6, 5.6, 0.9, ta);
      }
    }

    g.add(batch.toGroup('west_brompton_station'));
    return g;
  },
};
