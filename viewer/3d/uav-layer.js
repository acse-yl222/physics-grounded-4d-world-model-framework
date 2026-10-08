// Scene-specific Wave PDE flights; no traffic, bird or delivery scheduling data.
import * as THREE from 'three';
import { loadRandomUav } from './random-uav.mjs';
import { createActorLayer } from '../../agents/demo_rev02/actors/actor-layer.js';
import { addStations } from '../../agents/demo_rev02/stations.js';

export async function createUavLayer({ scene, sceneId, configURL: selectedConfigURL }) {
  const prefix = import.meta.url.includes('/src/visualization/legacy/') ? '../../../../../' : '../../';
  const configURL = selectedConfigURL ? new URL(selectedConfigURL, import.meta.url) : new URL(`${prefix}project/${sceneId}/configs/uav_visualization.json`, import.meta.url);
  const response = await fetch(configURL);
  if (!response.ok) throw Error(`UAV configuration: ${response.status}`);
  const config = await response.json();
  const flightData = await loadRandomUav(new URL(config.routes, configURL), { count: config.uav_count, seed: config.seed });
  const group = new THREE.Group(); group.name = `${sceneId} Wave PDE flights`;
  const actors = await createActorLayer({ scene: group, carCapacity: 1, uavCapacity: flightData.model.count,
    uavURL: new URL('../../agents/demo_rev02/assets/hexacopter_cargo.glb', import.meta.url).href });
  actors.updateCars([]); actors.setVisible({ cars: false });
  const stations = addStations(group, flightData.stations, []);
  const positions = [];
  for (const route of flightData.routes) for (let i = 1; i < route.points_m.length; i++) positions.push(...route.points_m[i-1], ...route.points_m[i]);
  const routeGeometry = new THREE.BufferGeometry(); routeGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  const corridors = new THREE.LineSegments(routeGeometry, new THREE.LineBasicMaterial({ color: 0xffb347, transparent: true, opacity: .23, depthWrite: false }));
  group.add(corridors);
  const markerGeometry = new THREE.BufferGeometry();
  markerGeometry.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(flightData.model.count * 3), 3));
  const markers = new THREE.Points(markerGeometry, new THREE.PointsMaterial({ color: 0x4f8cff, size: 7, sizeAttenuation: false, depthTest: false }));
  markers.frustumCulled = false; markers.renderOrder = 20; group.add(markers);
  const R = { group, flightData, actors, stations, corridors, markers, uavs: [], uavMode: 'random_wavepde', t: 0, speed: 1, playing: true,
    duration: flightData.model.duration,
    stats: `${flightData.model.count} random UAVs · ${flightData.routes.length} routes · ${flightData.stations.length} ground stations`,
    update(t) {
      R.t = Math.max(0, Math.min(R.duration - 1e-6, t)); R.uavs = flightData.model.sample(R.t);
      actors.updateUavs(R.uavs);
      R.uavs.forEach((u, i) => markerGeometry.attributes.position.setXYZ(i, u.x, u.y, u.z));
      markerGeometry.attributes.position.needsUpdate = true;
    },
    tick(dt) { if (R.playing) R.update((R.t + dt * R.speed) % R.duration); },
    applyLayers({ uavs = true, stations: showStations = true, routes = false } = {}) {
      actors.setVisible({ uavs }); markers.visible = uavs; corridors.visible = uavs && routes; stations.setVisible(showStations);
    },
    setVisible(value) { group.visible = value; },
    dispose() {
      actors.dispose(); group.removeFromParent();
      group.traverse(o => { o.geometry?.dispose(); for (const m of Array.isArray(o.material) ? o.material : o.material ? [o.material] : []) { m.map?.dispose(); m.dispose(); } });
    }
  };
  R.update(0); R.applyLayers(); scene.add(group); return R;
}
