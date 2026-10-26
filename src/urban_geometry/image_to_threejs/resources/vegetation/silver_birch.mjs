// Silver birch (Betula pendula): slender white trunk with dark lenticel bands and a light,
// airy, narrow crown of small yellow-green leaves.
// Unit-height prototype (1 m tall); the instancer scales it to the tree's height.
// High detail: tapered trunk, main limbs and 16 jittered leaf clusters with a
// dappled foliage texture; low detail: trunk plus one crown mass for distant trees.
export default {
  id: 'silver_birch',
  kind: 'vegetation',
  name: 'Silver birch',
  size: [0.38, 0.38, 1],
  references: [
    {
      title: 'London plane - Gdansk tree trail',
      url: 'https://pg.edu.pl/en/sustainable-development/tree-trail/london-plane',
      used_for: 'park species set used for planting variety',
    },
  ],
  notes: 'Airy crown approximated with many small clusters.',
  build({ THREE, kit, detail = 'high' }) {
    const P = {
      seed: 0.53,
      clear: 0.32,
      trunk: 0.012,
      lean: 0.01,
      crown: 0.17,
      centre: 0.66,
      spread: 0.85,
      vertical: 1.6,
      squash: 1.1,
      core: 0.35,
      clusters: 16,
      limbs: 4,
      rough: 0.4,
      bark: 'birch',
      barkColors: ['#e8e6df', '#2b2a28', '#9e9a90'],
      leaves: ['#7a9a4a', '#6d8f42', '#87a556'],
    };
    const rand = kit.rng(P.seed);
    const g = new THREE.Group();
    const bark = kit.paintedMaterial(
      `asset:bark:${P.bark}`,
      64,
      128,
      (c, w, h) => {
        const r = kit.rng(P.seed + 0.5);
        c.fillStyle = P.barkColors[0];
        c.fillRect(0, 0, w, h);
        for (let i = 0; i < 160; i++) {
          c.fillStyle = P.barkColors[1 + (i % (P.barkColors.length - 1))];
          const x = r() * w,
            y = r() * h;
          if (P.bark === 'birch') c.fillRect(x, y, 6 + r() * 14, 1.5 + r() * 2);
          else if (P.bark === 'plane') {
            c.beginPath();
            c.ellipse(x, y, 3 + r() * 8, 4 + r() * 10, r() * 3, 0, Math.PI * 2);
            c.fill();
          } else c.fillRect(x, y, 1.5 + r() * 2, 8 + r() * 24);
        }
      },
      { roughness: 0.95 },
    );
    const leaves = P.leaves.map((tone, i) =>
      kit.paintedMaterial(
        `asset:leaf:${tone}`,
        128,
        128,
        (c, w, h) => {
          const r = kit.rng(0.31 + i * 0.17);
          c.fillStyle = tone;
          c.fillRect(0, 0, w, h);
          for (let k = 0; k < 900; k++) {
            const f = 0.7 + r() * 0.6;
            const col = new THREE.Color(tone).multiplyScalar(f);
            c.fillStyle = `#${col.getHexString()}`;
            c.beginPath();
            c.ellipse(r() * w, r() * h, 1.5 + r() * 3, 1 + r() * 2, r() * 3, 0, Math.PI * 2);
            c.fill();
          }
        },
        { roughness: 0.9 },
      ),
    );
    // Leaf cluster: icosphere with position-hashed jitter (shared vertices move together,
    // so the surface stays closed) and radial normals for soft shading.
    const blob = (radius, level, squash, seed) => {
      const geo = new THREE.IcosahedronGeometry(radius, level);
      const p = geo.attributes.position;
      const n = new Float32Array(p.count * 3);
      for (let k = 0; k < p.count; k++) {
        const x = p.getX(k),
          y = p.getY(k),
          z = p.getZ(k);
        const l = Math.hypot(x, y, z) || 1;
        const hsh =
          Math.abs(
            Math.sin(
              Math.round(x * 997) * 12.9898 +
                Math.round(y * 991) * 78.233 +
                Math.round(z * 983) * 37.719 +
                seed,
            ) * 43758.5453,
          ) % 1;
        const f = 1 + (hsh - 0.5) * P.rough;
        p.setXYZ(k, x * f, y * f, z * f * squash);
        n[k * 3] = x / l;
        n[k * 3 + 1] = y / l;
        n[k * 3 + 2] = z / l;
      }
      geo.setAttribute('normal', new THREE.BufferAttribute(n, 3));
      return geo;
    };
    const limb = (x0, y0, z0, x1, y1, z1, r0, r1, seg) => {
      const len = Math.hypot(x1 - x0, y1 - y0, z1 - z0);
      const geo = new THREE.CylinderGeometry(r1, r0, len, seg, 1, true);
      const m = new THREE.Mesh(geo, bark);
      m.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
      m.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        new THREE.Vector3(x1 - x0, y1 - y0, z1 - z0).normalize(),
      );
      g.add(m);
    };
    const high = detail !== 'low';
    const top = P.clear + 0.06;
    limb(0, 0, 0, P.lean, 0, top, P.trunk, P.trunk * 0.7, high ? 10 : 5);
    if (P.tiers) {
      // Conifer: stacked cones, each jittered.
      const n = high ? P.tiers : 2;
      for (let i = 0; i < n; i++) {
        const t = i / n;
        const r = P.crown * (1 - t * 0.75);
        const hgt = ((1 - P.clear) / n) * 1.6;
        const cone = new THREE.ConeGeometry(r, hgt, high ? 12 : 7, 1, true).rotateX(Math.PI / 2);
        const m = new THREE.Mesh(cone, leaves[i % leaves.length]);
        m.position.set(P.lean, 0, P.clear + t * (1 - P.clear) * 0.9 + hgt / 2);
        m.rotation.z = rand() * 6.28;
        g.add(m);
      }
      return g;
    }
    if (!high) {
      const geo = blob(P.crown, 1, P.squash, P.seed);
      const m = new THREE.Mesh(geo, leaves[0]);
      m.position.set(P.lean, 0, P.centre);
      m.scale.set(P.spread, P.spread, P.vertical);
      g.add(m);
      return g;
    }
    // Main limbs to the cluster positions, then the clusters themselves.
    const golden = 2.39996;
    for (let i = 0; i < P.clusters; i++) {
      const a = i * golden + rand() * 0.6;
      const rad = P.crown * P.spread * (i === 0 ? 0 : 0.3 + 0.68 * Math.sqrt(rand()));
      const z = P.centre + (rand() - 0.45) * P.crown * P.vertical * (i === 0 ? 0.3 : 1);
      const x = P.lean + Math.cos(a) * rad,
        y = Math.sin(a) * rad;
      const size = P.crown * (i === 0 ? P.core : 0.3 + 0.22 * rand());
      if (i > 0 && i <= P.limbs)
        limb(
          P.lean,
          0,
          top - 0.02,
          x * 0.8,
          y * 0.8,
          z - size * 0.4,
          P.trunk * 0.55,
          P.trunk * 0.2,
          6,
        );
      const m = new THREE.Mesh(blob(size, 1, P.squash, P.seed + i), leaves[i % leaves.length]);
      m.position.set(x, y, z);
      m.rotation.z = rand() * 6.28;
      g.add(m);
    }
    return g;
  },
};
