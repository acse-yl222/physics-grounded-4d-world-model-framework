import * as THREE from 'three';
import { sample, enuToWorld, worldToEnu, assetURL } from '../shared/time.mjs';

const color = (value, low, high) => new THREE.Color().setHSL((1 - Math.max(0, Math.min(1, (value-low)/(high-low || 1)))) * .65, .75, .55);
const require = (test, message) => { if (!test) throw new Error(message); };
function shape(value, dims) {
  if (!dims.length) { require(typeof value === 'number' && Number.isFinite(value), 'Non-finite or invalid numeric data'); return; }
  require(Array.isArray(value) && value.length === dims[0], `Expected shape ${dims}`);
  value.forEach(item => shape(item, dims.slice(1)));
}
function validate(layer, data, times) {
  const kind=layer.kind, dynamic=layer.sampling !== 'static';
  let n;
  if (['mesh','scalar_field','vector_field'].includes(kind)) {
    n=data.positions?.length; require(n>0, 'Empty positions'); shape(data.positions,[n,3]);
  } else {
    const names=kind==='trajectories'?data.ids:data.labels;
    require(Array.isArray(names)&&names.length>0&&names.every(x=>typeof x==='string'&&x.length)&&new Set(names).size===names.length,'Invalid entity/channel IDs'); n=names.length;
  }
  const prefix=dynamic?[times.length]:[];
  if(kind==='mesh') {
    require(!dynamic, 'Mesh must be static'); require(data.triangles?.length>0,'Empty mesh'); shape(data.triangles,[data.triangles.length,3]);
    require(data.triangles.flat().every(i=>Number.isInteger(i)&&i>=0&&i<n),'Invalid mesh index');
  } else if(kind==='vector_field') shape(data.vectors,[...prefix,n,3]);
  else if(kind==='trajectories') { require(dynamic,'Trajectories require time'); shape(data.positions,[...prefix,n,3]); }
  else shape(data.values,[...prefix,n]);
  if(['scalar_field','vector_field','time_series'].includes(kind)) require(layer.field?.name&&layer.field?.unit,'Missing field name/unit');
}

export class DataWidget {
  async load(context, layer, signal) {
    this.context=context;this.layer=layer;this.visible=true;this.disposed=false;this.objects=[];
    for (const capability of layer.display.capabilities) require(['pick','legend','opacity'].includes(capability),`Unsupported capability: ${capability}`);
    require(layer.format==='json',`Unsupported format: ${layer.format}`);
    require(['static','step','linear'].includes(layer.sampling),'Unsupported sampling');
    const response=await fetch(assetURL(context.baseURL,layer.asset),{signal});
    require(response.ok,`Asset load failed (${response.status})`);this.data=await response.json();
    if(signal.aborted) throw new DOMException('Aborted','AbortError');
    this.initialize(context,layer,this.data);
  }
  initialize(context, layer, dataInput) {
    this.context=context;this.layer=layer;this.data=dataInput;this.visible=true;this.disposed=false;this.objects=[];
    validate(layer,this.data,context.manifest.time.samples);
    this.group=new THREE.Group();context.scene.add(this.group);
    const diagonal=new THREE.Vector3(...context.boundsSize).length();this.scale=Math.max(diagonal*.008,.04);
    const data=this.data,kind=layer.kind;
    if(kind==='mesh') {
      const geometry=new THREE.BufferGeometry(); geometry.setAttribute('position',new THREE.Float32BufferAttribute(data.positions.flatMap(enuToWorld),3));geometry.setIndex(data.triangles.flat());geometry.computeVertexNormals();
      this.group.add(new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0x8eaca3,side:THREE.DoubleSide,roughness:.8})));
    } else if(kind==='vector_field') {
      for(const position of data.positions) {const arrow=new THREE.ArrowHelper(new THREE.Vector3(1,0,0),new THREE.Vector3(...enuToWorld(position)),this.scale*5,0x53c4ea);this.objects.push(arrow);this.group.add(arrow);}
    } else if(kind==='scalar_field'||kind==='trajectories') {
      const n=kind==='scalar_field'?data.positions.length:data.ids.length;
      const geometry=new THREE.SphereGeometry(this.scale,8,6);
      this.instances=new THREE.InstancedMesh(geometry,new THREE.MeshStandardMaterial({color:0xffffff}),n);this.group.add(this.instances);
    } else {
      this.chart=document.createElement('canvas');this.chart.width=520;this.chart.height=150;this.chart.className='series';this.chart.title=layer.field.name;context.charts.append(this.chart);
    }
    const raw=kind==='scalar_field'||kind==='time_series'?data.values.flat(Infinity):kind==='vector_field'?(layer.sampling==='static'?data.vectors:data.vectors.flat()).map(v=>Math.hypot(...v)):[0,1];
    let min=Infinity,max=-Infinity;for(const value of raw){min=Math.min(min,value);max=Math.max(max,value);}this.range=layer.display.range||[min,max];
    if(layer.display.capabilities.includes('legend')) this.removeLegend=context.addLegend(layer,`${this.range[0].toPrecision(3)} — ${this.range[1].toPrecision(3)} ${layer.field?.unit||''}`);
    DataWidget.prototype.setTime.call(this,context.manifest.time.samples[0]||0);
  }
  setTime(seconds) {
    if(this.disposed)return;this.seconds=seconds;
    const kind=this.layer.kind,data=this.data;
    const source=kind==='vector_field'?data.vectors:kind==='trajectories'?data.positions:data.values;
    this.current=kind==='mesh'?true:sample(source,this.context.manifest.time.samples,seconds,this.layer.sampling);
    this.available=this.current!==null;this.group.visible=this.visible&&this.available;
    this.context.availability(this.layer.id,this.available);
    if(this.chart)this.chart.hidden=!this.visible||!this.available;
    if(!this.available)return;
    const [low,high]=this.range;
    if(kind==='scalar_field'||kind==='trajectories') {
      const positions=kind==='scalar_field'?data.positions:this.current;
      const updatePositions=kind==='trajectories'||!this.positionsInitialized;
      this.matrix ||= new THREE.Matrix4();
      positions.forEach((position,i)=>{if(updatePositions)this.instances.setMatrixAt(i,this.matrix.makeTranslation(...enuToWorld(position)));this.instances.setColorAt(i,kind==='scalar_field'?color(this.current[i],low,high):new THREE.Color(0xffbc62));});
      if(updatePositions){this.instances.instanceMatrix.needsUpdate=true;this.instances.computeBoundingSphere();this.positionsInitialized=true;}
      this.instances.instanceColor.needsUpdate=true;
    } else if(kind==='vector_field') {
      this.current.forEach((v,i)=>{const direction=new THREE.Vector3(...enuToWorld(v)),magnitude=direction.length();const arrow=this.objects[i];arrow.visible=magnitude>0;if(magnitude>0){arrow.setDirection(direction.normalize());arrow.setLength(this.scale*8*Math.min(2,magnitude/(high||1)));arrow.setColor(color(magnitude,low,high));}});
    } else if(kind==='time_series') this.drawChart();
  }
  drawChart() {
    const ctx=this.chart.getContext('2d'),w=this.chart.width,h=this.chart.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#e2e8f0';ctx.font='13px sans-serif';ctx.fillText(`${this.layer.field.name} (${this.layer.field.unit})`,12,19);
    const times=this.context.manifest.time.samples,values=this.layer.sampling==='static'?[this.data.values]:this.data.values;
    const [lo,hi]=this.range,denom=(times.at(-1)-times[0])||1;
    this.data.labels.forEach((label,k)=>{ctx.strokeStyle=`hsl(${k*90+170} 70% 60%)`;ctx.beginPath();values.forEach((row,i)=>{const x=12+((times[i]??0)-(times[0]??0))/denom*(w-24),y=h-25-(row[k]-lo)/(hi-lo||1)*(h-65);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.stroke();ctx.fillStyle=ctx.strokeStyle;ctx.fillText(`${label}: ${this.current[k].toFixed(3)}`,12+k*180,h-6);});
    if(times.length){const x=12+(this.seconds-times[0])/denom*(w-24);ctx.strokeStyle='#fff';ctx.beginPath();ctx.moveTo(x,28);ctx.lineTo(x,h-23);ctx.stroke();}
  }
  setVisible(visible) {this.visible=visible;if(this.group)this.group.visible=visible&&this.available;if(this.chart)this.chart.hidden=!visible||!this.available;}
  setOpacity(opacity) {if(this.chart)this.chart.style.opacity=opacity;this.group?.traverse(object=>{if(object.material){for(const material of (Array.isArray(object.material)?object.material:[object.material])){material.transparent=opacity<1;material.opacity=opacity;}}});}
  pick(query) {
    if(!this.visible||!this.available||!this.layer.display.capabilities.includes('pick'))return null;
    if(this.chart) {
      if(query.chart!==this.chart)return null;
      return {run_id:this.context.manifest.run_id,layer_id:this.layer.id,field:this.layer.field.name,values:this.current,unit:this.layer.field.unit};
    }
    const hit=query.raycaster.intersectObject(this.group,true)[0];if(!hit)return null;
    const i=hit.instanceId??this.objects.findIndex(a=>a===hit.object||a===hit.object.parent);
    return {run_id:this.context.manifest.run_id,layer_id:this.layer.id,position:worldToEnu(hit.point.toArray()),entity_id:this.data.ids?.[i],field:this.layer.field?.name,value:Array.isArray(this.current)?this.current[i]:undefined,unit:this.layer.field?.unit,distance:hit.distance};
  }
  dispose() {
    if(this.disposed)return;this.disposed=true;
    const geometries=new Set(),materials=new Set();this.group?.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m));});
    geometries.forEach(g=>g.dispose());materials.forEach(m=>{Object.values(m).forEach(v=>{if(v?.isTexture)v.dispose();});m.dispose();});this.group?.removeFromParent();this.chart?.remove();this.removeLegend?.();this.objects=[];
  }
}
export const registry=new Map(['mesh','scalar_field','vector_field','trajectories','time_series'].map(id=>[id,()=>new DataWidget()]));
