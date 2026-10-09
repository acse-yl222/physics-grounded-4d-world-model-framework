"""Validate/retain completed wind029 and prepare its100-frame display; never publish."""
import json,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
from common.storage import Storage
from common.export import write,digest
from common.contract import validate
from common.recorded_city_fields import prepare
from common.recorded_city_view import retain
from urban_flow.export.recorded_wind import package

ROOT=Path(__file__).resolve().parents[1]


def main():
    storage=Storage.load()
    # The inference runner records its explicit output path, independent of Storage category layout.
    config=ROOT/'project/tower_hamlets/configs/wind029_scaled.json';cfg=json.loads(config.read_text());raw=ROOT/cfg['output']
    meta=json.loads((raw/'metadata.json').read_text())
    if not meta.get('complete') or meta['sample_model_steps']!=list(range(1,101)):raise ValueError('100 completed genuine model steps required')
    heights=json.loads((raw/'sample_heights.json').read_text())
    samples=np.load(raw/'velocity_samples.npy',mmap_mode='r');mask=np.load(raw/'sample_invalid.npy').astype(bool);checks=[]
    if samples.shape[:3] != (100,3,len(heights)):raise ValueError('Expected100 independently decoded sampled frames')
    times=json.loads((raw/'sample_times_s.json').read_text())
    if times != [100*i for i in range(1,101)]:raise ValueError('Expected4x interpreted dt:100s')
    for i,a in enumerate(samples):
        if not np.isfinite(a).all() or np.any(a[:,mask]):raise ValueError('Invalid sampled frame: '+str(i+1))
        checks.append({'step':i+1,'finite':True,'solid_zero':True})
    final=np.load(raw/'velocity_final_enu.npy',mmap_mode='r')
    indices=[round((h-cfg['origin_enu_m'][2])/4-.5) for h in heights]
    if not np.array_equal(final[:,indices],samples[-1]):raise ValueError('Final samples differ from full output')
    write(raw/'completion_checks.json',{'passed':True,'frames':checks,'no_temporal_interpolation':True,'sample_sha256':digest(raw/'velocity_samples.npy'),'interpreted_dt_s':100})
    run_id='canary_wharf_wind4m029';wind=storage.run('tower_hamlets',run_id)
    if not wind.exists():
        geometry=storage.run('tower_hamlets','canary_wharf_geometry4m027')
        package(raw,config,raw/'metadata.json','tower_hamlets',run_id,'canary_wharf_geometry4m027',[ROOT/'src/urban_flow/scenarios/scaled_scene029.py',ROOT/'src/urban_flow/physics/wind/scaled_latent.py',Path(__file__)],retain=True,input_artifacts=[geometry/'full/solid.npy',geometry/'full/metadata.json'])
    validate(wind/'manifest.json')
    presentation=storage.scratch('tower_hamlets','city_presentation','canary_wharf_city_fields029');pcfg=ROOT/'project/tower_hamlets/configs/city_fields029.json'
    target=storage.run('tower_hamlets','canary_wharf_city_fields029')
    if not target.exists():
        if not presentation.exists():prepare(storage,pcfg,presentation)
        subprocess.run([sys.executable,str(ROOT/'src/visualization/adapters/legacy/shared/export_web_frames.py'),str(presentation),'--only=wind'],check=True,cwd=ROOT)
        data=np.load(presentation/'physics/wind.npy',mmap_mode='r');lo,hi=-2.5,2.5;clipped=0;worst=0.;png_hashes=[]
        for i,frame in enumerate(data):
            p=presentation/'physics/web/wind'/f'{i:03d}.png';pixels=np.asarray(Image.open(p)).transpose(2,0,1)
            expected=np.clip(np.round((frame-lo)/(hi-lo)*255),0,255).astype('u1')
            if not np.array_equal(pixels,expected):raise ValueError('RGB encoder differs from SouthKen mapping')
            decoded=lo+pixels.astype('f4')/255*(hi-lo);worst=max(worst,float(np.max(np.abs(decoded-frame))));clipped+=int(np.count_nonzero((frame<lo)|(frame>hi)));png_hashes.append(digest(p))
        write(presentation/'browser_encoding_check.json',{'passed':True,'frames':100,'component_range':[lo,hi],'max_component_error_m_s':worst,'clipped_components':clipped,'unique_png_frames':len(set(png_hashes)),'scientific_float32_unchanged':True})
        retain(storage,'tower_hamlets',presentation,'canary_wharf_city_fields029')
    validate(target/'manifest.json')
    write(raw/'ready_for_review.json',{'status':'ready_for_browser_review_not_published','wind_run':str(wind),'presentation_run':str(target),'defaults_changed':False,'public_site_changed':False})
    print(target,flush=True)

if __name__=='__main__':main()
