import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

const DEFAULT_CAR_COLORS=['#dae0e5','#33516e','#878b8c','#48474a','#842f2c','#bcc4cd','#d2c6a5','#377175'];
// Native vehicle IDs persist across sparse frames; render slots do not.
export function carColorForId(nativeNumericId){
 if(!Number.isSafeInteger(nativeNumericId)||nativeNumericId<0)throw new RangeError('Car colour requires a non-negative safe-integer native vehicle ID');
 return DEFAULT_CAR_COLORS[nativeNumericId%DEFAULT_CAR_COLORS.length];
}
const UP=new THREE.Vector3(0,1,0);

// Fade coverage, rather than changing a material's blending/depth settings:
// opaque instances stay in their original draw batch and source glass keeps its alpha.
// At opacity 1 no fragment is changed; at 0 every fragment is discarded.
function patchInstanceFade(material){
 const previousCompile=material.onBeforeCompile,previousKey=material.customProgramCacheKey();
 material.onBeforeCompile=function(shader,renderer){
  previousCompile.call(this,shader,renderer);
  if(!shader.vertexShader.includes('#include <common>')||!shader.vertexShader.includes('#include <begin_vertex>')||
     !shader.fragmentShader.includes('#include <common>')||!shader.fragmentShader.includes('#include <alphatest_fragment>')){
   throw new Error(`Actor fade: unsupported shader for ${material.name}`);
  }
  shader.vertexShader=shader.vertexShader
   .replace('#include <common>','#include <common>\nattribute float instanceFade;\nvarying float vActorInstanceFade;')
   .replace('#include <begin_vertex>','#include <begin_vertex>\nvActorInstanceFade = instanceFade;');
  shader.fragmentShader=shader.fragmentShader
   .replace('#include <common>','#include <common>\nvarying float vActorInstanceFade;')
   .replace('#include <alphatest_fragment>',`// Deterministic screen-door coverage avoids per-instance transparent sorting.
if ( vActorInstanceFade < 1.0 ) {
 float actorFadeThreshold = fract( 52.9829189 * fract( dot( floor( gl_FragCoord.xy ), vec2( 0.06711056, 0.00583715 ) ) ) );
 if ( vActorInstanceFade <= 0.0 || vActorInstanceFade < actorFadeThreshold ) discard;
}
#include <alphatest_fragment>`);
 };
 material.customProgramCacheKey=()=>`${previousKey}|actor-instance-fade-v1`;
}

/** World yaw: 0 faces +Z, +PI/2 faces +X, PI faces -Z (north).
 * SUMO clockwise-from-north radians therefore become Math.PI - sumoRadians.
 * The x/y/z reference is bottom contact at horizontal model centre, in metres.
 */
function instantiateModel(gltf,capacity,{name,tintNames=[],mergeByMaterial=true,palette=null}={}){
 if(!Number.isInteger(capacity)||capacity<1)throw new RangeError(`${name}: capacity must be a positive integer`);
 const source=gltf.scene;source.updateMatrixWorld(true);
 const sourceBounds=new THREE.Box3().setFromObject(source);
 const centre=sourceBounds.getCenter(new THREE.Vector3());
 const offset=new THREE.Vector3(-centre.x,-sourceBounds.min.y,-centre.z);
 const sourceSize=sourceBounds.getSize(new THREE.Vector3());
 const groups=new Map();let primitiveCount=0;
 source.traverse(o=>{
  if(!o.isMesh)return;
  if(o.isSkinnedMesh)throw new Error(`${name}: skinned geometry is not supported by the static actor layer`);
  if(Array.isArray(o.material))throw new Error(`${name}: expected GLTFLoader primitive mesh with one material`);
  let geometry=o.geometry.clone();geometry.applyMatrix4(o.matrixWorld);geometry.translate(offset.x,offset.y,offset.z);
  // These local assets have no textures. Keep position and normal for compatible merges.
  for(const key of Object.keys(geometry.attributes))if(!['position','normal'].includes(key))geometry.deleteAttribute(key);
  if(!geometry.attributes.normal)geometry.computeVertexNormals();
  if(geometry.index){const nonIndexed=geometry.toNonIndexed();geometry.dispose();geometry=nonIndexed;}
  const key=mergeByMaterial?o.material.uuid:`primitive-${primitiveCount}`;
  if(!groups.has(key))groups.set(key,{material:o.material,geometries:[],sourceNames:[]});
  groups.get(key).geometries.push(geometry);groups.get(key).sourceNames.push(o.name);primitiveCount++;
 });
 const group=new THREE.Group();group.name=name;
 const matrixData=new Float32Array(capacity*16),colorData=new Float32Array(capacity*3);
 const fadeData=new Float32Array(capacity).fill(1);
 const fadeAttribute=new THREE.InstancedBufferAttribute(fadeData,1);fadeAttribute.setUsage(THREE.DynamicDrawUsage);
 const visible=new Uint8Array(capacity);const meshes=[],tintedMeshes=[];
 const defaultColors=Array.from({length:capacity},(_,i)=>new THREE.Color(palette?palette[i%palette.length]:'#ffffff'));
 for(let i=0;i<capacity;i++){matrixData[i*16+15]=1;defaultColors[i].toArray(colorData,i*3);}
 let trianglesPerActor=0;
 for(const entry of groups.values()){
  const geometry=entry.geometries.length===1?entry.geometries[0]:mergeGeometries(entry.geometries,false);
  if(!geometry)throw new Error(`${name}: incompatible primitive attributes`);
  if(entry.geometries.length>1)entry.geometries.forEach(g=>g.dispose());
  geometry.computeBoundingBox();geometry.computeBoundingSphere();
  const material=entry.material.clone();patchInstanceFade(material);
  geometry.setAttribute('instanceFade',fadeAttribute);
  const mesh=new THREE.InstancedMesh(geometry,material,capacity);
  mesh.name=`${name} / ${material.name}`;mesh.frustumCulled=false;mesh.castShadow=false;mesh.receiveShadow=false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);mesh.instanceMatrix.array.set(matrixData);mesh.instanceMatrix.needsUpdate=true;mesh.count=0;
  mesh.userData.sourcePrimitives=entry.sourceNames;
  if(tintNames.includes(material.name)){
   mesh.instanceColor=new THREE.InstancedBufferAttribute(colorData.slice(),3);mesh.instanceColor.setUsage(THREE.DynamicDrawUsage);tintedMeshes.push(mesh);
  }
  trianglesPerActor+=geometry.attributes.position.count/3;meshes.push(mesh);group.add(mesh);
 }
 const matrix=new THREE.Matrix4(),position=new THREE.Vector3(),rotation=new THREE.Quaternion(),one=new THREE.Vector3(1,1,1),color=new THREE.Color();
 let activeCount=0;
 function update(records,{hideUnmentioned=true}={}){
  if(!Array.isArray(records))throw new TypeError(`${name}: update expects an array of actor records`);
  const seen=new Set();
  for(const record of records){
   const i=record.idIndex;
   if(!Number.isInteger(i)||i<0||i>=capacity)throw new RangeError(`${name}: idIndex ${i} outside 0..${capacity-1}`);
   if(seen.has(i))throw new Error(`${name}: repeated idIndex ${i} in one update`);seen.add(i);
   if(record.opacity!==undefined&&(!Number.isFinite(record.opacity)||record.opacity<0||record.opacity>1))throw new RangeError(`${name}: opacity must be finite and within 0..1 for actor ${i}`);
   if(record.visible!==false&&![record.x,record.y,record.z,record.headingRadians??0].every(Number.isFinite))throw new TypeError(`${name}: x/y/z/headingRadians must be finite for actor ${i}`);
  }
  if(hideUnmentioned){matrixData.fill(0);visible.fill(0);fadeData.fill(1);for(let i=0;i<capacity;i++)matrixData[i*16+15]=1;}
  for(const record of records){
   const i=record.idIndex;
   if(!Number.isInteger(i)||i<0||i>=capacity)throw new RangeError(`${name}: idIndex ${i} outside 0..${capacity-1}`);
   fadeData[i]=record.opacity??1;
   if(record.visible===false){matrixData.fill(0,i*16,(i+1)*16);matrixData[i*16+15]=1;visible[i]=0;continue;}
   const {x,y,z}=record,yaw=record.headingRadians??0;
   if(![x,y,z,yaw].every(Number.isFinite))throw new TypeError(`${name}: x/y/z/headingRadians must be finite for actor ${i}`);
   position.set(x,y,z);rotation.setFromAxisAngle(UP,yaw);matrix.compose(position,rotation,one).toArray(matrixData,i*16);visible[i]=1;
   if(record.color!==undefined)color.set(record.color).toArray(colorData,i*3);
   else defaultColors[i].toArray(colorData,i*3);
  }
  let highest=-1;activeCount=0;for(let i=0;i<capacity;i++)if(visible[i]){activeCount++;highest=i;}
  for(const mesh of meshes){mesh.instanceMatrix.array.set(matrixData);mesh.instanceMatrix.needsUpdate=true;mesh.count=highest+1;}
  fadeAttribute.needsUpdate=true;
  for(const mesh of tintedMeshes){mesh.instanceColor.array.set(colorData);mesh.instanceColor.needsUpdate=true;}
  return activeCount;
 }
 function dispose(){for(const mesh of meshes){mesh.geometry.dispose();mesh.material.dispose();}group.removeFromParent();}
 return {group,meshes,update,dispose,capacity,get activeCount(){return activeCount;},
  metadata:{name,capacity,sourcePrimitiveCount:primitiveCount,instancedPrimitiveGroups:meshes.length,trianglesPerActor,
   dimensionsXYZMetres:sourceSize.toArray(),sourceBoundsMetres:[sourceBounds.min.toArray(),sourceBounds.max.toArray()],
   bakedOffsetMetres:offset.toArray(),unitScale:1,forwardAxis:'+Z',upAxis:'+Y',placementReference:'bottom contact at horizontal model centre',
   rotorAnimation:false,mergedByMaterial:mergeByMaterial,opacityPolicy:'record.opacity defaults to 1; 0..1 screen-door coverage on cloned materials, preserving source alpha/blending/depth and instance transforms. Does not change activeCount or visible.',colorPolicy:tintNames.length?`Instance color multiplies ${tintNames.join(', ')}; other materials retain source color.`:'No tint material configured.'}};
}

/** Create all actor draw batches once; call updateCars/updateUavs on each replay frame.
 * Both GLBs use metre-scale geometry. There is deliberately no per-actor scale input.
 */
export async function createActorLayer({scene,carURL=new URL('./sedan_4p5m.glb',import.meta.url).href,
 uavURL='/assets/hexacopter_cargo.glb',carCapacity=1500,uavCapacity=300,mergeByMaterial=true}={}){
 const loader=new GLTFLoader();
 const [carGLTF,uavGLTF]=await Promise.all([loader.loadAsync(carURL),loader.loadAsync(uavURL)]);
 const cars=instantiateModel(carGLTF,carCapacity,{name:'Traffic cars',tintNames:['Body paint'],mergeByMaterial,palette:DEFAULT_CAR_COLORS});
 const uavs=instantiateModel(uavGLTF,uavCapacity,{name:'Cargo UAVs',tintNames:['Pearl shell.002'],mergeByMaterial});
 const group=new THREE.Group();group.name='World actors, metres';group.add(cars.group,uavs.group);scene?.add(group);
 return {group,cars,uavs,updateCars:(records,options)=>cars.update(records,options),updateUavs:(records,options)=>uavs.update(records,options),
  update({cars:carRecords,uavs:uavRecords}={},options){if(carRecords!==undefined)cars.update(carRecords,options);if(uavRecords!==undefined)uavs.update(uavRecords,options);},
  setVisible({cars:carsVisible,uavs:uavsVisible}={}){if(carsVisible!==undefined)cars.group.visible=Boolean(carsVisible);if(uavsVisible!==undefined)uavs.group.visible=Boolean(uavsVisible);},
  dispose(){cars.dispose();uavs.dispose();group.removeFromParent();},
  metadata:{cars:cars.metadata,uavs:uavs.metadata,claimBoundary:'Display geometry and replay transforms only; does not simulate traffic rules, UAV flight dynamics, collision avoidance, or scheduling.'}};
}

export const sumoHeadingToWorldYaw=radians=>Math.PI-radians;
