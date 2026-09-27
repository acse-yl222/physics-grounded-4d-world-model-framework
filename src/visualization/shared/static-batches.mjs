import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

// Combine opaque static meshes by material and city block. Source assets stay intact.
export async function batchStaticCity(root) {
  root.updateMatrixWorld(true);
  const buckets=new Map(), out=new THREE.Group();out.name='Static city batches';
  let sourceMeshes=0, sourceTriangles=0, batches=0;
  root.traverseVisible(o=>{
    if(!o.isMesh||o.isSkinnedMesh||o.isInstancedMesh||Array.isArray(o.material)||o.material.transparent||o.morphTargetInfluences?.length)return;
    const p=o.geometry.attributes.position;
    if(!p||o.geometry.drawRange.count!==Infinity)return;
    const centre=new THREE.Vector3();o.getWorldPosition(centre);
    const attrs=Object.keys(o.geometry.attributes).sort();
    const key=[o.material.uuid,Math.floor(centre.x/600),Math.floor(centre.z/600),attrs.map(k=>k+':'+o.geometry.attributes[k].itemSize).join(','),!!o.geometry.index].join('|');
    if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(o);
  });
  let processed=0;
  for(const objects of buckets.values()){
    if(objects.length<2)continue;
    let parts=[],vertices=0,members=[];
    function flush(){
      if(!parts.length)return;
      const merged=mergeGeometries(parts,false);
      if(!merged)throw new Error('Static city batch attribute mismatch');
      merged.computeBoundingSphere();merged.computeBoundingBox();
      const m=new THREE.Mesh(merged,objects[0].material);m.name='City block';out.add(m);
      for(const o of members)o.visible=false;
      for(const g of parts)g.dispose();
      batches++;parts=[];members=[];vertices=0;
    }
    for(const o of objects){
      const src=o.geometry,g=new THREE.BufferGeometry();
      for(const [name,attr] of Object.entries(src.attributes)){
        const array=new Float32Array(attr.count*attr.itemSize);
        for(let i=0;i<attr.count;i++)for(let j=0;j<attr.itemSize;j++)array[i*attr.itemSize+j]=attr.getComponent(i,j);
        g.setAttribute(name,new THREE.BufferAttribute(array,attr.itemSize));
      }
      if(src.index)g.setIndex(src.index.clone());
      g.applyMatrix4(o.matrixWorld);
      if(o.matrixWorld.determinant()<0){
        if(g.index){const a=g.index.array;for(let i=0;i<a.length;i+=3){const t=a[i+1];a[i+1]=a[i+2];a[i+2]=t;}}
        else for(const a of Object.values(g.attributes))for(let i=0;i<a.count;i+=3)for(let j=0;j<a.itemSize;j++){const x=(i+1)*a.itemSize+j,y=(i+2)*a.itemSize+j,t=a.array[x];a.array[x]=a.array[y];a.array[y]=t;}
      }
      parts.push(g);members.push(o);vertices+=g.attributes.position.count;
      sourceMeshes++;sourceTriangles+=(g.index?.count??g.attributes.position.count)/3;
      if(vertices>150000)flush();
    }
    flush();
    if(++processed%30===0)await new Promise(resolve=>setTimeout(resolve,0));
  }
  return {object:out,stats:{sourceMeshes,sourceTriangles,batches}};
}
