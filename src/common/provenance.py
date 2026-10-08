"""Capture the exact source checkout used by a trial without including private data."""
from pathlib import Path
import subprocess
import tarfile
from .locations import code_path, resource_path, checkout_root

SOURCE_SUFFIXES={'.py','.js','.mjs','.cjs','.json','.sh','.toml','.yaml','.yml','.md'}


def snapshot_sources(root,destination):
    root=Path(root);destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(destination,'w:gz') as archive:
        sources = [(f'src/{name}', code_path(f'src/{name}')) for name in
                   ('common', 'urban_geometry', 'urban_flow', 'traffic', 'uav_routing', 'visualization/adapters')]
        for folder, base in [*sources, ('schemas', resource_path('schemas'))]:
            for path in sorted(base.rglob('*')):
                if path.is_file() and not path.is_symlink() and path.suffix in SOURCE_SUFFIXES and '__pycache__' not in path.parts and 'resources' not in path.relative_to(base).parts:
                    archive.add(path,arcname=str(Path(folder)/path.relative_to(base)),recursive=False)
        for name in ('pyproject.toml','AGENTS.md'):
            path=(checkout_root() or root)/name
            if path.exists():archive.add(path,arcname=name,recursive=False)
    checkout = checkout_root()
    if checkout is None:
        return 'installed-package'
    result=subprocess.run(['git','-C',str(checkout),'rev-parse','HEAD'],capture_output=True,text=True)
    return result.stdout.strip() if result.returncode==0 else 'unversioned-checkout'
