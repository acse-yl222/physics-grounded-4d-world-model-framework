import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';

/** Screen-space width stays readable at district scale, with original route vertices. */
export function createFlightCorridors(routes, {route_width_px = 2.5, route_opacity = .55} = {}) {
  const positions=[];
  for(const route of routes)for(let i=1;i<route.points_m.length;i++)positions.push(...route.points_m[i-1],...route.points_m[i]);
  const geometry=new LineSegmentsGeometry();geometry.setPositions(positions);
  const material=new LineMaterial({color:0xffb347,linewidth:route_width_px,transparent:true,opacity:route_opacity,depthWrite:false});
  const lines=new LineSegments2(geometry,material);lines.name='Computed Wave PDE corridors';lines.renderOrder=19;
  return lines;
}

export function scaleStationLabels(stations,camera,pixels=48){
  for(const sprite of stations.labels.children){
    const mpp=2*camera.position.distanceTo(sprite.position)*Math.tan(camera.fov*Math.PI/360)/window.innerHeight;
    sprite.scale.set(pixels*mpp,pixels/(sprite.userData.aspect??(48/22))*mpp,1);
  }
}
