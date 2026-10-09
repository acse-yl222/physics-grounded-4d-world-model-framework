"""Select versioned, encoded city fields for Pages without publishing solver arrays."""
import argparse,json,shutil
from pathlib import Path
from common.storage import Storage
from common.export import digest,write
from common.contract import validate

def package(site,run_id,version):
    root=Storage.load().run('tower_hamlets',run_id);validate(root/'manifest.json')
    site=Path(site);target=site/'scenes/tower_hamlets';dest=target/version
    if dest.exists():raise FileExistsError(dest)
    old=json.loads((target/'scene.json').read_text());new=json.loads((root/'scene.json').read_text())
    if digest(root/new['model']['url'])!='222971c42f355f43bf983614b0bf689d43dea2bc91b7d5e3285573cc82de55ec':raise ValueError('Unexpected geometry mutation')
    index=json.loads((root/'physics/web/index.json').read_text())
    for key,layer in new['layers'].items():
        keys=['solar_'+d for d in layer['dates']] if key=='solar' else [key]
        for k in keys:
            if index['layers'][k]['frames']!=layer['frames']:raise ValueError('Incomplete encoded '+k)
    shutil.copytree(root/'physics/web',dest/'web');(dest/'masks').mkdir()
    reused=[];mask_paths={}
    for src in (root/'physics/masks').iterdir():
        rel='masks/'+src.name;prior=target/'physics027'/rel
        if prior.is_file() and digest(src)==digest(prior):
            mask_paths[rel]='../physics027/'+rel;reused.append({'path':mask_paths[rel],'sha256':digest(prior)})
        else:shutil.copy2(src,dest/rel)
    def replace_paths(value):
        if isinstance(value,dict):return {k:replace_paths(v) for k,v in value.items()}
        if isinstance(value,list):return [replace_paths(v) for v in value]
        return mask_paths.get(value,value) if isinstance(value,str) else value
    new=replace_paths(new)
    shutil.copy2(root/'physics/manifest.json',dest/'manifest.json')
    new['model']['parts_manifest']=old['model']['parts_manifest'];new['traffic']=old['traffic'];new['physics_dir']=version+'/'
    new['limits'].append('Browser fields use declared PNG quantization; complete scientific float32 outputs remain in retained runs.')
    write(target/'scene.json',new)
    write(dest/'publication.json',{'source_run':run_id,'source_manifest_sha256':digest(root/'manifest.json'),'browser_encoding':index['encoding'],'reused_masks':reused,'assets':[{'path':str(p.relative_to(dest)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(dest.rglob('*')) if p.is_file()]})
    write(target/'publication.json',{'source_run':run_id,'source_manifest_sha256':digest(root/'manifest.json'),'assets':[{'path':str(p.relative_to(target)),'bytes':p.stat().st_size,'sha256':digest(p)}for p in sorted(target.rglob('*'))if p.is_file()and p!=target/'publication.json']})
    with (site/'.gitignore').open('a') as f:f.write(f'\n# Selected {version} masks\n!scenes/tower_hamlets/{version}/masks/*.npy\n')
    print(dest)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('site');p.add_argument('--run',required=True);p.add_argument('--version',required=True);a=p.parse_args();package(a.site,a.run,a.version)
