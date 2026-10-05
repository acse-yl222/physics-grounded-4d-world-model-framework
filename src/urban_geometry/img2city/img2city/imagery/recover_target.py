"""Recover footprint-specific references with Google observations and agent selection."""
from pathlib import Path
import json
import math
import shutil
import hashlib
from img2city import config


def recover(meta, anchor, bdir, candidates=3):
    from img2city.imagery import maps_fetch as maps
    from img2city.imagery.acquire_view import ring_panos
    from img2city.city.quality import _ask,_write
    bdir=Path(bdir);work=bdir/'recovery';work.mkdir(exist_ok=True)
    if (work/'result.json').exists():return json.loads((work/'result.json').read_text())
    lat,lng=meta['center_latlng'];key=maps._key()
    ll=[(anchor['lat0']+y/110540,anchor['lon0']+x/(111320*math.cos(math.radians(anchor['lat0'])))) for x,y in meta['pts']]
    request={'center':f'{lat},{lng}','zoom':19,'size':'640x640','scale':2,'maptype':'satellite','key':key}
    for name,extra in [('satellite.png',{}),('target_satellite.png',{'path':'color:0xff0000ff|weight:3|'+'|'.join(f'{y},{x}' for y,x in ll+[ll[0]])})]:
        if not (work/name).exists():maps._get(maps.STATICMAP,dict(request,**extra),str(work/name))
    rows=[]
    for i,(plat,plng) in enumerate(ring_panos(lat,lng,45,4,key)[:candidates]):
        pm=maps.sv_metadata(plat,plng,10,key)
        if pm.get('status')!='OK':continue
        loc=pm['location'];heading=round(maps._bearing(loc['lat'],loc['lng'],lat,lng),1);image=work/f'candidate_{i}.png'
        if not image.exists():maps._get(maps.STREETVIEW,{'pano':pm['pano_id'],'heading':heading,'pitch':8,'fov':75,'size':'640x640','key':key},str(image))
        rows.append({'id':i,'file':str(image),'lat':loc['lat'],'lng':loc['lng'],'heading':heading,'pitch':8,'fov':75,'pano_id':pm['pano_id'],'date':pm.get('date')})
    _write(work/'candidates.json',rows)
    if not rows:
        result={'recovered':False,'reason':'No panorama candidates'};_write(work/'result.json',result);return result
    answer,usage=_ask('You are Img2City reference selection agent. Image 1 marks the EXACT OSM target footprint in red; remaining images are street candidates in order. Choose only a candidate that shows that target, not adjacent buildings. Return JSON {"selected":integer (-1 if none),"reason":string,"useful_evidence":[strings],"limitations":[strings],"refinement_guidance":[strings]}. Describe only observable target features. Ground the target correspondence in the red outline, street arrangement and candidate evidence; disclose occlusion.',{'building':meta,'candidates':rows},[str(work/'target_satellite.png')]+[r['file'] for r in rows],config.VISION_MODEL)
    _write(work/'selection.json',{'answer':answer,'usage':usage})
    selected=next((r for r in rows if r['id']==answer.get('selected')),None)
    if selected is None:
        result={'recovered':False,'reason':answer.get('reason')};_write(work/'result.json',result);return result
    for field in ['useful_evidence','limitations','refinement_guidance']:
        if not isinstance(answer.get(field),list) or not all(isinstance(v,str) for v in answer[field]):raise ValueError('invalid reference selection '+field)
    backup=work/'before';backup.mkdir(exist_ok=True)
    for name in ['spec.json','gate.json','streetview.png','satellite.png','pano.json','colors.json','facade_facts.json','typology.json','reference_audit.json']:
        if (bdir/name).exists():shutil.copy2(bdir/name,backup/name)
    shutil.copy2(selected['file'],bdir/'streetview.png')
    for name in ['satellite.png','target_satellite.png']:shutil.copy2(work/name,bdir/name)
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    _write(bdir/'pano.json',[selected[k] for k in ['lat','lng','heading','fov','pitch']])
    _write(bdir/'image_camera.json',dict(selected,image_sha256=sha(bdir/'streetview.png')))
    _write(bdir/'satellite_camera.json',{'center':[lat,lng],'zoom':19,'logical_size':[640,640],'scale':2,'image_sha256':sha(bdir/'satellite.png')})
    _write(bdir/'reference_audit.json',dict(identity='supported',camera_verified=False,model=config.VISION_MODEL,
        images={name:sha(bdir/name) for name in ['streetview.png','satellite.png','target_satellite.png']},
        **{k:answer[k] for k in ['useful_evidence','limitations','refinement_guidance']}))
    for name in ['spec.json','gate.json','colors.json','facade_facts.json','typology.json']:
        (bdir/name).unlink(missing_ok=True)
    result={'recovered':True,'reason':answer.get('reason')};_write(work/'result.json',result);return result


def main():
    import argparse
    from concurrent.futures import ThreadPoolExecutor,as_completed
    from img2city.city.quality import _write
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args();out=Path(args.out);data=json.loads((out/'buildings.json').read_text());todo=[]
    for m in data['buildings']:
        gate=out/'buildings'/str(m['id'])/'gate.json'
        if m['area_m2']>=40 and gate.exists() and json.loads(gate.read_text()).get('fallback'):todo.append(m)
    results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(recover,m,data['anchor'],out/'buildings'/str(m['id'])):m for m in todo}
        for future in as_completed(futures):
            m=futures[future]
            try:result=dict(id=m['id'],**future.result())
            except Exception as exc:result={'id':m['id'],'recovered':False,'error':str(exc)}
            results.append(result);_write(out/'recovery_report.json',results)
            print(f"[recovery] {len(results)}/{len(todo)} {m['id']}: {result.get('recovered')}",flush=True)


if __name__=='__main__':main()
