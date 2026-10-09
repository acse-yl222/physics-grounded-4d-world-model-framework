"""Copy a selected retained city-field presentation to a Pages checkout; never push."""
import argparse,json,shutil
from pathlib import Path
from common.export import digest,write
from common.storage import Storage
from common.contract import validate


def package(site,run_id):
    root=Storage.load().run('tower_hamlets',run_id);validate(root/'manifest.json')
    target=Path(site)/'scenes/tower_hamlets';physics=target/'physics027'
    if physics.exists():raise FileExistsError('Versioned physics destination already exists')
    old=json.loads((target/'scene.json').read_text());new=json.loads((root/'scene.json').read_text())
    if digest(root/new['model']['url'])!='222971c42f355f43bf983614b0bf689d43dea2bc91b7d5e3285573cc82de55ec':raise ValueError('Unexpected geometry change')
    new['model']['parts_manifest']=old['model']['parts_manifest'];new['traffic']=old['traffic'];new['physics_dir']='physics027/'
    shutil.copytree(root/'physics',physics)
    write(target/'scene.json',new)
    write(physics/'publication.json',{'source_run':run_id,'source_manifest_sha256':digest(root/'manifest.json'),'assets':[{'path':str(p.relative_to(physics)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(physics.rglob('*')) if p.is_file()]})
    write(target/'publication.json',{'source_run':run_id,'source_manifest_sha256':digest(root/'manifest.json'),'assets':[{'path':str(p.relative_to(target)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(target.rglob('*')) if p.is_file() and p!=target/'publication.json']})
    ignore=Path(site)/'.gitignore';ignore.write_text(ignore.read_text()+'\n# Recorded Canary near-ground scenario fields\n!scenes/tower_hamlets/physics027/**/*.npy\n!scenes/tower_hamlets/physics027/*.npy\n')
    print('Prepared versioned physics027 assets; geometry, traffic and UAV exports preserved.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('site',type=Path);p.add_argument('--run',default='canary_wharf_city_fields027');a=p.parse_args();package(a.site,a.run)
