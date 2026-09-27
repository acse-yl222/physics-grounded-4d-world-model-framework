import * as THREE from 'three';

const colors={hub:0xe8a23b,collection:0x128c96,dropoff:0x7356bb};
function label(text,fill){
 const c=document.createElement('canvas');c.width=192;c.height=88;const g=c.getContext('2d');
 g.fillStyle='#ffffff';g.beginPath();g.roundRect(2,2,188,78,18);g.fill();
 g.strokeStyle=fill;g.lineWidth=5;g.stroke();g.fillStyle=fill;g.font='bold 44px system-ui';g.textAlign='center';g.fillText(text,96,58);
 const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;
 const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false,transparent:true}));sprite.scale.set(30,13.75,1);sprite.renderOrder=30;sprite.userData={baseText:text,fill};return sprite;
}
export function addStations(scene,stations,parking){
 const group=new THREE.Group(),coverage=new THREE.Group(),labels=new THREE.Group();
 group.name='Delivery stations';coverage.name='300 metre coverage guides';labels.name='Station labels';
 for(const s of stations){
  const color=colors[s.role],mat=new THREE.MeshStandardMaterial({color,roughness:.9,metalness:0});
  const pad=new THREE.Mesh(new THREE.CylinderGeometry(s.role==='hub'?2.4:2,s.role==='hub'?2.4:2,.1,32),mat);
  pad.position.set(s.x_m,s.y_m,s.z_m);group.add(pad);
  const ring=new THREE.Mesh(new THREE.RingGeometry(299.2,300.8,128),new THREE.MeshBasicMaterial({color,transparent:true,opacity:.6,side:THREE.DoubleSide,depthTest:false}));
  ring.rotation.x=-Math.PI/2;ring.position.set(s.x_m,.5,s.z_m);ring.renderOrder=15;coverage.add(ring);
  const marker=label(s.label,new THREE.Color(color).getStyle());marker.position.set(s.x_m,s.y_m+22,s.z_m);marker.userData.stationId=s.station_id;labels.add(marker);
 }
 const geo=new THREE.RingGeometry(.8,.95,24);geo.rotateX(-Math.PI/2);
 const mesh=new THREE.InstancedMesh(geo,new THREE.MeshBasicMaterial({color:0xc5a05c,side:THREE.DoubleSide}),parking.length);
 const matrix=new THREE.Matrix4();parking.forEach((p,i)=>{matrix.makeTranslation(p.position_m[0],p.position_m[1]-.02,p.position_m[2]);mesh.setMatrixAt(i,matrix);});
 mesh.instanceMatrix.needsUpdate=true;group.add(mesh);coverage.visible=false;group.add(labels,coverage);scene.add(group);
 return {group,coverage,labels,setVisible:value=>group.visible=value,setCoverage:value=>coverage.visible=value,
  setGroundCounts(counts){for(const sprite of labels.children){
   const n=counts.get(sprite.userData.stationId)??0;if(sprite.userData.lastCount===n)continue;sprite.userData.lastCount=n;
   const c=sprite.material.map.image;c.width=224;c.height=n>1?126:88;const g=c.getContext('2d');
   g.fillStyle='#fff';g.beginPath();g.roundRect(2,2,220,c.height-4,16);g.fill();g.strokeStyle=sprite.userData.fill;g.lineWidth=4;g.stroke();
   g.fillStyle=sprite.userData.fill;g.font='bold 42px system-ui';g.textAlign='center';g.fillText(sprite.userData.baseText,112,56);
   if(n>1){g.font='28px system-ui';g.fillText(`${n} parked`,112,101);}
   sprite.material.map.needsUpdate=true;sprite.userData.aspect=c.width/c.height;
  }}
 };
}

export function addRoadSurfaces(scene,geometry){
 const positions=[];
 for(const lane of geometry.lanes){
  const points=lane.world_xyz,w=lane.width_m/2;
  for(let i=1;i<points.length;i++){
   const a=points[i-1],b=points[i],dx=b[0]-a[0],dz=b[2]-a[2],length=Math.hypot(dx,dz);if(length<1e-5)continue;
   const ox=-dz/length*w,oz=dx/length*w;
   const p=[a[0]+ox,a[1],a[2]+oz],q=[a[0]-ox,a[1],a[2]-oz],r=[b[0]+ox,b[1],b[2]+oz],s=[b[0]-ox,b[1],b[2]-oz];
   positions.push(...p,...r,...q,...q,...r,...s);
  }
 }
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.computeVertexNormals();
 const material=new THREE.MeshStandardMaterial({color:0x565f65,roughness:1,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1});
 const mesh=new THREE.Mesh(g,material);mesh.name='Qualified driving lanes';scene.add(mesh);return mesh;
}
