// Material-name-preserving simulation GLB: bake active-scene world transforms.
// Install dependencies with tools/requirements-city-node.json into cache/city_node.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const modules=path.resolve(process.env.CITY_NODE_MODULES||'cache/city_node/node_modules');
const {Document,NodeIO}=await import(pathToFileURL(path.join(modules,'@gltf-transform/core/dist/index.js')));
const {ALL_EXTENSIONS}=await import(pathToFileURL(path.join(modules,'@gltf-transform/extensions/dist/index.js')));
const {MeshoptDecoder}=await import(pathToFileURL(path.join(modules,'meshoptimizer/index.js')));
const {default:draco}=await import(pathToFileURL(path.join(modules,'draco3dgltf/draco3dgltf.js')));
const [source,target]=process.argv.slice(2);
if(!source||!target)throw Error('Usage: node tools/bake_city_geometry.mjs source.glb target.glb');
if(fs.existsSync(target))throw Error('Refusing to overwrite existing geometry');
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'draco3d.decoder':await draco.createDecoderModule()});
const original=await io.read(source), result=new Document(),buffer=result.createBuffer(),scene=result.createScene('Baked simulation geometry');
result.getRoot().setDefaultScene(scene);
const active=original.getRoot().getDefaultScene()||original.getRoot().listScenes()[0];
if(!active)throw Error('No active source scene');
let nodes=0,primitives=0;
active.traverse(node=>{
 const mesh=node.getMesh();if(!mesh)return;
 if(node.getSkin()||node.getWeights().length)throw Error('Skinned/morphed geometry requires an explicit pose');
 const matrix=node.getWorldMatrix(),baked=result.createMesh(mesh.getName());
 for(const primitive of mesh.listPrimitives()){
  if(primitive.getMode()!==4)throw Error('Only triangular geometry is supported');
  const position=primitive.getAttribute('POSITION'),values=new Float32Array(position.getCount()*3);
  for(let i=0;i<position.getCount();i++){
   const [x,y,z]=position.getElement(i,[]);
   values.set([matrix[0]*x+matrix[4]*y+matrix[8]*z+matrix[12],matrix[1]*x+matrix[5]*y+matrix[9]*z+matrix[13],matrix[2]*x+matrix[6]*y+matrix[10]*z+matrix[14]],i*3);
  }
  const p=result.createPrimitive().setAttribute('POSITION',result.createAccessor().setType('VEC3').setArray(values).setBuffer(buffer));
  const indices=primitive.getIndices();if(indices)p.setIndices(result.createAccessor().setType('SCALAR').setArray(indices.getArray().slice()).setBuffer(buffer));
  const material=primitive.getMaterial();if(material)p.setMaterial(result.createMaterial(material.getName()).setBaseColorFactor(material.getBaseColorFactor()));
  baked.addPrimitive(p);primitives++;
 }
 scene.addChild(result.createNode(node.getName()).setMesh(baked));nodes++;
});
fs.mkdirSync(path.dirname(target),{recursive:true});await new NodeIO().write(target,result);
console.log(JSON.stringify({source,target,nodes,primitives,scope:'Simulation geometry only; textures/normals omitted, material names retained. Original visualization GLB unchanged.'}));
