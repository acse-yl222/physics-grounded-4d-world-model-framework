"""Copy only public framework viewer assets into an existing legacy Pages checkout.

Create that checkout from the last published site revision, then run this script.
Never copies project data, local configuration, cache, or recovery history.
"""
import argparse
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args();target=args.destination.resolve()
    if target==ROOT or not (target/'viewer/3d/index.html').is_file():
        parser.error('Destination must be a separate checkout containing the published legacy site')
    for name in ('viewer','widgets','shared','vendor'):
        shutil.copytree(ROOT/'src/visualization'/name,target/'src/visualization'/name,dirs_exist_ok=True)
    shutil.copytree(ROOT/'examples',target/'examples',dirs_exist_ok=True)
    (target/'.nojekyll').touch()
    ignore=target/'.gitignore';rules=ignore.read_text() if ignore.exists() else ''
    exception='!examples/contract-v1.1/*.npy'
    if exception not in rules:ignore.write_text(rules+'\n# Tiny public protocol fixtures\n'+exception+'\n')
    # The former demo routes remain available, with their already-public assets.
    redirect='<!doctype html><meta charset="utf-8"><title>Physics-Grounded 4D World Model Framework</title><meta http-equiv="refresh" content="0; url=src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json"><a href="src/visualization/viewer/?manifest=../../../examples/contract-v1/manifest.json">Open unified viewer</a> · <a href="viewer/3d/">Previous city demo</a>\n'
    (target/'index.html').write_text(redirect)
    print(f'Built public viewer at {target}; existing legacy routes preserved.')

if __name__=='__main__':main()
