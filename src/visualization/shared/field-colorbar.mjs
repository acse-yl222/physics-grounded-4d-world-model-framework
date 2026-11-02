// Quantitative colour scales. Inputs remain unchanged; masks exclude unavailable cells.
export const palettes = {
  viridis: ['#440154','#3b528b','#21918c','#5ec962','#fde725'],
  blue: ['#f7fbff','#c6dbef','#6baed6','#2171b5','#08306b'],
  warm: ['#000004','#51127c','#b73779','#fc8961','#fcfdbf'],
};
export function normalized(value, lo, hi, scale) {
  if (!Number.isFinite(value) || !(hi > lo) || (scale === 'log' && (!(lo > 0) || !(value > 0)))) return NaN;
  return Math.max(0,Math.min(1,scale==='log'?Math.log(value/lo)/Math.log(hi/lo):(value-lo)/(hi-lo)));
}
export function fieldStats(n, value, valid) {
  let min=Infinity,max=-Infinity,positive=Infinity,count=0;
  for(let i=0;i<n;i++){const v=value(i);if(!valid(i)||!Number.isFinite(v))continue;count++;min=Math.min(min,v);max=Math.max(max,v);if(v>0)positive=Math.min(positive,v)}
  return {min,max,positive,count,total:n};
}
function lut(name) {
  const stops=palettes[name].map(s=>[1,3,5].map(i=>parseInt(s.slice(i,i+2),16)));
  return Array.from({length:256},(_,i)=>{const x=i/255*(stops.length-1),j=Math.min(stops.length-2,Math.floor(x)),t=x-j;return stops[j].map((v,k)=>Math.round(v+(stops[j+1][k]-v)*t))});
}
const fmt=v=>Number.isFinite(v)?Number(v.toPrecision(4)).toString():'—';
export function installColorbars({layers,repaint}) {
  const configs={}, cache={};
  const units={wind:'|V| m/s',temp:'°C',solar:'GHI W/m²',poll:'tracer · arbitrary units',flood:'water depth m'};
  for(const key of Object.keys(units)) {
    if(!layers[key])continue;
    const legend=document.querySelector(`.legend[data-layer="${key}"]`);if(!legend)continue;
    const range=layers[key].range||[0,1000];
    const initial={lo:range[0],hi:range[1],scale:key==='poll'?'log':'linear',palette:'viridis',threshold:key==='flood'?0.02:null};
    const c=configs[key]={...initial,enabled:false,lut:lut('viridis')};
    const details=document.createElement('details');details.className='field-colorbar';details.style.cssText='font:12px sans-serif;padding:6px 0;';
    details.innerHTML=`<summary>Adjust colour scale</summary><label><input data-cb="enabled" type="checkbox"> Quantitative colour map</label><div style="display:flex;gap:6px;margin:6px 0"><label>Min <input data-cb="lo" type="number" step="any" style="width:78px"></label><label>Max <input data-cb="hi" type="number" step="any" style="width:78px"></label></div><select data-cb="scale"><option value="linear">Linear</option><option value="log">Logarithmic (positive values)</option></select> <select data-cb="palette"><option value="viridis">Viridis</option><option value="blue">Blues</option><option value="warm">Warm</option></select>${key==='flood'?'<p>Hide water depth ≤ <input data-cb="threshold" type="number" min="0" step="any" style="width:65px"> m</p>':''}<p><button data-cb="fit">Fit current frame</button> <button data-cb="reset">Reset</button></p><div data-cb="bar" style="height:9px"></div><p data-cb="ticks"></p><p data-cb="status" aria-live="polite">Load this field to inspect its range.</p><small>Range stays fixed during playback. Out-of-range values use endpoint colours. Missing cells are transparent; log mode also hides nonpositive values. Layer opacity uses the slider above. Applies to heat maps; contour/shadow modes retain their own scales.</small>`;
    legend.after(details);c.element=details;c.legend=legend;
    const q=k=>details.querySelector(`[data-cb="${k}"]`) || c.display?.querySelector(`[data-cb="${k}"]`);
    c.display=document.createElement('div');c.display.hidden=true;c.display.append(q('bar'),q('ticks'));details.before(c.display);
    function sync(){for(const k of ['lo','hi','scale','palette','threshold'])if(q(k))q(k).value=c[k];q('enabled').checked=c.enabled;q('bar').style.background=`linear-gradient(to right,${palettes[c.palette].join(',')})`;q('ticks').textContent=`${fmt(c.lo)} → ${fmt(c.hi)} ${units[key]} · ${c.scale}`;}
    function update(){const lo=Number(q('lo').value),hi=Number(q('hi').value),scale=q('scale').value,threshold=q('threshold')?Number(q('threshold').value):null;
      if(q('lo').value===''||q('hi').value===''||!Number.isFinite(lo)||!Number.isFinite(hi)||hi<=lo||(scale==='log'&&lo<=0)||(threshold!==null&&(!Number.isFinite(threshold)||threshold<0))){q('status').textContent='Invalid range: max must exceed min; logarithmic min must be positive.';return}
      Object.assign(c,{lo,hi,scale,threshold,palette:q('palette').value,enabled:true});c.lut=lut(c.palette);sync();repaint();}
    for(const k of ['lo','hi','scale','palette','threshold'])if(q(k))q(k).onchange=update;
    q('enabled').onchange=()=>{c.enabled=q('enabled').checked;repaint()};
    q('fit').onclick=()=>{const s=cache[key]?.stats;if(!s?.count){q('status').textContent='No valid loaded cells.';return}const low=c.scale==='log'?s.positive:s.min;if(!Number.isFinite(low)){q('status').textContent='No positive values for logarithmic scale.';return}c.lo=low;c.hi=s.max;if(c.hi<=c.lo)c.hi=c.lo+Math.max(Math.abs(c.lo)*.01,1e-6);c.enabled=true;sync();repaint()};
    q('reset').onclick=()=>{Object.assign(c,initial,{enabled:false,lut:lut(initial.palette)});sync();repaint()};sync();
  }
  return {configs,resetLegends(){for(const c of Object.values(configs)){c.legend.style.display='';c.display.hidden=true;}},paint(key,array,plane,n,value,valid) {
    const c=configs[key];if(!c)return false;
    let record=cache[key];if(!record||record.array!==array){record=cache[key]={array,stats:fieldStats(n,value,valid)}}
    const s=record.stats,status=c.element.querySelector('[data-cb="status"]');
    if(!c.enabled){status.textContent=`Valid cells ${s.count}/${n}; current frame ${fmt(s.min)}–${fmt(s.max)}. Original display active.`;return false}
    c.legend.style.display='none';c.display.hidden=false;
    let below=0,above=0,hidden=0;
    for(let i=0;i<n;i++){const v=value(i),o=i*4;if(!valid(i)||!Number.isFinite(v)){plane.data[o+3]=0;continue}if(v<c.lo)below++;if(v>c.hi)above++;const t=normalized(v,c.lo,c.hi,c.scale);if(!Number.isFinite(t)||(c.threshold!==null&&v<=c.threshold)){hidden++;plane.data[o+3]=0;continue}const rgb=c.lut[Math.round(t*255)];plane.data[o]=rgb[0];plane.data[o+1]=rgb[1];plane.data[o+2]=rgb[2];plane.data[o+3]=235;}
    plane.tex.needsUpdate=true;
    const pct=x=>s.count?(100*x/s.count).toFixed(1):'0.0';
    status.textContent=`Valid ${s.count}/${n}; frame ${fmt(s.min)}–${fmt(s.max)}. Below range ${pct(below)}%; above ${pct(above)}%; hidden by log/threshold ${pct(hidden)}%.`;
    return true;
  }};
}
