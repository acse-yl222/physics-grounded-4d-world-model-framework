"""Capture the exact source checkout used by a trial without including private data."""
from pathlib import Path
import subprocess
import tarfile

SOURCE_SUFFIXES={'.py','.js','.mjs','.cjs','.json','.sh','.toml','.yaml','.yml','.md'}


def snapshot_sources(root,destination):
    root=Path(root);destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(destination,'w:gz') as archive:
        for folder in ('src','schemas'):
            for path in sorted((root/folder).rglob('*')):
                if path.is_file() and not path.is_symlink() and path.suffix in SOURCE_SUFFIXES and '__pycache__' not in path.parts:
                    archive.add(path,arcname=str(path.relative_to(root)),recursive=False)
        for name in ('pyproject.toml','AGENTS.md'):
            path=root/name
            if path.exists():archive.add(path,arcname=name,recursive=False)
    result=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True)
    return result.stdout.strip() if result.returncode==0 else 'unversioned-checkout'
