// Physical Energy, Kensington Gardens (G. F. Watts; this cast made at Thames Ditton in
// 1905 and unveiled on Lancaster Walk in 1907). A colossal bronze of a naked rider on a
// surging horse, the rider reining back and shading his eyes as he looks into the
// distance, on a plain granite pedestal at the meeting of Lancaster Walk and the
// radiating paths.
export default {
  id: 'physical_energy_statue',
  name: 'Physical Energy',
  claims: [],
  references: [
    {
      title: 'Physical Energy (sculpture) - Wikipedia',
      url: 'https://en.wikipedia.org/wiki/Physical_Energy_(sculpture)',
      used_for:
        'Watts, bronze casts, Kensington Gardens cast unveiled 1907, form of horse and rider',
    },
    {
      title: 'Physical Energy - Art UK',
      url: 'https://batch.artuk.org/discover/artworks/physical-energy-303930',
      used_for: 'bronze H 300 x W 380 x D 145 cm; granite plinth H 130 x W 503 x D 280 cm',
    },
    {
      title: 'Physical Energy equestrian statue, Lancaster Walk - British Listed Buildings',
      url: 'https://britishlistedbuildings.co.uk/101216829-physical-energy-equestrian-statue-lancaster-walk-knightsbridge-and-belgravia-ward/maps',
      used_for: 'position 51.5068, -0.1783 on Lancaster Walk; Grade II',
    },
    {
      title: 'Physical Energy - Victorian Web',
      url: 'https://www.victorianweb.org/victorian/sculpture/watts/3.html',
      used_for: 'rider shading his eyes, energy of the horse, Elgin Marbles influence',
    },
  ],
  notes:
    'Placed at the centre of the path junction in the scene (about 6 m from the listed coordinates). Pedestal ' +
    'and bronze sizes from Art UK; the horse and rider are a simplified low-poly reconstruction (body, ' +
    'straining neck, raised foreleg, rider leaning back with raised arm). The westward facing direction is an ' +
    'assumption.',
  build({ THREE, kit }) {
    const g = new THREE.Group();
    const batch = new kit.MeshBatch();
    const C = [1534.5, 38.5];
    const ang = Math.PI; // horse faces west (assumption)
    const ca = Math.cos(ang),
      sa = Math.sin(ang);
    const granite = kit.mat('#8f8a85', { roughness: 0.7 });
    const graniteL = kit.mat('#a39e98', { roughness: 0.7 });
    const bronze = kit.mat('#4a3d2e', { roughness: 0.45, metalness: 0.65 });
    // local x forward (head), y left, z up
    const M = (x, y, z, rz = 0, ry = 0, rx = 0) =>
      new THREE.Matrix4()
        .makeTranslation(C[0] + x * ca - y * sa, C[1] + x * sa + y * ca, z)
        .multiply(new THREE.Matrix4().makeRotationZ(ang + rz))
        .multiply(new THREE.Matrix4().makeRotationY(ry))
        .multiply(new THREE.Matrix4().makeRotationX(rx));
    const put = (geo, mat, m) => {
      batch.addGeometry(mat, geo, m);
      geo.dispose();
    };
    // granite pedestal 5.03 x 2.8 x 1.3 with a plinth step and cap moulding
    put(new THREE.BoxGeometry(5.5, 3.3, 0.25), graniteL, M(0, 0, 0.125));
    put(new THREE.BoxGeometry(5.03, 2.8, 1.0), granite, M(0, 0, 0.75));
    put(new THREE.BoxGeometry(5.2, 2.95, 0.15), graniteL, M(0, 0, 1.33));
    const Z = 1.4;
    // horse: barrel, chest, hindquarters
    const ell = (rx, ry, rz) => new THREE.SphereGeometry(1, 12, 8).scale(rx, ry, rz);
    put(ell(1.05, 0.42, 0.5), bronze, M(0.0, 0, Z + 1.45, 0, -0.12));
    put(ell(0.55, 0.44, 0.58), bronze, M(0.75, 0, Z + 1.6));
    put(ell(0.6, 0.46, 0.55), bronze, M(-0.8, 0, Z + 1.35));
    // neck and head thrust forward and up
    put(
      new THREE.CylinderGeometry(0.2, 0.32, 1.1, 10).rotateX(Math.PI / 2),
      bronze,
      M(1.3, 0, Z + 2.05, 0, 0.75),
    );
    put(ell(0.42, 0.17, 0.2), bronze, M(1.72, 0, Z + 2.45, 0, 0.45));
    // legs: hind legs planted, right foreleg raised
    const leg = (x, y, z0, len, tilt, bend = 0) => {
      const upper = new THREE.CylinderGeometry(0.09, 0.13, len * 0.55, 8).rotateX(Math.PI / 2);
      put(upper, bronze, M(x, y, z0 - len * 0.27, 0, tilt));
      const lx = x - Math.sin(tilt) * len * 0.55;
      const lower = new THREE.CylinderGeometry(0.07, 0.08, len * 0.5, 8).rotateX(Math.PI / 2);
      put(
        lower,
        bronze,
        M(lx + Math.sin(bend) * len * 0.2, y, z0 - len * 0.55 - len * 0.22, 0, bend),
      );
    };
    leg(-1.05, 0.22, Z + 1.15, 1.3, -0.25);
    leg(-1.0, -0.22, Z + 1.15, 1.3, -0.15);
    leg(0.85, 0.2, Z + 1.3, 1.35, 0.05);
    // raised foreleg
    put(
      new THREE.CylinderGeometry(0.09, 0.12, 0.6, 8).rotateX(Math.PI / 2),
      bronze,
      M(1.15, -0.2, Z + 1.15, 0, -1.0),
    );
    put(
      new THREE.CylinderGeometry(0.07, 0.08, 0.55, 8).rotateX(Math.PI / 2),
      bronze,
      M(1.42, -0.2, Z + 0.78, 0, 0.35),
    );
    // tail streaming back
    put(
      new THREE.ConeGeometry(0.16, 0.9, 8).rotateZ(Math.PI / 2 + 0.6),
      bronze,
      M(-1.55, 0, Z + 1.2),
    );
    // rocky ground base the hooves rest on
    put(new THREE.BoxGeometry(3.6, 1.2, 0.25), bronze, M(0, 0, Z + 0.12));
    // rider: torso leaning back, head, legs astride, right arm raised to shade eyes
    put(ell(0.22, 0.17, 0.45), bronze, M(0.15, 0, Z + 2.25, 0, -0.3));
    put(new THREE.SphereGeometry(0.15, 10, 8), bronze, M(0.32, 0, Z + 2.72));
    for (const sd of [-1, 1]) {
      put(
        new THREE.CylinderGeometry(0.08, 0.1, 0.85, 8).rotateX(Math.PI / 2),
        bronze,
        M(0.2, sd * 0.42, Z + 1.55, 0, 0.3, sd * 0.25),
      );
    }
    put(
      new THREE.CylinderGeometry(0.05, 0.06, 0.7, 8).rotateX(Math.PI / 2),
      bronze,
      M(0.45, -0.18, Z + 2.68, 0, -1.0, 0.3),
    );
    put(
      new THREE.CylinderGeometry(0.05, 0.06, 0.7, 8).rotateX(Math.PI / 2),
      bronze,
      M(0.1, 0.25, Z + 2.0, 0, 0.6, -0.4),
    );

    g.add(batch.toGroup('physical_energy_statue'));
    return g;
  },
};
