"""Copy only public framework viewer assets into an existing legacy Pages checkout.

Create that checkout from the last published site revision, then run this script.
Never copies project data, local configuration, cache, or recovery history.
"""
import argparse
import json
import re
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]

def windfarm_resources(catalog):
    """Derive immutable resource URLs from the same catalogue shown by the homepage."""
    scenes=[scene for scene in catalog['scenes'] if scene['scene_id']=='windfarm']
    if len(scenes)!=1:
        raise ValueError('Exactly one windfarm catalogue entry is required')
    base=catalog['resources_url'].rstrip('/')+'/'
    def version(category):
        prefix=f'windfarm_{category}_'
        matches=[key[len(prefix):] for key in scenes[0]['resource_ids'] if key.startswith(prefix)]
        if len(matches)!=1 or not re.fullmatch(r'[a-z][a-z0-9_]*',matches[0]):
            raise ValueError(f'Expected one canonical windfarm {category} version')
        return matches[0]
    return {'data_base':base+'project/windfarm/runs/'+version('runs')+'/',
            'model':base+'project/windfarm/geometry/'+version('geometry')+'/region.glb'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args();target=args.destination.resolve()
    if target==ROOT or not (target/'viewer/3d/index.html').is_file():
        parser.error('Destination must be a separate checkout containing the published legacy site')
    for name in ('viewer','widgets','shared','vendor','portal'):
        shutil.copytree(ROOT/'src/visualization'/name,target/'src/visualization'/name,dirs_exist_ok=True)
    shutil.copytree(ROOT/'examples',target/'examples',dirs_exist_ok=True)
    (target/'.nojekyll').touch()
    ignore=target/'.gitignore';rules=ignore.read_text() if ignore.exists() else ''
    exception='!examples/contract-v1.1/*.npy'
    if exception not in rules:ignore.write_text(rules+'\n# Tiny public protocol fixtures\n'+exception+'\n')
    shutil.copytree(ROOT/'src/visualization/published-pages',target,dirs_exist_ok=True)
    shutil.copy2(ROOT/'index.html',target/'index.html')
    shutil.copy2(ROOT/'src/visualization/legacy/serve.py',target/'serve.py')
    catalog=json.loads((ROOT/'src/visualization/public-scenes.json').read_text())
    for scene in catalog['scenes']:
        scene['viewer_url']=scene['viewer_url'].removeprefix('src/visualization/legacy/')
    (target/'src/visualization/public-scenes.json').write_text(json.dumps(catalog,indent=2)+'\n')
    base=catalog['resources_url'].rstrip('/')+'/'
    for old,canonical in [('south_kensington','south_ken/geometry/models_v1'),('white_city','white_city/geometry/white_city_v2')]:
        path=target/'scenes'/old/'scene.json'
        data=json.loads(path.read_text());data['model']['parts_manifest']=base+'project/'+canonical+'/manifest.json'
        path.write_text(json.dumps(data,indent=2)+'\n')
    for name in ('scene-navigation.js','bootstrap.js','model-source.js'):
        shutil.copy2(ROOT/'src/visualization/legacy/viewer'/name,target/'viewer'/name)
    for name in ('index.html','main.js','style.css','replay.js'):
        shutil.copy2(ROOT/'src/visualization/legacy/viewer/3d'/name,target/'viewer/3d'/name)
    movie=target/'viewer/windfarm-movie'
    shutil.copytree(ROOT/'src/visualization/legacy/viewer/windfarm-movie',movie,dirs_exist_ok=True)
    (movie/'resources.json').write_text(json.dumps(windfarm_resources(catalog),indent=2)+'\n')
    print(f'Built public viewer at {target}; existing legacy routes preserved.')

if __name__=='__main__':main()
