// Procedural demo asset. No image generation, downloaded textures or source-asset edits.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import * as T from '../vendor/three/build/three.module.js';
const out=path.dirname(fileURLToPath(import.meta.url));
const materialDefs=[
 ['Body paint',[1,1,1,1],.35,.28],
 ['Windows',[.018,.055,.073,1],.2,.19],
 ['Tyres and grille',[.015,.019,.022,1],0,.88],
 ['Wheel alloy and trim',[.44,.49,.54,1],.8,.26],
 ['Headlamps',[1,.91,.72,1],.1,.25,[.8,.66,.4]],
 ['Rear lamps',[.62,.012,.018,1],.05,.3,[.3,0,0]],
 ['Number plates',[.94,.88,.55,1],0,.5],
];
const groups=materialDefs.map(()=>[]);
function add(g,m,pos=[0,0,0],rot=[0,0,0]){
 const mat=new T.Matrix4().compose(new T.Vector3(...pos),new T.Quaternion().setFromEuler(new T.Euler(...rot)),new T.Vector3(1,1,1));
 g.applyMatrix4(mat);groups[m].push(g.index?g.toNonIndexed():g);
}
function box(w,h,l,m,x=0,y=0,z=0){add(new T.BoxGeometry(w,h,l),m,[x,y,z]);}
function triangleMesh(vertices,faces,m){const a=[];for(const f of faces)for(const k of f)a.push(...vertices[k]);const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(a,3));g.computeVertexNormals();add(g,m);}
function hull(lower,upper,y0,y1,m){
 const vs=lower.map(([x,z])=>[x,y0,z]).concat(upper.map(([x,z])=>[x,y1,z]));const n=lower.length,fs=[];
 for(let i=1;i<n-1;i++){fs.push([0,i+1,i],[n,n+i,n+i+1]);}
 for(let i=0;i<n;i++){const k=(i+1)%n;fs.push([i,k,n+k],[i,n+k,n+i]);}triangleMesh(vs,fs.map(f=>[f[0],f[2],f[1]]),m);
}
// Clockwise from above; chamfered body corners and tapered cabin.
const body=[[-.75,-2.25],[.75,-2.25],[.875,-2.05],[.875,1.99],[.735,2.25],[-.735,2.25],[-.875,1.99],[-.875,-2.05]];
const shoulder=[[-.73,-2.19],[.73,-2.19],[.83,-1.99],[.83,1.97],[.71,2.19],[-.71,2.19],[-.83,1.97],[-.83,-1.99]];
hull(body,shoulder,.38,.86,0);
box(1.65,.1,3.65,2,0,.4,0);
const cabinBase=[[-.76,-1.2],[.76,-1.2],[.76,.99],[-.76,.99]];
const cabinRoof=[[-.635,-.71],[.635,-.71],[.635,.35],[-.635,.35]];
hull(cabinBase,cabinRoof,.86,1.415,1);
box(1.29,.035,1.1,0,0,1.4325,-.18);
// Thin pillars visually split the glass; dimensions stay inside the outer body.
box(.07,.55,.08,0,-.752,1.12,-.1);box(.07,.55,.08,0,.752,1.12,-.1);
box(.065,.05,2.05,3,-.77,.875,-.09);box(.065,.05,2.05,3,.77,.875,-.09);
// Mirror tips fix the total width at 1.80 m.
box(.15,.11,.20,0,-.825,1.04,.66);box(.15,.11,.20,0,.825,1.04,.66);
for(const x of [-.8,.8])for(const z of [-1.4,1.37]){
 add(new T.CylinderGeometry(.315,.315,.16,16,1),2,[x,.315,z],[0,0,Math.PI/2]);
 add(new T.CylinderGeometry(.185,.185,.164,10,1),3,[x,.315,z],[0,0,Math.PI/2]);
}
box(1.49,.095,.045,3,0,.47,2.225);box(1.49,.095,.045,3,0,.47,-2.225);
box(.57,.16,.021,2,0,.67,2.236);
for(const x of [-.56,.56]){
 box(.32,.13,.023,4,x,.71,2.235);box(.30,.15,.023,5,x,.70,-2.235);
}
box(.42,.105,.025,6,0,.50,-2.23);box(.42,.105,.024,6,0,.51,2.23);
// A single GLB mesh contains one primitive per material, all in vehicle metres.
let blob=[],offset=0;const bufferViews=[],accessors=[],primitives=[];let bounds=new T.Box3(),triangles=0;
function binary(data,target){const b=Buffer.from(data.buffer,data.byteOffset,data.byteLength);const idx=bufferViews.length;bufferViews.push({buffer:0,byteOffset:offset,byteLength:b.length,target});blob.push(b);offset+=b.length;const pad=(4-offset%4)%4;if(pad){blob.push(Buffer.alloc(pad));offset+=pad;}return idx;}
for(let m=0;m<groups.length;m++){
 const geoms=groups[m];const count=geoms.reduce((s,g)=>s+g.attributes.position.count,0);let positions=new Float32Array(count*3),normals=new Float32Array(count*3),k=0;
 for(const g of geoms){positions.set(g.attributes.position.array,k);normals.set(g.attributes.normal.array,k);k+=g.attributes.position.array.length;}
 const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(let i=0;i<positions.length;i+=3){const v=new T.Vector3(...positions.subarray(i,i+3));bounds.expandByPoint(v);for(let c=0;c<3;c++){min[c]=Math.min(min[c],positions[i+c]);max[c]=Math.max(max[c],positions[i+c]);}}
 const p=accessors.length;accessors.push({bufferView:binary(positions,34962),componentType:5126,count,type:'VEC3',min,max});const n=accessors.length;accessors.push({bufferView:binary(normals,34962),componentType:5126,count,type:'VEC3'});primitives.push({attributes:{POSITION:p,NORMAL:n},material:m,mode:4});triangles+=count/3;
}
const json={asset:{version:'2.0',generator:'FieldFleet UWM demo procedural sedan builder'},scene:0,scenes:[{name:'Sedan metres +Z forward Y up',nodes:[0]}],nodes:[{name:'Sedan_4p50m_1p80m_1p45m',mesh:0}],meshes:[{name:'Sedan material primitives',primitives}],materials:materialDefs.map(([name,color,metallicFactor,roughnessFactor,emissiveFactor])=>({name,pbrMetallicRoughness:{baseColorFactor:color,metallicFactor,roughnessFactor},...(emissiveFactor?{emissiveFactor}:{})})),buffers:[{byteLength:offset}],bufferViews,accessors,extras:{units:'metres',up_axis:'+Y',forward_axis:'+Z',placement_reference:'Horizontal centre; tyre contact Y=0',provenance:'Procedurally generated native geometry for a synthetic urban traffic demo. No observed vehicle model, imported textures or physical dynamics claim.'}};
let jb=Buffer.from(JSON.stringify(json));jb=Buffer.concat([jb,Buffer.alloc((4-jb.length%4)%4,0x20)]);const bb=Buffer.concat(blob),header=Buffer.alloc(12),jh=Buffer.alloc(8),bh=Buffer.alloc(8);header.writeUInt32LE(0x46546c67);header.writeUInt32LE(2,4);header.writeUInt32LE(12+8+jb.length+8+bb.length,8);jh.writeUInt32LE(jb.length);jh.writeUInt32LE(0x4e4f534a,4);bh.writeUInt32LE(bb.length);bh.writeUInt32LE(0x004e4942,4);const file=Buffer.concat([header,jh,jb,bh,bb]);fs.writeFileSync(path.join(out,'sedan_4p5m.glb'),file);
const dimensions=bounds.getSize(new T.Vector3()).toArray();const qa={model:'sedan_4p5m.glb',bytes:file.length,bounds_m:[bounds.min.toArray(),bounds.max.toArray()],dimensions_xyz_m:dimensions,nominal_width_length_height_m:[1.8,4.5,1.45],triangles,material_primitives:primitives.length,up_axis:'+Y',front_axis:'+Z',tyre_ground_y_m:bounds.min.y,no_external_resources:true,checks:{width:Math.abs(dimensions[0]-1.8)<1e-5,length:Math.abs(dimensions[2]-4.5)<1e-5,height:Math.abs(dimensions[1]-1.45)<1e-5,ground:Math.abs(bounds.min.y)<1e-6}};
fs.writeFileSync(path.join(out,'sedan_geometry_QA.json'),JSON.stringify(qa,null,2));console.log(JSON.stringify(qa));
